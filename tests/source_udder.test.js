const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs');
const {SourceUdder}=require('../newsmuncher/static/source-udder.js');

function element(className=''){
 const listeners={},children=[],classes=new Set(className.split(' ').filter(Boolean));
 return {className,children,dataset:{liquid:'#f00'},style:{values:{},setProperty(k,v){this.values[k]=v;}},offsetWidth:20,
  classList:{add:x=>classes.add(x),remove:x=>classes.delete(x),contains:x=>classes.has(x)},
  addEventListener:(name,fn)=>listeners[name]=fn,dispatch(name,event={}){listeners[name]?.(event);},
  querySelector(selector){return selector==='.teat-shape'?this.shape:null;},appendChild(node){children.push(node);},
  remove(){this.removed=true;},setAttribute(){},getBoundingClientRect(){return{left:100,top:20,right:180,bottom:160,width:80,height:140}}};
}
function setup(){
 const buttons=Array.from({length:5},()=>{const b=element('udder-teat');b.shape=element('teat-shape');return b;});
 const layer=element(),frames=[],timers=[];let clock=0;
 global.document={createElement:()=>element(),querySelector:()=>({getBoundingClientRect:()=>({left:20,right:920,top:100,bottom:700,width:900,height:600})})};
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

test('click squashes, emits unique-colour liquid and cleans effects after three seconds',()=>{
 const t=setup(),button=t.buttons[0];button.dataset.liquid='#45a8e8';button.dispatch('click');
 assert(button.shape.classList.contains('squeezed'));assert.equal(t.layer.children.length,1);
 const travel=t.timers.find(x=>x.ms===350);travel.fn();assert(t.layer.children[0].removed);assert.equal(t.layer.children.length,2);
 const cleanup=t.timers.find(x=>x.ms===3100);cleanup.fn();assert(t.layer.children[1].removed);
});

test('template keeps five native accessible actions and page-level unclipped effect layer',()=>{
 const html=fs.readFileSync('newsmuncher/templates/pet_profile.html','utf8'),css=fs.readFileSync('newsmuncher/static/styles.css','utf8');
 assert.equal((html.match(/class="source-choice udder-teat"/g)||[]).length,1); // Jinja loop source
 for(const action of ['fetch_dating_from_api','fetch_historicalFunny_from_api','fetch_wikipedia_into_api','fetch_poem_into_api','fetch_people_into_api'])assert(html.includes(`'${action}'`));
 assert(html.includes("fetchAndDisplay('{{ action }}')"));
 assert(html.includes('aria-label="{{ label }}"'));assert.match(css,/\.udder-liquid-layer[^}]*position:\s*fixed[^}]*overflow:\s*visible[^}]*pointer-events:\s*none/);
 assert.match(css,/udder-blot-drain\s+3s/);assert.match(css,/prefers-reduced-motion/);
});
