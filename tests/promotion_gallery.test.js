const {test} = require('node:test');
const assert = require('node:assert/strict');
const {PromotionGallery} = require('../newsmuncher/static/promotion-gallery.js');
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

const {GalleryMedia} = require('../newsmuncher/static/promotion-gallery.js');
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
test('jingle starts first and narration starts only after its natural end', async()=>{
    const {media,players}=mediaSetup();
    await media.activate({jingle_url:'/music',narration_url:'/voice'});
    assert.deepEqual(players.map(p=>p.calls),[1,0]);
    assert(players[0].playing && !players[1].playing);
    players[0].finish(); await new Promise(setImmediate);
    assert.deepEqual(players.map(p=>p.calls),[1,1]);
    assert(!players[0].playing && players[1].playing);
    players[0].finish(); await new Promise(setImmediate);
    assert.equal(players[1].calls,1);
});
test('single tracks start immediately and text-only pages are silent', async()=>{
    const {media,players,states}=mediaSetup();
    await media.activate({jingle_url:'/music'});
    assert(players[0].playing);
    await media.activate({narration_url:'/voice'});
    assert(!players[0].playing && players[1].playing);
    await media.activate({});
    assert(!players[1].playing);
    assert.deepEqual(states.at(-1),{available:false,blocked:false});
});
test('page turn during jingle cancels queued narration even after a late ended event', async()=>{
    const {media,players}=mediaSetup();
    await media.activate({jingle_url:'/old-music',narration_url:'/old-voice'});
    await media.activate({jingle_url:'/new-music',narration_url:'/new-voice'});
    players[0].finish(); await new Promise(setImmediate);
    assert.equal(players[1].calls,0);
    assert(players.slice(0,2).every(p=>!p.playing && p.src===''));
    assert(players[2].playing && !players[3].playing);
});
test('page turn during narration stops and unloads it', async()=>{
    const {media,players}=mediaSetup();
    await media.activate({jingle_url:'/music',narration_url:'/voice'});
    players[0].finish(); await new Promise(setImmediate);
    assert(players[1].playing);
    await media.activate({narration_url:'/new'});
    assert(players.slice(0,2).every(p=>!p.playing && p.src===''));
    assert(players[2].playing);
});
test('rapid turns abort old media immediately and pending old startup cannot revive it', async()=>{
    const old=deferred();
    const {media,players}=mediaSetup([()=>old.promise]);
    const pending=media.activate({jingle_url:'/old'});
    await media.activate({narration_url:'/new'});
    assert.equal(players[0].src,''); assert(players[0].loaded);
    old.resolve();await pending;
    assert(!players[0].playing && players[1].playing);
    media.stop();assert(players.every(p=>!p.playing && p.src===''));
});
test('autoplay blocks gracefully and explicit play retries; missing media is silent', async()=>{
    let blocked=true;
    const {media,players,states}=mediaSetup([()=>blocked ? Promise.reject({name:'NotAllowedError'}) : Promise.resolve(),()=>Promise.reject({name:'NotSupportedError'})]);
    await media.activate({jingle_url:'/music',narration_url:'/missing'});
    assert.equal(states.at(-1).blocked,true);
    blocked=false; await media.play(); assert(players[0].playing);
    assert.equal(states.at(-1).blocked,false);
    players[0].finish(); await new Promise(setImmediate);
    assert.equal(players[1].calls,1); assert.equal(states.at(-1).blocked,false);
});
test('STOP cancels pending playback and permits deliberate restart',async()=>{
    const old=deferred(); const {media,players}=mediaSetup([()=>old.promise]);
    const pending=media.activate({jingle_url:'/old'});
    media.pause(); old.resolve(); await pending;
    assert(!players[0].playing);
    await media.play(); assert(players[1].playing);
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

test('autoplay fallback retries the active track without restarting the sequence', async()=>{
    let musicBlocked=true, voiceBlocked=true;
    const {media,players,states}=mediaSetup([
        ()=>musicBlocked ? Promise.reject({name:'NotAllowedError'}) : Promise.resolve(),
        ()=>voiceBlocked ? Promise.reject({name:'NotAllowedError'}) : Promise.resolve()
    ]);
    await media.activate({jingle_url:'/music',narration_url:'/voice'});
    assert(states.at(-1).blocked); assert.equal(players[1].calls,0);
    musicBlocked=false; await media.play();
    players[0].finish(); await new Promise(setImmediate);
    assert(states.at(-1).blocked);
    voiceBlocked=false; await media.play();
    assert.equal(players[0].calls,2); assert(players[1].playing);
    assert(!states.at(-1).blocked);
});
test('STOP during jingle invalidates ended callbacks and preserves the remaining sequence', async()=>{
    const {media,players}=mediaSetup();
    await media.activate({jingle_url:'/music',narration_url:'/voice'});
    media.pause(); players[0].finish(); await new Promise(setImmediate);
    assert(players.every(p=>!p.playing)); assert.equal(players[1].calls,0);
    await media.play(); assert(players[2].playing); assert.equal(players[3].calls,0);
    players[2].finish(); await new Promise(setImmediate);
    assert(players[3].playing);
    media.pause(); await media.play();
    assert.equal(players[4].src,'/voice'); assert(players[4].playing);
});
test('rapid sequential pages never revive old queued narration or overlap active tracks', async()=>{
    const starts=[deferred(),deferred(),deferred()];
    const {media,players}=mediaSetup([()=>starts[0].promise,()=>Promise.resolve(),
        ()=>starts[1].promise,()=>Promise.resolve(),()=>starts[2].promise,()=>Promise.resolve()]);
    const pending=starts.map((_,i)=>media.activate({jingle_url:'/music'+i,narration_url:'/voice'+i}));
    starts.forEach(d=>d.resolve()); await Promise.all(pending);
    players[0].finish(); players[2].finish(); await new Promise(setImmediate);
    assert.deepEqual(players.filter(p=>p.playing).map(p=>p.src),['/music2']);
    assert.equal(players[1].calls+players[3].calls+players[5].calls,0);
    players[4].finish(); await new Promise(setImmediate);
    assert.deepEqual(players.filter(p=>p.playing).map(p=>p.src),['/voice2']);
});

test('page turn cancels narration whose play promise is still pending', async()=>{
    const voice=deferred();
    const {media,players}=mediaSetup([()=>Promise.resolve(),()=>voice.promise]);
    await media.activate({jingle_url:'/music',narration_url:'/voice'});
    players[0].finish();
    await media.activate({jingle_url:'/new'});
    voice.resolve(); await new Promise(setImmediate);
    assert(!players[1].playing && players[1].src==='');
    assert.deepEqual(players.filter(p=>p.playing).map(p=>p.src),['/new']);
});
