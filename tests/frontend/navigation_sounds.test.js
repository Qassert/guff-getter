const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const {MasterAudioController}=require('../../newsmuncher/static/js/shared/master-audio.js');
const source=fs.readFileSync('newsmuncher/static/js/shared/mode-nav.js','utf8');
function setup({store=new Map(),blockedStorage=false,flush=async()=>{},muted=false,scriptSrc="https://example.test/prefix/static/js/shared/mode-nav.js"}={}) {
    const audio=[],visits=[],timers=[];
    class Audio {
        constructor(src){this.src=src;this.paused=true;this.currentTime=0;audio.push(this);}
        play(){this.paused=false;this.plays=(this.plays||0)+1;return Promise.resolve();}
        pause(){this.paused=true;}
    }
    const master=new MasterAudioController({MediaClass:Audio,storage:{getItem:()=>String(muted)},documentRef:null});
    const links=['CREATE','BUILD','GALLERY'].map(mode=>({
        dataset:{navSound:mode},href:`/${mode.toLowerCase()}`,classList:{add(){}},
        addEventListener(name,handler){this[name]=handler;}
    }));
    const storage={getItem:key=>{if(blockedStorage)throw Error('blocked');return store.get(key);},
        setItem:(key,value)=>{if(blockedStorage)throw Error('blocked');store.set(key,value);}};
    let random=0;
    const window={sessionStorage:storage,creationTextSaver:{flush},matchMedia:()=>({matches:false}),
        location:{assign:url=>visits.push(url)},setTimeout:(handler,delay)=>{handler.delay=delay;timers.push(handler);}};
    vm.runInNewContext(source,{Audio,URL,Math:{random:()=>random,floor:Math.floor},window,
        document:{currentScript:{src:scriptSrc},
            addEventListener(){},querySelectorAll:()=>links}});
    const click=(mode,options={})=>links.find(link=>link.dataset.navSound===mode).click({button:0,preventDefault(){},...options});
    return {audio,links,click,store,master,visits,timers,random:value=>{random=value;}};
}

test('all nine WAVs are cached and preloaded with correctly prefixed URLs',()=>{
    const unit=setup();assert.equal(unit.audio.length,9);
    for(const audio of unit.audio){
        assert.equal(audio.preload,'auto');
        assert(audio.src.startsWith('https://example.test/prefix/static/audio/bonkers_button_sounds/'));
        assert(fs.existsSync('newsmuncher/static/audio/bonkers_button_sounds/'+audio.src.split('/').pop()));
    }
});

test('each button selects only its three sounds and avoids consecutive repeats',async()=>{
    const unit=setup();
    for(const mode of ['CREATE','BUILD','GALLERY']){
        let previous;const seen=new Set();
        for(const random of [0,.99,.5,0,.99,.5]){
            unit.random(random);await unit.click(mode);
            const playing=unit.audio.filter(a=>!a.paused);assert.equal(playing.length,1);
            const filename=playing[0].src.split('/').pop();assert(filename.startsWith(mode+'_'));
            assert.notEqual(filename,previous);previous=filename;seen.add(filename);
        }
        assert.equal(seen.size,3);
    }
    assert.equal(unit.audio.length,9); // Clicks reuse cached media.
});

test('no-repeat state survives real navigation reloads but blocked storage is harmless',async()=>{
    const store=new Map(),first=setup({store});await first.click('BUILD');
    const filename=first.audio.find(a=>!a.paused).src;
    const next=setup({store});await next.click('BUILD');
    assert.notEqual(next.audio.find(a=>!a.paused).src,filename);
    const privateTab=setup({blockedStorage:true});await privateTab.click('CREATE');await privateTab.click('CREATE');
    assert.equal(privateTab.audio.filter(a=>!a.paused).length,1);
});

test('rapid cross-button clicks stop and rewind the previous navigation sound',async()=>{
    const unit=setup();await unit.click('CREATE');
    const old=unit.audio.find(a=>!a.paused);old.currentTime=.4;
    await unit.click('GALLERY');assert(old.paused);assert.equal(old.currentTime,0);
    assert.equal(unit.audio.filter(a=>!a.paused).length,1);
});

test('existing master mute applies to random sounds and can unmute them',async()=>{
    const unit=setup({muted:true});await unit.click('CREATE');
    const playing=unit.audio.find(a=>!a.paused);assert.equal(playing.muted,true);
    unit.master.setMuted(false);assert.equal(playing.muted,false);
});

test('navigation still flushes saves, preserves modifiers and uses the existing animation delay',async()=>{
    let release;const unit=setup({flush:()=>new Promise(r=>release=r)});
    await unit.click('BUILD',{ctrlKey:true});assert.equal(unit.audio.filter(a=>!a.paused).length,0);
    const pending=unit.click('BUILD');assert.equal(unit.timers.length,0);
    release();await pending;assert.equal(unit.visits.length,0);assert.equal(unit.timers[0].delay,170);unit.timers[0]();assert.deepEqual(unit.visits,['/build']);
});

test('failed saves and failed audio playback cannot discard work or break navigation',async()=>{
    const unit=setup({flush:async()=>{throw Error('save failed');}});await unit.click('CREATE');
    assert.equal(unit.timers.length,0);assert.equal(unit.visits.length,0);
    const next=setup();next.audio.forEach(audio=>audio.play=()=>Promise.reject(Error('blocked playback')));
    await next.click('GALLERY');assert.equal(next.timers.length,1);
});

test('current-page button plays without navigation and only the navigation labels lose old sounds',async()=>{
    const unit=setup();delete unit.links[0].href;await unit.click('CREATE');
    assert.equal(unit.audio.filter(a=>!a.paused).length,1);assert.equal(unit.timers.length,0);
    for(const file of ['pet_profile.html','build.html','promotion_gallery.html']){
        const template=fs.readFileSync('newsmuncher/templates/'+file,'utf8');
        for(const mode of ['CREATE','BUILD','GALLERY'])assert(template.includes(`data-nav-sound="${mode}"`));
        assert(!template.includes('data-squelch'));assert(!template.includes('data-hover-voice'));
        assert(template.includes('nav-sounds-2'));
    }
});


test('URL construction safely encodes spaces in deployment paths',()=>{
    const unit=setup({scriptSrc:'https://example.test/a path/static/js/shared/mode-nav.js'});
    assert(unit.audio.every(a=>a.src.includes('/a%20path/static/audio/bonkers_button_sounds/')));
    assert(unit.audio.every(a=>!a.src.includes(' ')));
});
