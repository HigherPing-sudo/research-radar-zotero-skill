#!/usr/bin/env python3
"""Resolve an explicit daily paper and safely link an existing reading note."""
import argparse
from datetime import date
import json
from pathlib import Path
import re
import sys
import tempfile

from zotero_inspect import snapshot, attachment_path, normalize_doi, normalize_title


def frontmatter(text):
    """Read the scalar identity fields; complex YAML is left to the host."""
    lines = text.lstrip('\ufeff').splitlines()
    if not lines or lines[0] != '---':
        return {}
    result = {}
    for line in lines[1:]:
        if line == '---':
            break
        match = re.fullmatch(r'([A-Za-z_]+):[ \t]*(.*)', line)
        if not match:
            continue
        key, value = match.groups()
        if value.startswith('"'):
            value = json.JSONDecoder().raw_decode(value)[0]
        elif value.startswith("'") and value.endswith("'"):
            value = value[1:-1].replace("''", "'")
        else:
            value = value.split(' #', 1)[0].strip()
        result[key] = value
    return result


def inside(root, value):
    target = (root / value).resolve()
    if not target.is_relative_to(root):
        raise ValueError('Configured path escapes the project')
    return target


def paper_span(text, number):
    lines = text.splitlines(keepends=True)
    starts, fence = [], None
    for i, line in enumerate(lines):
        marker = re.match(r'^ {0,3}(`{3,}|~{3,})(.*)', line.rstrip('\r\n'))
        if fence:
            if marker and marker[1][0] == fence[0] and len(marker[1]) >= fence[1] and not marker[2].strip():
                fence = None
            continue
        if marker:
            fence = (marker[1][0], len(marker[1]))
            continue
        heading = re.fullmatch(r'### Paper (\d+)[ \t]*\r?\n?', line)
        if heading and int(heading[1]) == number:
            starts.append(i)
        elif re.match(r'^#{1,3} ', line):
            starts.append(('end', i))
    matches = [i for i in starts if isinstance(i, int)]
    if len(matches) != 1:
        raise ValueError('Paper heading missing or ambiguous')
    start = matches[0]
    end = next((x[1] for x in starts if isinstance(x, tuple) and x[1] > start), len(lines))
    # A duplicate requested heading was already rejected above.
    return lines, start, end


def filename(day, number, title):
    safe = re.sub(r'[<>:"/\\|?*\[\]#\x00-\x1f\x7f]', '-', title)
    safe = re.sub(r'\s+', ' ', safe).strip(' .-') or 'Untitled'
    prefix = f'{day}-Paper{number}-'
    while len((prefix + safe).encode('utf-16-le')) // 2 > 160:
        safe = safe[:-1]
    return prefix + safe.rstrip(' .') + '.md'


