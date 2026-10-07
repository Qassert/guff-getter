const {test} = require('node:test');
const assert = require('node:assert/strict');
const {PromotionGallery,creatorEditUrl} = require('../newsmuncher/static/js/gallery/promotion-gallery.js');
const deferred = () => { let resolve, reject; const promise = new Promise((a,b) => {resolve=a; reject=b;}); return {promise,resolve,reject}; };
const response = data => ({ok:true, json:async () => data});
const item = id => ({id,title:'Title '+id,body:'Body '+id,promoted:false});
function setup(fetcher, afterDisplay) {
    const shown=[], errors=[];
    const view = {loading(){}, empty(){shown.push(null);}, show(i){shown.push(i);}, error(e){errors.push(e);}, promoting(){}, promoted(){}};
    return {gallery:new PromotionGallery({view,fetcher,afterDisplay}),shown,errors};
}
test('loads one creation and acknowledges only after display; promotion is idempotent', async () => {
    const calls=[], painted=deferred();
    const {gallery,shown} = setup(async (url, options) => {
        calls.push({url,options});
        return response(url.split('?')[0].endsWith('/next') ? {item:item('a'),view_token:'token'} : {promoted:true});
    }, () => painted.promise);
    const task=gallery.next();
    await new Promise(setImmediate);
    assert.equal(shown[0].title,'Title a');
    assert.equal(calls.length,1);
    painted.resolve(); await task;
    assert.equal(calls[1].url,'/promotion-gallery/displayed');
    await gallery.promote(); await gallery.promote();
    assert.equal(calls.filter(c=>c.url.endsWith('/promote')).length,1);
    assert(calls.every(c=>c.options.credentials==='same-origin'));
});
test('rapid turns discard late requests without counting or replacing the active page', async () => {
    const old=deferred(); let requests=0; const acks=[];
    const {gallery,shown}=setup(async (url,opts)=>{
        if(url.split('?')[0].endsWith('/next')) return ++requests===1 ? old.promise : response({item:item('new'),view_token:'new'});
        acks.push(JSON.parse(opts.body).view_token); return response({recorded:true});
    });
    const first=gallery.next(); await new Promise(setImmediate);
    await gallery.next(); old.resolve(response({item:item('old'),view_token:'old'})); await first;
    assert.deepEqual(shown.map(x=>x.id),['new']); assert.deepEqual(acks,['new']);
});
test('failed count is retried before another selection; empty collection is valid', async () => {
    let nexts=0, acks=0;
    const {gallery,shown,errors}=setup(async url=>{
        if(url.split('?')[0].endsWith('/next')) return response(++nexts===1 ? {item:item('a'),view_token:'a'} : {item:null});
        if(++acks===1) throw new Error('offline');
        return response({recorded:true});
    });
    await gallery.next(); assert.equal(errors[0],'offline');
    await gallery.next(); assert.equal(acks,2); assert.equal(nexts,2); assert.equal(shown.at(-1),null);
});
test('late promotion does not change another page; leaving cancels retrieval', async () => {
    const promotion=deferred(); let n=0;
    const {gallery}=setup(async url=>{
        if(url.endsWith('/promote')) return promotion.promise;
        return response(url.split('?')[0].endsWith('/next') ? {item:item(String(++n)),view_token:String(n)} : {});
    });
    await gallery.next(); const p=gallery.promote(); await gallery.next();
    promotion.resolve(response({promoted:true})); await p;
    assert.equal(gallery.current.promoted,false);
    gallery.leave(); assert(gallery.abort.signal.aborted);
});
test('EDIT targets the current rewrite within the authenticated Creator route',()=>{
    assert.equal(creatorEditUrl('/pets/pet_profile/current-pet','rewrite/id'),
        '/pets/pet_profile/current-pet?rewrite_id=rewrite%2Fid');
    assert.equal(creatorEditUrl('/pets/pet_profile/current-pet',null),'/pets/pet_profile/current-pet');
});

