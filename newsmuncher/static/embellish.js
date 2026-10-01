(function(root){
 class Embellish{
  constructor({media,image,render,loading=()=>{},schedule=(f,n)=>setTimeout(f,n),cancel=t=>clearTimeout(t)}){Object.assign(this,{media,image,render,loading,schedule,cancel});this.revision=0;}
  show(data){this.revision++;this.cancel(this.timer);this.data=data;this.running=false;this.render({available:!!(data?.nominated&&data?.image_url),message:''});}
  terminal(s,k){return !!(s?.[k+'_url']||(!s?.pending&&!['queued','started','submitted'].includes(s?.[k+'_status'])&&(s?.can_generate===false||s?.message)));}
  async run(replace=false){if(this.running||!this.data?.rewrite_id)return;this.running=true;this.errors='';const token=++this.revision,id=this.data.rewrite_id,sequence=(root.creationContext?.().sequence??this.data.sequence),m=this.media();this.loading(true);this.render({available:false,message:''});
   if(replace)m.Narration.pause();
   const audio=replace?null:Promise.allSettled([m.Narration.ensure(),m.Jingle.ensure()]);let prepared;
   try{prepared=await this.image(id,sequence,replace);}catch(e){this.errors='Image unavailable. Existing media retained.';}
   if(token!==this.revision)return;
   if(prepared){if(replace)await Promise.allSettled([m.Jingle.replace()]);await m.Video.show({nominated:true,rewrite_id:id});await m.Video.ensure();}
   if(audio)await Promise.allSettled([audio]);if(token!==this.revision)return;this.prepared=prepared;this.wait(token);
  }
  nominate(data){this.data={nominated:true,...data};return this.run(false);}
  reembellish(){return this.run(true);}
  wait(token,polls=0){if(token!==this.revision)return;const m=this.media(),done=this.terminal(m.Narration.snapshot(),'narration')&&this.terminal(m.Jingle.snapshot(),'jingle')&&this.terminal(m.Video.snapshot(),'video');if(done||polls>=720)return this.finish(token);this.timer=this.schedule(()=>this.wait(token,polls+1),1000);}
  finish(token){if(token!==this.revision)return;this.running=false;this.prepared?.reveal();this.loading(false);this.render({available:true,message:this.errors||''});const m=this.media();Promise.resolve(m.Narration.snapshot()?.narration_url&&m.Narration.playForEmbellish?.()).then(()=>{if(token===this.revision&&m.Jingle.snapshot()?.jingle_url)m.Jingle.playForEmbellish?.();});}
 }
 if(typeof module!=='undefined')module.exports={Embellish};if(typeof document==='undefined')return;
 root.embellishUI=new Embellish({media:()=>({Narration:narrationUI,Jingle:jingleUI,Video:root.videoUI}),image:(...a)=>root.generateCreationImage(...a),loading(on){if(on){showLoader();imageLoading.start();}else{hideLoader();imageLoading.stop();}},render({available,message}){const b=document.getElementById('embellishButton'),s=document.getElementById('embellishStatus');b.hidden=!available;b.textContent='RE-EMBELLISH';s.hidden=!message;s.textContent=message||'';}});
})(typeof globalThis!=='undefined'?globalThis:this);
