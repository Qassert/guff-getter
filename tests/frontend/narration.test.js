const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs');
test('Creator retires active narration while preserving the historical controller',()=>{
 const html=fs.readFileSync('newsmuncher/templates/pet_profile.html','utf8');
 const script=fs.readFileSync('newsmuncher/static/js/creation/script.js','utf8');
 assert(!html.includes('narration.js')); assert(!html.includes('narrationButton'));
 assert(!html.includes('narrationAudio')); assert(!html.includes('VOICE:'));
 assert(!script.includes('narrationUI'));
 assert(fs.existsSync('newsmuncher/static/narration.js'));
});
