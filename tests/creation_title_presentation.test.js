const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs');
const creator=fs.readFileSync('newsmuncher/templates/pet_profile.html','utf8');
const gallery=fs.readFileSync('newsmuncher/templates/promotion_gallery.html','utf8');
const galleryJs=fs.readFileSync('newsmuncher/static/promotion-gallery.js','utf8');
const galleryService=fs.readFileSync('newsmuncher/services/promotion_gallery.py','utf8');
const creatorJs=fs.readFileSync('newsmuncher/static/script.js','utf8');
const jingle=fs.readFileSync('newsmuncher/services/jingle_brief.py','utf8');

test('Creator retains generated title as hidden data and renders the body',()=>{
 assert.match(creator,/<input id="responseTitleDraft" type="hidden"/);
 assert(!creator.includes('<textarea id="responseTitleDraft"'));
 assert.match(creator,/<textarea id="responseBodyDraft"[^>]*aria-label="Response body"/);
 assert(creatorJs.includes("titleBox.value=data.crazyReplacement1Title||''"));
 assert(creatorJs.includes("crazyReplacement1Title: document.getElementById('responseTitleDraft').value"));
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
