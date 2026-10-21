const {test}=require('node:test'),assert=require('node:assert/strict');
const {MungeMusic,FADE_OUT_MS,CLIP_OVERLAP_SECONDS,SCHEDULE_LOOKAHEAD_SECONDS}=require('../../newsmuncher/static/js/creation/munge-music.js');

class Param{constructor(){this.value=1;this.calls=[];}setValueAtTime(v,t){this.value=v;this.calls.push(['set',v,t]);}linearRampToValueAtTime(v,t){this.value=v;this.calls.push(['ramp',v,t]);}cancelScheduledValues(t){this.calls.push(['cancel',t]);}}
class Context{
 constructor(duration=8){this.currentTime=0;this.duration=duration;this.destination={};this.starts=[];this.startedBuffers=[];this.gains=[];}
 resume(){this.resumed=true;return Promise.resolve();}
 decodeAudioData(){return Promise.resolve({duration:this.duration});}
 createGain(){const node={gain:new Param(),connect(){},disconnect(){this.disconnected=true;}};this.gains.push(node);return node;}
 createBufferSource(){const context=this;return{connect(){},disconnect(){this.disconnected=true;},start(...args){context.starts.push(args);context.startedBuffers.push(this.buffer);},stop(){this.stopped=true;this.onended?.();}};}
}
function response(value){return{ok:true,json:async()=>value,arrayBuffer:async()=>new ArrayBuffer(8)};}
function setup({duration=8,random=()=>0}={}){
 const context=new Context(duration),timers=[],cancelled=[];
 const jingles=Array.from({length:7},(_,i)=>({jingle_url:`/generated-audio/jingle-${i}.mp3`}));
 const requests=[];const fetcher=async url=>{requests.push(url);return response(url==='/jingles/soundtrack'?{jingles}:null);};
 const music=new MungeMusic({contextFactory:()=>context,fetcher,random,
  schedule:(fn,ms)=>{const item={fn,ms,id:timers.length+1};timers.push(item);return item.id;},
  cancel:id=>cancelled.push(id),logger:{debug(){}}});
 return{music,context,timers,requests,cancelled};
}

test('one MUNGE selects five jingles, unlocks audio and schedules a bounded snippet',async()=>{
 const t=setup();assert.equal(await t.music.start(),true);assert(t.context.resumed);
 assert.equal(t.music.selectedUrls.length,5);assert.equal(new Set(t.music.selectedUrls).size,5);
 assert.equal(t.requests.filter(x=>x!=='/jingles/soundtrack').length,5);assert.equal(t.context.starts.length,1);
 const [when,offset,length]=t.context.starts[0];assert(when>=0);assert(offset>=0&&offset+length<=8);assert(length>0);
 assert(Math.abs(length-3.65)<.001);
});

test('one recognisable pattern repeats without progressive chaos',async()=>{
 const t=setup({random:()=>0});await t.music.start();
 const pattern=JSON.stringify(t.music.pattern);
 for(let index=0;index<40;index++)t.timers.at(-1).fn();
 assert.equal(JSON.stringify(t.music.pattern),pattern);
 assert(t.music.tempo>=96&&t.music.tempo<=128);
 assert(t.context.starts.length<=41);
 assert.equal(t.music.master.gain.value,.82);
});

test('consecutive excerpts overlap by 500ms with complementary gain ramps',async()=>{
 const t=setup();await t.music.start();
 const firstVoice=[...t.music.sources][0],firstStart=t.context.starts[0][0];
 const transition=t.timers.find(timer=>Math.abs(timer.ms-
  (firstStart+3.65-CLIP_OVERLAP_SECONDS-SCHEDULE_LOOKAHEAD_SECONDS)*1000)<.001);
 assert(transition);transition.fn();
 const voices=[...t.music.sources],secondVoice=voices[1];
 assert.equal(t.context.starts.length,2);
 const secondStart=t.context.starts[1][0];
 assert(Math.abs((firstStart+3.65)-secondStart-CLIP_OVERLAP_SECONDS)<.001);
 assert.deepEqual(firstVoice.gain.gain.calls.slice(-2),[
  ['set',.22,firstStart+3.15],['ramp',0,firstStart+3.65]
 ]);
 assert.deepEqual(secondVoice.gain.gain.calls.slice(0,2),[
  ['set',0,secondStart],['ramp',.22,secondStart+CLIP_OVERLAP_SECONDS]
 ]);
});

test('very short clips use a bounded half-duration crossfade',async()=>{
 const t=setup({duration:.2});await t.music.start();
 const [,offset,length]=t.context.starts[0];
 assert.equal(length,.12);assert(offset>=0);
 const transition=t.timers.find(timer=>timer.ms===0);
 assert(transition);transition.fn();assert.equal(t.context.starts.length,2);
 const second=[...t.music.sources][1];
 const secondStart=t.context.starts[1][0];
 const [initial,ramp]=second.gain.gain.calls;
 assert.deepEqual(initial,['set',0,secondStart]);
 assert.deepEqual(ramp.slice(0,2),['ramp',.22]);
 assert(Math.abs(ramp[2]-(secondStart+.06))<.0001);
});

test('short or unavailable audio fails silently and never blocks generation',async()=>{
 const short=setup({duration:.08});assert.equal(await short.music.start(),false);assert.equal(short.context.starts.length,0);
 const broken=setup();broken.music.fetcher=async()=>({ok:false});assert.equal(await broken.music.start(),false);
 assert.equal(broken.music.running,false);
});

