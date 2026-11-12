const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs');
const html=fs.readFileSync('newsmuncher/templates/promotion_gallery.html','utf8');
const css=fs.readFileSync('newsmuncher/static/css/gallery/promotion-gallery.css','utf8');
const js=fs.readFileSync('newsmuncher/static/js/gallery/promotion-gallery.js','utf8');

test('completion notification stays in parchment normal flow and spans desktop grid',()=>{
 const article=html.slice(html.indexOf('<article id="galleryPage"'),html.indexOf('</article>'));
 assert.match(article,/id="galleryCompletionStatus"[^>]*role="status"[^>]*aria-live="polite"[^>]*aria-atomic="true"[^>]*tabindex="-1"/);
 const rule=css.match(/\.gallery-completion-status \{([^}]+)\}/)[1];
 assert.match(rule,/position: relative/);assert.match(rule,/grid-column: 1 \/ -1/);
 assert.match(rule,/max-width: 100%/);assert.match(rule,/overflow-wrap: anywhere/);
 assert.doesNotMatch(rule,/position: absolute|bottom:|translate/);
 assert.match(css,/:has\(\.gallery-completion-status:not\(\[hidden\]\)\)[^}]*padding-bottom:[^}]*--gallery-control-size/s);
 assert.match(css,/@media \(max-width: 620px\)[\s\S]*padding-bottom: calc\(14px \+ var\(--gallery-control-size\) \/ 2\)/);
});

test('visible-page errors use the contained notification and safe retry dialog explains both costs',()=>{
 assert.match(js,/this\.progress\(message\);\s*completionStatus\.dataset\.kind = 'error'/);
 assert.match(js,/completionStatus\.focus\?\./);
 assert.match(js,/Both requests may incur charges/);
 assert.match(js,/existing image and story will stay unchanged/);
 assert.match(html,/id="galleryEndImageRetryDescription"/);
});
