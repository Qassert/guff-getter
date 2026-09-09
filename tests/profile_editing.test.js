const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const nodes={};
const keys=['source','response'];
for(const id of ['sourceTitleHeading','nonsenseBox','crazyTitleBox','crazyExtractBox','titleDescBox','loader',...keys.flatMap(k=>[k+'Editor',k+'Display',k+'TitleDraft',k+'BodyDraft',k+'Edit'])]) {
 nodes[id]={value:'original',textContent:'...original...',hidden:false,style:{},classList:{remove(){},add(){}},setAttribute(k,v){this[k]=v;},focus(){this.focused=true;}};
}
const choices=['fetch_historicalFunny_from_api','fetch_wikipedia_into_api','fetch_poem_into_api','fetch_people_into_api'].map(source=>({dataset:{source},setAttribute(k,v){this[k]=v;}}));
let calls=0;
const ctx={console,document:{getElementById:id=>nodes[id],querySelectorAll:()=>choices},window:{addEventListener(){}},fetch(){calls++;return new Promise(()=>{});},setTimeout(){}};
vm.createContext(ctx);vm.runInContext(fs.readFileSync('newsmuncher/static/profile-editing.js','utf8')+'\nglobalThis.editor=profileEditing;',ctx);
vm.runInContext(fs.readFileSync('newsmuncher/static/script.js','utf8'),ctx);
for(const key of keys){
 const title=key==='source'?'sourceTitleHeading':'crazyTitleBox';
 const body=key==='source'?'nonsenseBox':'crazyExtractBox';
 nodes[key+'Editor'].hidden=true;
 ctx.editor.edit(key);
 assert(nodes[key+'TitleDraft'].focused);
 assert(nodes[key+'Display'].hidden);
 assert.equal(nodes[key+'Editor'].hidden,false);
 assert.equal(nodes[key+'TitleDraft'].value,'original');
 assert.equal(nodes[key+'BodyDraft'].value,'original');
 nodes[key+'TitleDraft'].value='cancelled title';
 nodes[key+'BodyDraft'].value='cancelled body';
 ctx.editor.cancel(key);
 assert.equal(nodes[title].textContent,'...original...');
 assert.equal(nodes[body].value,'original');
 assert(nodes[key+'Edit'].focused);
 ctx.editor.edit(key);
 nodes[key+'TitleDraft'].value='<new & text>';
 nodes[key+'BodyDraft'].value='<new & body>';
 ctx.editor.save(key);
 assert.equal(nodes[title].textContent,'...<new & text>...');
 assert.equal(nodes[body].value,'<new & body>');
 assert.equal(nodes[key+'Edit']['aria-expanded'],'false');
 assert.equal(nodes[key+'Editor'].hidden,true);
}
assert.equal(calls,0);
assert.equal(nodes.titleDescBox.value,'<new & text>');
for(const c of choices){ctx.fetchAndDisplay(c.dataset.source);assert.equal(choices.filter(b=>b['aria-pressed']==='true').length,1);assert.equal(c['aria-pressed'],'true');}
ctx.editor.edit('response');ctx.editor.reset('response');assert.equal(nodes.responseEditor.hidden,true);
console.log('Profile edits and exclusive source selection passed.');

let nominated=[];
ctx.fetch=(url,options)=>{nominated.push({url,body:JSON.parse(options.body)});return new Promise(()=>{});};
for(const key of keys) nodes[key+'Editor'].hidden=true;
ctx.bankThisBeauty();ctx.bankThisBeauty();
assert.equal(nominated.length,1);
assert.equal(nominated[0].url,'/temp/confirm_data');
assert.deepEqual(nominated[0].body,{crazyReplacement1Title:'<new & text>',crazyReplacement1Extract:'<new & body>'});
assert.equal(nodes.titleDescBox.value,'<new & text>');
console.log('Nomination captures edited response only and prevents duplicate in-flight requests.');

vm.runInContext('nominationPending = false;',ctx);
ctx.editor.edit('response');
nodes.responseTitleDraft.value='open draft title';
nodes.responseBodyDraft.value='open draft body';
ctx.bankThisBeauty();
assert.equal(nominated.length,2);
assert.deepEqual(nominated[1].body,{crazyReplacement1Title:'open draft title',crazyReplacement1Extract:'open draft body'});
assert.equal(nodes.titleDescBox.value,'<new & text>');
assert.equal(nodes.nonsenseBox.value,'<new & body>');
console.log('Open grouped response drafts are nominated without changing source fields.');

const markup=fs.readFileSync('newsmuncher/templates/pet_profile.html','utf8');
assert.equal((markup.match(/class="funky-button edit-tab"/g)||[]).length,2);
assert.equal((markup.match(/>EDIT<\/button>/g)||[]).length,2);
for(const key of keys) {
 assert(markup.includes('aria-controls="'+key+'Editor"'));
 assert(markup.includes('id="'+key+'TitleDraft" class="headline-editor" rows="1"'));
 assert(markup.includes(`onclick="profileEditing.save('${key}')"`));
}
assert(!markup.includes('editable-section'));
const css=fs.readFileSync('newsmuncher/static/styles.css','utf8');
assert(css.includes('background: transparent; appearance: none; box-shadow: none;'));
assert(!css.includes('.profile-page .editable-section'));
console.log('Two grouped controls, multiline editors, and overlay styling verified.');

// Each card owns its editing state; normal tabs are never hidden by the other group.
for (const key of keys) ctx.editor.reset(key);
for (const key of keys) {
 const other=key==='source'?'response':'source';
 ctx.editor.edit(key);
 assert.equal(nodes[key+'Edit']['aria-expanded'],'true');
 assert.equal(nodes[other+'Edit']['aria-expanded'],'false');
 assert.equal(nodes[other+'Editor'].hidden,true);
 assert.equal(nodes[other+'Edit'].hidden,false);
 ctx.editor.cancel(key);
 assert.equal(nodes[key+'Edit']['aria-expanded'],'false');
}
const ids=[...markup.matchAll(/\bid="([^"]+)"/g)].map(match=>match[1]);
assert.equal(ids.length,new Set(ids).size);
for (const key of keys) {
 const tag=markup.match(new RegExp('<button[^>]*id="'+key+'Edit"[^>]*>EDIT</button>'))[0];
 assert(tag.includes('aria-controls="'+key+'Editor"'));
 assert(tag.includes('aria-expanded="false"'));
 assert(!tag.includes(' hidden'));
}
assert.equal((markup.match(/>SAVE<\/button>/g)||[]).length,2);
assert.equal((markup.match(/>CANCEL<\/button>/g)||[]).length,2);
// Regression: without this containing block the response tab is positioned off-card.
assert(css.includes('.profile-page #outputContainer { position: relative; }'));
console.log('Independent EDIT tabs, response card anchor, uppercase labels, and unique IDs verified.');
for (const label of ['DRIVEL','WIKIPEDIA','POEM','PEOPLE','IMAGE GENERATION MODE','SHIZZALISE','NOMINATE']) {
 assert(markup.includes('>'+label+'<'));
}
assert(!markup.includes('edit-notice'));
assert(css.includes('min-width: 190px; min-height: 90px'));
assert(css.includes('left: calc(-1 * var(--paper-edge))'));
assert(css.includes('transform: translate(-50%, 32%)'));

assert(css.includes('translate(-50%, -32%)'));
assert(css.includes('justify-content: flex-start; text-align: left; padding-left: 24px'));
assert(css.includes('z-index: -2;'));
assert(css.includes('drop-shadow(1px 3px 2px #49382266)'));
assert(css.includes('isolation: isolate; background: transparent; border-image-source: none'));
