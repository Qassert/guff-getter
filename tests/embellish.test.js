const {test}=require('node:test'),assert=require('node:assert/strict');
const {Embellish}=require('../newsmuncher/static/embellish.js');
function setup(){
 const calls=[],renders=[],timers=[];
 const unit=(kind)=>({state:{can_generate:true},snapshot(){return this.state;},async ensure(){calls.push(kind);this.state={[kind+'_url']:'/'+kind,can_generate:false};},pause(){}});
 const media={Narration:unit('narration'),Jingle:unit('jingle'),Video:unit('video')};
 media.Video.show=async()=>calls.push('video-show');media.Jingle.replace=async()=>{calls.push('jingle-replace');media.Jingle.state={jingle_url:'/new'};};
 const image=async(_id,_seq,replace)=>{calls.push(replace?'replace-image':'image');return{reveal:()=>calls.push('reveal')}};
 const ui=new Embellish({media:()=>media,image,render:x=>renders.push(x),loading:x=>calls.push(x?'loading':'loaded'),schedule:fn=>{timers.push(fn);return timers.length;},cancel(){}});
 return{ui,media,calls,renders,timers};
}
test('nomination starts narration and jingle with image, then video after image',async()=>{const t=setup();t.ui.show({nominated:true,rewrite_id:'r'});await t.ui.nominate({rewrite_id:'r',sequence:1});assert(t.calls.indexOf('video-show')>t.calls.indexOf('image'));assert(t.calls.includes('narration'));assert(t.calls.includes('jingle'));assert(t.calls.includes('reveal'));});
test('re-embellish replaces image then jingle and video while retaining narration',async()=>{const t=setup();t.ui.show({nominated:true,rewrite_id:'r',image_url:'/old'});t.media.Narration.state={narration_url:'/voice'};await t.ui.reembellish();assert(t.calls.indexOf('jingle-replace')>t.calls.indexOf('replace-image'));assert(!t.calls.includes('narration'));assert(t.calls.includes('video'));});
test('busy media keeps loading until terminal and stale timer is ignored',async()=>{const t=setup();t.media.Video.ensure=async()=>{t.calls.push('video');t.media.Video.state={video_status:'queued'};};t.ui.show({nominated:true,rewrite_id:'r'});await t.ui.nominate({rewrite_id:'r',sequence:1});assert.equal(t.calls.at(-1),'video');t.ui.show(null);t.media.Video.state={video_url:'/done'};t.timers.at(-1)();assert(!t.calls.includes('reveal'));});
