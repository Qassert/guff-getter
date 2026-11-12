const {test}=require('node:test'),assert=require('node:assert/strict');
const {PromotionGallery}=require('../../newsmuncher/static/js/gallery/promotion-gallery.js');
const fax=require('../fixtures/fax_vicar_nomination.json');
const deferred=()=>{let resolve;const promise=new Promise(r=>resolve=r);return{promise,resolve};};
const response=data=>({ok:true,json:async()=>data});
function setup(fetcher){
 const messages=[],errors=[],busy=[];
 const media={stop(){},activate(){}};
 const gallery=new PromotionGallery({fetcher,media,visual:media,backdrop:media,
  view:{completing:v=>busy.push(v),progress:v=>messages.push(v),error:v=>errors.push(v),show(){},completed(){}}});
 return{gallery,messages,errors,busy};
}
const item=(id='A')=>({id,rewrite_id:'rewrite-'+id,title:fax.title,body:fax.body,
 image_url:'/image.png',video_url:'/video.mp4',jingle_url:'/jingle.mp3',can_enhance:true});

test('known fax ENHANCE reports content rejection without another paid submission',async()=>{
 const original={...item(fax.id),rewrite_id:fax.rewrite_id,video_url:null};const calls=[];
 const t=setup(async(url,opts)=>{calls.push([url,opts]);return response(url.startsWith('/videos/')?
  {rewrite_id:fax.rewrite_id,video_status:'failed_or_uncertain',end_image_status:'definitive_failed',failure_kind:'content_policy',
   message:'The video end image was rejected by the provider safety policy. Existing story and media are unchanged.'}:original);});
 t.gallery.current={...original};await t.gallery.complete();
 assert(t.errors.some(x=>x.includes('safety policy')));assert(!t.errors.some(x=>x.includes('outcome is uncertain')));
 assert(!calls.some(([url,opts])=>!url.includes('prepare-completion')&&opts.method==='POST'));
 assert.equal(t.gallery.current.body,fax.body);assert.equal(t.gallery.current.rewrite_id,fax.rewrite_id);
});

test('new nomination enhancement sends only the selected rewrite identity',async()=>{
 let record={...item(),image_url:null};const calls=[];
 const t=setup(async(url,opts)=>{calls.push([url,opts]);if(url==='/temp/generate_image')record={...record,image_url:'/new.png'};return response(record);});
 t.gallery.current={...record};await t.gallery.complete();
 const request=calls.find(([url])=>url==='/temp/generate_image');
 assert.deepEqual(JSON.parse(request[1].body),{rewrite_id:'rewrite-A'});
 assert.equal(t.gallery.current.body,fax.body);assert.equal(t.errors.length,0);
});

test('switch during delayed preparation/status cannot generate stale media or clear newer busy state',async()=>{
 const a=deferred(),b=deferred(),calls=[];
 const t=setup(async(url,opts)=>{calls.push(url);if(url.includes('/B/prepare'))return b.promise;
  if(url.endsWith('/items/A'))return a.promise;return response(item('A'));});
 t.gallery.current=item('A');const first=t.gallery.complete();await new Promise(setImmediate);
 t.gallery.sequence++;t.gallery.completionAbort.abort();t.gallery.completing=false;t.gallery.current=item('B');
 const second=t.gallery.complete();a.resolve(response({...item('A'),image_url:null}));await first;
 assert.equal(t.gallery.completing,true);assert.equal(t.gallery.current.id,'B');assert(!calls.includes('/temp/generate_image'));
 b.resolve(response(item('B')));await second;assert.equal(t.gallery.completing,false);
});

test('preparation data errors and missing media identity do not masquerade as moderation',async()=>{
 const t=setup(async()=>response({...item(),can_enhance:false,enhancement_error:'No committed media identity.'}));
 t.gallery.current=item();await t.gallery.complete();
 assert(t.messages.some(x=>x.includes('Creation data')));assert(!t.errors.some(x=>x.includes('safety')));
});

test('unexpected nomination response stops enhancement before generation',async()=>{
 const calls=[];const t=setup(async(url)=>{calls.push(url);return response(item('other'));});
 t.gallery.current=item('A');await t.gallery.complete();
 assert.equal(calls.length,1);assert.equal(t.gallery.current.id,'A');assert(t.errors.length);
});


test('story edited after preparation stops before any generation request',async()=>{
 const calls=[];const t=setup(async(url)=>{calls.push(url);return response(url.includes('prepare-completion')?
  {...item(),image_url:null}:{...item(),body:'Saved by another editor',image_url:null});});
 t.gallery.current=item();await t.gallery.complete();
 assert(!calls.includes('/temp/generate_image'));assert(t.errors.some(x=>x.includes('saved text changed')));
});


test('older nomination metadata commit requires an explicit confirmation click',async()=>{
 const calls=[];const t=setup(async(url,opts)=>{calls.push([url,opts]);return response(url.includes('prepare-completion')?
  {...item(),rewrite_id:'local-editor-identity',can_enhance:false,enhancement_revision:'token',enhancement_error:'Needs preparation'}:
  {...item(),rewrite_id:'committed-media-identity'});});
 t.gallery.view.confirmEnhancementPreparation=async()=>true;
 t.gallery.current=item();await t.gallery.complete();
 const committed=calls.find(([url])=>url.includes('commit-enhancement'));
 assert.deepEqual(JSON.parse(committed[1].body),{confirmed:true,revision:'token'});
 assert.equal(t.gallery.current.rewrite_id,'committed-media-identity');
 assert.equal(t.errors.length,0);
});


test('main-image content rejection remains distinct from data validation failures',()=>{
 const t=setup(async()=>response(item()));
 const policy=new Error('blocked');policy.mediaState={detail:{code:'media_content_rejected',message:'The provider rejected this visual interpretation.'}};
 assert.match(t.gallery.completionFailure('image',policy),/provider rejected/);
 const data=new Error('Saved story missing');data.httpStatus=422;
 assert.match(t.gallery.completionFailure('orchestration',data),/Creation data/);
});
