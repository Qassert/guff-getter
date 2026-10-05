const {test}=require('node:test'),assert=require('node:assert/strict');
const {LoadingAudio,ImageShuffle,LOADING_JINGLE_OFFSET_SECONDS}=require('../newsmuncher/static/image-loading.js');
const flush=()=>new Promise(resolve=>setImmediate(resolve));
function setup({duration=10,blocked=false}={}) {
 const players=[],timers=new Map();let id=0;
 const audio=new LoadingAudio({makeAudio(url){
  const player={url,duration,readyState:0,volume:1,currentTime:0,events:{},plays:0,pauses:0,
   addEventListener(name,fn){this.events[name]=fn;},load(){},removeAttribute(){this.unloaded=true;},pause(){this.pauses++;},
   async play(){this.plays++;if(blocked)throw Object.assign(Error('blocked'),{name:'NotAllowedError'});}};
  players.push(player);return player;
 },schedule(fn,ms){timers.set(++id,{fn,ms});return id;},cancel:id=>timers.delete(id)});
 return {audio,players,timers,ramp(){for(const [id,t] of [...timers]){timers.delete(id);t.fn();}}};
}
test('associated track seeks to two seconds; musicless image silences it; next track restarts',async()=>{
 const t=setup();t.audio.select('/one');let p=t.players[0];await p.events.loadedmetadata();
 assert.equal(p.currentTime,LOADING_JINGLE_OFFSET_SECONDS);assert.equal(p.plays,1);
 t.ramp();assert.equal(p.volume,1);t.audio.select(null);assert.equal(p.pauses,0);t.ramp();assert(p.unloaded);
 t.audio.select('/two');const q=t.players[1];await q.events.canplay();
 assert.equal(q.currentTime,2);assert.equal(q.plays,1);
 assert([...t.timers.values()].every(x=>x.ms<=100));t.ramp();assert.equal(q.volume,1);
 t.audio.select('/two');const again=t.players[2];await again.events.loadedmetadata();await again.events.canplay();
 assert.equal(again.plays,1);assert.equal(again.currentTime,2);
 t.audio.stop();assert(t.players.every(p=>p.unloaded));assert.equal(t.timers.size,0);
});
test('short tracks start at zero; stale metadata and pending selections cannot play',async()=>{
 const t=setup({duration:1});t.audio.select('/old');const old=t.players[0];t.audio.select('/new');
 await old.events.loadedmetadata();assert.equal(old.plays,0);
 const current=t.players[1];await current.events.loadedmetadata();assert.equal(current.currentTime,0);
 t.audio.select('/late');const late=t.players[2];t.audio.select(null);await late.events.canplay();assert.equal(late.plays,0);
 t.audio.stop();await current.events.canplay();assert.equal(current.plays,1);
});
test('autoplay rejection silences rest of session without repeated attempts',async()=>{
 const t=setup({blocked:true});t.audio.select('/a');await t.players[0].events.loadedmetadata();
 t.audio.select('/b');t.audio.select('/c');assert.equal(t.players.length,1);assert(t.players[0].unloaded);
 t.audio.reset();t.audio.select('/new-session');assert.equal(t.players.length,2);
});
test('late play promise after cleanup cannot restart audio',async()=>{
 const t=setup();t.audio.select('/a');const p=t.players[0];let resolve;p.play=()=>new Promise(r=>resolve=r);
 const work=p.events.loadedmetadata();t.audio.stop();const before=p.pauses;resolve();await work;assert(p.pauses>before);
});
test('image lifecycle chooses optional audio and every stop including frozen completion cleans it',async()=>{
 const selected=[];let stopped=0;const timers=[];
 const items=[{image_url:'/generated-images/aaa.png',jingle_url:'/generated-audio/'+ 'a'.repeat(24)+'.mp3'},
  {image_url:'/generated-images/bbb.png',jingle_url:null}];
 let reduced=false;
 const ui=new ImageShuffle({view:{start(){},stop(){},show(){}},audio:{reset(){},stop(){stopped++;},select(url){selected.push(url);}},
  fetcher:async()=>({ok:true,json:async()=>({images:items})}),reduced:()=>reduced,random:()=>.99,schedule:fn=>{timers.push(fn);return 1;},cancel(){}});
 await ui.start();assert.equal(selected[0],items[0].jingle_url);timers[0]();assert.equal(selected[1],null);
 const before=stopped;ui.stop(true);assert.equal(stopped,before+1);timers.at(-1)();assert.equal(selected.length,2);
 reduced=true;await ui.start();assert.equal(selected.length,2);
});
