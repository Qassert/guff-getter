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
    await ui.show({rewrite_id:'a'}); await ui.act(); await ui.show({rewrite_id:'a'});
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
    await ui.show({rewrite_id:'a'});
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
    await ui.show({rewrite_id:'a'}); await ui.act(); await ui.act();
    assert.deepEqual(calls,['GET','POST','GET']);
});
test('rewrite switch ignores old responses and timer callbacks', async () => {
    const old=deferred(), calls=[];
    const {ui,states,timers,stops}=setup(async (url,opts)=>{
        calls.push(url);
        if(url.endsWith('/old')) return old.promise;
        return response({video_status:'started',can_generate:false});
    });
    const request=ui.show({rewrite_id:'old'}); await ui.show({rewrite_id:'new'});
    old.resolve(response({can_generate:true,video_url:'/old-video'})); await request;
    assert.equal(states.at(-1).video_status,'started'); assert.equal(ui.key,'new');
    ui.stop(); const count=calls.length; await timers[0](); assert.equal(calls.length,count); assert(stops()>=3);
});
test('permission failures use safe sign-in message without exposing provider detail', async () => {
    const {ui,states}=setup(async()=>({ok:false,status:401}));
    await ui.show({rewrite_id:'a'}); await ui.act();
    assert.match(states.at(-1).message,/Sign in/); assert(!ui.state.can_generate);
});
