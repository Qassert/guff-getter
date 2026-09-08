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
context.window.scrollY=950;images[0].onload();assert.equal(progress(),1);
assert.equal(slots[0].image.url,'/one.png');
context.window.scrollY=0;listeners.scroll();listeners.scroll();assert.equal(frames.length,1);frames.shift()();assert.equal(progress(),0);
context.window.scrollY=460;listeners.scroll();frames.shift()();assert.equal(progress(),.5);
context.bg.preload('/two.png',()=>true);assert.equal(slots[0].style.opacity,'1');
images[1].onerror();assert.equal(slots[1].image,undefined);
let current=true;context.bg.preload('/stale.png',()=>current);current=false;images[2].onload();assert.equal(slots[1].image,undefined);
context.bg.preload('/new.png',()=>true);images[3].onload();assert.equal(slots[1].image.url,'/new.png');assert.equal(slots[0].style.opacity,'1');assert.equal(slots[1].style.zIndex,'1');
context.bg.preload('/latest.png',()=>true);images[4].onload();assert.equal(slots.length,2);assert.equal(slots[0].image.url,'/latest.png');
context.bg.preload('/latest.png',()=>true);assert.equal(images.length,5);
assert.match(fs.readFileSync('newsmuncher/static/styles.css','utf8'), /prefers-reduced-motion: reduce[\s\S]*generated-backdrop/);
console.log('Background checks passed: preload, late arrival, scroll, throttle, errors, stale results, slot reuse.');
