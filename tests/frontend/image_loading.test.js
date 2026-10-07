const {test}=require('node:test'), assert=require('node:assert/strict'), fs=require('node:fs');
const {ImageShuffle}=require('../../newsmuncher/static/js/creation/image-loading.js');
function setup(images, reduced=false) {
 const shown=[], timers=[], cancelled=[];let stopped=0, fetches=0;
 const ui=new ImageShuffle({view:{start(){},show(url,animate){shown.push({url,animate});},stop(){stopped++;}},
 fetcher:async()=>{fetches++;return {ok:true,json:async()=>({images})};},reduced:()=>reduced,random:()=>0,
 schedule(fn,ms){timers.push({fn,ms});return timers.length;},cancel:id=>cancelled.push(id)});
 return {ui,shown,timers,cancelled,stops:()=>stopped,fetches:()=>fetches};
}
const images=Array.from({length:8},(_,i)=>`/generated-images/000${i}.png`);
test('at most five distinct existing images; 500ms loop without adjacent repeats',async()=>{
 const t=setup(images);await t.ui.start();
 for(let i=0;i<20;i++) {assert.equal(t.timers[i].ms,500);t.timers[i].fn();}
 assert.equal(new Set(t.shown.slice(0,5).map(x=>x.url)).size,5);
 assert.equal(t.fetches(),1);assert.equal(t.shown.length,21);
 assert(t.shown.every(x=>images.slice(0,5).includes(x.url)));
 assert(t.shown.every((x,i)=>!i || x.url!==t.shown[i-1].url));
 t.ui.stop();const count=t.shown.length;t.timers.at(-1).fn();assert.equal(t.shown.length,count);
});
test('empty and reduced motion cases keep loader without a rotating timer',async()=>{
 const empty=setup([]);await empty.ui.start();assert.equal(empty.timers.length,0);
 const reduced=setup(images,true);await reduced.ui.start();assert.equal(reduced.shown.length,1);
 assert(!reduced.shown[0].animate);assert.equal(reduced.timers.length,0);
});
test('completion freezes visuals until real image loads; late retrieval ignored after teardown',async()=>{
 const t=setup(images);await t.ui.start();const before=t.stops();t.ui.freeze();
 assert(t.ui.isActive());assert.equal(t.stops(),before);t.timers[0].fn();assert.equal(t.shown.length,1);t.ui.stop();assert(!t.ui.isActive());assert.equal(t.stops(),before+1);
 let resolve;t.ui.fetcher=()=>new Promise(r=>resolve=r);const work=t.ui.start();t.ui.stop();
 resolve({ok:true,json:async()=>({images})});await work;assert.equal(t.shown.length,1);
});
test('shared loader, centered redo/overlay, stable clipped pane and reduced motion styles',()=>{
 const css=fs.readFileSync('newsmuncher/static/css/shared/styles.css','utf8');
 assert.match(css,/\.loader \{/);assert(!css.includes('.spinner'));
 assert.match(css,/\.creation-actions\s*\{[^}]*justify-content:\s*center/);
 assert.match(css,/\.creation-actions\s*\{[^}]*flex-wrap:\s*wrap/);
 assert.match(css,/\.page-loader, \.image-loader.*top: 50%; left: 50%/);
 assert.match(css,/\.image-loading.*position: absolute; inset: 0; overflow: hidden/);
 assert.match(css,/\.image-panel.*aspect-ratio: 1/);
 assert.match(css,/prefers-reduced-motion/);
});
