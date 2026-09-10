const assert = require('node:assert/strict'), fs=require('node:fs'), vm=require('node:vm');
const flush = () => new Promise(resolve=>setImmediate(resolve));
function setup() {
 const ids=['jingleControls','jingleButton','jingleStop','jingleMessage'];
 const nodes=Object.fromEntries(ids.map(id=>[id,{hidden:true,textContent:'',disabled:false}]));
 const calls=[], audios=[], timers=[];
 let answer={jingle_status:'none',can_generate:true}, resolvePost;
 const context={
  document:{getElementById:id=>nodes[id]},
  setTimeout:fn=>{timers.push(fn);return 1;},clearTimeout(){},
  Audio:class {constructor(url){this.url=url;audios.push(this);}play(){this.played=true;return Promise.resolve();}pause(){this.paused=true;}},
  fetch(url, options) {
   calls.push({url,options});
   if(options.method==='POST')return new Promise(resolve=>{resolvePost=resolve;});
   return Promise.resolve({ok:true,json:async()=>answer});
  }
 };
 vm.createContext(context);
 vm.runInContext(fs.readFileSync('newsmuncher/static/jingles.js','utf8')+'\nglobalThis.ui=jingleUI;',context);
 return {ui:context.ui,nodes,calls,audios,timers,setAnswer:v=>answer=v,
  complete:(data,ok=true)=>resolvePost({ok,json:async()=>data})};
}
(async()=>{
 let t=setup();
 t.ui.show({nominated:false,rewrite_id:'draft'});
 assert(t.nodes.jingleControls.hidden);assert.equal(t.calls.length,0);
 t.ui.show({nominated:true,rewrite_id:'one'});await flush();
 assert.equal(t.nodes.jingleButton.textContent,'MAKE JINGLE');
 assert.equal(t.nodes.jingleButton.disabled,false);
 t.ui.act();t.ui.act();
 assert.equal(t.calls.filter(c=>c.options.method==='POST').length,1);
 assert.equal(t.nodes.jingleButton.textContent,'MAKING JINGLE…');
 assert(t.nodes.jingleButton.disabled);
 t.complete({jingle_status:'complete',jingle_url:'/generated-audio/one.mp3',can_generate:false});await flush();
 assert.equal(t.nodes.jingleButton.textContent,'▶ PLAY JINGLE');
 const before=t.calls.length;
 await t.ui.act();await t.ui.act();
 assert.equal(t.calls.length,before);assert.equal(t.audios.length,1);
 assert(t.audios[0].played);t.ui.stop();assert(t.audios[0].paused);
 // Restore a stored jingle without POST.
 t=setup();t.setAnswer({jingle_status:'complete',jingle_url:'/generated-audio/stored.mp3'});
 t.ui.show({nominated:true,rewrite_id:'saved'});await flush();
 assert.equal(t.nodes.jingleButton.textContent,'▶ PLAY JINGLE');
 assert(!t.calls.some(c=>c.options.method==='POST'));
 // Late old response cannot attach to a new rewrite.
 t=setup();t.ui.show({nominated:true,rewrite_id:'old'});await flush();
 t.ui.act();t.ui.show({nominated:false,rewrite_id:'new'});
 t.complete({jingle_url:'/old.mp3'});await flush();
 assert(t.nodes.jingleControls.hidden);assert.equal(t.audios.length,0);
 // Quota and uncertain outcomes never auto-submit.
 t=setup();t.ui.show({nominated:true,rewrite_id:'capped'});await flush();
 t.ui.act();t.complete({detail:'Daily limit reached'},false);await flush();
 assert(t.nodes.jingleButton.disabled);
 await t.ui.act();assert.equal(t.calls.filter(c=>c.options.method==='POST').length,1);
 assert(t.nodes.jingleMessage.textContent.includes('Daily limit'));
 console.log('Jingle UI: nomination gating, loading, single POST, stored PLAY/STOP, restore, stale responses and cap passed.');
})().catch(error=>{console.error(error);process.exitCode=1;});
