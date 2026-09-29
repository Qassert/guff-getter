const {test}=require('node:test'), assert=require('node:assert/strict');
const {Embellish}=require('../newsmuncher/static/embellish.js');
function setup() {
 const calls=[], states=[], timers=[];
 const media=Object.fromEntries(['Narration','Video','Jingle'].map(name=>[name,{
   state:{}, snapshot(){return this.state;}, async ensure(){calls.push(name);this.state[name.toLowerCase()+'_url']='/saved';}
 }]));
 const ui=new Embellish({media:()=>media, render:data=>states.push(data),schedule:fn=>{timers.push(fn);return timers.length;},cancel(){}});
 return {ui,media,calls,states,timers};
}
test('only explicit nominated action coordinates all existing controllers once',async()=>{
 const t=setup();t.ui.show({nominated:false,rewrite_id:'a'});await t.ui.act();assert.equal(t.calls.length,0);
 t.ui.show({nominated:true,rewrite_id:'a'});assert.equal(t.calls.length,0);assert(t.states.at(-1).available);
 await Promise.all([t.ui.act(),t.ui.act(),t.ui.act()]);
 assert.deepEqual(t.calls,['Narration','Video','Jingle']);assert.equal(t.states.at(-1).label,'EMBELLISHED');
});
test('failure isolated; queued components keep independent statuses until complete',async()=>{
 const t=setup();t.media.Narration.ensure=async()=>{throw Error('unavailable');};
 t.media.Video.ensure=async()=>{t.media.Video.state={video_status:'queued'};};
 t.ui.show({nominated:true,rewrite_id:'a'});await t.ui.act();
 assert.equal(t.states.at(-1).label,'EMBELLISHING…');
 assert.match(t.states.at(-1).message,/Narration: unavailable/);
 assert.doesNotMatch(t.states.at(-1).message,/Jingle: ready/);
 t.media.Video.state={video_url:'/saved'};t.timers.at(-1)();
 assert.equal(t.states.at(-1).label,'EMBELLISH — CHECK STATUS');
});
test('rewrite switch cancels aggregate timers and late completions',async()=>{
 const t=setup();let release;t.media.Narration.ensure=()=>new Promise(resolve=>release=resolve);
 t.ui.show({nominated:true,rewrite_id:'a'});const action=t.ui.act();
 t.ui.show(null);release();await action;t.timers[0]();assert(!t.states.at(-1).available);
});
