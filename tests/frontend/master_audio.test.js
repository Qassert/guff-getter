const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const {MasterAudioController,STORAGE_KEY}=require('../../newsmuncher/static/js/shared/master-audio.js');

class Storage {
  constructor(seed={}){this.values=new Map(Object.entries(seed));}
  getItem(key){return this.values.has(key)?this.values.get(key):null;}
  setItem(key,value){this.values.set(key,String(value));}
}
function MediaClass(){
  return class Media {
    constructor(muted=false){this.muted=muted;this.events={};this.playStates=[];}
    addEventListener(name,fn){this.events[name]=fn;}
    play(){this.playStates.push(this.muted);return Promise.resolve();}
  };
}
function button(){return{dataset:{},attributes:{},classList:{toggle(name,on){this[name]=on;}},
  addEventListener(name,fn){this[name]=fn;},setAttribute(name,value){this.attributes[name]=value;},
  getAttribute(name){return this.attributes[name];}};}

test('master mute defaults off, toggles accessibly and persists once bound',()=>{
  const storage=new Storage(),controller=new MasterAudioController({storage,MediaClass:MediaClass(),documentRef:null});
  const control=button();controller.bind(control);controller.bind(control);
  assert.equal(controller.muted,false);assert.equal(control.textContent,'🔊');
  control.click();assert.equal(controller.muted,true);
  assert.equal(storage.getItem(STORAGE_KEY),'true');assert.equal(control.attributes['aria-pressed'],'true');
  assert.equal(control.attributes['aria-label'],'Unmute all sound');assert.equal(control.classList['is-muted'],true);
});

test('playing and future media mute immediately, then restore individual mute state',async()=>{
  const Media=MediaClass(),controller=new MasterAudioController({storage:new Storage(),MediaClass:Media,documentRef:null});
  const audible=new Media(false),individuallyMuted=new Media(true);
  controller.registerMedia(audible);controller.registerMedia(individuallyMuted);
  controller.setMuted(true);
  assert(audible.muted&&individuallyMuted.muted);
  const later=new Media(false);await later.play();
  assert.equal(later.playStates[0],true,'play interception applies mute before native playback');
  controller.setMuted(false);
  assert.equal(audible.muted,false);assert.equal(later.muted,false);
  assert.equal(individuallyMuted.muted,true,'individual mute survives the master cycle');
});

test('saved preference survives a new controller and explicit playback unmutes synchronously',()=>{
  const storage=new Storage({[STORAGE_KEY]:'true'});
  const controller=new MasterAudioController({storage,MediaClass:MediaClass(),documentRef:null});
  assert.equal(controller.muted,true);
  assert.equal(controller.unmuteForExplicitPlayback(),false);
  assert.equal(storage.getItem(STORAGE_KEY),'false');
});

test('registered Web Audio mute gain follows master state without changing another gain',()=>{
  const calls=[],parameter={value:1,cancelScheduledValues:t=>calls.push(['cancel',t]),
    setValueAtTime:(value,time)=>{parameter.value=value;calls.push(['set',value,time]);}};
  const muteGain={gain:parameter},creativeGain={value:.82};
  const controller=new MasterAudioController({storage:new Storage(),MediaClass:MediaClass(),documentRef:null});
  controller.registerGain(muteGain,1);controller.setMuted(true);assert.equal(parameter.value,0);
  controller.setMuted(false);assert.equal(parameter.value,1);assert.equal(creativeGain.value,.82);
  controller.unregisterGain(muteGain);const count=calls.length;controller.setMuted(true);assert.equal(calls.length,count);
});

test('base control and both explicit PLAY handlers share the central synchronous unmute',()=>{
  const base=fs.readFileSync('newsmuncher/templates/base.html','utf8');
  const create=fs.readFileSync('newsmuncher/static/js/creation/jingles.js','utf8');
  const gallery=fs.readFileSync('newsmuncher/static/js/gallery/promotion-gallery.js','utf8');
  assert.match(base,/<button[^>]+id="masterMuteButton"[^>]+aria-pressed="false"/);
  assert.match(base,/js\/shared\/master-audio\.js/);
  assert.match(create,/if \(state\.jingle_url\)[\s\S]*NewsMuncherAudio\?\.unmuteForExplicitPlayback\(\);[\s\S]*await playCurrent\(\)/);
  assert.match(gallery,/music\.addEventListener\('click',[\s\S]*else \{[\s\S]*NewsMuncherAudio\?\.unmuteForExplicitPlayback\(\);[\s\S]*media\.restart\(\)/);
});
