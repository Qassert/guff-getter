const {test} = require('node:test');
const assert = require('node:assert/strict');
const {AnimationUI} = require('../newsmuncher/static/video.js');
const deferred = () => { let resolve, reject; const promise = new Promise((a,b) => {resolve=a;reject=b;}); return {promise,resolve,reject}; };
const response = data => ({ok:true,json:async()=>data});
function setup(fetcher) {
    const states=[], timers=[]; let stops=0;
    const ui = new AnimationUI({fetcher, view:{render(data,pending){states.push({...data,pending});},stop(){stops++;}},
        schedule(fn){timers.push(fn);return timers.length;},cancel(){}});
    return {ui,states,timers,stops:()=>stops};
}
test('view/restore performs GET only; no image hides generation; existing video reused', async () => {
    const calls=[];
    const {ui,states}=setup(async (url,opts)=>{calls.push(opts.method);return response({video_status:'complete',video_url:'/stored',can_generate:false});});
    await ui.show({nominated:true,rewrite_id:'a'}); await ui.act(); await ui.show({nominated:true,rewrite_id:'a'});
    assert.deepEqual(calls,['GET','GET']); assert.equal(states.at(-1).video_url,'/stored');
    await ui.show(null); await ui.act(); assert.equal(calls.length,2);
});
test('explicit click submits once while pending then polls GET', async () => {
    const submitted=deferred(), calls=[];
    const {ui,states}=setup(async (url,opts)=>{
        calls.push(opts.method);
        if(opts.method==='POST') return submitted.promise;
        return response({can_generate:calls.length===1,video_status:calls.length===1?'none':'started'});
    });
    await ui.show({nominated:true,rewrite_id:'a'});
    const work=ui.act(); await ui.act(); assert(states.at(-1).pending);
    submitted.resolve(response({video_status:'queued',can_generate:false})); await work;
    assert.deepEqual(calls,['GET','POST','GET']); assert.equal(ui.state.video_status,'started');
});
test('ambiguous submission never retries POST and failed status disables generation', async () => {
    const calls=[];
    const {ui}=setup(async (url,opts)=>{
        calls.push(opts.method);
        if(opts.method==='POST') throw Error('network');
        return response(calls.length===1?{can_generate:true}:{video_status:'failed_or_uncertain',can_generate:false});
    });
    await ui.show({nominated:true,rewrite_id:'a'}); await ui.act(); await ui.act();
    assert.deepEqual(calls,['GET','POST','GET']);
});
test('rewrite switch ignores old responses and timer callbacks', async () => {
    const old=deferred(), calls=[];
    const {ui,states,timers,stops}=setup(async (url,opts)=>{
        calls.push(url);
        if(url.endsWith('/old')) return old.promise;
        return response({video_status:'started',can_generate:false});
    });
    const request=ui.show({nominated:true,rewrite_id:'old'}); await ui.show({nominated:true,rewrite_id:'new'});
    old.resolve(response({can_generate:true,video_url:'/old-video'})); await request;
    assert.equal(states.at(-1).video_status,'started'); assert.equal(ui.key,'new');
    ui.stop(); const count=calls.length; await timers[0](); assert.equal(calls.length,count); assert(stops()>=3);
});
test('permission failures use safe sign-in message without exposing provider detail', async () => {
    const {ui,states}=setup(async()=>({ok:false,status:401}));
    await ui.show({nominated:true,rewrite_id:'a'}); await ui.act();
    assert.match(states.at(-1).message,/Sign in/); assert(!ui.state.can_generate);
});

