const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const code=fs.readFileSync(path.join(__dirname,'../assets/daily-decisions-index.md'),'utf8').match(/```dataviewjs\s*([\s\S]*?)```/)[1];
const AsyncFunction=Object.getPrototypeOf(async function(){}).constructor;
const dailyPage={file:{name:'2026-10-22',path:'Research Radar/Daily Papers/2026-10-22.md'}};
const daily='### Paper 1\n- **Title:** Daily paper\n- [x] 值得进一步阅读\n- [x] 进行精读\n';
const personal={type:'literature',title:'Personal paper',source_date:'',paper_number:0,read_date:'2026-10-26',template:false,status:'reading',zotero_item_url:'zotero://select/library/items/PARENT01',zotero_pdf_url:'zotero://open-pdf/library/items/PDFKEY01',file:{name:'2026-10-26-personal',path:'Research Radar/Note/2026-10-26-personal.md'}};
function pages(values){const result=[...values];result.where=fn=>pages(values.filter(fn));result.sort=(fn,order)=>pages([...values].sort((a,b)=>String(fn(a)).localeCompare(String(fn(b)))*(order==='desc'?-1:1)));return result;}
async function render(notes){
  const tables=[],paragraphs=[];let heading='';
  const dv={pages:q=>pages(q.includes('Daily Papers')?[dailyPage]:notes),io:{load:async file=>file===dailyPage.file.path?daily:'[]'},paragraph:x=>paragraphs.push(x),header:(n,x)=>heading=x,table:(columns,rows)=>tables.push({heading,columns,rows}),fileLink:(p,e,t)=>({path:p,title:t})};
  await new AsyncFunction('dv',code)(dv);return {tables,paragraphs};
}
(async()=>{
  const realTemplate={type:'literature-template',template:true,file:{name:'template',path:'template.md'}};
  const sourced={...personal,title:'Daily paper',source_date:'2026-10-22',paper_number:1};
  let result=await render([personal,sourced,realTemplate]);
  assert(result.paragraphs[0].includes('共 2 篇'));
  const manual=result.tables.find(t=>t.heading.includes('自主精读'));
  assert.equal(manual.rows.length,1);assert.equal(manual.rows[0][0],'2026-10-26');assert.equal(manual.rows[0][2],'阅读中');
  assert.equal(manual.rows[0][1].path,'Research Radar/Note/2026-10-26-personal');
  assert(manual.rows[0][3].includes('PARENT01')&&manual.rows[0][3].includes('PDFKEY01'));
  assert.equal(result.tables.find(t=>t.heading.includes('值得进一步阅读')).rows.length,1);
  result=await render([{...personal,read_date:undefined,template:'true'}]);
  assert.equal(result.tables.find(t=>t.heading.includes('自主精读')).rows[0][0],'2026-10-26');
  assert.equal(result.tables.find(t=>t.heading.includes('自主精读')).rows[0][2],'已读');
  result=await render([{...personal,read_date:{toFormat:()=> '2026-10-25'},status:'done'}]);
  assert.equal(result.tables.find(t=>t.heading.includes('自主精读')).rows[0][0],'2026-10-25');
  result=await render([sourced,realTemplate]);assert(result.paragraphs[0].includes('共 1 篇'));
  assert(!result.tables.some(t=>t.heading.includes('自主精读')));
  console.log('Decisions index: personal notes, date fallback, Dataview dates, status, Zotero links, source deduplication and template exclusion passed');
})().catch(error=>{console.error(error);process.exitCode=1;});
