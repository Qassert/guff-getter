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
        return response(url.endsWith('/next') ? {item:item('a'),view_token:'token'} : {promoted:true});
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
        if(url.endsWith('/next')) return ++requests===1 ? old.promise : response({item:item('new'),view_token:'new'});
        acks.push(JSON.parse(opts.body).view_token); return response({recorded:true});
    });
    const first=gallery.next(); await new Promise(setImmediate);
    await gallery.next(); old.resolve(response({item:item('old'),view_token:'old'})); await first;
    assert.deepEqual(shown.map(x=>x.id),['new']); assert.deepEqual(acks,['new']);
});
test('failed count is retried before another selection; empty collection is valid', async () => {
    let nexts=0, acks=0;
    const {gallery,shown,errors}=setup(async url=>{
        if(url.endsWith('/next')) return response(++nexts===1 ? {item:item('a'),view_token:'a'} : {item:null});
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
        return response(url.endsWith('/next') ? {item:item(String(++n)),view_token:String(n)} : {});
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
test('both media play calls start together; text-only and single-track pages work', async()=>{
    const music=deferred(), voice=deferred();
    const {media,players}=mediaSetup([()=>music.promise,()=>voice.promise]);
    const start=media.activate({jingle_url:'/music',narration_url:'/voice'});
    assert.deepEqual(players.map(p=>p.calls),[1,1]);
    music.resolve();voice.resolve();await start;
    assert(players.every(p=>p.playing));
    await media.activate({narration_url:'/voice-only'});
    assert(players.slice(0,2).every(p=>!p.playing && p.src===''));
    assert(players[2].playing);
    await media.activate({}); assert(!players[2].playing);
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
