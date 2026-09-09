const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const frames=[], images=[], listeners={};
const slots=[0,1].map(()=>({style:{},replaceChildren(img){this.image=img;}}));
const body={style:{setProperty(k,v){this[k]=v;}}};
const context={Image:class {constructor(){images.push(this);}set src(url){this.url=url;}},
 document:{body,documentElement:{scrollHeight:2200},getElementById(id){return id==='generatedBackdrop'?{children:slots}:{getBoundingClientRect:()=>({top:1200-context.window.scrollY})};}},
 window:{scrollY:0,innerHeight:800,addEventListener(name,fn){listeners[name]=fn;}},
 requestAnimationFrame(fn){frames.push(fn);}};
vm.createContext(context);vm.runInContext(fs.readFileSync('newsmuncher/static/image-background.js','utf8')+'\nglobalThis.bg=generatedBackground;',context);
const progress=()=>Number(body.style['--generated-background-progress']);
context.bg.preload('/one.png',()=>true);
assert.equal(slots[0].image,undefined); // Not active before load.
context.window.scrollY=950;images[0].onload();assert.equal(progress(),NaN);
assert.equal(slots[0].image.url,'/one.png');
context.window.scrollY=0;
assert.equal(listeners.scroll,undefined);
assert.equal(body.style['--generated-background-progress'],undefined);
context.window.scrollY=950;
assert.equal(slots[0].style.opacity,'1');
context.bg.preload('/two.png',()=>true);assert.equal(slots[0].style.opacity,'1');
images[1].onerror();assert.equal(slots[1].image,undefined);
let current=true;context.bg.preload('/stale.png',()=>current);current=false;images[2].onload();assert.equal(slots[1].image,undefined);
context.bg.preload('/new.png',()=>true);images[3].onload();assert.equal(slots[1].image.url,'/new.png');assert.equal(slots[0].style.opacity,'1');assert.equal(slots[1].style.zIndex,'1');
context.bg.preload('/latest.png',()=>true);images[4].onload();assert.equal(slots.length,2);assert.equal(slots[0].image.url,'/latest.png');
context.bg.preload('/latest.png',()=>true);assert.equal(images.length,5);
assert.match(fs.readFileSync('newsmuncher/static/styles.css','utf8'), /prefers-reduced-motion: reduce[\s\S]*generated-backdrop/);
console.log('Background checks passed: preload, late arrival, scroll, throttle, errors, stale results, slot reuse.');

(async () => {
 const initial={replaceChildren(img){this.image=img;}};
 const startupImages=[], startupSlots=[0,1].map(()=>({style:{},replaceChildren(img){this.image=img;}}));
 const startupListeners={};
 let requests=0;
 const startup={
  Image:class {constructor(){startupImages.push(this);}set src(url){this.url=url;}},
  fetch:async()=>{requests++;return {ok:true,json:async()=>({image_url:'/generated-images/start.png'})};},
  document:{body,documentElement:{scrollHeight:2200},getElementById(id){
   if(id==='initialBackground')return initial;
   if(id==='generatedBackdrop')return {children:startupSlots};
   return {getBoundingClientRect:()=>({top:1200-startup.window.scrollY})};
  }},
  window:{scrollY:950,innerHeight:800,addEventListener(name,fn){startupListeners[name]=fn;}},
  requestAnimationFrame(fn){fn();}
 };
 vm.createContext(startup);
 vm.runInContext(fs.readFileSync('newsmuncher/static/image-background.js','utf8')+'\nglobalThis.bg=generatedBackground;',startup);
 await startupListeners.DOMContentLoaded();
 assert.equal(requests,1);assert.equal(startupImages.length,1);assert.equal(initial.image,undefined);
 startupImages[0].onload();
 assert.equal(initial.image.url,'/generated-images/start.png');
 // No generation (toggle OFF) leaves the initial layer alone.
 assert.equal(startupListeners.scroll,undefined);assert.equal(initial.image,startupImages[0]);
 startup.bg.preload('/new.png',()=>true);
 assert.equal(initial.image,startupImages[0]);
 startupImages[1].onerror();assert.equal(initial.image,startupImages[0]);
 startup.bg.preload('/good.png',()=>true);startupImages[2].onload();
 assert.equal(startupSlots[0].image.url,'/good.png');
 assert.equal(initial.image,startupImages[0]); // retained beneath scroll crossfade
 assert.equal(body.style['--generated-background-progress'],undefined);
 startup.fetch=async()=>({ok:true,json:async()=>null});
 await startupListeners.DOMContentLoaded();assert.equal(startupImages.length,3);
 const template=fs.readFileSync('newsmuncher/templates/pet_profile.html','utf8');
 assert(!template.includes('/avatars/'));assert(template.includes('id="initialBackground"'));
 console.log('Nominated startup background: single preload, fallback, retained during OFF/failure, generated handover passed.');
})().catch(error=>{console.error(error);process.exitCode=1;});

const backgroundCSS=fs.readFileSync('newsmuncher/static/styles.css','utf8');
assert(!backgroundCSS.includes('--generated-background-progress'));
assert(!backgroundCSS.includes('initial-background-overlay'));
assert(!backgroundCSS.includes('generated-backdrop-shade'));
assert(backgroundCSS.includes('.initial-background { position: fixed; inset: 0;'));
