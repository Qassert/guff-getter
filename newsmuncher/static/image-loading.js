/* Read-only entertainment: temporary images never enter rewrite metadata. */
(function(root) {
    class ImageShuffle {
        constructor({view, fetcher=()=>fetch('/temp/loading_images', {credentials:'include',cache:'no-store'}),
                     reduced=()=>false, schedule=(fn,ms)=>setTimeout(fn,ms), cancel=id=>clearTimeout(id), random=Math.random}) {
            Object.assign(this,{view,fetcher,reduced,schedule,cancel,random});
            this.revision=0;
        }
        stop(keepVisual=false) {
            this.revision++; this.cancel(this.timer);
            if (!keepVisual) this.view.stop();
        }
        async start() {
            this.stop();
            const token=this.revision;
            this.view.start();
            try {
                const response=await this.fetcher();
                const data=await response.json();
                if (token!==this.revision || !response.ok) return;
                const urls=[...new Set(data.images || [])].filter(url=>/^\/generated-images\/[a-f0-9-]+\.png$/.test(url)).slice(0,5);
                if (!urls.length) return;
                let last=null, bag=[];
                const next=()=>{
                    if (token!==this.revision) return;
                    if (!bag.length) {
                        bag=urls.slice();
                        for (let i=bag.length-1;i>0;i--) {
                            const j=Math.floor(this.random()*(i+1));
                            [bag[i],bag[j]]=[bag[j],bag[i]];
                        }
                        if (bag.length>1 && bag[0]===last) [bag[0],bag[1]]=[bag[1],bag[0]];
                    }
                    const url=bag.shift();
                    this.view.show(url, !this.reduced()); last=url;
                    if (!this.reduced() && urls.length>1) this.timer=this.schedule(next,500);
                };
                next();
            } catch (_) {} // Loader alone is valid; no retry or generation.
        }
    }
    if (typeof module !== 'undefined') module.exports={ImageShuffle};
    if (typeof document==='undefined') return;
    let layer=null, previous=null, outgoing=null;
    const panel=()=>document.getElementById('imagePanel');
    root.imageLoading=new ImageShuffle({
        reduced:()=>!!root.matchMedia?.('(prefers-reduced-motion: reduce)').matches,
        view:{
            start() {
                panel().classList.remove('hidden');
                layer=document.createElement('div');layer.className='image-loading';
                const loader=document.createElement('div');loader.className='loader image-loader';
                loader.setAttribute('role','status');loader.setAttribute('aria-label','Generating image');
                layer.appendChild(loader);panel().appendChild(layer);
            },
            show(url, animate) {
                outgoing?.remove(); outgoing=previous;
                if (outgoing) { if (animate) outgoing.className='shuffle-card shuffle-out'; else outgoing.remove(); }
                const img=new Image();img.alt='';img.className='shuffle-card'+(animate?' shuffle-in':'');
                img.onerror=()=>img.remove();img.src=url;
                layer.appendChild(img);previous=img;
            },
            stop() { layer?.remove(); layer=null; previous=null; outgoing=null; }
        }
    });
    root.addEventListener('pagehide',()=>root.imageLoading.stop());
})(typeof globalThis !== 'undefined' ? globalThis : this);