test('stop fades for 1.5 seconds while sources play, then releases every source',async()=>{
 const t=setup();await t.music.start();const voices=[...t.music.sources];t.music.stop();
 assert.equal(t.music.running,false);assert(t.cancelled.length>0);
 assert(voices.every(voice=>!voice.source.stopped));
 assert.deepEqual(t.music.master.gain.calls.slice(-3),[
  ['cancel',0],['set',.82,0],['ramp',0,1.5]
 ]);
 const cleanup=t.timers.find(timer=>timer.ms===FADE_OUT_MS);assert(cleanup);cleanup.fn();
 assert.equal(t.music.sources.size,0);assert(voices.every(voice=>voice.source.stopped));
});

test('a new MUNGE immediately cleans a fading soundtrack before starting another',async()=>{
 const t=setup();await t.music.start();const oldVoices=[...t.music.sources];t.music.stop();
 const pendingCleanup=t.timers.find(timer=>timer.ms===FADE_OUT_MS);
 const restarting=t.music.start();await restarting;
 assert(t.cancelled.includes(pendingCleanup.id));
 assert(oldVoices.every(voice=>voice.source.stopped));
 assert(t.music.running);assert(t.music.master);
});

test('MUNGE Web Audio registers a dedicated master-mute gain and releases it',async()=>{
 const previous=globalThis.NewsMuncherAudio,registered=[],released=[];
 globalThis.NewsMuncherAudio={registerGain(node,value){registered.push({node,value});node.gain.setValueAtTime(0,0);},
  unregisterGain(node){released.push(node);}};
 try {
  const t=setup();await t.music.start();
  assert.equal(registered.length,1);assert.equal(registered[0].node,t.music.muteGain);
  assert.equal(registered[0].value,1);assert.equal(t.music.muteGain.gain.value,0);
  assert.equal(t.music.master.gain.value,.82,'creative master volume remains independent');
  const muteGain=t.music.muteGain;t.music.stop(true);
  assert.deepEqual(released,[muteGain]);assert.equal(muteGain.disconnected,true);
 } finally { globalThis.NewsMuncherAudio=previous; }
});

test('successive starts replace playback and create fresh arrangements while reusing decoded cache',async()=>{
 let values=[0,.2,.4,.6,.8,.1,.3,.5,.7,.9],index=0;const t=setup({random:()=>values[index++%values.length]});
 await t.music.start();const first=[...t.music.selectedUrls],firstPattern=JSON.stringify(t.music.pattern),audioFetches=t.requests.filter(x=>x!=='/jingles/soundtrack').length;
 const starts=t.context.starts.length,secondStart=t.music.start();
 await new Promise(resolve=>setImmediate(resolve));
 assert(t.context.starts.length>starts);
 await secondStart;assert.notDeepEqual(t.music.selectedUrls,first);
 assert.notEqual(JSON.stringify(t.music.pattern),firstPattern);
 assert(t.requests.filter(x=>x!=='/jingles/soundtrack').length<=audioFetches+5);
 assert.equal(t.requests.filter(x=>x==='/jingles/soundtrack').length,1);
});

test('playback starts with the first decoded sample and later samples join the arrangement',async()=>{
 const t=setup(),resolvers=[];
 t.context.decodeAudioData=()=>new Promise(resolve=>resolvers.push(resolve));
 const starting=t.music.start();
 await new Promise(resolve=>setImmediate(resolve));
 assert.equal(resolvers.length,5);
 resolvers[0]({duration:8});
 await new Promise(resolve=>setImmediate(resolve));
 assert.equal(t.context.starts.length,1);assert.equal(t.music.buffers.filter(Boolean).length,1);
 const pattern=JSON.stringify(t.music.pattern),step=t.music.step;
 const lateBuffer={duration:8};resolvers[1](lateBuffer);
 await new Promise(resolve=>setImmediate(resolve));
 assert.equal(t.music.buffers.filter(Boolean).length,2);
 assert.equal(JSON.stringify(t.music.pattern),pattern);assert.equal(t.music.step,step);
 for(let index=0;index<t.music.pattern.length&&!t.context.startedBuffers.includes(lateBuffer);index++)t.timers.at(-1).fn();
 assert(t.context.startedBuffers.includes(lateBuffer));
 resolvers.slice(2).forEach(resolve=>resolve({duration:8}));
 assert.equal(await starting,true);assert.equal(t.music.buffers.filter(Boolean).length,5);
});

test('excerpt duration is half the decoded usable audio for short and long jingles',()=>{
 const t=setup();
 for(const duration of [6,8,10]){
  const excerpt=t.music.excerpt({duration},{position:.5});
  const boundary=Math.min(.35,duration*.08);
  assert(Math.abs(excerpt.length-(duration-boundary*2)*.5)<.001);
  assert(excerpt.offset>=boundary);
  assert(excerpt.offset+excerpt.length<=duration-boundary+.001);
 }
});

test('startup diagnostics cover click through playback without delaying API dispatch',async()=>{
 let now=100;const t=setup();t.music.clock=()=>++now;
 const starting=t.music.start(100);t.music.markApiDispatched();
 assert(t.music.timings.munge_api_request_dispatched<
        (t.music.timings.jingle_list_available??Infinity));
 await starting;
 t.timers.find(timer=>timer.ms<=30)?.fn();
 for(const milestone of ['soundtrack_initialization_started','audio_context_created',
  'audio_context_resumed','jingle_list_available','first_jingle_fetch_started',
  'first_jingle_fetch_completed','first_jingle_decoded','first_playable_sample_scheduled',
  'first_sample_playback_started','remaining_jingles_loaded'])assert(milestone in t.music.timings);
});
