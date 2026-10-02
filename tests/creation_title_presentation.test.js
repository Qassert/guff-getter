const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const creator=fs.readFileSync('newsmuncher/templates/pet_profile.html','utf8');
const gallery=fs.readFileSync('newsmuncher/templates/promotion_gallery.html','utf8');
const galleryJs=fs.readFileSync('newsmuncher/static/promotion-gallery.js','utf8');
const galleryService=fs.readFileSync('newsmuncher/services/promotion_gallery.py','utf8');
const creatorJs=fs.readFileSync('newsmuncher/static/script.js','utf8');
const jingle=fs.readFileSync('newsmuncher/services/jingle_brief.py','utf8');

test('Creator retains source and generated titles as hidden data and renders body fields only',()=>{
 const distinctiveSourceHeading='DEAD FUNNY - 1994 AMERICAN FILM';
 assert.match(creator,/<input id="sourceTitleDraft" type="hidden"/);
 assert(!creator.includes('<textarea id="sourceTitleDraft"'));
 assert.match(creator,/<input id="responseTitleDraft" type="hidden"/);
 assert(!creator.includes('<textarea id="responseTitleDraft"'));
 assert.match(creator,/<textarea id="responseBodyDraft"[^>]*aria-label="Response body"/);
 assert.match(creator,/<textarea id="sourceBodyDraft"[^>]*aria-label="Source body"/);
 assert(!creator.includes(distinctiveSourceHeading));
 assert(creatorJs.includes("title.value=[data.title,data.description].filter(Boolean).join(' - ')"));
 assert(creatorJs.includes("titleBox.value=data.crazyReplacement1Title||''"));
 assert(creatorJs.includes("crazyReplacement1Title: document.getElementById('responseTitleDraft').value"));
});

test('distinctive source heading follows the real loader into hidden metadata while body remains visible',async()=>{
 const nodes=new Map();
 const get=id=>{if(!nodes.has(id))nodes.set(id,{value:'',type:id==='sourceTitleDraft'?'hidden':'textarea',style:{},scrollHeight:24,classList:{add(){},remove(){}}});return nodes.get(id);};
 const heading='DEAD FUNNY - 1994 AMERICAN FILM',body='The body remains readable.';
 const context={console,document:{getElementById:get,querySelectorAll:()=>[]},window:{},sessionStorage:{getItem:()=>null,setItem(){},removeItem(){}},setTimeout,clearTimeout,requestAnimationFrame:fn=>fn(),fetch:async()=>({ok:true,json:async()=>({title:'DEAD FUNNY',description:'1994 AMERICAN FILM',extract:body})})};
 vm.createContext(context);vm.runInContext(creatorJs,context);context.populateTempData();
 for(let i=0;i<6;i++)await Promise.resolve();
 assert.equal(get('sourceTitleDraft').value,heading);assert.equal(get('sourceTitleDraft').type,'hidden');
 assert.equal(get('sourceBodyDraft').value,body);assert.equal(get('sourceBodyDraft').type,'textarea');
});

test('Viewing renders body without a generated-title element while retaining API title',()=>{
 assert(!gallery.includes('id="galleryTitle"'));assert(gallery.includes('id="galleryBody"'));
 assert(!galleryJs.includes("get('galleryTitle')"));assert(galleryJs.includes("get('galleryBody').textContent = item.body"));
 assert.match(galleryService,/['"]title['"]:\s*entry\.get\(['"]crazyReplacement1Title['"]\)/);
});

test('saved title remains available to the jingle seed',()=>{
 assert.match(jingle,/title\s*=\s*entry\.get\(["']crazyReplacement1Title["']\)/);
 assert.match(jingle,/input=json\.dumps\(\{"title":\s*title\[:200\]\}/);
});
