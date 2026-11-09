const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const objectApi = require('../../newsmuncher/static/js/creation/object-generator.js');
const swearApi = require('../../newsmuncher/static/js/creation/swear-generator.js');

const csv = fs.readFileSync('newsmuncher/static/data/object-generator-vocabulary.csv', 'utf8');

test('OBJECT has its own categories, source and four grammatical structures', () => {
    const vocabulary = objectApi.parseCSV(csv);
    assert.deepEqual(objectApi.CATEGORIES, ['adjective', 'surreal_descriptor', 'object', 'device']);
    assert.deepEqual(objectApi.CATEGORIES.map(key => vocabulary[key].length), [73, 97, 1442, 857]);
    assert.deepEqual(objectApi.STRUCTURES, [
        ['adjective', 'object'], ['adjective', 'device'],
        ['object', 'device'], ['adjective', 'object', 'device'],
        ['adjective', 'surreal_descriptor', 'object'],
        ['adjective', 'surreal_descriptor', 'device'],
        ['adjective', 'surreal_descriptor', 'object', 'device'],
        ['surreal_descriptor', 'adjective', 'object', 'device']
    ]);
    assert(vocabulary.object.includes('cheese grater'));
    assert(vocabulary.device.includes('washing machine'));
    assert(!csv.includes('bijv_nw') && !csv.includes('handelend'));
});

test('seeded weighted selection produces approximately 70% two-descriptor names', () => {
    const vocabulary = objectApi.parseCSV(csv);
    let state = 0x51f15e;
    const random = () => ((state = (1664525 * state + 1013904223) >>> 0) / 0x100000000);
    const generator = new objectApi.ObjectGenerator(vocabulary, {random});
    let long = 0;
    const sampleSize = 10000;
    for (let index = 0; index < sampleSize; index++) {
        const slots = generator.candidate();
        if (slots.some(slot => slot.category === 'surreal_descriptor')) long++;
    }
    const ratio = long / sampleSize;
    assert(ratio > .68 && ratio < .72, `expected about 70%, received ${ratio}`);
});

test('every OBJECT structure is selectable and multi-word entries remain one slot', () => {
    const vocabulary = objectApi.parseCSV(csv);
    const generator = new objectApi.ObjectGenerator(vocabulary, {random: () => 0});
    for (const structure of objectApi.STRUCTURES)
        assert.deepEqual(generator.candidate(structure).map(slot => slot.category), structure);
    assert(vocabulary.object.some(value => value.includes(' ')));
});

test('OBJECT reuses five-flick 100ms overlap and supports isolated slot replacement', async () => {
    const vocabulary = {adjective:['odd','rusty'], surreal_descriptor:['bipolar','chemical'],
        object:['bucket','tea tray'], device:['toaster','camera']};
    const queue = [], events = [];
    const generator = new objectApi.ObjectGenerator(vocabulary, {
        random: () => 0,
        schedule(fn, delay) { queue.push({fn, delay}); return fn; },
        cancel() {}, reducedMotion: () => false,
        display(event) { events.push({index:event.index, final:event.final}); }
    });
    const pending = generator.generate();
    while (queue.length) { const task = queue.shift(); assert.equal(task.delay, 100); task.fn(); }
    await pending;
    assert.equal(events.filter(event => event.index === 0).length, 5);
    assert(events.findIndex(event => event.index === 1) <
        events.findIndex(event => event.index === 0 && event.final));
    const before = generator.slots.map(slot => slot.word);
    generator.reducedMotion = () => true; generator.random = () => .99;
    await generator.replacement(0);
    assert.notEqual(generator.slots[0].word, before[0]);
    assert.deepEqual(generator.slots.slice(1).map(slot => slot.word), before.slice(1));
});

test('surreal descriptor is independently replaceable and COPY phrase contains every slot', async () => {
    const generator = new objectApi.ObjectGenerator({
        adjective:['transparent'], surreal_descriptor:['anxious','chemical'],
        object:['wrench'], device:['projector']
    }, {random:()=>.99, reducedMotion:()=>true});
    generator.slots = [
        {category:'adjective',word:'transparent'},
        {category:'surreal_descriptor',word:'anxious'},
        {category:'object',word:'wrench'},
        {category:'device',word:'projector'}
    ];
    await generator.replacement(1);
    assert.equal(generator.phrase(), 'Transparent chemical wrench projector');
    assert.equal(generator.slots[1].category, 'surreal_descriptor');
});

