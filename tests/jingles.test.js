const assert = require('node:assert/strict'), fs=require('node:fs'), vm=require('node:vm');
const flush = () => new Promise(resolve=>setImmediate(resolve));
function setup() {
 const ids=['jingleControls','jingleButton','jingleStop','jingleMessage','crazyTitleBox','crazyExtractBox'];
 const nodes=Object.fromEntries(ids.map(id=>[id,{hidden:true,textContent:'',value:'',disabled:false,children:[],replaceChildren(){this.children=[];},appendChild(child){this.children.push(child);}}]));
 const calls=[], audios=[], timers=[];
 let savedAnswer=null;
 let answer={jingle_status:'none',can_generate:true}, resolvePost;
 const context={
  document:{getElementById:id=>nodes[id],createElement:()=>({})},
  setTimeout:fn=>{timers.push(fn);return 1;},clearTimeout(){},
  Audio:class {constructor(url){this.url=url;this.paused=true;audios.push(this);}play(){this.played=true;this.paused=false;return Promise.resolve();}pause(){this.paused=true;}},
  fetch(url, options) {
   calls.push({url,options});
   if(options.method==='POST')return new Promise(resolve=>{resolvePost=resolve;});
   return Promise.resolve({ok:true,json:async()=>url === '/jingles/' && savedAnswer ? savedAnswer : answer});
  }
 };
 vm.createContext(context);
 vm.runInContext(fs.readFileSync('newsmuncher/static/jingles.js','utf8')+'\nglobalThis.ui=jingleUI;',context);
 return {ui:context.ui,nodes,calls,audios,timers,setAnswer:v=>answer=v,setSaved:v=>savedAnswer=v,
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
 t.setSaved({jingles:[{entry_id:'one',title:'New jingle',jingle_url:'/generated-audio/one.mp3'}]});
 t.complete({jingle_status:'complete',jingle_url:'/generated-audio/one.mp3',can_generate:false});await flush();
 assert.equal(t.nodes.jingleButton.textContent,'▶ PLAY JINGLE');
 assert.equal(t.nodes.savedJingleSelect, undefined);
 assert.equal(t.nodes.savedJingles, undefined);
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

 // Fresh session / refresh: backend discovery finds saved jingle and hydrates existing control.
 t=setup();
 t.nodes.crazyTitleBox.textContent = '...Original Title...';
 t.nodes.crazyExtractBox.value = 'Original extract body';
 t.setAnswer({jingles:[{rewrite_id:'persistent',title:'Saved title from backend',
   jingle_url:'/generated-audio/persistent.mp3',text_changed:true}]});
 await t.ui.discover();

 // 1. exactly one jingle control is visible after refresh
 assert.equal(t.nodes.jingleControls.hidden, false);
 assert.equal(t.nodes.savedJingles, undefined);

 // 2. no Saved jingles selector/dropdown is rendered
 assert.equal(t.nodes.savedJingleSelect, undefined);

 // 3. discovery does not render the nomination title
 assert(!JSON.stringify(t.nodes).includes('Saved title from backend'));

 // 4. discovered audio hydrates the existing jingle control
 assert.equal(t.nodes.jingleButton.textContent, '▶ PLAY JINGLE');
 assert.equal(t.nodes.jingleButton.disabled, false);
 assert(t.nodes.jingleMessage.textContent.includes('earlier nominated text'));

 // 5. PLAY/STOP works through that control
 await t.ui.act();
 assert.equal(t.audios[0].url, '/generated-audio/persistent.mp3');
 assert(t.audios[0].played);
 assert.equal(t.nodes.jingleStop.hidden, false);
 await t.ui.act(); // clicking control again stops
 assert(t.audios[0].paused);
 assert.equal(t.nodes.jingleStop.hidden, true);
 await t.ui.act(); // starts playing again
 assert(!t.audios[0].paused);
 t.ui.stop(); // stop() also stops
 assert(t.audios[0].paused);
 assert.equal(t.nodes.jingleStop.hidden, true);

 // 6. displayed rewrite/title remains untouched
 assert.equal(t.nodes.crazyTitleBox.textContent, '...Original Title...');
 assert.equal(t.nodes.crazyExtractBox.value, 'Original extract body');

 // A nomination refresh retains playback control and updates warning if text matches.
 t.setSaved({jingles:[{rewrite_id:'persistent',title:'Edited title',
   jingle_url:'/generated-audio/persistent.mp3',text_changed:false}]});
 await t.ui.discover();
 assert.equal(t.nodes.jingleMessage.textContent, '');
 assert(!JSON.stringify(t.nodes).includes('Edited title'));

 // Unnominated draft is not hydrated by discovery
 t.ui.show({nominated: false, rewrite_id: 'draft'});
 assert(t.nodes.jingleControls.hidden);
 await t.ui.discover();
 assert(t.nodes.jingleControls.hidden);

 // Refresh flow: entry restored and displayed with rewrite_id, then discovery hydrates it.
 t=setup();
 t.nodes.crazyTitleBox.textContent = '...Persisted Rewrite Title...';
 t.nodes.crazyExtractBox.value = 'Persisted rewrite extract';
 t.ui.show({nominated: true, rewrite_id: 'restored-nomination'});
 t.setSaved({jingles:[{rewrite_id:'restored-nomination',title:'Ignored Backend Title',
   jingle_url:'/generated-audio/restored.mp3',text_changed:false}]});
 await t.ui.discover();
 assert.equal(t.nodes.jingleControls.hidden, false);
 assert.equal(t.nodes.jingleButton.textContent, '▶ PLAY JINGLE');
 assert.equal(t.nodes.crazyTitleBox.textContent, '...Persisted Rewrite Title...');
 assert.equal(t.nodes.crazyExtractBox.value, 'Persisted rewrite extract');
 assert(!JSON.stringify(t.nodes).includes('Ignored Backend Title'));
 await t.ui.act();
 assert.equal(t.audios[0].url, '/generated-audio/restored.mp3');
 t.ui.stop();
 assert(t.audios[0].paused);

 console.log('Jingle UI: nomination gating, loading, single POST, stored PLAY/STOP, restore, stale responses, cap, and single-control discovery passed.');
})().catch(error=>{console.error(error);process.exitCode=1;});
