const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const {creatorEditUrl}=require('../../newsmuncher/static/js/gallery/promotion-gallery.js');
const source=fs.readFileSync('newsmuncher/static/js/creation/script.js','utf8');
const defer=()=>{let resolve;const promise=new Promise(r=>resolve=r);return{promise,resolve};};
function setup(fetcher){
 const fields={};for(const id of ['responseTitleDraft','responseBodyDraft','outputContainer','bankButton','mungeMessage',
 'sourceTitleDraft','sourceBodyDraft','sourceUrlDraft','sourceNameDraft','sourceAuthorDraft','sourceLicenceDraft'])fields[id]={value:'',style:{},hidden:true,classList:{remove(){}}};
 fields.responseBodyDraft.value='Unsaved current story';
 const window={location:{search:'?rewrite_id=old'}};
 const context={window,document:{getElementById:id=>fields[id]},sessionStorage:{getItem:()=> 'stale',setItem(){}},URLSearchParams,
 fetch:fetcher,autoResize(){},resetImagePanel(){context.cleared=true;},setNominationState(){},renderNominationButton(){},displayRewriteImage(){},console:{warn(){}},
 setDisplayedRewriteId:id=>{context.loaded=id;}};
 vm.createContext(context);vm.runInContext('let rewriteSequence=1,displayedRewriteId=null;'+source.slice(source.indexOf('let rewriteRestoreSequence'),source.indexOf("document.getElementById('mungeControls')")),context);
 return{context,fields,window};
}

test('Gallery EDIT preserves rewrite identity or falls back to nomination ID',()=>{
 assert.equal(creatorEditUrl('/create','old','entry'),'/create?rewrite_id=old');
 assert.equal(creatorEditUrl('/create',null,'entry'),'/create?nomination_id=entry');
});

test('explicit legacy nomination overrides stale session ID and restores exact editable text',async()=>{
 let requested;const t=setup(async url=>{requested=url;return{ok:true,json:async()=>({rewrite_id:'restored',nominated:true,crazyReplacement1Extract:'Dickens and Gainsbourg.',extract:'Original source.'})};});
 t.window.location.search='?nomination_id=entry';await t.context.restoreImageRewrite();
 assert.equal(requested,'/temp/gallery_creation/entry');assert.equal(t.context.loaded,'restored');
 assert.equal(t.fields.responseBodyDraft.value,'Dickens and Gainsbourg.');assert.equal(t.fields.sourceBodyDraft.value,'Original source.');
 assert.equal(t.fields.outputContainer.style.display,'block');assert.equal(t.context.cleared,true);
});

test('failed explicit load preserves current text and reports a visible error',async()=>{
 const t=setup(async()=>({ok:false,status:404}));await t.context.restoreImageRewrite();
 assert.equal(t.fields.responseBodyDraft.value,'Unsaved current story');assert.equal(t.context.loaded,undefined);
 assert.equal(t.fields.mungeMessage.hidden,false);assert.match(t.fields.mungeMessage.textContent,/could not be loaded/);
});

test('out-of-order restoration never replaces the newly selected nomination',async()=>{
 const pending={old:defer(),new:defer()};const t=setup(url=>pending[url.split('/').at(-1)].promise);
 const a=t.context.restoreImageRewrite();t.window.location.search='?rewrite_id=new';const b=t.context.restoreImageRewrite();
 pending.new.resolve({ok:true,json:async()=>({rewrite_id:'new',crazyReplacement1Extract:'New story'})});await b;
 pending.old.resolve({ok:true,json:async()=>({rewrite_id:'old',crazyReplacement1Extract:'Old story'})});await a;
 assert.equal(t.fields.responseBodyDraft.value,'New story');assert.equal(t.context.loaded,'new');
});
