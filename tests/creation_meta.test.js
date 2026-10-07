const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const {CreationMeta} = require('../newsmuncher/static/js/creation/creation-meta.js');

test('metadata line includes only populated values with dynamic separators', () => {
    const node = {textContent: '', hidden: true};
    const meta = new CreationMeta(id => id === 'creationMeta' ? node : null);
    meta.setStyle('Cyberpunk');
    assert.equal(node.textContent, 'IMAGE STYLE: CYBERPUNK');
    meta.setGenre('Heavy Metal');
    assert.equal(node.textContent,
        'IMAGE STYLE: CYBERPUNK – MUSIC GENRE: HEAVY METAL');
    meta.setStyle('');
    assert.equal(node.textContent, 'MUSIC GENRE: HEAVY METAL');
    meta.reset();
    assert.equal(node.textContent, '');
    assert.equal(node.hidden, true);
});

test('template has one metadata line, one shared action row and correct script order', () => {
    const html = fs.readFileSync('newsmuncher/templates/pet_profile.html', 'utf8');
    assert.equal((html.match(/id="creationMeta"/g) || []).length, 1);
    assert.equal((html.match(/id="creationActions"/g) || []).length, 1);
    for (const id of ['bankButton', 'embellishButton', 'jingleButton',
                      'jingleStop']) {
        const row = html.slice(html.indexOf('id="creationActions"'), html.indexOf('</div>', html.indexOf('id="animationControls"')) + 6);
        assert(row.includes(`id="${id}"`), `${id} must be in shared action row`);
    }
    assert(!html.includes('id="redoImageButton"'));
    assert(!html.includes('id="animationButton"'));
    assert(!html.includes('id="imageStyle"'));
    assert(!html.includes('id="jingleGenre"'));
    assert(html.indexOf("path='js/creation/creation-meta.js'") < html.indexOf("path='js/creation/video.js'"));
    assert(!html.includes("path='narration.js'"));
    assert(!html.includes('narrationButton'));
    assert(!html.includes('VOICE:'));
    assert(html.indexOf("path='js/creation/creation-meta.js'") < html.indexOf("path='js/creation/jingles.js'"));
});

test('shared action CSS centres, wraps and removes hidden controls from layout', () => {
    const css = fs.readFileSync('newsmuncher/static/css/shared/styles.css', 'utf8');
    assert.match(css, /\.creation-actions\s*\{[^}]*justify-content:\s*center/);
    assert.match(css, /\.creation-actions\s*\{[^}]*flex-wrap:\s*wrap/);
    assert.match(css, /\.creation-actions\s*>\s*\[hidden\][^{]*\{\s*display:\s*none/);
    assert.match(css, /\.creation-actions #bankButton[\s\S]*position:\s*relative/);
});
