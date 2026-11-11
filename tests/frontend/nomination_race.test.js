const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const {BuildWorkshop}=require('../../newsmuncher/static/build-page.js');
const source=fs.readFileSync('newsmuncher/static/js/creation/script.js','utf8');
const deferred=()=>{let resolve;const promise=new Promise(r=>resolve=r);return {promise,resolve};};

test('late BUILD draft banks clicked A without replacing B or consuming its draft',async()=>{
 const a=deferred(),b=deferred(),calls=[],body={value:'Story A'},button={};let sequence=1;
 global.creationContext=()=>({sequence});
 global.creationActions={hasDraft:()=>false,attachDraft:d=>calls.push(['attach',d.rewrite_id]),nominate:d=>calls.push(['nominate',d])};
 const element={dataset:{draftUrl:'/build/draft'},querySelector:s=>s==='[data-build-story]'?body:button};
 const workshop={element,fetcher:()=>sequence===1?a.promise:b.promise};
 const first=BuildWorkshop.prototype.nominateStory.call(workshop);
 sequence=2;body.value='Story B';
 const second=BuildWorkshop.prototype.nominateStory.call(workshop);
 b.resolve({ok:true,json:async()=>({rewrite_id:'B',crazyReplacement1Title:'B title'})});await second;
 a.resolve({ok:true,json:async()=>({rewrite_id:'A',crazyReplacement1Title:'A title'})});await first;
 assert.equal(body.value,'Story B');
 assert.deepEqual(calls[0],['attach','B']);assert.equal(calls[1][0],'nominate');
 assert.equal(calls[2][1].rewrite_id,'A');assert.equal(calls[2][1].text.crazyReplacement1Extract,'Story A');
 assert.equal(calls[2][1].sequence,1);assert.equal(calls.length,3);
 delete global.creationContext;delete global.creationActions;
});

function setup(){
 const requests=[],media=[],editors={responseTitleDraft:{value:'Title A'},responseBodyDraft:{value:'Story A'}};
 const context={window:{},document:{getElementById:id=>editors[id]},console,
 currentResultText:()=>({crazyReplacement1Title:editors.responseTitleDraft.value,crazyReplacement1Extract:editors.responseBodyDraft.value}),
 renderNominationButton(){},renderRedoImage(){},showLoader(){},hideLoader(){},
 embellishUI:{show(){},nominate:d=>media.push(d)},jingleUI:{show(){},discover(){media.push('discover');}},
 fetch:(url,options)=>{const d=deferred();requests.push({url,body:JSON.parse(options.body),...d});return d.promise;}};
 vm.createContext(context);vm.runInContext('let creationNominated=false, displayedRewriteId="A", rewriteSequence=1, nominatedSnapshot=null, nominationPending=false, imageRedoPending=false,currentImageUrl=null;',context);
 vm.runInContext(source.slice(source.indexOf('function bankThisBeauty('),source.indexOf('function setImageStyle')),context);
 return{context,requests,media,editors};
}

test('A confirmation completing after B keeps B pending and sends exact snapshots',async()=>{
 const t=setup(),a=t.context.bankThisBeauty();
 vm.runInContext('displayedRewriteId="B";rewriteSequence=2;nominationPending=false;',t.context);
 t.editors.responseBodyDraft.value='Story B';const b=t.context.bankThisBeauty();
 t.requests[0].resolve({ok:true,json:async()=>({nominated:true,rewrite_id:'A'})});await a;
 assert.equal(vm.runInContext('nominationPending',t.context),true);assert.equal(t.media.length,0);
 t.requests[1].resolve({ok:true,json:async()=>({nominated:true,rewrite_id:'B'})});await b;
 assert.equal(t.requests[0].body.crazyReplacement1Extract,'Story A');assert.equal(t.requests[1].body.crazyReplacement1Extract,'Story B');
 assert.match(t.requests[0].url,/rewrite_id=A/);assert.match(t.requests[1].url,/rewrite_id=B/);
 assert.equal(t.media[0].rewrite_id,'B');assert.equal(t.editors.responseBodyDraft.value,'Story B');
});

test('detached nomination submits its immutable ID/text without touching newer UI',async()=>{
 const t=setup();const p=t.context.bankThisBeauty({rewrite_id:'old',sequence:0,text:{crazyReplacement1Title:'Old',crazyReplacement1Extract:'Old story'}});
 assert.match(t.requests[0].url,/rewrite_id=old/);assert.equal(t.requests[0].body.crazyReplacement1Extract,'Old story');
 t.requests[0].resolve({ok:true,json:async()=>({nominated:true,rewrite_id:'old'})});await p;
 assert.equal(t.editors.responseBodyDraft.value,'Story A');assert.equal(t.media.length,0);
});
