const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs');
const {UdderSounds,MungeTeatSounds,MIXKIT_SOUNDS,MUNGE_SOUNDS,SUSPENSE_SOUND}=require('../../newsmuncher/static/js/creation/udder-sounds.js');

function element(){const listeners={};return{listeners,addEventListener:(name,fn)=>(listeners[name]??=[]).push(fn),dispatch(name,event={}){for(const fn of listeners[name]||[])fn(event);}};}
class FakeAudio{
 static all=[];constructor(src){this.src=src;this.listeners={};FakeAudio.all.push(this);}
 addEventListener(name,fn){this.listeners[name]=fn;}
 play(){this.played=true;return this.rejection?Promise.reject(Error('blocked')):Promise.resolve();}
 finish(name='ended'){this.listeners[name]?.();}
}
function setup(random=()=>0,count=5,options={}){FakeAudio.all=[];const buttons=Array.from({length:count},element),munge=element();return{buttons,munge,sounds:new UdderSounds({buttons,munge,AudioClass:FakeAudio,random,...options})};}
function control(engine){const listeners={},teats=Array.from({length:6},element),classes=new Set();return{dataset:{mungeEngine:engine},teats,listeners,classList:{contains:name=>classes.has(name),add:name=>classes.add(name),remove:name=>classes.delete(name)},querySelectorAll:selector=>selector==='.munge-teat'?teats:[],addEventListener:(name,fn)=>(listeners[name]??=[]).push(fn),dispatch(name,event={}){for(const fn of listeners[name]||[])fn(event);}};}

test('page load assigns five unique Mixkit sounds and remains silent',()=>{
 const {sounds}=setup();assert.equal(sounds.assignments.length,5);assert.equal(new Set(sounds.assignments).size,5);
 assert(sounds.assignments.every(sound=>MIXKIT_SOUNDS.includes(sound)));assert(!sounds.assignments.includes(SUSPENSE_SOUND));assert.equal(FakeAudio.all.length,0);
});

test('pointer re-entry and different teats create overlapping independent playback',()=>{
 const {buttons,sounds}=setup();buttons[0].dispatch('pointerenter',{pointerType:'mouse'});buttons[0].dispatch('pointerenter',{pointerType:'mouse'});buttons[1].dispatch('pointerenter',{pointerType:'mouse'});
 assert.equal(FakeAudio.all.length,3);assert.notEqual(FakeAudio.all[0],FakeAudio.all[1]);assert.equal(FakeAudio.all[0].src,FakeAudio.all[1].src);
 assert.notEqual(FakeAudio.all[1].src,FakeAudio.all[2].src);assert.equal(sounds.active.size,3);
 buttons[2].dispatch('pointerenter',{pointerType:'touch'});assert.equal(FakeAudio.all.length,3);
});

test('click plays suspense and rerandomises a unique set without replacing click behaviour',()=>{
 let values=[.1,.2,.3,.4,.5,.6,.7,.8,.9,.9,.8,.7,.6,.5,.4,.3,.2,.1],i=0;
 const {buttons,sounds}=setup(()=>values[i++%values.length]);const before=[...sounds.assignments];let existing=0;buttons[2].addEventListener('click',()=>existing++);
 buttons[2].dispatch('click');assert.equal(existing,1);assert(FakeAudio.all.at(-1).src.endsWith('/suspense.wav'));
 assert.equal(sounds.assignments.length,5);assert.equal(new Set(sounds.assignments).size,5);assert(!sounds.assignments.includes(SUSPENSE_SOUND));assert.notDeepEqual(sounds.assignments,before);
});

test('MUNGE plays suspense and finished instances are released',()=>{
 const {munge,sounds}=setup();munge.dispatch('click');const audio=FakeAudio.all[0];assert(audio.src.endsWith('/suspense.wav'));assert.equal(sounds.active.size,1);audio.finish();assert.equal(sounds.active.size,0);
});

test('rejected playback is swallowed and cleaned up',async()=>{
 class RejectedAudio extends FakeAudio{play(){this.played=true;return Promise.reject(Error('blocked'));}}
 const buttons=Array.from({length:5},element),sounds=new UdderSounds({buttons,AudioClass:RejectedAudio,random:()=>0});buttons[0].dispatch('pointerenter',{pointerType:'mouse'});
 await new Promise(resolve=>setImmediate(resolve));assert.equal(sounds.active.size,0);
});

