const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs');
const {PromotionGallery}=require('../../newsmuncher/static/js/gallery/promotion-gallery.js');
const defer=()=>{let resolve;const promise=new Promise(r=>resolve=r);return{promise,resolve};};
const response=data=>({ok:true,json:async()=>data});
function setup(storage,fetcher){
 const modes=[],shown=[],calls=[];const media={stop(){},activate(){}};
 const view={sorting:m=>modes.push(m),loading(){},completing(){},progress(){},show:i=>shown.push(i),backAvailable(){},error(){}};
 const gallery=new PromotionGallery({view,storage,media,visual:media,backdrop:media,fetcher:async(url,options)=>{
  calls.push(url);return fetcher?fetcher(url,options):response({item:{id:'a',rewrite_id:'ra',body:'A'},cycle_complete:false});}});
 return{gallery,modes,shown,calls};
}
function storage(initial){let value=initial;return{getItem:()=>value,setItem:(_key,next)=>{value=next;}};}

test('first visit defaults to RANDOM; saved selection survives new Gallery instances',async()=>{
 const preference=storage(null),a=setup(preference);
 assert.equal(a.gallery.sortMode,'random');assert.deepEqual(a.modes,['random']);
 await a.gallery.setSort('latest');assert.equal(setup(preference).gallery.sortMode,'latest');
 await a.gallery.setSort('random');assert.equal(setup(preference).gallery.sortMode,'random');
});

test('blocked storage does not prevent sorting and invalid preference defaults to RANDOM',async()=>{
 const t=setup({getItem(){throw Error('blocked');},setItem(){throw Error('blocked');}});
 assert.equal(t.gallery.sortMode,'random');await t.gallery.setSort('latest');assert.equal(t.gallery.sortMode,'latest');
 assert.equal(setup(storage('invalid')).gallery.sortMode,'random');
});

test('switch resets old history/cursors and applies sorting before retrieval',async()=>{
 const t=setup(storage(null));t.gallery.current={id:'old'};t.gallery.history=[{id:'older'}];t.gallery.forward=[{id:'old-forward'}];t.gallery.cycleSeen=['old'];
 await t.gallery.setSort('latest');
 const query=new URL(t.calls[0],'https://local.invalid').searchParams;
 assert.equal(query.get('sort'),'latest');assert.equal(query.get('chronological_index'),'0');assert(!query.has('shown'));assert(!query.has('previous'));
 assert.deepEqual(t.gallery.history,[]);assert.deepEqual(t.gallery.forward,[]);assert.equal(t.gallery.current.id,'a');
 const count=t.calls.length;await t.gallery.setSort('latest');assert.equal(t.calls.length,count);
});

test('RANDOM keeps a stable seed and excludes displayed IDs throughout a cycle',async()=>{
 let next=0;const t=setup(storage(null),async()=>response({item:{id:String(++next)}}));
 await t.gallery.next();await t.gallery.next();
 const a=new URL(t.calls[0],'https://local.invalid').searchParams,b=new URL(t.calls[1],'https://local.invalid').searchParams;
 assert.equal(a.get('sort'),'random');assert.equal(a.get('seed'),b.get('seed'));assert.equal(b.get('shown'),'1');
});

test('rapid mode switching ignores stale responses and actions keep the latest identity',async()=>{
 const pending=defer();const t=setup(storage(null),async url=>{
  const mode=new URL(url,'https://local.invalid').searchParams.get('sort');
  return mode==='latest'?pending.promise:response({item:{id:'random-item',rewrite_id:'random-rewrite'}});});
 const latest=t.gallery.setSort('latest');await new Promise(setImmediate);
 await t.gallery.setSort('random');pending.resolve(response({item:{id:'stale-latest',rewrite_id:'wrong'}}));await latest;
 assert.equal(t.gallery.current.id,'random-item');assert.equal(t.gallery.current.rewrite_id,'random-rewrite');
 assert.deepEqual(t.shown.map(i=>i.id),['random-item']);
});

test('parchment toggle has accessible depressed state and responsive styling',()=>{
 const html=fs.readFileSync('newsmuncher/templates/promotion_gallery.html','utf8'),css=fs.readFileSync('newsmuncher/static/css/gallery/promotion-gallery.css','utf8');
 assert(html.indexOf('class="gallery-sort"')<html.indexOf('<figure id="galleryIllustration"'));
 assert.match(html,/data-gallery-sort="random" aria-pressed="true">RANDOM/);
 assert.match(html,/data-gallery-sort="latest" aria-pressed="false">LATEST FIRST/);
 assert.match(css,/\.gallery-sort \.funky-button\[aria-pressed="true"\][^{]*\{[^}]*translateY\(2px\)[^}]*inset[^}]*underline/s);
 assert.match(css,/@media \(max-width: 620px\)[\s\S]*\.gallery-sort/);
});


test('switching modes cancels pending arrow, promotion and edit animation actions',()=>{
 const vm=require('node:vm'),source=fs.readFileSync('newsmuncher/static/js/gallery/promotion-gallery.js','utf8');
 const start=source.indexOf("    document.querySelectorAll('[data-gallery-sort]')",source.indexOf("page.addEventListener('animationend'"));
 const end=source.indexOf("    const nextButton =",start),cleared=[];let click,selected;
 const control={disabled:true,classList:{remove(){}}};
 const context={document:{querySelectorAll:()=>[{dataset:{gallerySort:'latest'},addEventListener:(_event,fn)=>click=fn}]},
  gallery:{sortMode:'random',setSort:mode=>selected=mode},clearTimeout:id=>cleared.push(id),
  nextTimer:1,promoteTimer:2,editTimer:3,promotePending:true,editPending:true,
  nextButton:control,promote:control,edit:control};
 vm.runInNewContext(source.slice(start,end),context);click();
 assert.deepEqual(cleared,[1,2,3]);assert.equal(selected,'latest');
 assert.equal(context.promotePending,false);assert.equal(context.editPending,false);assert.equal(control.disabled,false);
});
