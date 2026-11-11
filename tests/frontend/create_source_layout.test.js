const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const css=fs.readFileSync('newsmuncher/static/css/shared/styles.css','utf8');
const script=fs.readFileSync('newsmuncher/static/js/creation/script.js','utf8');

test('source alone gains exactly 2pt without changing line-height or result fitting',()=>{
 const rule=css.match(/\.profile-page #sourceBodyDraft\s*\{([^}]+)\}/)[1];
 assert.match(rule,/font-size:\s*calc\(1rem \+ 2pt\)/);
 assert.doesNotMatch(rule,/line-height|font-family|font-weight/);
 assert.match(css,/input, textarea \{[^}]*font-size: 1rem; line-height: 1.6/s);
 assert.match(css,/#responseBodyDraft\s*\{[^}]*font-size: var\(--creation-body-font-size\)/s);
});

test('CREATE controls reserve their scaled upper footprint without changing BUILD',()=>{
 const rule=css.match(/\.profile-page \.profile-container:has\(#sourceEditor\) \.munge-generation-controls\s*\{([^}]+)\}/)[1];
 assert.match(rule,/position:\s*relative/);assert.match(rule,/transform:\s*none/);
 assert.match(rule,/height:\s*calc\(var\(--source-munge-width\) \/ 1.18 \/ 2\)/);
 assert.match(css,/:has\(#sourceEditor\) \.munge-control\s*\{[^}]*flex: 0 0 var\(--source-munge-width\)/s);
 assert.match(css,/:has\(#sourceEditor\) \{ --source-munge-width: 33\.333vw/);
 assert.doesNotMatch(css.match(/\.profile-page #sourceEditor\s*\{([^}]+)\}/)[1],/margin-bottom:\s*-/);
});

test('source textarea grows for short/medium/long text and recalculates after wrapping and font loading',async()=>{
 const events={},body={id:'sourceBodyDraft',clientWidth:600,scrollHeight:40,style:{}},fonts={};
 fonts.ready=new Promise(resolve=>fonts.resolve=resolve);let callback,layouts=0;
 const context={document:{getElementById:()=>body,fonts},window:{NewsMuncherMadHelper:{scheduleLayout:()=>layouts++},addEventListener:(name,fn)=>events[name]=fn},ResizeObserver:class{constructor(fn){callback=fn;}observe(el){assert.equal(el,body);}}};
 vm.createContext(context);
 vm.runInContext(script.slice(script.indexOf('function autoResize('),script.indexOf('const responseArticleFitter =')),context);
 for(const height of [40,180,1200]){body.scrollHeight=height;context.autoResize(body);assert.equal(body.style.height,height+'px');}
 body.clientWidth=320;body.scrollHeight=1800;callback();assert.equal(body.style.height,'1800px');
 const before=layouts;callback();assert.equal(layouts,before,'height-only changes must not cause a resize loop');
 body.scrollHeight=2000;events.resize();assert.equal(body.style.height,'2000px');
 body.scrollHeight=2100;fonts.resolve();await Promise.resolve();assert.equal(body.style.height,'2100px');
 assert.equal(body.style.fontSize,undefined,'source must grow rather than shrink its font');
});
