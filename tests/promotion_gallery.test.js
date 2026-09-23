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
