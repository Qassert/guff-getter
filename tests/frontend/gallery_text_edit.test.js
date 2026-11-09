const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const {StoryTextSaver} = require('../../newsmuncher/static/js/creation/story-text-save.js');
const {PromotionGallery} = require('../../newsmuncher/static/js/gallery/promotion-gallery.js');
const defer = () => {let resolve; const promise=new Promise(r=>resolve=r); return {promise,resolve};};

function editor(fetcher) {
    let current = {crazyReplacement1Title:'Title', crazyReplacement1Extract:'Original'};
    let saved = JSON.stringify(current);
    const notices=[];
    const saver=new StoryTextSaver({
        snapshot:()=>JSON.stringify(current)!==saved ? {rewrite_id:'rewrite-a',text:{...current}}:null,
        saved:draft=>{saved=JSON.stringify(draft.text);},notify:text=>notices.push(text),fetcher
    });
    return {saver,notices,edit:text=>{current.crazyReplacement1Extract=text;},dirty:()=>JSON.stringify(current)!==saved};
}
function navigation(saver) {
    let click; const visits=[];
    const link={href:'/promotion-gallery/',dataset:{},classList:{add(){}},addEventListener:(_name,handler)=>click=handler};
    const window={creationTextSaver:saver,matchMedia:()=>({matches:true}),
        location:{assign:url=>visits.push(url)},setTimeout:handler=>handler()};
    vm.runInNewContext(fs.readFileSync('newsmuncher/static/js/shared/mode-nav.js','utf8'),
        {window,document:{addEventListener(){},querySelectorAll:()=>[link]}});
    return {visits,click:()=>click({button:0,preventDefault(){}})};
}

test('normal editor-to-Gallery navigation waits for durable save; refreshed clients read edited text',async()=>{
    const ack=defer(), calls=[];
    const record={id:'a',body:'Original',image_url:'/kept.png',jingle_url:'/kept.mp3',video_url:'/kept.mp4'};
    const e=editor(async(url,options)=>{
        calls.push({url,options});await ack.promise;
        record.body=JSON.parse(options.body).crazyReplacement1Extract;
        return {ok:true};
    });
    e.edit('Edited and saved story');
    const nav=navigation(e.saver), pending=nav.click();
    assert.deepEqual(nav.visits,[]);
    assert.equal(record.body,'Original');
    ack.resolve();await pending;
    assert.deepEqual(nav.visits,['/promotion-gallery/']);
    assert.equal(e.dirty(),false);
    assert.equal(calls.length,1);
    assert.equal(calls[0].url,'/temp/creation/rewrite-a/text');
    assert.equal(calls[0].options.method,'PATCH');
    assert.equal(calls[0].options.keepalive,true);
    for(let i=0;i<2;i++) {
        const gallery=new PromotionGallery({view:{},fetcher:async()=>({ok:true,json:async()=>({...record})})});
        const shown=await gallery.storedItem(record);
        assert.equal(shown.body,'Edited and saved story');
        assert.equal(shown.image_url,'/kept.png');assert.equal(shown.jingle_url,'/kept.mp3');assert.equal(shown.video_url,'/kept.mp4');
    }
});

test('failed saves keep editor navigation in place and edits available for retry',async()=>{
    const e=editor(async()=>({ok:false}));e.edit('Unsaved work');
    const nav=navigation(e.saver);await nav.click();
    assert.deepEqual(nav.visits,[]);assert.equal(e.dirty(),true);
    assert.match(e.notices.at(-1),/could not be saved/);
    e.saver.fetcher=async()=>({ok:true});await nav.click();
    assert.deepEqual(nav.visits,['/promotion-gallery/']);assert.equal(e.dirty(),false);
});

test('autosave serializes rapid edits, drains the newest text and avoids duplicate saves',async()=>{
    const first=defer(), saved=[];
    const e=editor(async(_url,options)=>{
        const body=JSON.parse(options.body).crazyReplacement1Extract;
        if(!saved.length) await first.promise;
        saved.push(body);return {ok:true};
    });
    e.edit('Edit one');e.saver.schedule();
    const pending=e.saver.flush();
    e.edit('Edit two');assert.equal(e.saver.flush(),pending);
    first.resolve();await pending;
    assert.deepEqual(saved,['Edit one','Edit two']);
    await e.saver.flush();assert.equal(saved.length,2);
});

test('browser-back Gallery resume reloads the same saved item without regenerating media',async()=>{
    const shown=[], requests=[];
    const gallery=new PromotionGallery({view:{show:item=>shown.push(item),error:assert.fail},
        fetcher:async(url,options)=>{requests.push({url,options});return {ok:true,json:async()=>({id:'a',body:'Latest saved body'})};}});
    gallery.current={id:'a',body:'Original'};
    gallery.leave();await gallery.resume();
    assert.equal(shown.at(-1).body,'Latest saved body');
    assert.equal(requests.length,1);assert.equal(requests[0].url,'/promotion-gallery/items/a');
    assert.equal(requests[0].options.cache,'no-store');
});

test('editor wires text saves separately from nomination/media and retains local draft recovery',()=>{
    const script=fs.readFileSync('newsmuncher/static/js/creation/script.js','utf8');
    assert.match(script,/function responseEdited\(\)\s*\{[\s\S]*?creationTextSaver\?\.schedule/);
    assert.match(script,/window\.addEventListener\('pagehide',[^\n]*creationTextSaver\.flush/);
    assert.match(script,/creationNominated && displayedRewriteId && window\.creationTextSaver/);
    assert.match(script,/access\.restore\(\); responseEdited\(\)/);
    const gallery=fs.readFileSync('newsmuncher/static/js/gallery/promotion-gallery.js','utf8');
    assert.match(gallery,/pageshow[^\n]*event\.persisted[^\n]*gallery\.resume/);
});

test('an acknowledged local editor draft cannot replace newer server text on reopen',()=>{
    const local={sourceTitleDraft:'Source',sourceBodyDraft:'Source body',responseTitleDraft:'Old title',responseBodyDraft:'Old saved text',rewriteId:'a'};
    local.savedTextSnapshot=JSON.stringify({crazyReplacement1Title:local.responseTitleDraft,crazyReplacement1Extract:local.responseBodyDraft});
    const nodes=new Map();
    const get=id=>{
        if(!nodes.has(id))nodes.set(id,{value:id==='responseBodyDraft'?'Newer server text':id==='responseTitleDraft'?'Newer title':'',style:{}});
        return nodes.get(id);
    };
    let adapter;
    const access={register:(_name,value)=>adapter=value,read:()=>local,restore:()=>{adapter.restore(local);return true;}};
    const context={window:{adoptionAccess:access,location:{search:'?rewrite_id=a'}},document:{getElementById:get},
        displayedRewriteId:'a',creationNominated:true,nominatedSnapshot:JSON.stringify({crazyReplacement1Title:'Newer title',crazyReplacement1Extract:'Newer server text'}),
        URLSearchParams,autoResize(){},updateCopyButton(){},restoreImageRewrite:()=>new Promise(()=>{})};
    vm.createContext(context);
    const source=fs.readFileSync('newsmuncher/static/js/creation/script.js','utf8');
    vm.runInContext(source.slice(source.indexOf('window.onload =')),context);
    context.window.onload();
    assert.equal(get('responseBodyDraft').value,'Newer server text');
    assert.equal(get('responseTitleDraft').value,'Newer title');
    assert.equal(get('sourceBodyDraft').value,'Source body');
});