def load_target(project, day, number):
    if date.fromisoformat(day).isoformat() != day or number < 1:
        raise ValueError('Use YYYY-MM-DD and a positive paper number')
    root = Path(project).expanduser().resolve()
    cfgpath = root / 'research-radar.local.json'
    config = json.loads(cfgpath.read_text(encoding='utf-8-sig')) if cfgpath.exists() else {}
    daily = inside(root, config.get('daily_directory', 'Daily Papers')) / (day + '.md')
    raw = daily.read_bytes()
    text = raw.decode('utf-8-sig')
    actual_date = frontmatter(text).get('date')
    if actual_date and actual_date != day:
        raise ValueError('Daily frontmatter date does not match requested date')
    lines, start, end = paper_span(text, number)
    block = ''.join(lines[start:end])
    metadata_lines, fence = [], None
    for line in block.splitlines():
        marker=re.match(r'^ {0,3}(`{3,}|~{3,})(.*)',line)
        if fence:
            if marker and marker[1][0]==fence[0] and len(marker[1])>=fence[1] and not marker[2].strip(): fence=None
            continue
        if marker:
            fence=(marker[1][0],len(marker[1]))
            continue
        metadata_lines.append(line)
    metadata='\n'.join(metadata_lines)
    def field(name):
        match = re.search(r'^-[ \t]+\*\*' + re.escape(name) + r'[:：]\*\*[ \t]*(.*)$', metadata, re.M)
        return match[1].strip() if match else ''
    title = field('Title')
    if not title:
        raise ValueError('The selected paper has no title')
    doi_match = re.search(r'10\.\d{4,9}/[^\s)\]>]+', field('DOI'))
    arxiv_match = re.search(r'(\d{4}\.\d{4,5})(?:v\d+)?', field('arXiv ID'))
    def uri(name, route):
        match = re.search(r'zotero://' + route + r'/(?:library|groups/\d+)/items/[A-Z0-9]{8}(?![A-Z0-9])', field(name))
        return match[0] if match else None
    item_uri = uri('Zotero 文献', 'select')
    pdf_uri = uri('Zotero PDF', 'open-pdf')
    note_root = inside(root, config.get('note_directory', 'Note'))
    existing = []
    if note_root.exists():
        for note in note_root.rglob('*.md'):
            meta = frontmatter(note.read_text(encoding='utf-8-sig'))
            if meta.get('type') == 'literature' and str(meta.get('source_date')) == day and str(meta.get('paper_number')) == str(number):
                existing.append(note)
    if len(existing) > 1:
        raise ValueError('Multiple reading notes match the same daily paper')
    existing_meta = frontmatter(existing[0].read_text(encoding='utf-8-sig')) if existing else {}
    if existing and normalize_title(existing_meta.get('title')) != normalize_title(title):
        raise ValueError('Existing note title differs from this daily paper')
    output = existing[0] if existing else note_root / filename(day, number, title)
    if output.exists() and not existing:
        raise ValueError('Suggested output already exists with a different or missing identity')
    prefix = config.get('obsidian_project_path', '').strip('/')
    def vault_path(path):
        return '/'.join(s for s in [prefix, path.relative_to(root).with_suffix('').as_posix()] if s)
    decision = re.search(r'^\s*-\s*\[([xX ])\][ \t]*进行精读[ \t]*$', metadata, re.M)
    note_status = 'done' if str(existing_meta.get('template', '')).lower() == 'true' else existing_meta.get('status')
    result = {
        'source_date':day, 'paper_number':number, 'title':title, 'authors':field('Authors'),
        'published':field('Published'), 'reading_status':note_status or field('阅读状态') or 'unread',
        'deep_read_requested':decision[1].lower() == 'x' if decision else None,
        'doi':normalize_doi(doi_match[0]) if doi_match else None,
        'arxiv_id':arxiv_match[1] if arxiv_match else None,
        'daily_path':str(daily), 'source_daily':f'[[{vault_path(daily)}#Paper {number}]]',
        'zotero_item_url':item_uri, 'zotero_pdf_url':pdf_uri,
        'zotero_item_key':item_uri.rsplit('/',1)[-1] if item_uri else None,
        'zotero_pdf_key':pdf_uri.rsplit('/',1)[-1] if pdf_uri else None,
        'note_path':str(output), 'note_exists':bool(existing),
        'note_wikilink':f'[[{vault_path(output)}]]', 'paper_block':block,
        'pdf':{'status':'not_checked','content_verified':False},
    }
    return root, config, daily, raw, lines, start, end, result


def resolve(project, day, number):
    root, config, daily, raw, lines, start, end, result = load_target(project, day, number)
    data_dir = config.get('zotero', {}).get('data_dir')
    if data_dir and result['zotero_item_key'] and result['zotero_pdf_key'] and '/library/items/' in result['zotero_item_url'] and '/library/items/' in result['zotero_pdf_url']:
        try:
            with snapshot(data_dir) as (db, data_root):
                row = db.execute('''SELECT a.path,a.contentType,p.key,p.libraryID FROM itemAttachments a
                    JOIN items i ON i.itemID=a.itemID JOIN items p ON p.itemID=a.parentItemID
                    WHERE i.key=? AND p.key=? AND i.itemID NOT IN (SELECT itemID FROM deletedItems)
                    AND p.itemID NOT IN (SELECT itemID FROM deletedItems)''',
                    (result['zotero_pdf_key'], result['zotero_item_key'])).fetchall()
                if len(row) != 1 or row[0][1] != 'application/pdf':
                    raise ValueError('Attachment/parent identity missing or ambiguous')
                library_type=db.execute('SELECT type FROM libraries WHERE libraryID=?',(row[0][3],)).fetchone()
                if not library_type or library_type[0]!='user':
                    raise ValueError('Library URI does not match a personal library')
                stored_doi=db.execute('''SELECT v.value FROM itemData d JOIN items i ON i.itemID=d.itemID
                    JOIN fields f ON f.fieldID=d.fieldID JOIN itemDataValues v ON v.valueID=d.valueID
                    WHERE i.key=? AND i.libraryID=? AND f.fieldName='DOI' ''',(result['zotero_item_key'],row[0][3])).fetchone()
                if result['doi'] and stored_doi and normalize_doi(stored_doi[0])!=result['doi']:
                    raise ValueError('Zotero parent DOI differs from daily paper')
                path = attachment_path(data_root,result['zotero_pdf_key'],row[0][0],config.get('zotero',{}).get('attachment_base'))
                if not path or not path.is_file():
                    raise ValueError('Local PDF missing')
                with path.open('rb') as stream:
                    if stream.read(5) != b'%PDF-':
                        raise ValueError('Invalid PDF header')
                result['pdf']={'status':'local_available','path':str(path),'parent_verified':True,'content_verified':False}
        except Exception as error:
            result['pdf']={'status':'unverified','reason':str(error),'content_verified':False}
    return result