test('template loads teat sounds after controls without binding the retired MUNGE body sound',()=>{
 const html=fs.readFileSync('newsmuncher/templates/pet_profile.html','utf8'),script=fs.readFileSync('newsmuncher/static/js/creation/udder-sounds.js','utf8');assert(html.includes('id="mungeControls"'));assert(html.includes("path='js/creation/udder-sounds.js'"));assert(html.indexOf('source-udder.js')<html.indexOf('munge-control.js'));assert(html.indexOf('munge-control.js')<html.indexOf('udder-sounds.js'));assert.match(script,/buttons:control\.querySelectorAll\('\.munge-teat'\)/);assert.match(script,/new MungeTeatSounds\(\{controls/);assert.doesNotMatch(script,/munge:button/);assert.doesNotMatch(script,/bodies:Object\.fromEntries/);
});

test('six-teat MUNGE set keeps stable unique instruments and never plays legacy suspense',()=>{
 let values=[.1,.2,.3,.4,.5,.6,.7,.8,.9,.9,.8,.7,.6,.5,.4,.3,.2,.1],i=0;
 const {buttons,sounds}=setup(()=>values[i++%values.length],6,{rootPath:'/static/audio/effects/munge/',pool:MUNGE_SOUNDS,clickSound:'assigned',pressSound:true,randomiseOnInteraction:false});assert.equal(sounds.assignments.length,6);assert.equal(new Set(sounds.assignments).size,6);assert(!sounds.assignments.includes(SUSPENSE_SOUND));
 const before=[...sounds.assignments];for(const button of buttons)button.dispatch('pointerenter',{pointerType:'mouse'});assert.equal(FakeAudio.all.length,6);assert.equal(sounds.active.size,6);
 let munges=0;buttons[4].addEventListener('click',()=>munges++);buttons[4].dispatch('pointerdown');buttons[4].dispatch('click');assert.equal(munges,1);assert.equal(FakeAudio.all.filter(a=>a.src.endsWith('/suspense.wav')).length,0);assert(FakeAudio.all.at(-1).src.startsWith('/static/audio/effects/munge/'));
 assert.deepEqual(sounds.assignments,before);buttons[4].dispatch('pointerdown');buttons[4].dispatch('click');assert.equal(FakeAudio.all.at(-1).src,FakeAudio.all.at(-2).src);FakeAudio.all[0].finish();assert.equal(sounds.active.size,7);
});

test('each engine gets six unique stable sounds and selection refreshes only that engine',()=>{
 const controls=['classic','current','experimental'].map(control),values=[.03,.17,.31,.47,.61,.79,.89,.71,.53,.37,.19,.07],pool=Array.from({length:38},(_,i)=>`sound-${i}.mp3`);let i=0;
 FakeAudio.all=[];const sounds=new MungeTeatSounds({controls,AudioClass:FakeAudio,random:()=>values[i++%values.length],rootPath:'/munge/',pool});
 const initial=Object.fromEntries(controls.map(item=>[item.dataset.mungeEngine,sounds.assignments(item.dataset.mungeEngine)]));
 for(const engine of Object.keys(initial)){assert.equal(initial[engine].length,6);assert.equal(new Set(initial[engine]).size,6);}
 controls[0].dispatch('pointerdown');const selected=sounds.assignments('classic');controls[0].teats[2].dispatch('pointerdown');controls[0].teats[2].dispatch('click');controls[0].teats[2].dispatch('pointerdown');controls[0].teats[2].dispatch('click');
 assert.notDeepEqual(selected,initial.classic);assert.equal(new Set(selected).size,6);assert.equal(FakeAudio.all.at(-1).src,FakeAudio.all.at(-2).src);
 assert.deepEqual(sounds.assignments('current'),initial.current);assert.deepEqual(sounds.assignments('experimental'),initial.experimental);
 controls[1].dispatch('pointerdown');assert.notDeepEqual(sounds.assignments('current'),initial.current);
 const firstClassic=[...selected];controls[0].dispatch('pointerdown');assert.notDeepEqual(sounds.assignments('classic'),firstClassic);
});

test('teat interaction during processing keeps the selected six-sound mapping',()=>{
 const selected=control('experimental'),pool=Array.from({length:38},(_,i)=>`sound-${i}.mp3`);let tick=0;
 const sounds=new MungeTeatSounds({controls:[selected],AudioClass:FakeAudio,random:()=>((tick++*7)%37)/38,rootPath:'/munge/',pool});
 selected.dispatch('pointerdown');const assignment=sounds.assignments('experimental');selected.classList.add('munge-control-processing');selected.dispatch('pointerdown');selected.teats[0].dispatch('pointerdown');selected.teats[0].dispatch('click');
 assert.deepEqual(sounds.assignments('experimental'),assignment);assert(FakeAudio.all.at(-1).src.endsWith('/'+assignment[0]));
});

test('MUNGE pool contains every unique supported asset and omits the duplicate copy',()=>{
 const root='newsmuncher/static/audio/effects/munge';
 assert.equal(MUNGE_SOUNDS.length,38);assert.equal(new Set(MUNGE_SOUNDS).size,38);
 assert(MUNGE_SOUNDS.every(sound=>fs.existsSync(`${root}/${sound}`)));
 assert(!MUNGE_SOUNDS.includes('edr-synth-side-stick-471670 (1).mp3'));
});
