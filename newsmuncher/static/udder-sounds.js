/* Polyphonic, interaction-only sound effects for the Creator udder. */
(function(root) {
    const SOUND_ROOT = '/static/audio/udder/';
    const SUSPENSE_SOUND = 'suspense.wav';
    const MIXKIT_SOUNDS = Object.freeze([
        'mixkit-wet-accident-fart-3041.wav',
        'mixkit-cartoon-catapult-737.wav',
        'mixkit-cartoon-fail-blow-fart-3053.wav',
        'mixkit-long-kiss-clean-sound-2188.wav',
        'mixkit-falling-into-mud-surface-385.wav',
        'mixkit-cartoon-fart-sound-2891.wav',
        'mixkit-funny-clown-horn-sounds-2886.wav',
        'mixkit-funny-cartoon-fast-splat-2889.wav',
        'mixkit-cartoon-laugh-voice-2882.wav'
    ]);

    class UdderSounds {
        constructor({buttons, munge, AudioClass=root.Audio, random=Math.random,
                     rootPath=SOUND_ROOT, pool=MIXKIT_SOUNDS}={}) {
            this.buttons=[...(buttons || [])]; this.munge=munge; this.AudioClass=AudioClass;
            this.random=random; this.rootPath=rootPath; this.pool=[...pool]; this.active=new Set();
            if (this.pool.length < this.buttons.length) throw new Error('Not enough unique udder sounds.');
            this.randomise();
            this.buttons.forEach((button,index)=>{
                button.addEventListener('pointerenter',event=>{
                    if (event.pointerType === 'touch') return;
                    this.play(this.assignments[index]);
                });
                button.addEventListener('click',()=>{ this.suspense(); this.randomise(); });
            });
            this.munge?.addEventListener('click',()=>this.suspense());
        }
        randomise() {
            const choices=[...this.pool];
            for(let i=choices.length-1;i>0;i--){
                const j=Math.floor(this.random()*(i+1));
                [choices[i],choices[j]]=[choices[j],choices[i]];
            }
            this.assignments=choices.slice(0,this.buttons.length);
            return [...this.assignments];
        }
        suspense() { return this.play(SUSPENSE_SOUND); }
        play(filename) {
            if (!filename || !this.AudioClass) return null;
            const audio=new this.AudioClass(this.rootPath+filename); this.active.add(audio);
            let cleaned=false;
            const cleanup=()=>{ if(cleaned)return;cleaned=true;this.active.delete(audio); };
            audio.addEventListener?.('ended',cleanup,{once:true});
            audio.addEventListener?.('error',cleanup,{once:true});
            try {
                const attempt=audio.play();
                if(attempt?.catch)attempt.catch(cleanup);
            } catch (_) { cleanup(); }
            return audio;
        }
    }

    if(typeof module!=='undefined')module.exports={UdderSounds,MIXKIT_SOUNDS,SUSPENSE_SOUND,SOUND_ROOT};
    if(typeof document==='undefined')return;
    const udder=document.getElementById('sourceUdder'),munge=document.getElementById('mungeButton');
    if(!udder)return;
    root.udderSounds=new UdderSounds({buttons:udder.querySelectorAll('.udder-teat'),munge});
})(typeof globalThis!=='undefined'?globalThis:this);