def link(project, day, number, note_path):
    root, config, daily, raw, lines, start, end, result = load_target(project, day, number)
    note = inside(root,note_path)
    note_root = inside(root,config.get('note_directory','Note'))
    if not note.is_relative_to(note_root):
        raise ValueError('Reading note must be inside note_directory')
    meta = frontmatter(note.read_text(encoding='utf-8-sig'))
    if not (meta.get('type')=='literature' and str(meta.get('source_date'))==day and str(meta.get('paper_number'))==str(number)
            and normalize_title(meta.get('title'))==normalize_title(result['title'])):
        raise ValueError('Reading note identity differs from daily paper')
    if note.resolve() != Path(result['note_path']).resolve():
        raise ValueError('A different reading note is already associated')
    prefix=config.get('obsidian_project_path','').strip('/')
    target='/'.join(x for x in [prefix,note.relative_to(root).with_suffix('').as_posix()] if x)
    if re.search(r'[\[\]|#\r\n]',target):
        raise ValueError('Note path cannot be represented as an unambiguous Wikilink')
    expected=f'- **精读笔记:** [[{target}]]'
    links=[i for i in range(start,end) if re.match(r'^- \*\*精读笔记[:：]\*\*',lines[i])]
    if links:
        if len(links)!=1 or lines[links[0]].strip()!=expected:
            raise ValueError('Existing reading-note link conflicts; preserve it for review')
        return {'changed':False,'note_wikilink':f'[[{target}]]'}
    newline='\r\n' if b'\r\n' in raw else '\n'
    insert=next((i+1 for i in range(start,end) if lines[i].startswith('- **Zotero PDF:')),start+1)
    lines.insert(insert,expected+newline)
    encoded=''.join(lines).encode('utf-8')
    if raw.startswith(b'\xef\xbb\xbf'):
        encoded=b'\xef\xbb\xbf'+encoded
    pending = None
    try:
        with tempfile.NamedTemporaryFile(
            mode='wb', dir=daily.parent, prefix=f'.{daily.name}.', suffix='.pending', delete=False
        ) as stream:
            pending = Path(stream.name)
            stream.write(encoded)
        if daily.read_bytes() != raw:
            raise ValueError('Daily changed during linking; retry after re-reading')
        pending.replace(daily)
    finally:
        if pending is not None:
            pending.unlink(missing_ok=True)
    return {'changed':True,'note_wikilink':f'[[{target}]]'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest='command',required=True)
    for name in ['resolve','link']:
        sub=commands.add_parser(name)
        sub.add_argument('--project',required=True)
        sub.add_argument('--date',required=True)
        sub.add_argument('--paper',type=int,required=True)
        if name=='link': sub.add_argument('--note',required=True)
    args=parser.parse_args()
    try:
        result=resolve(args.project,args.date,args.paper) if args.command=='resolve' else link(args.project,args.date,args.paper,args.note)
        print(json.dumps(result,ensure_ascii=False,indent=2))
    except (ValueError,OSError,json.JSONDecodeError) as error:
        print(json.dumps({'error':str(error),'safe_to_create_note':False},ensure_ascii=False))
        return 1
    return 0


if __name__=='__main__':
    sys.exit(main())
