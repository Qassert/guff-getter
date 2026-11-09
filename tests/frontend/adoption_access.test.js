const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const {AdoptionAccess} = require('../../newsmuncher/static/js/shared/adoption-access.js');
const build = require('../../newsmuncher/static/build-page.js');
const tick = () => new Promise(resolve => setImmediate(resolve));

function fixture(adopted = false) {
    const saved = new Map(), notices = [], redirects = [];
    const storage = {getItem: key => saved.get(key), setItem: (key, value) => saved.set(key, value)};
    const location = {pathname: '/build', search: '', assign: url => redirects.push(url)};
    const access = new AdoptionAccess({storage, location, notify: value => notices.push(value),
        fetcher: async () => ({ok: true, json: async () => ({adopted, adoption_url: '/pets/view_pets?next=%2Fbuild'})})});
    return {access, saved, notices, redirects, storage, location};
}

test('missing adoption saves current work before redirect and valid adoption never redirects', async () => {
    const f = fixture();
    const draft = {recipe: ['Selected axolotl'], prompt: 'Edited instructions', story: 'Keep this story'};
    f.access.register('build', {snapshot: () => draft, restore() {}});
    assert.equal(await f.access.ensure(), false);
    assert.deepEqual(JSON.parse(f.saved.get(f.access.key())), draft);
    assert.deepEqual(f.redirects, ['/pets/view_pets?next=%2Fbuild']);
    const valid = fixture(true);
    assert.equal(await valid.access.ensure(), true);
    assert.equal(valid.redirects.length, 0);
    assert.equal(valid.saved.size, 0); // No alternate adoption state is stored.
});

test('storage and status failures keep work in place and do not redirect', async () => {
    const f = fixture();
    f.access.register('create', {snapshot: () => ({source: 'Do not lose me'}), restore() {}});
    f.storage.setItem = () => { throw new Error('quota'); };
    assert.equal(await f.access.ensure(), false);
    assert.equal(f.redirects.length, 0);
    assert.match(f.notices[0], /Stay on this page/);
    f.access.fetcher = async () => { throw new Error('offline'); };
    assert.equal(await f.access.ensure(), false);
    assert.equal(f.redirects.length, 0);
});

test('draft restoration is per mode and unsafe redirect URLs are ignored', () => {
    const f = fixture();
    let restored;
    f.access.register('create', {snapshot: () => ({source: 'Original source'}), restore: value => restored = value});
    f.access.save();
    f.access.register('build', {snapshot: () => ({recipe: ['Kept goat']}), restore: value => restored = value});
    assert.equal(f.access.restore(), false);
    f.access.save();
    assert.equal(f.access.restore(), true);
    assert.deepEqual(restored, {recipe: ['Kept goat']});
    assert.equal(f.access.redirect('//evil.test'), false);
    f.access.register('create', {snapshot() {}, restore: value => restored = value});
    f.access.restore();
    assert.deepEqual(restored, {source: 'Original source'});
});

test('browser back/forward pageshow rechecks adoption, including Gallery without an editor', async () => {
    const f = fixture();
    const events = {};
    const window = {...f, sessionStorage: f.storage, fetch: f.access.fetcher,
        addEventListener: (name, handler) => events[name] = handler,
        document: {addEventListener() {}, getElementById() {return {prepend() {}};}, createElement() {return {setAttribute() {}};}}};
    vm.runInNewContext(fs.readFileSync('newsmuncher/static/js/shared/adoption-access.js', 'utf8'), {window});
    window.location.pathname = '/promotion-gallery/';
    events.pageshow({persisted: true});
    await tick();
    assert.equal(f.redirects.length, 1);
});

async function loadBuild(access) {
    global.adoptionAccess = access;
    const nodes = new Map();
    const element = {dataset: {stuffUrl: 'stuff', swearUrl: 'swear', modifierUrl: 'modifier', personUrl: 'person'},
        querySelector: selector => {
            if (!nodes.has(selector)) nodes.set(selector, {value: '', style: {}, scrollHeight: 20,
                addEventListener() {}, classList: {contains: () => false}});
            return nodes.get(selector);
        }, querySelectorAll: () => [], addEventListener() {}};
    const csv = {
        stuff: 'category,word\nadjective,absurd\nobject,axolotl\ndevice,toaster\nsurreal_descriptor,haunted',
        swear: 'category,word\nbijv_nw,bloody\ngilles,old\nzelfs_nw,goat\nhandelend,licker',
        modifier: 'category,word\nadjective,criminally flamboyant', person: 'category,word\nperson,The bishop'
    };
    const instance = new build.BuildWorkshop(element, {fetcher: async url => ({ok: true, text: async () => csv[url]})});
    await instance.load();
    return instance;
}

