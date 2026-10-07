const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs');
const {MungeControl}=require('../../newsmuncher/static/js/creation/munge-control.js');
function element(className=''){
 const listeners={},classes=new Set(className.split(' ').filter(Boolean));
 const style={values:{'--axis-x':'1','--axis-y':'0'},setProperty(k,v){this.values[k]=v;},getPropertyValue(k){return this.values[k]||'';}};
 return{listeners,style,offsetWidth:20,classList:{add:x=>classes.add(x),remove:x=>classes.delete(x),contains:x=>classes.has(x)},addEventListener:(n,f)=>(listeners[n]??=[]).push(f),dispatch(n,e={}){for(const f of listeners[n]||[])f(e);},querySelector(){return this.shape;}};
}
function setup(){const buttons=Array.from({length:6},()=>{const b=element('munge-teat');b.shape=element('munge-teat-shape');return b;}),frames=[],timers=[];let clock=0;return{buttons,frames,timers,setTime:v=>clock=v,ui:new MungeControl({buttons,reduced:()=>false,raf:fn=>{frames.push(fn);return frames.length;},now:()=>clock,schedule:(fn,ms)=>timers.push({fn,ms})})};}

test('six independent radial controls reuse one MUNGE action exactly once each',()=>{
 const t=setup();let munges=0;for(const button of t.buttons)button.addEventListener('click',()=>munges++);
 for(const button of t.buttons){const before=munges;button.dispatch('click');assert.equal(munges,before+1);assert(button.shape.classList.contains('squeezed'));}
 assert.equal(munges,6);assert.equal(t.timers.filter(x=>x.ms===260).length,6);
});

test('pointer motion bends along configured radial axis and touch does not hover-animate',()=>{
 const t=setup(),button=t.buttons[0];button.style.values['--axis-x']='-.72';button.style.values['--axis-y']='-.70';
 t.setTime(0);button.dispatch('pointerenter',{pointerType:'mouse',clientX:10,clientY:10});t.setTime(8);button.dispatch('pointermove',{pointerType:'mouse',clientX:35,clientY:20});
 assert(t.ui.states[0].target);t.frames.shift()();assert.match(button.shape.style.values['--travel-x'],/px$/);assert.match(button.shape.style.values['--travel-y'],/px$/);
 const untouched=t.buttons[1];untouched.dispatch('pointerenter',{pointerType:'touch',clientX:0,clientY:0});assert.equal(t.ui.states[1].lastX,null);
});

test('template and CSS assemble one supplied body with six separately tuned teat hit areas',()=>{
 const html=fs.readFileSync('newsmuncher/templates/pet_profile.html','utf8'),css=fs.readFileSync('newsmuncher/static/css/shared/styles.css','utf8');
 assert(html.includes('images/udders/munge/munge-body.png'));assert.equal((html.match(/class="munge-teat munge-teat-/g)||[]).length,1);
 for(const name of ['upper-left','upper-right','left','right','lower-left','lower-right'])assert(html.includes(`('${name}'`)||html.includes(`, '${name}'`));
 for(let i=1;i<=6;i++)assert(html.includes(`munge-teat-' ~ image`));
 const script=fs.readFileSync('newsmuncher/static/js/creation/script.js','utf8');assert.match(script,/querySelectorAll\?\.\('\.munge-teat, \.munge-body-button'\)\?\.forEach\(button => button\.addEventListener\('click', confirmData\)\)/);assert(!html.includes('id="mungeButton"'));
 for(const variable of ['--x','--y','--w','--axis-x','--axis-y','--origin-x','--origin-y','--base-rotation'])assert(html.includes(variable));
 assert.match(css,/\.munge-body-button\s*\{[^}]*z-index:\s*1/s);assert.match(css,/\.munge-body\s*\{[^}]*pointer-events:\s*none/s);assert.match(css,/\.munge-teat\s*\{[^}]*z-index:\s*2/s);assert.match(css,/prefers-reduced-motion/);
 const positions={"upper-left":['calc(32% + 16px)','23%'],"upper-right":['calc(68% - 16px)','23%'],left:['calc(26% + 8px)','calc(42% - 21px)'],right:['calc(74% - 6px)','calc(42% - 22px)'],"lower-left":['calc(37% + 20px)','calc(60% - 16px)'],"lower-right":['calc(63% - 12px)','calc(60% - 16px)']};
 for(const [name,[x,y]] of Object.entries(positions))assert(html.includes(`('${name}',`)&&html.includes(`'${x}', '${y}'`));
 assert.match(css,/\.munge-generation-controls\s*\{[^}]*position:\s*absolute[^}]*bottom:\s*calc\(-1 \* var\(--paper-edge\)\)[^}]*transform:\s*translate\(-50%, 50%\)/s);
 assert.match(css,/\.profile-page \.profile-container\s*\{\s*margin-bottom:\s*38px/);
 assert.match(css,/\.profile-page \.profile-container\s*\{\s*z-index:\s*2/);
});
