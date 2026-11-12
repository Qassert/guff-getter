const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs');
const html=fs.readFileSync('newsmuncher/templates/promotion_gallery.html','utf8');
const css=fs.readFileSync('newsmuncher/static/css/gallery/promotion-gallery.css','utf8');
const js=fs.readFileSync('newsmuncher/static/js/gallery/promotion-gallery.js','utf8');

test('completion status is screen-reader-only with no visible box or parchment space',()=>{
 assert.match(html,/id="galleryCompletionStatus"[^>]*role="status"[^>]*aria-live="polite"/);
 const rule=css.match(/\.gallery-completion-status \{([^}]+)\}/)[1];
 assert.match(rule,/position: absolute/);assert.match(rule,/width: 1px; height: 1px/);
 assert.match(rule,/clip-path: inset\(50%\)/);assert.match(rule,/border: 0/);
 assert.doesNotMatch(css,/:has\(\.gallery-completion-status/);
 assert.doesNotMatch(js,/completionStatus\.focus/);
});

test('retry popup retains its description and cost warning',()=>{
 assert.match(js,/this\.progress\(message\);\s*completionStatus\.dataset\.kind = 'error'/);
 assert.match(js,/Both requests may incur charges/);
 assert.match(js,/existing image and story will stay unchanged/);
 assert.match(html,/id="galleryEndImageRetryDescription"/);
});