const {GalleryMedia} = require('../newsmuncher/static/js/gallery/promotion-gallery.js');
class FakeAudio {
    constructor(start) { this.start=start; this.src=''; this.playing=false; this.events={}; this.calls=0; }
    addEventListener(name, callback) {this.events[name]=callback;}
    play() { this.calls++; return this.start().then(() => {this.playing=true; this.events.playing?.();}); }
    finish() {this.playing=false; this.ended=true; this.events.ended?.();}
    pause() {this.playing=false;}
    removeAttribute() {this.src='';}
    load() {this.loaded=true;}
}
function mediaSetup(starts=[]) {
    const players=[], states=[];
    const media = new GalleryMedia({makeAudio:()=>{
        const player=new FakeAudio(starts.shift() || (()=>Promise.resolve())); players.push(player); return player;
    },status:s=>states.push(s)});
    return {media,players,states};
}
test('gallery plays only the jingle and ignores historical narration', async()=>{
    const {media,players}=mediaSetup();
    await media.activate({jingle_url:'/music',narration_url:'/historical-voice'});
    assert.equal(players.length,1); assert.equal(players[0].src,'/music'); assert(players[0].playing);
});
test('jingle-only starts immediately and narration-only pages are silent', async()=>{
    const {media,players,states}=mediaSetup();
    await media.activate({jingle_url:'/music'}); assert(players[0].playing);
    await media.activate({narration_url:'/historical-voice'});
    assert(!players[0].playing); assert.equal(players.length,1);
    assert.deepEqual(states.at(-1),{available:false,blocked:false});
});
test('page turn stops and unloads old jingle with no overlap', async()=>{
    const {media,players}=mediaSetup();
    await media.activate({jingle_url:'/old'});
    await media.activate({jingle_url:'/new'});
    assert(!players[0].playing && players[0].src===''); assert(players[1].playing);
});
test('autoplay fallback retries the active jingle sensibly', async()=>{
    let blocked=true; const {media,players,states}=mediaSetup([()=>blocked ? Promise.reject({name:'NotAllowedError'}) : Promise.resolve()]);
    await media.activate({jingle_url:'/music'}); assert(states.at(-1).blocked);
    blocked=false; await media.play(); assert(players[0].playing); assert(!states.at(-1).blocked);
});
test('STOP cancels pending playback and permits deliberate restart',async()=>{
    const old=deferred(); const {media,players}=mediaSetup([()=>old.promise]);
    const pending=media.activate({jingle_url:'/old'}); media.pause(); old.resolve(); await pending;
    assert(!players[0].playing); await media.play(); assert(players[1].playing);
});
test('next stops current audio before waiting on retrieval and page exit stops playback',async()=>{
    const pending=deferred(); const {media,players}=mediaSetup();
    await media.activate({jingle_url:'/old'});
    const {gallery}=setup(()=>pending.promise); gallery.media=media;
    const task=gallery.next(); assert(!players[0].playing);
    gallery.leave(); pending.resolve(response({item:item('late'),view_token:'late'})); await task;
    assert(!gallery.current);
});

test('expired acknowledgement releases navigation on the next attempt', async()=>{
    let nexts=0;
    const {gallery}=setup(async url=>{
        if (url.split('?')[0].endsWith('/next')) return response(++nexts===1 ? {item:item('a'),view_token:'expired'} : {item:null});
        return {ok:false,status:409};
    });
    await gallery.next(); assert.equal(gallery.receipt,null);
    await gallery.next(); assert.equal(nexts,2);
});

test('default fetch adapter does not bind native fetch to the gallery instance', async () => {
    const original = globalThis.fetch;
    try {
        globalThis.fetch = function () {
            assert(!(this instanceof PromotionGallery), 'Native fetch rejects this receiver');
            return Promise.resolve(response({item: null}));
        };
        let empty = false;
        const gallery = new PromotionGallery({view: {
            loading() {}, empty() { empty = true; }, error(message) { assert.fail(message); }
        }});
        await gallery.next();
        assert(empty);
    } finally { globalThis.fetch = original; }
});