test('OBJECT bounded duplicate tracking and rapid cancellation remain independent of SWEAR', async () => {
    const objectVocabulary = {adjective:['a'], object:['b'], device:['c']};
    const object = new objectApi.ObjectGenerator(objectVocabulary, {random:()=>0, reducedMotion:()=>true});
    const phrases=[];
    for (let index=0; index<4; index++) phrases.push(await object.generate());
    assert.equal(new Set(phrases).size, 4);
    assert(await object.generate());

    const swearVocabulary = Object.fromEntries(swearApi.CATEGORIES.map(key => [key,['x','y']]));
    const swear = new swearApi.SwearGenerator(swearVocabulary, {random:()=>0, reducedMotion:()=>true});
    await swear.generate();
    assert.equal(object.used.has(swear.key(swear.slots)), false);

    const queue=[];
    const rapid = new objectApi.ObjectGenerator({adjective:['a','b'],object:['c'],device:['d']}, {
        random:()=>0, reducedMotion:()=>false,
        schedule(fn){queue.push(fn); return fn;},
        cancel(timer){const index=queue.indexOf(timer); if(index>=0) queue.splice(index,1);}
    });
    const first=rapid.generate();
    const cancelled=assert.rejects(first, error=>error.name==='AbortError');
    const second=rapid.generate();
    while(queue.length) queue.shift()();
    await Promise.all([cancelled, second]);
});

test('Create places OBJECT directly above SWEAR with independent COPY and storage', () => {
    const template=fs.readFileSync('newsmuncher/templates/pet_profile.html','utf8');
    const shared=fs.readFileSync('newsmuncher/static/js/creation/swear-generator.js','utf8');
    const object=fs.readFileSync('newsmuncher/static/js/creation/object-generator.js','utf8');
    const objectIndex=template.indexOf('data-object-generator');
    const swearIndex=template.indexOf('data-swear-generator');
    assert(objectIndex > template.indexOf('id="responseEditor"') && objectIndex < swearIndex);
    assert(swearIndex < template.indexOf('id="imagePanel"'));
    assert.match(template,/data-object-generate>STUFF<\/button>/);
    assert.match(template,/data-object-copy disabled>COPY<\/button>/);
    assert.match(template,/object-generator-vocabulary\.csv/);
    assert.match(object,/newsmuncher\.objectGenerator\.used/);
    assert.match(shared,/newsmuncher\.swearGenerator\.used/);
    assert.doesNotMatch(object,/StatCounter|https?:\/\//i);
});

test('STUFF and SWEAR share body size plus 2pt and equal generate-button widths', () => {
    const sharedStyles=fs.readFileSync('newsmuncher/static/css/shared/styles.css','utf8');
    const generatorStyles=fs.readFileSync('newsmuncher/static/css/creation/swear-generator.css','utf8');
    assert.match(sharedStyles,/--creation-body-font-size:\s*\.9375rem/);
    assert.match(sharedStyles,/#responseBodyDraft\s*\{[^}]*font-size:\s*var\(--creation-body-font-size\)/s);
    assert.match(generatorStyles,/\[data-swear-generate\],[^}]*\[data-object-generate\]\s*\{\s*width:104px;/s);
    const sharedSize=/font:700 calc\(var\(--creation-body-font-size\) \+ 2pt\)\/1\.25 Georgia,serif/g;
    assert.equal([...generatorStyles.matchAll(sharedSize)].length,2);
});

test('OBJECT inherits plain-text clipboard feedback and disabled-state lifecycle', () => {
    const shared=fs.readFileSync('newsmuncher/static/js/creation/swear-generator.js','utf8');
    assert.match(shared,/copyPlainText\(phrase\)/);
    assert.match(shared,/copy\.textContent = 'COPIED'/);
    assert.match(shared,/generate\.disabled = true; copy\.disabled = true/);
});
