const fs = require('fs'), vm = require('vm'), assert = require('assert');
const key = 'a'.repeat(24);
function fixture() {
    const nodes = new Map();
    function get(id) {
        if (!nodes.has(id)) nodes.set(id, {hidden: true, disabled: false, textContent: '', value: '',
            style: {}, children: [], classList: {add(){}, remove(){}},
            paused:true, plays:0, pause(){this.paused=true;}, load(){}, async play(){this.plays++;this.paused=false;}, removeAttribute(name){ delete this[name]; },
            getAttribute(name){ return this[name]; },
            replaceChildren(){ this.children = []; }, appendChild(node){ this.children.push(node); }});
        return nodes.get(id);
    }
    get('crazyTitleBox').textContent = '...Visible title...';
    get('crazyExtractBox').value = 'Visible body.';
    const requests = [], response = {entry_id: key, can_generate: true, narration_status: 'none'};
    const context = {console, document: {getElementById:get, createElement: () => ({})},
        setTimeout: () => 1, clearTimeout(){}, window: {addEventListener(){}},
        sessionStorage: {getItem:()=>null, setItem(){}, removeItem(){}},
        requestAnimationFrame: fn => fn(),
        fetch: async (url, options={}) => {
            requests.push({url, options});
            let data = response;
            if (url === '/narrations/') data = {narrations: [response]};
            return {ok:true, json:async()=>data};
        }};
    vm.createContext(context);
    vm.runInContext(fs.readFileSync('newsmuncher/static/creation-meta.js','utf8') +
        fs.readFileSync('newsmuncher/static/narration.js','utf8') + '\nthis.ui=narrationUI;',context);
    return {context, get, requests, response};
}
(async()=>{
    const f=fixture(), {ui}=f.context;
    await ui.show({nominated:false});
    assert.equal(f.requests.length,0);
    assert(f.get("narrationControls").hidden);
    assert.match(fs.readFileSync("newsmuncher/static/styles.css", "utf8"), /\.narration-controls-hidden\[hidden\]/);
    await ui.show({nominated:true,rewrite_id:'rewrite'});
    assert(!f.get('narrationControls').hidden);
    assert.equal(f.requests.filter(r=>r.options.method==='POST').length,0);
    f.get('responseEditor').hidden=false;
    f.get('responseTitleDraft').value='Edited title';
    f.get('responseBodyDraft').value='Edited body';
    let release;
    const original=f.context.fetch;
    f.context.fetch=async(url,options={})=>{
        if(options.method!=='POST') return original(url,options);
        f.requests.push({url,options});
        await new Promise(resolve=>release=resolve);
        return {ok:true,json:async()=>({entry_id:key,narration_url:'/narrations/'+key+'/audio',voice_name:'Coral',narration_status:'complete'})};
    };
    const generation=ui.act();
    await ui.act();
    assert(f.get('narrationButton').disabled);
    assert(f.get('narrationButton').textContent.includes('GENERATING'));
    release(); await generation;
    const posts=f.requests.filter(r=>r.options.method==='POST');
    assert.equal(posts.length,1);
    assert.deepEqual(JSON.parse(posts[0].options.body),{title:'Edited title',body:'Edited body'});
    assert.equal(f.get('narrationButton').hidden,false);
    assert.equal(f.get('narrationButton').textContent,'▶ PLAY NARRATION');
    assert.equal(f.get('narrationAudio').hidden,true);
    assert.equal(f.get('narrationAudio').plays,0);
    await ui.act(); await ui.act();
    assert.equal(f.requests.filter(r=>r.options.method==='POST').length,1);
    assert(f.get('narrationAudio').src.endsWith('/audio'));
    assert.equal(f.get('narrationMessage').textContent,'');
    assert.equal(f.get('creationMeta').textContent,'VOICE: CORAL');
    assert.equal(f.get('crazyTitleBox').textContent,'...Visible title...');

    const late=fixture();
    await late.context.ui.show({nominated:true,rewrite_id:'old'});
    let finish;
    late.context.fetch=async()=>{await new Promise(resolve=>finish=resolve);return {ok:true,json:async()=>({narration_url:'/old.mp3'})};};
    const running=late.context.ui.act();
    await late.context.ui.show({nominated:false});
    finish();await running;
    assert.equal(late.get('narrationAudio').src,undefined);
    assert.equal(late.get('narrationButton').textContent,'READ ALOUD');
    assert(late.get('narrationButton').disabled);

    const fresh=fixture();
    Object.assign(fresh.response,{narration_url:'/saved.mp3',title:'Saved',voice_name:'Cedar'});
    await fresh.context.ui.show({nominated:true,rewrite_id:'saved-rewrite'});
    assert.equal(fresh.get('narrationAudio').src,'/saved.mp3');
    assert.equal(fresh.get('narrationAudio').hidden,true);
    assert.equal(fresh.get('narrationButton').hidden,false);
    await fresh.context.ui.ensure();
    assert.equal(fresh.get('narrationAudio').plays,0);
    await fresh.context.ui.act();
    assert.equal(fresh.get('narrationAudio').plays,1);
    assert(!/id="narrationAudio"[^>]*controls/.test(fs.readFileSync('newsmuncher/templates/pet_profile.html','utf8')));
    assert.equal(fresh.get('narrationMessage').textContent,'');
    assert.equal(fresh.get('creationMeta').textContent,'VOICE: CEDAR');
    assert.equal(fresh.requests.filter(r=>r.options.method==='POST').length,0);
    assert.equal(fresh.get('crazyTitleBox').textContent,'...Visible title...');

    // Exercise the existing SHIZZALISE path with the real narration hooks installed.
    const normal=fixture();
    vm.runInContext(fs.readFileSync('newsmuncher/static/script.js','utf8'),normal.context);
    vm.runInContext('resetImagePanel=()=>{}; showLoader=()=>{}; hideLoader=()=>{};',normal.context);
    normal.get('sourceTitleDraft').value='Source title'; normal.get('sourceBodyDraft').value='Original source';
    normal.context.fetch=async(url,options={})=>{
        normal.requests.push({url,options});
        return {ok:true,json:async()=>({nominated:false,rewrite_id:'new',crazyReplacement1Title:'New title',crazyReplacement1Extract:'New body'})};
    };
    normal.context.confirmData();
    for(let i=0;i<10;i++) await Promise.resolve();
    assert.deepEqual(normal.requests.map(r=>r.url),['/temp/shizzalise_data']);
    assert.equal(normal.get('responseTitleDraft').value,'New title');
    console.log('Narration: explicit generation only, direct edited text, duplicate guard, reuse and stale responses.');
})().catch(error=>{console.error(error);process.exit(1);});
