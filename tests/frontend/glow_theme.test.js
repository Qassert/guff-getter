const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs');
const {GlowTheme,PALETTE,CONTROL_SELECTOR}=require('../../newsmuncher/static/js/shared/glow-theme.js');

function fixture(randomValues=[0]){
 const values=[...randomValues],properties={},listeners={};
 const rootElement={style:{setProperty(name,value){properties[name]=value;}}};
 const target={addEventListener(name,fn,capture){listeners[name]={fn,capture};},removeEventListener(name){delete listeners[name];}};
 return{properties,listeners,target,theme:new GlowTheme({rootElement,random:()=>values.shift()??0})};
}

test('page binding chooses a non-orange shared colour before any interaction',()=>{
 const f=fixture([0]);f.theme.bind(f.target);
 assert.deepEqual([+f.properties['--glow-r'],+f.properties['--glow-g'],+f.properties['--glow-b']],PALETTE[0]);
 assert.equal(f.listeners.click.capture,true);
 assert(PALETTE.every(([r,g,b])=>!(r>200&&g>90&&g<200&&b<80)));
});

test('each enabled decorated control selects a different palette colour',()=>{
 const f=fixture([0,0,0]);f.theme.bind(f.target);const first={...f.properties};
 const control={disabled:false,getAttribute:()=>null};
 f.listeners.click.fn({target:{closest:selector=>{assert.equal(selector,CONTROL_SELECTOR);return control;}}});
 assert.notDeepEqual(f.properties,first);const second={...f.properties};
 f.listeners.click.fn({target:{closest:()=>control}});assert.notDeepEqual(f.properties,second);
});

test('disabled controls do not change colour and teardown removes the listener',()=>{
 const f=fixture([0,0]);f.theme.bind(f.target);const first={...f.properties};
 f.listeners.click.fn({target:{closest:()=>({disabled:true,getAttribute:()=>null})}});assert.deepEqual(f.properties,first);
 f.theme.destroy(f.target);assert.equal(f.listeners.click,undefined);
});

test('Create and Gallery use the shared glow variables on grouped artwork and controls',()=>{
 const shared=fs.readFileSync('newsmuncher/static/css/shared/styles.css','utf8');
 const gallery=fs.readFileSync('newsmuncher/static/css/gallery/promotion-gallery.css','utf8');
 const base=fs.readFileSync('newsmuncher/templates/base.html','utf8');
 assert(base.includes("path='js/shared/glow-theme.js'"));
 assert.match(shared,/--glow-rest-filter:[^;]*var\(--glow-r\)/);
 assert.match(shared,/--glow-rest-filter:\s*drop-shadow\(0 5px 5px[^;]*drop-shadow\(0 0 16px/);
 assert.match(shared,/--glow-hover-filter:\s*drop-shadow\(0 6px 6px[^;]*drop-shadow\(0 0 20px/);
 assert.doesNotMatch(shared,/\.profile-page \.funky-button::before\s*\{\s*filter:\s*var\(--tab-tint\) drop-shadow/);
 for(const selector of ['.source-udder','.munge-control','.mode-nav-button','.master-mute-button'])assert(shared.includes(selector));
 for(const selector of ['.gallery-page','.gallery-arrow','.gallery-fur-control','.funky-button'])assert(gallery.includes(selector));
 assert.match(shared,/transition:\s*filter 700ms ease/);assert.match(gallery,/transition:\s*filter 700ms ease/);
});
