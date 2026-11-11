const {test}=require('node:test'),assert=require('node:assert/strict');
const {Embellish}=require('../../newsmuncher/static/js/creation/embellish.js');

function setup(){
 const calls=[],renders=[],timers=[];
 const unit=kind=>({state:{can_generate:true},snapshot(){return this.state;},
  async show(){calls.push(kind+'-show');},async ensure(){calls.push(kind);this.state={[kind+'_url']:'/'+kind,can_generate:false};},
  pause(){calls.push(kind+'-pause');},isPlaying(){return false;},playForEmbellish(){calls.push('play-'+kind);}});
 const media={Jingle:unit('jingle'),Video:unit('video')};
 media.Jingle.beginEmbellish=()=>calls.push('jingle-armed');
 media.Video.show=async()=>calls.push('video-show');
 media.Jingle.replace=async()=>{calls.push('jingle-replace');media.Jingle.state={jingle_url:'/new',can_generate:false};};
 const image=async(_id,_seq,replace)=>{calls.push(replace?'replace-image':'image');return{reveal:async()=>calls.push('reveal')}};
 const ui=new Embellish({media:()=>media,image,persist:async()=>calls.push('persist'),render:x=>renders.push(x),
  loading:x=>calls.push(x?'loading':'loaded'),schedule:fn=>{timers.push(fn);return timers.length;},cancel(){}});
 return{ui,media,calls,renders,timers};
}

test('nomination reveals still before requesting dependent video',async()=>{
 const t=setup();t.ui.show({nominated:true,rewrite_id:'r'});await t.ui.nominate({rewrite_id:'r',sequence:1});
 assert(t.calls.includes('jingle'));assert(!t.calls.includes('narration'));
 assert(t.calls.indexOf('reveal')<t.calls.indexOf('video-show'));
 assert(t.calls.indexOf('loaded')<t.calls.indexOf('video-show'));
});

test('re-embellish persists first and replaces jingle without narration',async()=>{
 const t=setup();t.ui.show({nominated:true,rewrite_id:'r',image_url:'/old'});await t.ui.reembellish();
 assert(t.calls.indexOf('persist')<t.calls.indexOf('replace-image'));
 assert(!t.calls.some(call=>call.includes('narration')));
 assert(t.calls.includes('jingle-replace'));assert(t.calls.includes('video'));
});

test('ready jingle autoplays without narration',async()=>{
 const t=setup(); let ready;
 t.media.Jingle.ensure=()=>new Promise(resolve=>ready=()=>{t.media.Jingle.state={jingle_url:'/music',can_generate:false};resolve();});
 t.ui.show({nominated:true,rewrite_id:'r'});const running=t.ui.nominate({rewrite_id:'r',sequence:1});
 ready();await running;await Promise.resolve();
 assert(t.calls.includes('play-jingle'));assert(!t.calls.some(call=>call.includes('narration')));
});

test('loading audio owns playback until the real image is displayed and stopped',async()=>{
 const t=setup();let reveal;
 t.ui.image=async()=>({reveal:()=>new Promise(resolve=>reveal=()=>{t.calls.push('reveal');resolve();})});
 t.media.Jingle.ensure=async()=>{t.calls.push('jingle-ready');t.media.Jingle.state={jingle_url:'/music',can_generate:false};};
 const running=t.ui.nominate({rewrite_id:'r',sequence:1});
 await Promise.resolve();await Promise.resolve();
 assert(!t.calls.includes('play-jingle'));
 reveal();await running;await Promise.resolve();
 assert(t.calls.indexOf('loaded')<t.calls.indexOf('play-jingle'));
 assert(t.calls.indexOf('reveal')<t.calls.indexOf('play-jingle'));
 assert.equal(t.calls.filter(call=>call==='play-jingle').length,1);
});

test('queued video does not hold back the still and stale completion is ignored',async()=>{
 const t=setup();t.media.Video.ensure=async()=>{t.calls.push('video');t.media.Video.state={video_status:'queued'};};
 t.ui.show({nominated:true,rewrite_id:'r'});await t.ui.nominate({rewrite_id:'r',sequence:1});
 assert(t.calls.includes('reveal'));assert(t.calls.includes('loaded'));
 t.ui.show(null);t.media.Video.state={video_url:'/done'};t.timers.at(-1)();
 assert(!t.renders.at(-1).available);
});


test('out-of-order images keep B identity and never start stale A video',async()=>{
 const t=setup(),pending={},ids=[];
 t.ui.image=id=>new Promise(resolve=>pending[id]=()=>resolve({reveal:async()=>ids.push('reveal-'+id)}));
 t.media.Video.show=async data=>ids.push('video-'+data.rewrite_id);
 const a=t.ui.nominate({rewrite_id:'A',sequence:1});
 t.ui.show(null);const b=t.ui.nominate({rewrite_id:'B',sequence:2});
 pending.B();await b;pending.A();await a;
 assert.deepEqual(ids,['reveal-B','video-B']);
});

test('reset during delayed video status cannot start a different story video',async()=>{
 const t=setup();let ready;
 t.media.Video.show=()=>new Promise(resolve=>ready=resolve);
 const a=t.ui.nominate({rewrite_id:'A',sequence:1});
 for(let i=0;i<5&&!ready;i++)await Promise.resolve();
 assert(ready);t.ui.show(null);ready();await a;
 assert(!t.calls.includes('video'));
});
