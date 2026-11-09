/* Polyphonic, interaction-only sound effects for the Creator udder. */
(function(root) {
    const SOUND_ROOT = '/static/audio/effects/udder/';
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
    const MUNGE_ROOT = '/static/audio/effects/munge/';
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
        'slap sound effect funny memes - QuickSounds.com.mp3',
        '24687763-vegan-fart-voice-043-12382.mp3',
        '50986408-dubstep-snare-385349.mp3',
        'alex_jauk-funny-fart-216687.mp3',
        'apebble-fart-6-228246.mp3',
        'apebble-fart-7-228247.mp3',
        'beanfrog-proud-fart-288263.mp3',
        'beanfrog-unusual-sounding-fart-249278.mp3',
        'beetpro-fart-sound-effect-16-11093.mp3',
        'edr-synth-cowbell-high-169970.mp3',
        'edr-synth-cowbell-low-169971.mp3',
        'edr-synth-side-stick-471670.mp3',
        'freesound_community-bad-chili-fartwav-14462.mp3',
        'freesound_community-dw-tom-2-85123.mp3',
        'freesound_community-fart-sound-36983.mp3',
        'freesound_community-heavy-kick-39406.mp3',
        'freesound_community-odd-sound-104393.mp3',
        'freesound_community-slowmo-voice-growl-104204.mp3',
        'freesound_community-snare-drum-3-94292.mp3',
        'freesound_community-snare-drum-5-91466.mp3',
        'freesound_community-soda-bottle-base-drum-46019.mp3',
        'freesound_community-tom-2-85124.mp3',
        'freesound_community-wet-fart-6139.mp3',
        'freesound_community-wibble-92687.mp3',
        'shut_up_ghost-odd-tones-168473.mp3',
        'u_vlqddce8yw-tcp2-so-mean-808-completesoundaudio-419168.mp3',
        'u_vlqddce8yw-tcp2-so-sick-808-completesoundaudio-419171.mp3',
        'u_vlqddce8yw-tcp2-the-opps-808-completesoundaudio-419172.mp3',
        'u_vlqddce8yw-tcp2-your-god-kick-completesound-419149.mp3'
    ]);

    class UdderSounds {
        constructor({buttons, munge, AudioClass=root.Audio, random=Math.random,
                     rootPath=SOUND_ROOT, pool=MIXKIT_SOUNDS, clickSound=SUSPENSE_SOUND,
                     pressSound=false, shuffleBag=false,
                     randomiseOnInteraction=true}={}) {
            this.buttons=[...(buttons || [])]; this.munge=munge; this.AudioClass=AudioClass;
            this.random=random; this.rootPath=rootPath;
            this.pool=[...pool].filter(sound=>sound.toLowerCase()!==SUSPENSE_SOUND.toLowerCase());
            this.active=new Set();
            this.clickSound=clickSound;this.pressSound=pressSound;this.shuffleBag=shuffleBag;
            this.randomiseOnInteraction=randomiseOnInteraction;
            this.queue=[];this.lastSound=null;this.suppressClick=false;this.pressed=new WeakSet();
            if (this.pool.length < this.buttons.length) throw new Error('Not enough unique udder sounds.');
            this.randomise();
            this.buttons.forEach((button,index)=>{
                button.addEventListener('pointerenter',event=>{
                    if (event.pointerType === 'touch') return;
                    this.play(this.shuffleBag?this.nextSound():this.assignments[index]);
                });
                if(this.pressSound)button.addEventListener('pointerdown',()=>{this.pressed.add(button);this.interaction(index);if(!this.shuffleBag&&this.randomiseOnInteraction)this.randomise();});
                button.addEventListener('click',()=>{
                    if(this.pressed.has(button)){this.pressed.delete(button);return;}
                    this.interaction(index);if(!this.shuffleBag&&this.randomiseOnInteraction)this.randomise();
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
        nextSound() {
            if(!this.queue.length){
                this.queue=[...this.pool];
                for(let i=this.queue.length-1;i>0;i--){
                    const j=Math.floor(this.random()*(i+1));
                    [this.queue[i],this.queue[j]]=[this.queue[j],this.queue[i]];
                }
                if(this.queue.length>1&&this.queue[0]===this.lastSound){
                    [this.queue[0],this.queue[1]]=[this.queue[1],this.queue[0]];
                }
            }
            const sound=this.queue.shift();this.lastSound=sound;return sound;
        }
        suspense() { return this.play(SUSPENSE_SOUND); }
        interaction(index) {
            const sound=this.shuffleBag?this.nextSound():this.clickSound==='assigned'?this.assignments[index]:
                this.clickSound==='random'?this.pool[Math.floor(this.random()*this.pool.length)]:this.clickSound;
            return this.play(sound);
        }
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

    class MungeTeatSounds {
        constructor({controls, AudioClass=root.Audio, random=Math.random,
                     rootPath=MUNGE_ROOT, pool=MUNGE_SOUNDS}={}) {
            this.controls=[...(controls || [])];this.instruments=new Map();
            this.pointerSelection=null;
            this.controls.forEach(control=>{
                const engine=control.dataset.mungeEngine;
                const instrument=new UdderSounds({
                    buttons:control.querySelectorAll('.munge-teat'), AudioClass, random,
                    rootPath, pool, clickSound:'assigned', pressSound:true,
                    randomiseOnInteraction:false,
                });
                this.instruments.set(engine,instrument);
                control.addEventListener('pointerdown',()=>{
                    if(this.busy(control))return;
                    this.select(engine);this.pointerSelection=control;
                },true);
                control.addEventListener('click',()=>{
                    if(this.pointerSelection===control){this.pointerSelection=null;return;}
                    if(!this.busy(control))this.select(engine);
                },true);
                control.addEventListener('pointercancel',()=>{
                    if(this.pointerSelection===control)this.pointerSelection=null;
                },true);
            });
        }
        busy(control) {
            return control.classList?.contains('munge-control-processing') ||
                control.classList?.contains('munge-control-decelerating');
        }
        select(engine) {
            const instrument=this.instruments.get(engine);
            return instrument?instrument.randomise():[];
        }
        assignments(engine) {
            return [...(this.instruments.get(engine)?.assignments || [])];
        }
    }

    if(typeof module!=='undefined')module.exports={UdderSounds,MungeTeatSounds,MIXKIT_SOUNDS,MUNGE_SOUNDS,SUSPENSE_SOUND,SOUND_ROOT,MUNGE_ROOT};
    if(typeof document==='undefined')return;
    const udder=document.getElementById('sourceUdder'),munge=document.getElementById('mungeControls');
    if(!udder)return;
    root.udderSounds=new UdderSounds({buttons:udder.querySelectorAll('.udder-teat'),pressSound:true});
    if(munge){
        const controls=[...munge.querySelectorAll('.munge-control')];
        const bodies=Object.fromEntries(controls.map(control=>[
            control.dataset.mungeEngine,control.querySelector('.munge-body-button')]));
        root.mungeSoundTargets=Object.freeze({...bodies});
        root.mungeSounds=new MungeTeatSounds({controls,rootPath:MUNGE_ROOT,pool:MUNGE_SOUNDS});
    }
})(typeof globalThis!=='undefined'?globalThis:this);
