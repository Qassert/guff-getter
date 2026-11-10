const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const {AnimationCycle,MadHelper,placementGeometry,avoidControls,discoverPlacements,contentOf,choose,idleDelay,KEY}=require('../../newsmuncher/static/js/shared/mad-helper.js');
const manifest=JSON.parse(fs.readFileSync('newsmuncher/static/images/mad-helper/manifest.json'));
function clock(){let id=0;const queued=new Map();return {queued,setTimeout(fn,delay){queued.set(++id,{fn,delay});return id;},clearTimeout(id){queued.delete(id);}};}

test('all sixteen original animations have alpha-video and transparent fallback derivatives',()=>{
    assert.equal(manifest.animations.length,16);assert.equal(Object.keys(manifest.originals).length,17);
    for(const clip of manifest.animations){
        assert(clip.duration>0&&clip.duration<20);
        for(const key of ['webm','fallback'])assert(fs.statSync('newsmuncher/static/images/mad-helper/'+clip[key]).size>100);
    }
});

test('80/20 time budget accounts for each selected clip duration with randomized intervals',()=>{
    for(const duration of [5.2,9.05,12.9,16.7]){
        assert.equal(idleDelay(duration,.2,()=>.5),duration*4000);
        assert(idleDelay(duration,.2,()=>0)<idleDelay(duration,.2,()=>1));
    }
    let active=0,idle=0;
    for(const clip of manifest.animations){active+=clip.duration;idle+=idleDelay(clip.duration,.2,()=>.5)/1000;}
    assert(Math.abs(active/(active+idle)-.2)<1e-10);
});

test('scheduled and click-triggered animations avoid repeats and keep a single timer',()=>{
    const timers=clock(),played=[],clips=manifest.animations;
    const cycle=new AnimationCycle({clips,timers,random:()=>0,onPlay:clip=>played.push(clip)});
    cycle.schedule();assert.equal(timers.queued.size,1);
    timers.queued.get(cycle.timer).fn();assert.equal(played[0],clips[0]);assert.equal(timers.queued.size,0);
    cycle.trigger();assert.equal(played[1],clips[1]);
    cycle.complete();cycle.schedule();assert.equal(timers.queued.size,1);
    cycle.stop();assert.equal(timers.queued.size,0);
});

test('hidden, disabled or reduced-motion idle cycles do not start playback',()=>{
    const timers=clock();let active=false,plays=0;
    const cycle=new AnimationCycle({clips:manifest.animations,timers,canRun:()=>active,onPlay:()=>plays++});
    cycle.schedule();cycle.trigger();assert.equal(plays,0);assert.equal(timers.queued.size,0);
    active=true;cycle.schedule();assert.equal(timers.queued.size,1);
    active=false;timers.queued.get(cycle.timer).fn();assert.equal(plays,0);
});

test('every animation remains selectable without the immediately previous one',()=>{
    const clips=manifest.animations,seen=new Set();
    for(let i=0;i<16;i++)seen.add(choose(clips,null,()=>i/16));
    assert.equal(seen.size,16);
    assert.notEqual(choose(clips,clips[0],()=>0),clips[0]);
});

test('desktop geometry anchors the LEFT edge at the rendered-text midpoint without unnecessary padding',()=>{
    const geometry=placementGeometry({paper:{left:200},text:{left:290,top:100,height:300},textHeight:180,viewportWidth:1200});
    assert.equal(geometry.x,200);assert.equal(geometry.y,190);assert.equal(geometry.clearance,0);
    assert(geometry.x+geometry.width/2<290);
});

test('mobile geometry stays in the viewport and reserves only necessary textarea clearance',()=>{
    const geometry=placementGeometry({paper:{left:12},text:{left:58,top:20,height:100},textHeight:800,viewportWidth:390});
    assert(geometry.x-geometry.width/2>=4);assert(geometry.x+geometry.width/2<390);
    assert.equal(geometry.y,70);assert(geometry.clearance>0);
    assert(58+geometry.clearance>=geometry.x+geometry.width/2+10);
});

function runtime(run){
    const timers=clock(),saved={};
    for(const name of ['setTimeout','clearTimeout','Audio','autoResize'])saved[name]=global[name];
    const voices=[];global.setTimeout=timers.setTimeout.bind(timers);global.clearTimeout=timers.clearTimeout.bind(timers);
    global.Audio=class{constructor(){this.paused=true;voices.push(this);}pause(){this.paused=true;}play(){this.paused=false;return Promise.resolve();}};
    const element=()=>({hidden:false,style:{},append(){},removeAttribute(){},load(){},pause(){}});
    const nodes=[0,1].map(()=>({button:element(),image:element(),bubble:element(),host:element(),text:{style:{}},padding:''}));
    const helper=Object.assign(Object.create(MadHelper.prototype),{nodes,enabled:true,doc:{hidden:false},random:()=>0,animations:manifest.animations,
        sounds:['boing','fart'],voices:new Map(),video:element(),fallback:element(),token:0,toggle:{checked:true},bubbleDuration:2500,alpha:false});
    helper.cycle=new AnimationCycle({clips:helper.animations,timers,onPlay:clip=>helper.play(clip,nodes[0]),onIdle:()=>helper.stopPlayback()});
    try{run({helper,nodes,timers,voices});}finally{helper.stopPlayback();helper.stopSound();for(const name of Object.keys(saved))global[name]=saved[name];}
}