const {GalleryVideo,GalleryBackdrop} = require('../newsmuncher/static/js/gallery/promotion-gallery.js');
function videoSetup(start=()=>Promise.resolve()) {
    const players=[], timers=[], revealed=[], cancelled=[]; let reduce=false;
    const visual=new GalleryVideo({makeVideo(){
        const player=new FakeAudio(start);
        player.setAttribute=()=>{}; player.remove=()=>{player.removed=true;};
        players.push(player); return player;
    },mount(){},reveal(value){revealed.push(value);},reduced:()=>reduce,
    schedule(fn,delay){timers.push({fn,delay});return timers.length;},cancel(id){cancelled.push(id);}});
    return {visual,players,timers,revealed,cancelled,reduce(){reduce=true;}};
}
const animated={image_url:'/still',video_url:'/stored-video'};
test('still loads first; 1.5s delay then muted inline loop fades only on playing', async()=>{
    const {visual,players,timers,revealed}=videoSetup(); const image=deferred();
    visual.activate(animated,image.promise); await Promise.resolve();
    assert.equal(timers.length,0); image.resolve(true); await Promise.resolve();
    assert.equal(timers[0].delay,1500); assert.equal(players.length,0);
    await timers[0].fn(); const video=players[0];
    assert(video.muted && video.defaultMuted && video.playsInline && video.loop);
    assert.equal(video.src,'/stored-video'); assert.equal(revealed.at(-1),true);
});
test('video page turn cancels delay, old image load and late play/event completion', async()=>{
    const pending=deferred(); const {visual,players,timers,revealed}=videoSetup(()=>pending.promise);
    visual.activate(animated); await Promise.resolve(); const oldTimer=timers[0];
    visual.stop(); await oldTimer.fn(); assert.equal(players.length,0);
    const image=deferred(); visual.activate(animated,image.promise); visual.stop();
    image.resolve(true); await Promise.resolve(); assert.equal(timers.length,1);
    visual.activate(animated); await Promise.resolve(); const play=timers[1].fn();
    const old=players[0]; visual.stop(); pending.resolve(); await play;
    old.events.playing(); assert(!old.playing); assert(old.removed); assert.equal(old.src,'');
    assert.equal(revealed.at(-1),false);
});
test('image-only, text-only, failed image and reduced motion never start video', async()=>{
    const {visual,players,timers,reduce}=videoSetup();
    visual.activate({image_url:'/still'}); visual.activate({video_url:'/stored'});
    visual.activate(animated,Promise.resolve(false)); await Promise.resolve();
    reduce(); visual.activate(animated); await Promise.resolve();
    assert.equal(timers.length,0); assert.equal(players.length,0);
});
test('autoplay rejection or media error retains the still; reduced motion rechecked at delay', async()=>{
    const {visual,players,timers,revealed}=videoSetup(()=>Promise.reject(Object.assign(Error(),{name:'NotAllowedError'})));
    visual.activate(animated); await Promise.resolve(); await timers[0].fn();
    assert.equal(revealed.at(-1),false); assert(players[0].removed);
    const second=videoSetup(); second.visual.activate(animated); await Promise.resolve();
    second.reduce(); await second.timers[0].fn(); assert.equal(second.players.length,0);
    const third=videoSetup(); third.visual.activate(animated); await Promise.resolve(); await third.timers[0].fn();
    third.players[0].events.error(); assert.equal(third.revealed.at(-1),false);
});
test('gallery navigation and leave stop visuals before retrieval, independent of audio', async()=>{
    const calls=[]; const wait=deferred();
    const gallery=new PromotionGallery({view:{loading(){calls.push('loading');},empty(){}},
        media:{stop(){calls.push('audio-stop');}},visual:{stop(){calls.push('video-stop');}},
        fetcher:()=>wait.promise});
    const next=gallery.next(); assert.deepEqual(calls,['audio-stop','video-stop','loading']);
    gallery.leave(); assert.deepEqual(calls.slice(-2),['audio-stop','video-stop']);
    wait.resolve(response({item:null})); await next;
});

