/* Read-only entertainment: temporary images never enter rewrite metadata. */
(function(root) {
    const LOADING_JINGLE_OFFSET_SECONDS = 2;
    const LOADING_JINGLE_FADE_MS = 100;
    class LoadingAudio {
        constructor({makeAudio=url=>new Audio(url), schedule=(fn,ms)=>setTimeout(fn,ms), cancel=id=>clearTimeout(id)}={}) {
            Object.assign(this,{makeAudio,schedule,cancel});
            this.players=new Set();this.revision=0;this.blocked=false;
        }
        dispose(player) {
            if (!this.players.delete(player)) return;
            player.timers.forEach(id=>this.cancel(id));
            player.audio.pause();player.audio.removeAttribute('src');player.audio.load();
            if (this.current===player) this.current=null;
        }
        fade(player, target, done=()=>{}) {
            const initial=player.audio.volume;
            for (let step=1;step<=4;step++) {
                const id=this.schedule(()=>{
                    player.timers.delete(id);
                    if (!this.players.has(player)) return;
                    player.audio.volume=initial+(target-initial)*step/4;
                    if (step===4) done();
                },LOADING_JINGLE_FADE_MS*step/4);
                player.timers.add(id);
            }
        }
        stop() {
            this.revision++;
            [...this.players].forEach(player=>this.dispose(player));
        }
        reset() { this.stop();this.blocked=false; }
        select(url) {
            const token=++this.revision;
            if (!url) {
                // Continue audible music, but don't start a late-loading old selection.
                if (this.current && !this.current.playing) this.dispose(this.current);
                return;
            }
            if (this.blocked) return;
            const previous=this.current;
            if (previous) {
                previous.timers.forEach(id=>this.cancel(id));previous.timers.clear();
                if (previous.playing) this.fade(previous,0,()=>this.dispose(previous));
                else this.dispose(previous);
            }
            const player={audio:this.makeAudio(url),timers:new Set(),playing:false,attempted:false};
            this.current=player;this.players.add(player);
            const audio=player.audio;
            audio.preload='auto';audio.volume=0;audio.loop=false;
            const start=async()=>{
                if (token!==this.revision || this.current!==player || player.attempted) return;
                if (!Number.isFinite(audio.duration) || audio.duration<=0) return;
                try { audio.currentTime=audio.duration>LOADING_JINGLE_OFFSET_SECONDS ? LOADING_JINGLE_OFFSET_SECONDS : 0; }
                catch (_) { return; } // A later canplay event may make seeking safe.
                player.attempted=true;
                try {
                    await audio.play();
                    if (token!==this.revision || this.current!==player) { audio.pause();this.dispose(player);return; }
                    player.playing=true;this.fade(player,1);
                } catch (error) {
                    if (token!==this.revision) return;
                    this.blocked=true;this.stop(); // Remain silent for this loading session; never retry play.
                }
            };
            audio.addEventListener('loadedmetadata',start);
            audio.addEventListener('canplay',start);
            audio.addEventListener('error',()=>this.dispose(player));
            audio.load();
            if (audio.readyState>=1) start();
        }
    }
    class ImageShuffle {
        constructor({view, fetcher=()=>fetch('/temp/loading_images', {credentials:'include',cache:'no-store'}),
                     reduced=()=>false, schedule=(fn,ms)=>setTimeout(fn,ms), cancel=id=>clearTimeout(id), random=Math.random, audio=null}) {
            Object.assign(this,{view,fetcher,reduced,schedule,cancel,random,audio});
            this.revision=0;
        }
        stop(keepVisual=false) {
            this.revision++; this.cancel(this.timer);
            this.audio?.stop();
            if (!keepVisual) this.view.stop();
        }
        async start() {
            this.stop();
            this.audio?.reset();
            const token=this.revision;
            this.view.start();
            try {
                const response=await this.fetcher();
                const data=await response.json();
                if (token!==this.revision || !response.ok) return;
                const items=new Map((data.images || []).map(item=>typeof item==='string' ? [item,{image_url:item}] : [item.image_url,item]));
                const urls=[...items.keys()].filter(url=>/^\/generated-images\/[a-f0-9-]+\.png$/.test(url)).slice(0,5);
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
                    const jingle=items.get(url).jingle_url;
                    if (this.reduced()) this.audio?.stop();
                    else this.audio?.select(/^\/generated-audio\/[a-f0-9]{24}\.mp3$/.test(jingle) ? jingle : null);
                    if (!this.reduced() && urls.length>1) this.timer=this.schedule(next,500);
                };
                next();
            } catch (_) {} // Loader alone is valid; no retry or generation.
        }
    }
    if (typeof module !== 'undefined') module.exports={ImageShuffle,LoadingAudio,LOADING_JINGLE_OFFSET_SECONDS};
    if (typeof document==='undefined') return;
    let layer=null, previous=null, outgoing=null;
    const panel=()=>document.getElementById('imagePanel');
    root.imageLoading=new ImageShuffle({
        audio:new LoadingAudio(),
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
    root.matchMedia?.('(prefers-reduced-motion: reduce)').addEventListener('change',event=>{
        if (event.matches) root.imageLoading.audio.stop();
    });
    root.addEventListener('pagehide',()=>root.imageLoading.stop());
})(typeof globalThis !== 'undefined' ? globalThis : this);