test('rapid clicks share one animation and sound; late callbacks cannot resurrect the old placement',()=>runtime(({helper,nodes,voices,timers})=>{
    helper.click(nodes[0]);const stale=helper.fallback.onload;
    assert.equal(nodes[0].bubble.hidden,false);assert.equal(voices.filter(v=>!v.paused).length,1);
    helper.click(nodes[1]);stale();
    assert.equal(helper.owner,nodes[1]);assert.equal(nodes[0].image.style.visibility,'');
    assert.equal(nodes[0].bubble.hidden,true);assert.equal(nodes[1].bubble.hidden,false);
    assert.equal(voices.filter(v=>!v.paused).length,1);
    helper.fallback.onload();assert.equal(nodes[1].image.style.visibility,'hidden');
    const bubbleTimer=timers.queued.get(helper.bubbleTimer);assert.equal(bubbleTimer.delay,2500);
    bubbleTimer.fn();assert(nodes.every(n=>n.bubble.hidden));
    helper.cycle.complete();assert.equal(helper.owner,null);assert.equal(nodes[1].image.style.visibility,'');
}));

test('disable stops playback, sound and timers, restores layout and persists separately from mute',()=>runtime(({helper,nodes,voices,timers})=>{
    const stored=new Map();helper.storage={setItem:(key,value)=>stored.set(key,value)};helper.listen=()=>{};
    helper.click(nodes[0]);helper.setEnabled(false);
    assert.equal(stored.get(KEY),'false');assert(!stored.has('newsmuncher.masterMuted'));
    assert(nodes.every(n=>n.host.hidden&&n.bubble.hidden));assert(voices.every(v=>v.paused));
    assert.equal(helper.owner,null);assert.equal(timers.queued.size,0);
    helper.click(nodes[0]);assert.equal(voices.filter(v=>!v.paused).length,0);
}));

test('all three modes opt in through shared settings and explicit text anchors',()=>{
    const create=fs.readFileSync('newsmuncher/templates/pet_profile.html','utf8');
    assert(create.includes("partials/mad-helper-toggle.html"));
    for(const file of ['pet_profile.html','build.html','promotion_gallery.html']) {
        const template=fs.readFileSync('newsmuncher/templates/'+file,'utf8');
        assert(template.includes('data-mad-helper-text'));assert(template.includes('data-mad-helper-paper'));
        assert(template.includes("partials/mad-helper-toggle.html"));assert(template.includes('mad-helper-2'));
    }
    assert.match(fs.readFileSync('newsmuncher/static/js/creation/script.js','utf8'),/function autoResize\(textarea\) \{\s*window.NewsMuncherMadHelper\?\.scheduleLayout\(\)/);
    const css=fs.readFileSync('newsmuncher/static/css/creation/mad-helper.css','utf8');
    assert(css.includes('position: absolute'));assert(css.includes('pointer-events: none'));
});


test('read-only Gallery text and empty editable prompts preserve their actual content',()=>{
    assert.equal(contentOf({textContent:'The latest saved Gallery story!'}),'The latest saved Gallery story!');
    assert.equal(contentOf({value:'',textContent:'Initial prompt markup'}),'');
    assert.equal(contentOf({value:'Manual BUILD prompt edits'}),'Manual BUILD prompt edits');
});

test('Gallery controls remain clear while the helper stays on the left parchment edge',()=>{
    const geometry={x:100,y:300,width:128,clearance:0};
    const arrow={left:60,right:140,top:250,bottom:350};
    const adjusted=avoidControls(geometry,[arrow]);
    assert.equal(adjusted.x,100);
    assert(adjusted.y+64+12<=arrow.top||adjusted.y-64-12>=arrow.bottom);
    assert.deepEqual(avoidControls(geometry,[{left:700,right:800,top:250,bottom:350}]),geometry);
});

test('placement discovery includes only explicit regions and resolves their own parchment',()=>{
    const paper={},unrelated={dataset:{},closest:()=>null};
    const textarea={dataset:{},closest:()=>paper};
    const arrow={},body={dataset:{madHelperAvoid:'.gallery-arrow'},closest:()=>paper};
    const doc={querySelectorAll:selector=>selector==='.gallery-arrow'?[arrow]:[textarea,body,unrelated]};
    const placements=discoverPlacements(doc);
    assert.equal(placements.length,2);assert.equal(placements[0].text,textarea);
    assert.equal(placements[0].paper,paper);assert.deepEqual(placements[1].avoid,[arrow]);
});
