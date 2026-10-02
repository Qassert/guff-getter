const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs');
const {UdderSounds,MIXKIT_SOUNDS,SUSPENSE_SOUND}=require('../newsmuncher/static/udder-sounds.js');

function element(){const listeners={};return{listeners,addEventListener:(name,fn)=>(listeners[name]??=[]).push(fn),dispatch(name,event={}){for(const fn of listeners[name]||[])fn(event);}};}
class FakeAudio{
 static all=[];constructor(src){this.src=src;this.listeners={};FakeAudio.all.push(this);}
 addEventListener(name,fn){this.listeners[name]=fn;}
 play(){this.played=true;return this.rejection?Promise.reject(Error('blocked')):Promise.resolve();}
 finish(name='ended'){this.listeners[name]?.();}
}
function setup(random=()=>0,count=5){FakeAudio.all=[];const buttons=Array.from({length:count},element),munge=element();return{buttons,munge,sounds:new UdderSounds({buttons,munge,AudioClass:FakeAudio,random})};}

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

test('template loads isolated sound module and identifies the existing MUNGE action',()=>{
 const html=fs.readFileSync('newsmuncher/templates/pet_profile.html','utf8');assert(html.includes('id="mungeControl"'));assert(html.includes("path='udder-sounds.js'"));assert(html.indexOf('source-udder.js')<html.indexOf('munge-control.js'));assert(html.indexOf('munge-control.js')<html.indexOf('udder-sounds.js'));
});

test('six-teat MUNGE set is unique, polyphonic and rerandomises with one suspense per click',()=>{
 let values=[.1,.2,.3,.4,.5,.6,.7,.8,.9,.9,.8,.7,.6,.5,.4,.3,.2,.1],i=0;
 const {buttons,sounds}=setup(()=>values[i++%values.length],6);assert.equal(sounds.assignments.length,6);assert.equal(new Set(sounds.assignments).size,6);assert(!sounds.assignments.includes(SUSPENSE_SOUND));
 const before=[...sounds.assignments];for(const button of buttons)button.dispatch('pointerenter',{pointerType:'mouse'});assert.equal(FakeAudio.all.length,6);assert.equal(sounds.active.size,6);
 let munges=0;buttons[4].addEventListener('click',()=>munges++);buttons[4].dispatch('click');assert.equal(munges,1);assert.equal(FakeAudio.all.filter(a=>a.src.endsWith('/suspense.wav')).length,1);
 assert.equal(new Set(sounds.assignments).size,6);assert.notDeepEqual(sounds.assignments,before);FakeAudio.all[0].finish();assert.equal(sounds.active.size,6);
});
