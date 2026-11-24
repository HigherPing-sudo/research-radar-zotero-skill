import json
from contextlib import contextmanager
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import reading_target as rt


class ReadingTargetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        (self.root/'Daily Papers').mkdir()
        (self.root/'Note').mkdir()
        self.config={'obsidian_project_path':'Research Radar'}
        self.daily=self.root/'Daily Papers/2026-10-22.md'
        self.text='''---
date: 2026-10-22
---
# Daily
```markdown
### Paper 2
- **Title:** Wrong fenced example
```
## Recommendations
### Paper 1
- **Title:** First paper
### Paper 2
- **Title:** Exact: Raman / Paper?
- **DOI:** [10.1000/real](https://doi.org/10.1000/real)
- **Zotero 文献:** [item](zotero://select/library/items/PARENT01)
- **Zotero PDF:** [pdf](zotero://open-pdf/library/items/PDFKEY01)
- **阅读状态:** unread
#### Further Reading Decision
- [x] 暂不处理
- **我的判断 / 下一步：** Keep my text.
### Paper 3
- **Title:** Third paper
## Summary
Keep summary.
'''
        self.daily.write_bytes(self.text.replace('\n','\r\n').encode())
        self.save_config()

    def save_config(self):
        (self.root/'research-radar.local.json').write_text(json.dumps(self.config),encoding='utf-8')

    def make_note(self, name=None, **updates):
        result=rt.resolve(self.root,'2026-10-22',2)
        path=Path(result['note_path']) if name is None else self.root/'Note'/name
        meta={'type':'literature','title':result['title'],'source_date':'2026-10-22','paper_number':2,'status':'reading'}
        meta.update(updates)
        path.write_text('---\n'+'\n'.join(f'{k}: {json.dumps(v,ensure_ascii=False)}' for k,v in meta.items())+'\n---\n\n# Analysis\n\nMy annotation.\n',encoding='utf-8')
        return path

    def test_exact_number_and_fence_scope(self):
        r=rt.resolve(self.root,'2026-10-22',2)
        self.assertEqual(r['title'],'Exact: Raman / Paper?')
        self.assertEqual(r['doi'],'10.1000/real')
        self.assertNotIn('Third paper',r['paper_block'])
        self.assertEqual(r['source_daily'],'[[Research Radar/Daily Papers/2026-10-22#Paper 2]]')
        self.assertEqual(r['zotero_pdf_key'],'PDFKEY01')

    def test_invalid_dates_and_missing_number_stop(self):
        for day,num in [('2026-02-30',2),('2026-10-22',0),('2026-10-22',8)]:
            with self.subTest(day=day,num=num),self.assertRaises(ValueError):
                rt.resolve(self.root,day,num)

    def test_duplicate_heading_stops(self):
        self.daily.write_text(self.text+'\n### Paper 2\n- **Title:** Duplicate\n')
        with self.assertRaises(ValueError): rt.resolve(self.root,'2026-10-22',2)

    def test_empty_title_does_not_consume_next_field(self):
        self.daily.write_text(self.text.replace('Exact: Raman / Paper?',''))
        with self.assertRaises(ValueError): rt.resolve(self.root,'2026-10-22',2)

    def test_metadata_inside_fenced_example_is_ignored(self):
        self.daily.write_text(self.text.replace('- **DOI:** [10.1000/real](https://doi.org/10.1000/real)', '```md\n- **DOI:** [10.1000/fake](https://doi.org/10.1000/fake)\n```'))
        self.assertIsNone(rt.resolve(self.root,'2026-10-22',2)['doi'])

    def test_wrong_daily_frontmatter_date_stops(self):
        self.daily.write_text(self.text.replace('date: 2026-10-22','date: 2026-10-21'))
        with self.assertRaises(ValueError): rt.resolve(self.root,'2026-10-22',2)

    def test_safe_unicode_filename(self):
        result=rt.filename('2026-10-22',2,'试验😀<>:"/\\|?*[]#'+('长'*300))
        self.assertLessEqual(len(result.encode('utf-16-le'))//2,163)
        self.assertNotRegex(result,r'[<>:"/\\|?*\[\]#]')
        self.assertTrue(result.startswith('2026-10-22-Paper2-'))

    def test_link_preserves_every_other_byte_and_is_idempotent(self):
        note=self.make_note()
        before=self.daily.read_bytes()
        note_before=note.read_bytes()
        result=rt.link(self.root,'2026-10-22',2,str(note.relative_to(self.root)))
        after=self.daily.read_bytes()
        added=('- **精读笔记:** '+result['note_wikilink']+'\r\n').encode()
        self.assertEqual(after.replace(added,b''),before)
        self.assertEqual(note.read_bytes(),note_before)
        self.assertFalse(rt.link(self.root,'2026-10-22',2,str(note.relative_to(self.root)))['changed'])
        self.assertEqual(self.daily.read_bytes(),after)

    def test_checked_note_is_reused_linked_and_preserved(self):
        note=self.make_note(template=True)
        before=note.read_bytes()
        result=rt.resolve(self.root,'2026-10-22',2)
        self.assertTrue(result['note_exists'])
        self.assertEqual(Path(result['note_path']),note)
        self.assertEqual(result['reading_status'],'done')
        self.assertTrue(rt.link(self.root,'2026-10-22',2,str(note.relative_to(self.root)))['changed'])
        self.assertFalse(rt.link(self.root,'2026-10-22',2,str(note.relative_to(self.root)))['changed'])
        self.assertEqual(note.read_bytes(),before)

    def test_link_preserves_preexisting_pending_hard_link(self):
        note = self.make_note()
        with tempfile.TemporaryDirectory() as outside:
            unrelated = Path(outside) / 'unrelated.txt'
            original = b'Unrelated file contents'
            unrelated.write_bytes(original)
            pending = self.daily.with_name(self.daily.name + '.pending')
            os.link(unrelated, pending)

            result = rt.link(self.root, '2026-10-22', 2, str(note.relative_to(self.root)))

            self.assertTrue(result['changed'])
            self.assertEqual(unrelated.read_bytes(), original)
            self.assertEqual(pending.read_bytes(), original)
            self.assertCountEqual(self.daily.parent.iterdir(), [self.daily, pending])

    def test_link_cleans_temporary_file_when_replacement_fails(self):
        note = self.make_note()
        before = self.daily.read_bytes()
        with patch.object(Path, 'replace', side_effect=OSError('Replacement failed')):
            with self.assertRaisesRegex(OSError, 'Replacement failed'):
                rt.link(self.root, '2026-10-22', 2, str(note.relative_to(self.root)))

        self.assertEqual(self.daily.read_bytes(), before)
        self.assertEqual(list(self.daily.parent.iterdir()), [self.daily])

    def test_link_preserves_daily_edited_while_writing_temporary_file(self):
        note = self.make_note()
        edited = self.daily.read_bytes() + b'Concurrent annotation\r\n'
        create_temp = rt.tempfile.NamedTemporaryFile

        @contextmanager
        def edit_after_write(*args, **kwargs):
            with create_temp(*args, **kwargs) as stream:
                yield stream
            self.daily.write_bytes(edited)

        with patch.object(rt.tempfile, 'NamedTemporaryFile', edit_after_write):
            with self.assertRaisesRegex(ValueError, 'Daily changed during linking'):
                rt.link(self.root, '2026-10-22', 2, str(note.relative_to(self.root)))

        self.assertEqual(self.daily.read_bytes(), edited)
        self.assertEqual(list(self.daily.parent.iterdir()), [self.daily])

    def test_unchecked_note_preserves_its_reading_status(self):
        self.make_note(template=False,status='reading')
        self.assertEqual(rt.resolve(self.root,'2026-10-22',2)['reading_status'],'reading')

    def test_deep_read_choice_and_fenced_example(self):
        self.assertIsNone(rt.resolve(self.root,'2026-10-22',2)['deep_read_requested'])
        for marker,expected in [('x',True),('X',True),(' ',False)]:
            with self.subTest(marker=marker):
                self.daily.write_text(self.text.replace('#### Further Reading Decision',f'- [{marker}] 进行精读\n#### Further Reading Decision'))
                self.assertIs(rt.resolve(self.root,'2026-10-22',2)['deep_read_requested'],expected)
        self.daily.write_text(self.text.replace('#### Further Reading Decision','```md\n- [x] 进行精读\n```\n#### Further Reading Decision'))
        self.assertIsNone(rt.resolve(self.root,'2026-10-22',2)['deep_read_requested'])

    def test_identity_conflict_never_overwrites(self):
        note=self.make_note(title='Different research')
        before=self.daily.read_bytes()
        with self.assertRaises(ValueError): rt.link(self.root,'2026-10-22',2,str(note))
        self.assertEqual(self.daily.read_bytes(),before)

    def test_existing_link_conflict_is_preserved(self):
        note=self.make_note()
        self.daily.write_text(self.text.replace('- **阅读状态:**','- **精读笔记:** [[Manual choice]]\n- **阅读状态:**'))
        before=self.daily.read_bytes()
        with self.assertRaises(ValueError): rt.link(self.root,'2026-10-22',2,str(note))
        self.assertEqual(self.daily.read_bytes(),before)

    def test_duplicate_notes_stop(self):
        self.make_note('first.md')
        # Write a second match without resolving again.
        (self.root/'Note/second.md').write_bytes((self.root/'Note/first.md').read_bytes())
        with self.assertRaises(ValueError): rt.resolve(self.root,'2026-10-22',2)

    def test_output_collision_stops(self):
        output=Path(rt.resolve(self.root,'2026-10-22',2)['note_path'])
        output.write_text('Personal unrelated note')
        with self.assertRaises(ValueError): rt.resolve(self.root,'2026-10-22',2)

    def test_config_cannot_escape_project(self):
        self.config['note_directory']='../outside'
        self.save_config()
        with self.assertRaises(ValueError): rt.resolve(self.root,'2026-10-22',2)

    def test_local_pdf_checks_parent_and_doi(self):
        data=self.root/'Zotero'
        (data/'storage/PDFKEY01').mkdir(parents=True)
        pdf=data/'storage/PDFKEY01/main.pdf'
        pdf.write_bytes(b'%PDF-fake-header-only')
        db=sqlite3.connect(data/'zotero.sqlite')
        self.addCleanup(db.close)
        db.executescript('''CREATE TABLE libraries(libraryID INTEGER,type TEXT);
            CREATE TABLE items(itemID INTEGER,key TEXT,libraryID INTEGER);
            CREATE TABLE itemAttachments(itemID INTEGER,parentItemID INTEGER,path TEXT,contentType TEXT);
            CREATE TABLE deletedItems(itemID INTEGER);
            CREATE TABLE itemData(itemID INTEGER,fieldID INTEGER,valueID INTEGER);
            CREATE TABLE fields(fieldID INTEGER,fieldName TEXT);
            CREATE TABLE itemDataValues(valueID INTEGER,value TEXT);
            INSERT INTO libraries VALUES(1,'user');
            INSERT INTO items VALUES(1,'PARENT01',1),(2,'PDFKEY01',1);
            INSERT INTO itemAttachments VALUES(2,1,'storage:main.pdf','application/pdf');
            INSERT INTO fields VALUES(1,'DOI');
            INSERT INTO itemDataValues VALUES(1,'10.1000/real');
            INSERT INTO itemData VALUES(1,1,1);''')
        db.commit()
        self.config['zotero']={'data_dir':str(data)}
        self.save_config()
        result=rt.resolve(self.root,'2026-10-22',2)
        self.assertEqual(result['pdf']['path'],str(pdf))
        self.assertFalse(result['pdf']['content_verified'])
        db.execute("UPDATE itemDataValues SET value='10.1000/wrong'")
        db.commit()
        self.assertEqual(rt.resolve(self.root,'2026-10-22',2)['pdf']['status'],'unverified')
        db.close()


if __name__=='__main__': unittest.main()
