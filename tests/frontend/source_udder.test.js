const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs');
const {SourceUdder}=require('../../newsmuncher/static/js/creation/source-udder.js');

function element(className=''){
 const listeners={},children=[],classes=new Set(className.split(' ').filter(Boolean));
 return {className,children,dataset:{liquid:'#f00'},style:{values:{},setProperty(k,v){this.values[k]=v;}},offsetWidth:20,
  classList:{add:x=>classes.add(x),remove:x=>classes.delete(x),contains:x=>classes.has(x)},
  addEventListener:(name,fn)=>(listeners[name]??=[]).push(fn),dispatch(name,event={}){event.preventDefault??=()=>{};event.stopImmediatePropagation??=()=>{};for(const fn of listeners[name]||[])fn(event);},
  querySelector(selector){return selector==='.teat-shape'?this.shape:null;},appendChild(node){children.push(node);},
  getContext(){return new Proxy({}, {get:(target,key)=>target[key]||(()=>{})});},
  remove(){this.removed=true;},setAttribute(){},getBoundingClientRect(){return{left:100,top:20,right:180,bottom:160,width:80,height:140}}};
}
function setup(){
 const buttons=Array.from({length:5},()=>{const b=element('udder-teat');b.shape=element('teat-shape');return b;});
 const layer=element(),frames=[],timers=[];let clock=0;
 const parchment=element();parchment.getBoundingClientRect=()=>({left:20,right:920,top:100,bottom:700,width:900,height:600});
 global.addEventListener=()=>{};global.innerWidth=1000;global.innerHeight=800;global.requestAnimationFrame=()=>1;
 global.document={createElement:()=>element(),body:element(),querySelector:()=>parchment};
 const ui=new SourceUdder({udder:element(),buttons,layer,reduced:()=>false,raf:fn=>{frames.push(fn);return frames.length;},now:()=>clock,schedule:(fn,ms)=>{timers.push({fn,ms});return timers.length;}});
 return{ui,buttons,layer,frames,timers,setTime:v=>clock=v};
}

test('pointer brush bends without activating and fast movement flicks harder',()=>{
 const t=setup(),button=t.buttons[2];let activations=0;button.onclick=()=>activations++;
 t.setTime(0);button.dispatch('pointerenter',{pointerType:'mouse',clientX:20});
 t.setTime(100);button.dispatch('pointermove',{pointerType:'mouse',clientX:24});const slow=Math.abs(t.ui.states[2].target);
 t.setTime(108);button.dispatch('pointermove',{pointerType:'mouse',clientX:60});const fast=Math.abs(t.ui.states[2].target);
 assert(fast>slow);assert.equal(activations,0);assert.notEqual(t.ui.states[1].velocity,0);
 button.dispatch('pointerleave');assert.equal(t.ui.states[2].target,0);
});

test('click squashes and starts the teat-specific canvas effect',()=>{
 const t=setup(),button=t.buttons[0];button.dataset.liquid='#45a8e8';button.dispatch('click');
 assert(button.shape.classList.contains('effect-squeezed'));
 assert(t.ui.effects.isActive(0));assert.equal(t.ui.effects.effects.length,1);
 assert.equal(t.ui.effects.effects[0].kind,'cream');assert.equal(t.ui.effects.effects[0].duration,5200);
});

test('rapid clicks retain independent canvas effects for different teats',()=>{
 const t=setup();t.buttons[0].dispatch('click');t.buttons[1].dispatch('click');
 assert.equal(t.ui.effects.effects.length,2);
 assert.deepEqual(t.ui.effects.effects.map(effect=>effect.index),[0,1]);
 assert(t.ui.effects.isActive(0));assert(t.ui.effects.isActive(1));
});

test('template keeps five native accessible actions and page-level unclipped effect layer',()=>{
 const html=fs.readFileSync('newsmuncher/templates/pet_profile.html','utf8'),css=fs.readFileSync('newsmuncher/static/css/shared/styles.css','utf8');
 assert.equal((html.match(/class="source-choice udder-teat/g)||[]).length,1); // Jinja loop source
 for(const action of ['fetch_dating_from_api','fetch_historicalFunny_from_api','fetch_wikipedia_into_api','fetch_poem_into_api','fetch_people_into_api'])assert(html.includes(`'${action}'`));
 assert(html.includes("fetchAndDisplay('{{ action }}')"));
 assert(html.includes("images/udders/source/udder-master-body.png"));for(let i=1;i<=5;i++)assert(html.includes(`udder-teat-${i}.png`));
 assert(!html.includes('<svg class="udder-body"'));assert.match(css,/transform-origin:\s*50% 5%/);
 assert(html.includes('--teat-width: {{ width }}'));assert.match(css,/width:\s*var\(--teat-width\)/);
 assert.match(css,/\.profile-page \.udder-master-body\s*\{[^}]*z-index:\s*2[^}]*pointer-events:\s*none/s);
 assert.match(css,/\.udder-teat\s*\{[^}]*z-index:\s*3/s);assert(!css.includes('mask-image: linear-gradient'));
 assert.match(css,/\.profile-page \.udder-master-body\s*\{[^}]*top:\s*0/s);assert.match(css,/top:\s*calc\(min\(132px, 14\.8vw\) \+ var\(--teat-offset-y\)\)/);
 assert.match(css,/\.profile-page \.workshop\s*\{[^}]*position:\s*relative/s);
 assert.match(css,/\.profile-page \.mode-nav\s*\{[^}]*position:\s*absolute[^}]*margin-bottom:\s*0/s);
 assert.match(css,/\.profile-page \.nonsense-container\s*\{[^}]*top:\s*calc\(-1\.25 \* var\(--paper-edge\)\)/s);
 assert(!css.includes('var(--paper-edge) - 60px'));
 for(const socket of ['18.1%','33.3%','50.9%','68.5%','84.7%'])assert(html.includes(`'${socket}'`));
 assert(html.includes('aria-label="{{ label }}"'));assert.match(css,/\.udder-liquid-layer[^}]*position:\s*fixed[^}]*overflow:\s*visible[^}]*pointer-events:\s*none/);
 assert.match(css,/udder-blot-drain\s+4s/);assert.match(css,/opacity:1/);assert.match(css,/prefers-reduced-motion/);
});

test('outer teat resting offsets move hit areas without touching animation transforms',()=>{
 const css=fs.readFileSync('newsmuncher/static/css/shared/styles.css','utf8');
 assert.match(css,/\.udder-teat:first-of-type\s*\{\s*--teat-offset-y:\s*-12px;/);
 assert.match(css,/\.udder-teat:last-of-type\s*\{\s*--teat-offset-x:\s*-12px;\s*--teat-offset-y:\s*-12px;/);
 assert.match(css,/left:\s*calc\(var\(--teat-x\) \+ var\(--teat-offset-x\)\)/);
 assert.match(css,/top:\s*calc\(min\(132px, 14\.8vw\) \+ var\(--teat-offset-y\)\)/);
});