test('BUILD restores real slots, USE recipe, editable prompt and story after adoption', async () => {
    const f = fixture();
    try {
        const before = await loadBuild(f.access);
        before.useSlot('stuff', before.slots.stuff[0].id);
        before.element.querySelector('[data-prompt-editor]').value = 'My hand-edited prompt';
        before.promptDirty = true;
        before.element.querySelector('[data-build-story]').value = 'My generated and edited story';
        before.generatedHeadline = 'Saved headline';
        before.promptTarget = 90;
        const recipe = JSON.parse(JSON.stringify(before.recipe));
        const ids = before.slots.stuff.map(slot => slot.id);
        assert.equal(await f.access.ensure(), false);
        const after = await loadBuild(f.access);
        assert.deepEqual(after.recipe, recipe);
        assert.deepEqual(after.slots.stuff.map(slot => slot.id), ids);
        assert.equal(after.currentPrompt(), 'My hand-edited prompt');
        assert.equal(after.element.querySelector('[data-build-story]').value, 'My generated and edited story');
        assert.equal(after.generatedHeadline, 'Saved headline');
        assert.equal(after.promptTarget, 90);
        await after.generateStory(30); // Missing adoption: no generation or prompt mutation.
        assert.equal(after.currentPrompt(), 'My hand-edited prompt');
        assert.equal(after.promptTarget, 90);
    } finally { delete global.adoptionAccess; }
});

function createContext(ensure) {
    const nodes = new Map();
    const get = id => {
        if (!nodes.has(id)) nodes.set(id, {value: id.includes('source') ? 'Kept source' : 'Kept result',
            disabled: false, hidden: false, classList: {remove() {}, add() {}}});
        return nodes.get(id);
    };
    let resets = 0, requests = 0, body;
    const context = {window: {adoptionAccess: {ensure}, performance: {now: () => 0}},
        document: {getElementById: get}, mungeProcessing: false, rewriteSequence: 0,
        resetImagePanel: () => resets++, showLoader() {}, hideLoader() {}, workingSession: () => 'session',
        fetch: async (_url, options) => { requests++; body = JSON.parse(options.body); return {ok: false, status: 401, json: async () => ({detail: 'No pet'})}; },
        console: {error() {}}};
    const source = fs.readFileSync('newsmuncher/static/js/creation/script.js', 'utf8');
    vm.createContext(context);
    vm.runInContext(source.slice(source.indexOf('let adoptionCheckPending'), source.indexOf('let nominationPending')), context);
    return {context, get, resets: () => resets, requests: () => requests, body: () => body};
}

test('CREATE missing adoption stops before loaders, resets or provider requests', async () => {
    const f = createContext(async () => false);
    await f.context.confirmData();
    assert.equal(f.resets(), 0);
    assert.equal(f.requests(), 0);
    assert.equal(f.get('sourceBodyDraft').value, 'Kept source');
    assert.equal(f.get('responseBodyDraft').value, 'Kept result');
});

test('failed CREATE MUNGE retains source, result, image and nomination control state', async () => {
    const f = createContext(async () => true);
    await f.context.confirmData(); await tick();
    assert.equal(f.requests(), 1);
    assert.equal(f.resets(), 0);
    assert.equal(f.get('sourceBodyDraft').value, 'Kept source');
    assert.equal(f.get('responseBodyDraft').value, 'Kept result');
    assert.equal(f.get('bankButton').disabled, false);
    assert.equal(f.get('mungeMessage').textContent, 'No pet');
});

test('CREATE restores source metadata, manual source edits and generated response before hydration', () => {
    const f = fixture();
    const values = {sourceTitleDraft: 'Edited source title', sourceBodyDraft: 'Edited source body',
        sourceUrlDraft: 'https://example.test/original', sourceNameDraft: 'Original source',
        sourceAuthorDraft: 'Original author', sourceLicenceDraft: 'CC BY',
        responseTitleDraft: 'Kept headline', responseBodyDraft: 'Kept edited result', rewriteId: null};
    f.storage.setItem('newsmuncher.work.v1.create', JSON.stringify(values));
    const nodes = new Map();
    const get = id => {
        if (!nodes.has(id)) nodes.set(id, {value: '', style: {}});
        return nodes.get(id);
    };
    const context = {window: {adoptionAccess: f.access, location: {search: ''}},
        document: {getElementById: get}, displayedRewriteId: null, URLSearchParams,
        autoResize() {}, updateCopyButton() {},
        populateTempData: () => { throw new Error('Must not overwrite restored source'); },
        restoreImageRewrite: () => { throw new Error('No rewrite to restore'); }};
    vm.createContext(context);
    const source = fs.readFileSync('newsmuncher/static/js/creation/script.js', 'utf8');
    vm.runInContext(source.slice(source.indexOf('window.onload =')), context);
    context.window.onload();
    for (const [id, value] of Object.entries(values)) {
        if (id !== 'rewriteId') assert.equal(get(id).value, value);
    }
    assert.equal(get('outputContainer').style.display, 'block');
});

test('CREATE retains the selected MUNGE engine after asynchronous adoption validation', async () => {
    let release;
    const f = createContext(() => new Promise(resolve => release = resolve));
    const event = {currentTarget: {dataset: {mungeEngine: 'radical'}}};
    const pending = f.context.confirmData(event);
    event.currentTarget = null; // Browsers clear currentTarget after event dispatch.
    release(true);
    await pending; await tick();
    assert.equal(f.body().engine, 'radical');
});

test('BUILD automatic prompts still update when USE adds ingredients after restoring a draft', async () => {
    const f = fixture();
    try {
        const before = await loadBuild(f.access);
        before.useSlot('stuff', before.slots.stuff[0].id);
        f.access.save();
        const after = await loadBuild(f.access);
        assert.equal(after.promptDirty, false);
        after.useSlot('person', after.slots.person[0].id);
        assert.ok(after.currentPrompt().includes('People: The bishop'));
    } finally { delete global.adoptionAccess; }
});
