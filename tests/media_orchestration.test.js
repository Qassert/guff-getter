const {test}=require('node:test'), assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const {Embellish}=require('../newsmuncher/static/embellish.js');
const {AnimationUI}=require('../newsmuncher/static/video.js');
function setup(mode='missing') {
 const nodes={},calls=[],audios=[];
 const get=id=>nodes[id] ||= {hidden:true,paused:true,value:'body',textContent:'...title...',
   events:{},addEventListener(name,fn){this.events[name]=fn;},removeEventListener(name,fn){if(this.events[name]===fn)delete this.events[name];},
   pause(){this.paused=true;},plays:0,async play(){this.plays++;this.paused=false;},load(){},removeAttribute(k){delete this[k];},getAttribute(k){return this[k];}};
 const fetcher=async(url,opts={})=>{
   calls.push([url,opts.method||'GET']);
   if(url==='/jingles/') return {ok:true,json:async()=>({jingles:[]})};
   const kind=url.startsWith('/narrations')?'narration':url.startsWith('/videos')?'video':'jingle';
   const ready=mode==='saved'||opts.method==='POST';
   return {ok:true,json:async()=>({entry_id:'entry',can_generate:mode==='missing'&&!ready,
     [kind+'_status']:ready?'complete':mode==='working'?'started':'none',
     ...(ready?{[kind+'_url']:'/saved-'+kind}:{}),voice_name:'Marin'})};
 };
 const context={document:{getElementById:get},fetch:fetcher,setTimeout:()=>1,clearTimeout(){},
   Audio:class{constructor(){this.paused=true;audios.push(this);}async play(){this.paused=false;this.played=true;}pause(){this.paused=true;}}};
 vm.createContext(context);
 vm.runInContext(fs.readFileSync('newsmuncher/static/narration.js','utf8')+fs.readFileSync('newsmuncher/static/jingles.js','utf8')+'\nthis.narration=narrationUI;this.jingle=jingleUI;',context);
 const video=new AnimationUI({view:{render(){},stop(){}},fetcher,schedule:()=>1,cancel(){}});
 const states=[];const ui=new Embellish({media:()=>({Narration:context.narration,Jingle:context.jingle,Video:video}),render:s=>states.push(s),schedule:()=>1,cancel(){}});
 return {ui,video,context,calls,nodes,audios,states};
}
for(const mode of ['missing','saved','working']) test(`real controllers reuse existing paths: ${mode}`,async()=>{
 const t=setup(mode), data={nominated:true,rewrite_id:'creation'};
 const showing=t.context.narration.show(data);t.context.jingle.show(data);const viewing=t.video.show(data);
 t.ui.show(data);const first=t.ui.act();await t.ui.act();await first;await showing;await viewing;
 const posts=t.calls.filter(x=>x[1]==='POST');
 assert.equal(posts.length,mode==='missing'?3:0);
 if(mode!=='working') {
   await new Promise(setImmediate);
   assert.equal(t.states.at(-1).label,'EMBELLISHED');
   assert.equal(t.nodes.narrationAudio.plays,1);assert(t.nodes.narrationAudio.hidden);
   assert.equal(t.audios.length,0);
   t.nodes.narrationAudio.events.ended();await new Promise(setImmediate);
   assert.equal(t.audios.length,1);assert(t.audios[0].played);
 }
 await t.ui.act();assert.equal(t.calls.filter(x=>x[1]==='POST').length,posts.length);
});
