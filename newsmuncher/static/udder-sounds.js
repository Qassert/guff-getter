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
    const MUNGE_ROOT = '/static/audio/Munge it/';
    const MUNGE_SOUNDS = Object.freeze([
        'Funny Run Up Take - QuickSounds.com.mp3',
        'Man screaming aaaah - QuickSounds.com.mp3',
        'fart-02.wav',
        'fart-03.wav',
        'fart-08.wav',
        'fart-quick-puffy-brukowskij-fart-quick-and-puffy-02-1-0m00s.mp3',
        'fart-raspy-flab-om-fx-1-00-02.mp3',
        'fart-squeak-01.wav',
        'hello meme funny - QuickSounds.com.mp3',
        'slap sound effect funny memes - QuickSounds.com.mp3'
    ]);

    class UdderSounds {
        constructor({buttons, munge, AudioClass=root.Audio, random=Math.random,
                     rootPath=SOUND_ROOT, pool=MIXKIT_SOUNDS, clickSound=SUSPENSE_SOUND,
                     pressSound=false}={}) {
            this.buttons=[...(buttons || [])]; this.munge=munge; this.AudioClass=AudioClass;
            this.random=random; this.rootPath=rootPath;
            this.pool=[...pool].filter(sound=>sound.toLowerCase()!==SUSPENSE_SOUND.toLowerCase());
            this.active=new Set();
            this.clickSound=clickSound;this.pressSound=pressSound;this.suppressClick=false;this.pressed=new WeakSet();
            if (this.pool.length < this.buttons.length) throw new Error('Not enough unique udder sounds.');
            this.randomise();
            this.buttons.forEach((button,index)=>{
                button.addEventListener('pointerenter',event=>{
                    if (event.pointerType === 'touch') return;
                    this.play(this.assignments[index]);
                });
                if(this.pressSound)button.addEventListener('pointerdown',()=>{this.pressed.add(button);this.interaction();this.randomise();});
                button.addEventListener('click',()=>{
                    if(this.pressed.has(button)){this.pressed.delete(button);return;}
                    this.interaction();this.randomise();
                });
                button.addEventListener('pointercancel',()=>this.pressed.delete(button));
            });
            if(this.munge){
                if(this.pressSound)this.munge.addEventListener('pointerdown',()=>{this.suppressClick=true;this.interaction();this.randomise();});
                this.munge.addEventListener('click',()=>{if(this.suppressClick){this.suppressClick=false;return;}this.interaction();this.randomise();});
                this.munge.addEventListener('pointercancel',()=>{this.suppressClick=false;});
            }
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
        interaction() { return this.play(this.clickSound==='random'?this.pool[Math.floor(this.random()*this.pool.length)]:this.clickSound); }
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

    if(typeof module!=='undefined')module.exports={UdderSounds,MIXKIT_SOUNDS,MUNGE_SOUNDS,SUSPENSE_SOUND,SOUND_ROOT,MUNGE_ROOT};
    if(typeof document==='undefined')return;
    const udder=document.getElementById('sourceUdder'),munge=document.getElementById('mungeControl');
    if(!udder)return;
    root.udderSounds=new UdderSounds({buttons:udder.querySelectorAll('.udder-teat'),pressSound:true});
    if(munge)root.mungeSounds=new UdderSounds({buttons:munge.querySelectorAll('.munge-teat'),munge:document.getElementById('mungeBodyButton'),rootPath:MUNGE_ROOT,pool:MUNGE_SOUNDS,clickSound:SUSPENSE_SOUND,pressSound:true});
})(typeof globalThis!=='undefined'?globalThis:this);
