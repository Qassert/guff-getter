const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const {ArticleTextFitter,DEFAULT_MIN_PX,DEFAULT_MAX_PX}=require('../../newsmuncher/static/js/shared/article-text-fit.js');

const never={ready:new Promise(()=>{})};
function textBox(fitsThrough,{width=300,height=200,text='Unchanged article\nwith punctuation!'}={}) {
  const style={},dataset={};
  return {style,dataset,textContent:text,value:text,clientWidth:width,clientHeight:height,
    get scrollHeight(){return parseFloat(style.fontSize||'16')<=fitsThrough?height:height+20;},
    get scrollWidth(){return parseFloat(style.fontSize||'16')<=fitsThrough?width:width+20;}};
}
function fitter(element,extras={}) {
  return new ArticleTextFitter({element,fonts:never,ResizeObserverClass:null,
    resizeTarget:null,raf:fn=>{fn();return 1;},cancelRaf(){},...extras});
}

test('short articles expand to the generous 60px maximum without changing content',()=>{
  const element=textBox(80),before=element.textContent;
  assert.equal(fitter(element).fit(),DEFAULT_MAX_PX);
  assert.equal(element.style.fontSize,'60px');assert.equal(element.textContent,before);
});

test('fitting uses the allocated content region rather than the text element own height',()=>{
  const style={},element={style,dataset:{},clientWidth:100,clientHeight:20,
    get scrollHeight(){return 170;},get scrollWidth(){return 280;}};
  const container={clientWidth:300,clientHeight:220};
  assert.equal(fitter(element,{container}).fit(),DEFAULT_MAX_PX);
  assert.equal(element.style.height,'170px');
});

test('long articles shrink by rendered overflow measurement and remain within bounds',()=>{
  const element=textBox(13.4),size=fitter(element).fit();
  assert(size>=13 && size<=13.5);assert.equal(element.style.overflowY,'hidden');
  assert(size>=DEFAULT_MIN_PX && size<=DEFAULT_MAX_PX);
});

test('unfittable articles stop at 6pt and use contained scrolling',()=>{
  const element=textBox(4),size=fitter(element).fit();
  assert.equal(size,8);assert.equal(element.style.fontSize,'8px');
  assert.equal(element.style.overflowY,'auto');assert.equal(element.dataset.textFitOverflow,'true');
});

test('resize, observed layout changes and font readiness schedule fitting once per frame',async()=>{
  let resize,observed,frame,fitCalls=0;
  const resizeTarget={addEventListener(name,fn){assert.equal(name,'resize');resize=fn;},removeEventListener(){}};
  class Observer {constructor(fn){observed=fn;}observe(){}disconnect(){}}
  const fonts={ready:Promise.resolve()};
  const unit=new ArticleTextFitter({element:textBox(20),fonts,resizeTarget,ResizeObserverClass:Observer,
    raf:fn=>{frame=fn;return 7;},cancelRaf(){}});
  unit.fit=()=>{fitCalls++;};resize();observed();await fonts.ready;await Promise.resolve();
  assert.equal(fitCalls,0);frame();assert.equal(fitCalls,1);
});

test('disconnect cleans observers, pending animation frame and resize listener',()=>{
  let removed=false,disconnected=false,cancelled=null;
  const resizeTarget={addEventListener(){},removeEventListener(name){removed=name==='resize';}};
  class Observer {observe(){}disconnect(){disconnected=true;}}
  const unit=new ArticleTextFitter({element:textBox(20),fonts:never,resizeTarget,ResizeObserverClass:Observer,
    raf:()=>9,cancelRaf:id=>{cancelled=id;}});
  unit.schedule();unit.disconnect();
  assert(disconnected&&removed);assert.equal(cancelled,9);assert.equal(unit.frame,null);
});

test('Create and Gallery wire dynamic updates into the shared fitter lifecycle',()=>{
  const create=fs.readFileSync('newsmuncher/static/js/creation/script.js','utf8');
  const gallery=fs.readFileSync('newsmuncher/static/js/gallery/promotion-gallery.js','utf8');
  const createTemplate=fs.readFileSync('newsmuncher/templates/pet_profile.html','utf8');
  const galleryTemplate=fs.readFileSync('newsmuncher/templates/promotion_gallery.html','utf8');
  assert(createTemplate.includes('js/shared/article-text-fit.js'));
  assert(galleryTemplate.includes('js/shared/article-text-fit.js'));
  assert(galleryTemplate.includes('id="galleryTextRegion"'));
  assert(createTemplate.includes('class="section-editor article-fit-region"'));
  assert.match(create,/container: document\.getElementById\('responseEditor'\)/);
  assert.match(gallery,/container: get\('galleryTextRegion'\)/);
  assert.match(create,/responseBodyDraft[\s\S]*responseArticleFitter\.schedule\(\)/);
  assert.match(create,/responseArticleFitter\?\.disconnect\(\)/);
  assert.match(gallery,/show\(item\)[\s\S]*galleryBody[\s\S]*articleFitter\?\.schedule\(\)/);
  assert.match(gallery,/articleFitter\?\.disconnect\(\)/);
});

test('Create and Gallery regions vertically centre fitted text with breathing room',()=>{
  const shared=fs.readFileSync('newsmuncher/static/css/shared/styles.css','utf8');
  const gallery=fs.readFileSync('newsmuncher/static/css/gallery/promotion-gallery.css','utf8');
  assert.match(shared,/#responseEditor\s*\{[^}]*padding: 26px 0;[^}]*align-items: center;/s);
  assert.match(gallery,/\.gallery-text-region\s*\{[^}]*align-items: center;[^}]*padding: 26px 0;/s);
});