function backdropSetup(start=()=>Promise.resolve(), reduced=false) {
    const players=[], images=[], revealed=[];
    const backdrop=new GalleryBackdrop({makeVideo(){
        const player=new FakeAudio(start); player.setAttribute=()=>{};
        player.remove=()=>{player.removed=true;}; players.push(player); return player;
    },mount(){},showImage:url=>images.push(url),reveal:value=>revealed.push(value),reduced:()=>reduced});
    return {backdrop,players,images,revealed};
}
test('gallery backdrop uses saved video over its still and replaces the old player',async()=>{
    const {backdrop,players,images,revealed}=backdropSetup();
    backdrop.activate({image_url:'/still-a',video_url:'/video-a'}); await new Promise(setImmediate);
    players[0].events.playing();
    assert.equal(images.at(-1),'/still-a'); assert.equal(revealed.at(-1),true);
    assert(players[0].muted && players[0].playsInline && players[0].loop);
    backdrop.activate({image_url:'/still-b',video_url:'/video-b'}); await new Promise(setImmediate);
    assert(!players[0].playing && players[0].removed && players[0].src==='');
    assert.equal(players.length,2); assert.equal(images.at(-1),'/still-b');
});
test('image-only, reduced-motion and blocked backdrop playback retain the still',async()=>{
    const imageOnly=backdropSetup(); imageOnly.backdrop.activate({image_url:'/still'});
    assert.deepEqual(imageOnly.images,[null,'/still']); assert.equal(imageOnly.players.length,0);
    const reduced=backdropSetup(()=>Promise.resolve(),true);
    reduced.backdrop.activate({image_url:'/reduced',video_url:'/moving'});
    assert.equal(reduced.images.at(-1),'/reduced'); assert.equal(reduced.players.length,0);
    const blocked=backdropSetup(()=>Promise.reject(Error('blocked')));
    blocked.backdrop.activate({image_url:'/fallback',video_url:'/blocked'}); await new Promise(setImmediate);
    assert(blocked.players[0].removed); assert.equal(blocked.images.at(-1),'/fallback');
    assert.equal(blocked.revealed.at(-1),false);
});


for (const operation of ['stop', 'schedule']) {
    test(`default browser timers support GalleryVideo ${operation} without an illegal receiver`, async () => {
        const fs = require('node:fs'), vm = require('node:vm');
        const context = vm.createContext({module: {exports: {}}, timers: [], cancellations: []});
        // Browser-style globals reject a GalleryVideo instance as their receiver.
        vm.runInContext(`
            function setTimeout(fn, delay) {
                if (this !== globalThis) throw new TypeError('Illegal invocation');
                timers.push({fn, delay});
                return 42;
            }
            function clearTimeout(timer) {
                if (this !== globalThis) throw new TypeError('Illegal invocation');
                cancellations.push(timer);
            }
        `, context);
        vm.runInContext(fs.readFileSync('newsmuncher/static/js/gallery/promotion-gallery.js', 'utf8'), context);
        const BrowserGalleryVideo = context.module.exports.GalleryVideo;
        if (operation === 'stop') {
            const visual = new BrowserGalleryVideo();
            assert.doesNotThrow(() => visual.stop());
            visual.timer = 42;
            assert.doesNotThrow(() => visual.stop());
            assert.deepEqual(Array.from(context.cancellations), [undefined, 42]);
        } else {
            // Isolate scheduling so the old cancel bug cannot mask the schedule bug.
            const visual = new BrowserGalleryVideo({cancel: () => {}});
            const played = [];
            visual.play = (url, generation) => played.push({url, generation});
            visual.activate(animated);
            await new Promise(setImmediate);
            assert.equal(context.timers.length, 1);
            assert.equal(context.timers[0].delay, 1500);
            assert.equal(visual.timer, 42);
            context.timers[0].fn();
            assert.deepEqual(played, [{url: animated.video_url, generation: visual.generation}]);
        }
    });
}