test('real DOM binding presents animation states with no generation button for saved/failed video', async()=>{
    const fs=require('node:fs'), vm=require('node:vm'); const elements={};
    for(const id of ['animationControls','animationButton','animationMessage','imagePanel']) {
        elements[id]={hidden:false,src:'',events:{},classList:{toggle(){}},querySelector(){return null;},addEventListener(name,fn){this.events[name]=fn;},
            pause(){},load(){},removeAttribute(){this.src='';},getAttribute(){return this.src;}};
    }
    const context={document:{getElementById:id=>elements[id]},addEventListener(){},setTimeout,clearTimeout,fetch:async()=>response({can_generate:true})};
    vm.createContext(context); vm.runInContext(fs.readFileSync('newsmuncher/static/video.js','utf8'),context);
    await context.videoUI.show({nominated:true,rewrite_id:'a'});
    assert.equal(elements.animationButton.textContent,'ANIMATE IMAGE'); assert(!elements.animationButton.disabled);
    context.videoUI.render({video_status:'started',can_generate:false});
    assert.equal(elements.animationButton.textContent,'ANIMATING…'); assert(elements.animationButton.disabled);
    context.videoUI.render({video_status:'complete',video_url:'/stored',can_generate:false});
    assert(elements.animationButton.hidden); assert.equal(elements.animationStop, undefined);
    assert.equal(elements.animationMessage.textContent,'ANIMATION READY');
    context.videoUI.render({video_status:'failed_or_uncertain',can_generate:false});
    assert(elements.animationButton.hidden); assert.match(elements.animationMessage.textContent,/ANIMATION FAILED/);
    const template=fs.readFileSync('newsmuncher/templates/pet_profile.html','utf8');
    assert(!template.includes('STOP ANIMATION'));
    assert(!fs.readFileSync('newsmuncher/templates/promotion_gallery.html','utf8').includes('STOP ANIMATION'));
    await context.videoUI.show({rewrite_id:'draft',nominated:false});
    assert(elements.animationControls.hidden);
    await context.videoUI.act();
    assert(!template.includes('animationPreview'));
    assert(!template.includes('<video'));
    const css=fs.readFileSync('newsmuncher/static/styles.css','utf8');
    assert.match(css,/\.image-panel \.creation-animation \{ position: absolute; inset: 0; width: 100%; height: 100%/);
    assert.match(css,/\.image-panel\.animation-playing \.creation-animation \{ opacity: 1/);
});


for (const operation of ['show/stop', 'poll scheduling']) {
    test(`browser timer defaults support AnimationUI ${operation}`, async () => {
        const fs = require('node:fs'), vm = require('node:vm');
        const context = vm.createContext({module: {exports: {}}, timers: [], cancelled: []});
        vm.runInContext(`
            function setTimeout(fn, delay) {
                if (this !== globalThis) throw new TypeError('Illegal invocation');
                timers.push({fn, delay});
                return timers.length;
            }
            function clearTimeout(timer) {
                if (this !== globalThis) throw new TypeError('Illegal invocation');
                cancelled.push(timer);
            }
        `, context);
        vm.runInContext(fs.readFileSync('newsmuncher/static/video.js', 'utf8'), context);
        const calls = [], states = [];
        const ui = new context.module.exports.AnimationUI({
            view: {stop() {}, render(data) { states.push(data); }},
            fetcher: async (url, options) => {
                calls.push(options.method);
                return response({video_status: operation === 'show/stop' ? 'none' : 'started',
                                 can_generate: operation === 'show/stop'});
            },
            // Isolate the scheduling regression from cancellation's independent failure.
            ...(operation === 'poll scheduling' ? {cancel() {}} : {})
        });
        await ui.show({nominated:true,rewrite_id: 'fixture'});
        if (operation === 'show/stop') {
            assert.equal(states.at(-1).can_generate, true);
            ui.timer = 42;
            assert.doesNotThrow(() => ui.stop());
            assert.deepEqual(Array.from(context.cancelled), [undefined, 42]);
            assert.equal(ui.key, null);
        } else {
            assert.equal(context.timers.length, 1);
            assert.equal(context.timers[0].delay, 5000);
            assert.equal(ui.timer, 1);
            await context.timers[0].fn();
            assert.equal(context.timers.length, 2);
            assert.deepEqual(calls, ['GET', 'GET']);
            ui.stop();
            await context.timers[1].fn();
            assert.equal(calls.length, 2);
        }
        assert(calls.every(method => method === 'GET'));
    });
}

const {CreationVideo} = require('../newsmuncher/static/video.js');
function visualSetup(start = () => Promise.resolve()) {
    const players=[], shown=[], messages=[];
    let imageReady=true, reduced=false;
    const visual=new CreationVideo({makeVideo(){
        const player={events:{},readyState:0,calls:0,paused:true,
            addEventListener(name,fn){this.events[name]=fn;},setAttribute(){},
            play(){this.calls++;this.paused=false;return start();},pause(){this.paused=true;},
            removeAttribute(){this.src='';},load(){this.loads=(this.loads||0)+1;},remove(){this.removed=true;}};
        players.push(player);return player;
    },hasImage:()=>imageReady,reduced:()=>reduced,mount(player){player.mounted=true;},
    reveal(value){shown.push(value);},status(message){messages.push(message);}});
    return {visual,players,shown,messages,setImage(value){imageReady=value;},setReduced(value){reduced=value;}};
}
test('generation retains still; ready URL preloads in place and canplay automatically starts muted inline loop', async()=>{
    const {visual,players,shown}=visualSetup();
    const pending=deferred();
    const ui=new AnimationUI({view:{stop:()=>visual.stop(),render(data){if(data.video_url)visual.show(data.video_url);}},
        fetcher:async()=>response(await pending.promise),schedule(){},cancel(){}});
    const loading=ui.show({nominated:true,rewrite_id:'a'});
    ui.render({video_status:'queued'});ui.render({video_status:'started'});
    assert.equal(players.length,0);assert(shown.every(value=>!value));
    pending.resolve({video_status:'complete',video_url:'/stored',can_generate:false});await loading;
    const player=players[0];
    assert(player.mounted);assert.equal(player.preload,'auto');assert.equal(player.calls,0);
    assert.equal(shown.at(-1),false);
    assert(player.muted && player.defaultMuted && player.playsInline && player.loop && !player.controls);
    await player.events.canplay();assert.equal(player.calls,1);
    assert.equal(shown.at(-1),false); // No fade until actual playback, not merely a resolved promise.
    player.events.playing();assert.equal(shown.at(-1),true);
    await player.events.canplay();ui.render({video_url:'/stored'});
    assert.equal(player.calls,1);assert.equal(players.length,1);
});
test('saved video waits for the current still to mount before attaching',()=>{
    const {visual,players,setImage}=visualSetup();setImage(false);
    visual.show('/stored');assert.equal(players.length,0);
    setImage(true);visual.ready();assert.equal(players.length,1);
});
test('reduced motion retains still and prevents autoplay even if enabled while loading',async()=>{
    const {visual,players,shown,setReduced}=visualSetup();setReduced(true);
    visual.show('/stored');visual.ready();assert.equal(players.length,0);
    setReduced(false);visual.show('/another');assert.equal(players.length,1);
    setReduced(true);await players[0].events.canplay();
    assert.equal(players[0].calls,0);assert(players[0].removed);assert.equal(shown.at(-1),false);
});
test('rewrite/page stop unloads old video and invalidates readiness and late play promises',async()=>{
    const pending=deferred();const {visual,players,shown}=visualSetup(()=>pending.promise);
    visual.show('/old');const old=players[0];const playing=old.events.canplay();
    visual.stop();assert(old.paused && old.removed);assert.equal(old.src,'');
    visual.show('/new');pending.resolve();await playing;
    old.events.playing();await old.events.canplay();
    assert(old.paused);assert.equal(old.calls,1);assert.equal(shown.at(-1),false);
    assert.equal(players[1].src,'/new');
    visual.stop();await players[1].events.canplay();assert.equal(players[1].calls,0);
});
test('autoplay rejection and media error keep still and do not retry or regenerate',async()=>{
    const {visual,players,shown,messages}=visualSetup(()=>Promise.reject(Error('NotAllowedError')));
    visual.show('/stored');await players[0].events.canplay();
    assert(players[0].removed && players[0].paused);assert.equal(shown.at(-1),false);
    assert.match(messages[0],/still image/);
    visual.show('/stored');visual.ready();assert.equal(players.length,1);
    const other=visualSetup();other.visual.show('/broken');other.players[0].events.error();
    assert.equal(other.shown.at(-1),false);assert(other.players[0].removed);
});

test('draft generation is gated despite an eligible backend status', async () => {
    const calls=[];
    const {ui}=setup(async (url, opts)=>{calls.push(opts.method);return response({can_generate:true});});
    await ui.show({rewrite_id:'draft',nominated:false});await ui.act();
    assert.deepEqual(calls,['GET']);
    await ui.show({rewrite_id:'draft',nominated:true});await ui.act();
    assert.deepEqual(calls,['GET','GET','POST']);
});
