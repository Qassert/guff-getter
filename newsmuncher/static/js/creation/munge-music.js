/* Repeating browser-side MUNGE soundtrack assembled from five saved jingles. */
(function(root) {
    const JINGLE_PATH = /^\/generated-audio\/[a-z0-9._-]+\.mp3$/i;
    const FADE_OUT_MS = 1500;
    class MungeMusic {
        constructor({contextFactory=()=>new (root.AudioContext||root.webkitAudioContext)(),
                     fetcher=(url,options)=>fetch(url,options), random=Math.random,
                     schedule=(fn,ms)=>setTimeout(fn,ms), cancel=id=>clearTimeout(id),
                     clock=()=>root.performance?.now?.()??Date.now(),logger=root.console}={}) {
            Object.assign(this,{contextFactory,fetcher,random,schedule,cancel,clock,logger});
            this.cache=new Map();this.sources=new Set();this.revision=0;this.running=false;
        }
        mark(name,details={}) {
            if(!this.timings||Object.hasOwn(this.timings,name))return;
            const elapsed=Math.round((this.clock()-this.timingOrigin)*10)/10;
            this.timings[name]=elapsed;
            this.logger?.debug?.('[munge-audio]',{milestone:name,elapsed_ms:elapsed,...details});
        }
        markApiDispatched(){this.mark('munge_api_request_dispatched');}
        shuffle(values) {
            const result=[...values];
            for(let i=result.length-1;i>0;i--){const j=Math.floor(this.random()*(i+1));[result[i],result[j]]=[result[j],result[i]];}
            return result;
        }
        async buffer(url) {
            if(!this.cache.has(url)) this.cache.set(url,(async()=>{
                this.mark('first_jingle_fetch_started',{url});
                const response=await this.fetcher(url,{credentials:'include',cache:'force-cache'});
                if(!response.ok)throw new Error('Jingle unavailable');
                const bytes=(await response.arrayBuffer()).slice(0);
                this.mark('first_jingle_fetch_completed',{url});
                const decoded=await this.context.decodeAudioData(bytes);
                this.mark('first_jingle_decoded',{url,duration:decoded.duration});
                return decoded;
            })().catch(error=>{this.cache.delete(url);throw error;}));
            return this.cache.get(url);
        }
        excerpt(buffer,clip) {
            const boundary=Math.min(.35,buffer.duration*.08);
            const usableStart=boundary,usableDuration=Math.max(.12,buffer.duration-boundary*2);
            const length=Math.min(buffer.duration,Math.max(.12,usableDuration*.5));
            const travel=Math.max(0,usableDuration-length);
            return {offset:Math.min(buffer.duration-length,usableStart+travel*clip.position),length};
        }
        voice(buffer, when, clip) {
            if(!this.running||!buffer||!Number.isFinite(buffer.duration)||buffer.duration<.12)return null;
            const {offset,length}=this.excerpt(buffer,clip);
            const source=this.context.createBufferSource(),gain=this.context.createGain();
            source.buffer=buffer;source.connect(gain);gain.connect(this.master);
            const fade=Math.min(.08,length/4);
            gain.gain.setValueAtTime(0,when);gain.gain.linearRampToValueAtTime(.22,when+fade);
            gain.gain.setValueAtTime(.22,Math.max(when+fade,when+length-fade));
            gain.gain.linearRampToValueAtTime(0,when+length);
            const voice={source,gain};this.sources.add(voice);
            source.onended=()=>{this.sources.delete(voice);source.disconnect?.();gain.disconnect?.();};
            source.start(when,offset,length);
            this.mark('first_playable_sample_scheduled',{offset,length,audio_time:when});
            if(!Object.hasOwn(this.timings,'first_sample_playback_started')){
                this.cancel(this.playbackMarkTimer);
                const delay=Math.max(0,(when-this.context.currentTime)*1000);
                this.playbackMarkTimer=this.schedule(
                    ()=>this.mark('first_sample_playback_started'),delay);
            }
            return {...voice,length};
        }
        chooseUrls(library) {
            const urls=this.shuffle(library).slice(0,5);
            if(urls.length>1&&this.previousUrls===urls.join('|'))urls.push(urls.shift());
            this.previousUrls=urls.join('|');this.selectedUrls=urls;return urls;
        }
        buildPattern(sampleCount) {
            this.tempo=96+Math.floor(this.random()*33);
            this.beatMs=Math.round(60000/this.tempo);
            if(!sampleCount){this.pattern=[];return;}
            const order=this.shuffle(Array.from({length:sampleCount},(_,index)=>index));
            this.pattern=order.map(sampleIndex=>({sampleIndex,position:this.random()}));
        }
        addBuffer(buffer, token, index) {
            if(!this.running||token!==this.revision||!Number.isFinite(buffer?.duration)||buffer.duration<.12)return false;
            this.buffers[index]=buffer;
            if(this.master)return true;
            this.master=this.context.createGain();this.master.gain.setValueAtTime(.82,this.context.currentTime);
            this.master.connect(this.context.destination);
            const firstStep=this.pattern.findIndex(hit=>hit?.sampleIndex===index);
            this.step=firstStep<0?0:firstStep;
            this.tick(token);return true;
        }
        async loadArrangement(urls, token) {
            this.buffers=new Array(urls.length);this.buildPattern(urls.length);
            const loads=urls.map((url,index)=>this.buffer(url).then(
                buffer=>this.addBuffer(buffer,token,index),()=>false));
            const results=await Promise.all(loads);
            this.mark('remaining_jingles_loaded',{
                usable:results.filter(Boolean).length,selected:urls.length});
            return results.some(Boolean);
        }
        tick(token) {
            if(!this.running||token!==this.revision||!this.pattern?.length)return;
            let hit,buffer;
            for(let checked=0;checked<this.pattern.length;checked++){
                hit=this.pattern[this.step++%this.pattern.length];
                buffer=this.buffers[hit.sampleIndex];
                if(buffer)break;
            }
            const playing=this.voice(buffer,this.context.currentTime+.025,hit);
            const seconds=playing?.length||this.beatMs/1000;
            const beats=Math.max(1,Math.round((seconds-.08)/(this.beatMs/1000)));
            this.timer=this.schedule(()=>this.tick(token),beats*this.beatMs);
        }
        async start(clickedAt=this.clock()) {
            this.stop(true);const token=++this.revision;this.running=true;
            this.timingOrigin=clickedAt;this.timings={click:0};
            this.mark('soundtrack_initialization_started');
            try {
                if(!this.context){this.context=this.contextFactory();this.mark('audio_context_created');}
                await this.context.resume?.();
                this.mark('audio_context_resumed');
                if(!this.libraryUrls){
                    this.mark('jingle_list_request_started');
                    const response=await this.fetcher('/jingles/soundtrack',{credentials:'include',cache:'force-cache'});
                    if(!response.ok)throw new Error('Jingle list unavailable');
                    const data=await response.json();
                    this.libraryUrls=[...new Set((data.jingles||[]).map(x=>x.jingle_url)
                        .filter(url=>typeof url==='string'&&JINGLE_PATH.test(url)))];
                }
                this.mark('jingle_list_available',{count:this.libraryUrls.length});
                const ready=await this.loadArrangement(this.chooseUrls(this.libraryUrls),token);
                if(!ready&&token===this.revision)this.running=false;
                return ready;
            } catch (_) { if(token===this.revision)this.stop(true);return false; }
        }
        stop(immediate=false) {
            this.running=false;this.revision++;this.cancel(this.timer);this.timer=null;
            this.cancel(this.stopTimer);this.stopTimer=null;
            this.cancel(this.playbackMarkTimer);this.playbackMarkTimer=null;
            const finish=()=>{for(const voice of [...this.sources]){try{voice.source.stop();}catch(_){}voice.source.disconnect?.();voice.gain.disconnect?.();}this.sources.clear();this.master?.disconnect?.();this.master=null;};
            if(!this.master||immediate)return finish();
            const now=this.context.currentTime;this.master.gain.cancelScheduledValues?.(now);
            this.master.gain.setValueAtTime(this.master.gain.value,now);
            this.master.gain.linearRampToValueAtTime(0,now+FADE_OUT_MS/1000);
            this.stopTimer=this.schedule(finish,FADE_OUT_MS);
        }
    }
    if(typeof module!=='undefined')module.exports={MungeMusic,JINGLE_PATH,FADE_OUT_MS};
    if(typeof document==='undefined')return;
    root.mungeMusic=new MungeMusic();
    root.addEventListener('pagehide',()=>root.mungeMusic.stop(true));
})(typeof globalThis!=='undefined'?globalThis:this);
