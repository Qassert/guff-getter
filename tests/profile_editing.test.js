const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const nodes={};
const keys=['sourceTitle','sourceBody','responseTitle','responseBody'];
for(const id of ['sourceTitleHeading','nonsenseBox','crazyTitleBox','crazyExtractBox','titleDescBox','loader',...keys.flatMap(k=>[k+'Editor',k+'Draft',k+'Edit'])]) {
 nodes[id]={value:'original',textContent:'...original...',hidden:false,style:{},classList:{remove(){},add(){}},setAttribute(k,v){this[k]=v;},focus(){this.focused=true;}};
}
const choices=['fetch_historicalFunny_from_api','fetch_wikipedia_into_api','fetch_poem_into_api','fetch_people_into_api'].map(source=>({dataset:{source},setAttribute(k,v){this[k]=v;}}));
let calls=0;
const ctx={console,document:{getElementById:id=>nodes[id],querySelectorAll:()=>choices},window:{addEventListener(){}},fetch(){calls++;return new Promise(()=>{});},setTimeout(){}};
vm.createContext(ctx);vm.runInContext(fs.readFileSync('newsmuncher/static/profile-editing.js','utf8')+'\nglobalThis.editor=profileEditing;',ctx);
vm.runInContext(fs.readFileSync('newsmuncher/static/script.js','utf8'),ctx);
for(const key of keys){
 const display={sourceTitle:'sourceTitleHeading',sourceBody:'nonsenseBox',responseTitle:'crazyTitleBox',responseBody:'crazyExtractBox'}[key];
 ctx.editor.edit(key);assert(nodes[key+'Draft'].focused);assert(nodes[display].hidden);
 nodes[key+'Draft'].value='cancelled';ctx.editor.cancel(key);assert.equal(nodes[display].value,'original');assert.equal(nodes[display].textContent,'...original...');assert(nodes[key+'Edit'].focused);
 ctx.editor.edit(key);nodes[key+'Draft'].value='<new & text>';ctx.editor.save(key);
 assert.equal(key.includes('Title')?nodes[display].textContent:nodes[display].value,key.includes('Title')?'...<new & text>...':'<new & text>');
 assert.equal(nodes[key+'Edit']['aria-expanded'],'false');
}
assert.equal(calls,0);
assert.equal(nodes.titleDescBox.value,'<new & text>');
for(const c of choices){ctx.fetchAndDisplay(c.dataset.source);assert.equal(choices.filter(b=>b['aria-pressed']==='true').length,1);assert.equal(c['aria-pressed'],'true');}
ctx.editor.edit('responseBody');ctx.editor.reset('response');assert.equal(nodes.responseBodyEditor.hidden,true);
console.log('Profile edits and exclusive source selection passed.');

let nominated=[];
ctx.fetch=(url,options)=>{nominated.push({url,body:JSON.parse(options.body)});return new Promise(()=>{});};
for(const key of keys) nodes[key+'Editor'].hidden=true;
ctx.bankThisBeauty();ctx.bankThisBeauty();
assert.equal(nominated.length,1);
assert.equal(nominated[0].url,'/temp/confirm_data');
assert.deepEqual(nominated[0].body,{crazyReplacement1Title:'<new & text>',crazyReplacement1Extract:'<new & text>'});
assert.equal(nodes.titleDescBox.value,'<new & text>');
console.log('Nomination captures edited response only and prevents duplicate in-flight requests.');
