(function(root,factory){
  const api=factory();
  if(typeof module==='object'&&module.exports)module.exports=api;
  else root.NewsMuncherGlowTheme=api;
})(typeof globalThis!=='undefined'?globalThis:this,function(){
  const PALETTE=[
    [62,184,255],   // sky blue
    [48,220,190],   // turquoise
    [111,225,76],   // vivid green
    [206,238,52],   // lime
    [190,93,255],   // violet
    [255,76,190],   // magenta
    [255,72,92]     // coral red
  ];
  const CONTROL_SELECTOR='.mode-nav-button, .funky-button, .gallery-arrow, .gallery-fur-control, .munge-body-button, .munge-teat, .udder-teat, .master-mute-button, .mad-helper-button';

  class GlowTheme {
    constructor({rootElement,random=Math.random,palette=PALETTE}={}){
      this.rootElement=rootElement||document.documentElement;
      this.random=random;
      this.palette=palette;
      this.index=-1;
      this.bound=false;
      this.onClick=this.onClick.bind(this);
    }
    next(){
      if(!this.palette.length)return null;
      const offset=this.index<0?Math.floor(this.random()*this.palette.length):1+Math.floor(this.random()*Math.max(1,this.palette.length-1));
      this.index=this.index<0?offset:(this.index+offset)%this.palette.length;
      const colour=this.palette[this.index];
      this.rootElement.style.setProperty('--glow-r',String(colour[0]));
      this.rootElement.style.setProperty('--glow-g',String(colour[1]));
      this.rootElement.style.setProperty('--glow-b',String(colour[2]));
      return colour.slice();
    }
    onClick(event){
      const control=event.target?.closest?.(CONTROL_SELECTOR);
      if(!control||control.disabled||control.getAttribute?.('aria-disabled')==='true')return;
      this.next();
    }
    bind(target=document){
      if(this.bound)return this;
      this.bound=true;
      this.next();
      target.addEventListener('click',this.onClick,true);
      return this;
    }
    destroy(target=document){
      if(!this.bound)return;
      target.removeEventListener('click',this.onClick,true);
      this.bound=false;
    }
  }

  if(typeof document!=='undefined'){
    const theme=new GlowTheme();
    theme.bind(document);
    globalThis.newsMuncherGlowTheme=theme;
  }
  return{GlowTheme,PALETTE,CONTROL_SELECTOR};
});
