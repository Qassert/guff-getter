const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const flush = () => new Promise(resolve => setImmediate(resolve));
function setup(options = {}) {
  const elements = {};
  for (const id of ['loader','generateImages','imagePanel','titleDescBox','sourceTitleHeading','nonsenseBox','crazyTitleBox','crazyExtractBox','outputContainer','bankButton','imageAmbient']) {
    const classes = new Set(['hidden']);
    elements[id] = {value:'source', checked:false, style:{setProperty(k,v){this[k]=v;}}, scrollHeight:20, textContent:'',
      classList:{add:(...xs)=>xs.forEach(x=>classes.add(x)),remove:(...xs)=>xs.forEach(x=>classes.delete(x)),contains:x=>classes.has(x)},
      replaceChildren(...children){this.children=children;this.textContent='';}};
  }
  elements.imageAmbient.children = [0,1].map(()=>{
    const classes = new Set();
    return {style:{setProperty(k,v){this[k]=v;}},classList:{add:(...xs)=>xs.forEach(x=>classes.add(x)),remove:(...xs)=>xs.forEach(x=>classes.delete(x)),contains:x=>classes.has(x)}};
  });
  const calls=[], frames=[], timers=[], images=[];
  let samples=0;
  const storage = new Map(options.restore ? [["newsmuncher.imageRewrite", "saved"]] : []);
  let rewriteSuccess=true, imageResolve;
  const context = {alert(){},generatedBackground:{preload(){}},console, setTimeout:(fn,delay)=>{if(delay===0) fn();else timers.push([fn,delay]);}, requestAnimationFrame:fn=>frames.push(fn),
    document:{getElementById:id=>elements[id], createElement(){
      samples++;
      if(options.sampleFails) throw new Error('canvas unavailable');
      return {getContext:()=>({drawImage(){},getImageData:()=>({data:new Uint8ClampedArray([180,40,60,255,30,110,170,255])})})};
    }}, window:{addEventListener(){},innerWidth:1200,innerHeight:900,matchMedia:()=>({matches:!!options.reduced})},
    sessionStorage:{getItem:k=>storage.get(k),setItem:(k,v)=>storage.set(k,v),removeItem:k=>storage.delete(k)},
    Image:class { constructor(){this.classList={add(){}};images.push(this);} getBoundingClientRect(){return {left:100,top:200,width:400,height:400};} set src(value){this.url=value;if(!options.deferLoad)this.onload();}},
    fetch: async (url,options) => {
      calls.push([url,options]);
      if(url==='/temp/temp_data') return {ok:true,json:async()=>({title:'Ham Shanker',description:'Bum Seeking intellectual connection',extract:'Source text'})};
      if(url==='/temp/shizzalise_data') return {ok:rewriteSuccess,json:async()=>({crazyReplacement1Title:'REWRITTEN',crazyReplacement1Extract:'TEXT',rewrite_id:'id-'+calls.length})};
      if(url==='/temp/generate_image') {
        assert.equal(elements.crazyTitleBox.textContent,'...REWRITTEN...');
        assert.equal(elements.outputContainer.style.display,'block');
        return new Promise(resolve=>imageResolve=resolve);
      }
      if(url==='/temp/image_result/saved') return {ok:true,json:async()=>({rewrite_id:'saved',crazyReplacement1Title:'SAVED',crazyReplacement1Extract:'TEXT',image_url:'/generated-images/saved.png'})};
      return {ok:true,json:async()=>({})};
    }};
  vm.createContext(context);vm.runInContext(fs.readFileSync('newsmuncher/static/image-colors.js','utf8'),context);vm.runInContext(fs.readFileSync('newsmuncher/static/script.js','utf8'),context);
  return {context,elements,calls,images,timers,get samples(){return samples;},finishFade(){while(timers.length)timers.shift()[0]();},paint(){while(frames.length) frames.shift()();}, resolveImage(ok){imageResolve({ok,json:async()=>({image_url:'/static/image-stub.svg'})});}, failRewrite(){rewriteSuccess=false;}};
}
(async()=>{
  assert(!/id="generateImages"[^>]*\bchecked/.test(fs.readFileSync('newsmuncher/templates/pet_profile.html','utf8')));
  let t=setup();t.elements.generateImages.checked=true;t.context.window.onload();assert.equal(t.elements.generateImages.checked,false);
  await flush();assert.equal(t.elements.sourceTitleHeading.textContent,'...Ham Shanker - Bum Seeking intellectual connection...');
  assert.equal(t.elements.titleDescBox.value,'Ham Shanker - Bum Seeking intellectual connection');
  t=setup();t.context.confirmData();await flush();t.paint();await flush();
  assert.equal(t.calls.length,1);assert.equal(t.elements.crazyTitleBox.textContent,'...REWRITTEN...');
  assert.equal(JSON.parse(t.calls[0][1].body).generate_images,undefined);
  t=setup();t.elements.generateImages.checked=true;t.context.confirmData();await flush();
  assert.equal(t.calls.length,1);assert.equal(t.elements.crazyTitleBox.textContent,'...REWRITTEN...');
  t.paint();await flush();assert.equal(t.calls.length,2);
  t.resolveImage(false);await flush();assert.match(t.elements.imagePanel.textContent,/unavailable/);assert.equal(t.elements.crazyTitleBox.textContent,'...REWRITTEN...');
  t=setup();t.elements.generateImages.checked=true;t.context.confirmData();await flush();t.paint();await flush();
  t.elements.generateImages.checked=false;t.context.confirmData();await flush();t.resolveImage(true);await flush();
  assert(t.elements.imagePanel.classList.contains('hidden'));assert.equal(t.elements.imagePanel.children.length,0);
  t=setup();t.failRewrite();t.elements.generateImages.checked=true;t.context.confirmData();await flush();t.paint();assert.equal(t.calls.length,1);
  t=setup();t.elements.generateImages.checked=true;t.context.confirmData();await flush();t.paint();await flush();t.resolveImage(true);await flush();t.paint();assert.equal(t.elements.imagePanel.children[0].url,'/static/image-stub.svg');
  // Sampling occurs after image load and fade, only once.
  t=setup({deferLoad:true});t.elements.generateImages.checked=true;t.context.confirmData();await flush();t.paint();await flush();t.resolveImage(true);await flush();
  assert.equal(t.samples,0);t.images[0].onload();t.paint();assert.equal(t.samples,0);t.finishFade();assert.equal(t.samples,1);
  assert(t.elements.imageAmbient.children.some(g=>g.classList.contains('active')));
  t=setup({sampleFails:true,reduced:true});t.elements.generateImages.checked=true;t.context.confirmData();await flush();t.paint();await flush();t.resolveImage(true);await flush();t.paint();
  assert.equal(t.samples,1);assert.equal(t.elements.imagePanel.children.length,1);assert.equal(t.timers.length,0);
  // A newer rewrite invalidates a queued colour callback from the previous image.
  t=setup();t.elements.generateImages.checked=true;t.context.confirmData();await flush();t.paint();await flush();t.resolveImage(true);await flush();t.paint();
  t.elements.generateImages.checked=false;t.context.confirmData();await flush();t.finishFade();assert.equal(t.samples,0);
  t=setup({restore:true,reduced:true});t.context.window.onload();await flush();t.paint();
  assert.equal(t.elements.generateImages.checked,false);assert.equal(t.elements.crazyTitleBox.textContent,'...SAVED...');assert.equal(t.samples,1);
  assert(!t.calls.some(([url])=>url==='/temp/generate_image'));
  t=setup();t.elements.generateImages.checked=true;t.context.confirmData();await flush();t.paint();await flush();
  t.elements.crazyTitleBox.textContent='...Edited title...';t.elements.crazyExtractBox.value='Edited body';
  t.resolveImage(true);await flush();t.paint();t.finishFade();
  assert.equal(t.elements.crazyTitleBox.textContent,'...Edited title...');assert.equal(t.elements.crazyExtractBox.value,'Edited body');
  t=setup();t.context.confirmData();await flush();
  assert.equal(t.elements.bankButton.textContent,'NOMINATE');
  t.context.bankThisBeauty();t.context.bankThisBeauty();await flush();
  assert.equal(t.elements.bankButton.textContent,'NOMINATED');
  assert.equal(t.calls.filter(([url])=>url.startsWith('/temp/confirm_data')).length,1);
  t.context.bankThisBeauty();await flush();
  assert.equal(t.calls.filter(([url])=>url.startsWith('/temp/confirm_data')).length,1);
  t.elements.crazyExtractBox.value='edited nomination';t.context.responseEdited();
  assert.equal(t.elements.bankButton.textContent,'UPDATE NOMINATION');
  t.context.bankThisBeauty();await flush();
  assert.equal(t.calls.filter(([url])=>url.startsWith('/temp/confirm_data')).length,2);
  t.context.confirmData();await flush();assert.equal(t.elements.bankButton.textContent,'NOMINATE');
  const rewriteCalls=t.calls.filter(([url])=>url==='/temp/shizzalise_data');
  assert.equal(JSON.parse(rewriteCalls[0][1].body).draft_session,JSON.parse(rewriteCalls[1][1].body).draft_session);
  const colors=t.context.representativeColors(new Uint8ClampedArray([255,255,255,255,0,0,0,255,200,40,50,0,180,40,60,255,30,110,170,255]));
  assert.equal(JSON.stringify(colors),'[[180,40,60],[30,110,170]]');
  assert.equal(t.context.representativeColors(new Uint8ClampedArray([255,255,255,255])),null);
  assert.match(fs.readFileSync('newsmuncher/static/styles.css','utf8'), /prefers-reduced-motion/);
  console.log('JavaScript checks passed: flow, restore, sampling, stale colours, reduced motion.');
})().catch(error=>{console.error(error);process.exitCode=1;});
