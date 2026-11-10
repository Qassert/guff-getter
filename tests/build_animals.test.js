const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const crypto = require('node:crypto');
const build = require('../newsmuncher/static/build-page.js');
const bytes = fs.readFileSync('newsmuncher/static/data/build-stuff.csv');
const originalBytes = 51767;
const original = bytes.subarray(0, originalBytes);
const additions = build.parseCSV('category,word\n' + bytes.subarray(originalBytes).toString());
const animals = new Set(additions.object);
const vocabulary = build.parseCSV(bytes.toString());

function workshop(random) {
  const nodes = new Map();
  const element = {
    querySelector(selector) {
      if (!nodes.has(selector)) nodes.set(selector, {
        value: '', style: {}, scrollHeight: 100,
        classList: {contains: () => false}
      });
      return nodes.get(selector);
    },
    querySelectorAll: () => []
  };
  const result = new build.BuildWorkshop(element, {random});
  result.vocabularies = {stuff: vocabulary};
  return result;
}

function seededRandom(seed) {
  return () => {
    seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0;
    return seed / 4294967296;
  };
}

test('animal expansion preserves every original CSV byte and all existing pools', () => {
  assert.equal(crypto.createHash('sha256').update(original).digest('hex'), '45f4e688d33ee1199e6e0c920a69a4dad3586946d518f89d5c55aeaa2c08d259');
  assert.deepEqual(Object.keys(additions), ['object']);
  assert.equal(animals.size, 683);
  assert.equal(vocabulary.object.length, 1442 + animals.size);
  for (const name of ['axolotl', 'naked mole-rat', 'shoebill stork', 'blobfish',
    'aye-aye', 'pangolin', 'wombat', 'mantis shrimp', 'secretary bird',
    'proboscis monkey', 'tasmanian devil', 'giant isopod', 'capybara',
    'star-nosed mole', 'saiga antelope', 'cow', 'pigeon', 'badger', 'ferret',
    'goat', 'chicken', 'donkey', 'seagull']) assert.ok(animals.has(name), name);
  assert.ok(!animals.has('dragon'));
  const before = build.parseCSV(original.toString());
  for (const category of Object.keys(before)) {
    for (const word of before[category]) assert.ok(vocabulary[category].includes(word));
  }
});

test('existing weighted random selection produces animals in 20–25% of Stuff phrases', () => {
  const objectWeight = build.STUFF_STRUCTURES.reduce((sum, parts, index) =>
    sum + (parts.includes('object') ? build.STUFF_WEIGHTS[index] : 0), 0);
  const totalWeight = build.STUFF_WEIGHTS.reduce((sum, value) => sum + value, 0);
  const expected = objectWeight / totalWeight * animals.size / vocabulary.object.length;
  assert.ok(expected >= 0.20 && expected <= 0.25, expected);
  const instance = workshop(seededRandom(20261108));
  let animalPhrases = 0, objectPhrases = 0;
  for (let i = 0; i < 30000; i++) {
    const parts = instance.candidate('stuff');
    if (parts.some(part => animals.has(part.word))) animalPhrases++;
    if (parts.some(part => part.category === 'object' && !animals.has(part.word))) objectPhrases++;
    assert.ok(parts.every(part => vocabulary[part.category].includes(part.word)));
  }
  const observed = animalPhrases / 30000;
  assert.ok(observed >= 0.20 && observed <= 0.25, observed);
  assert.ok(Math.abs(observed - expected) < 0.01, observed);
  assert.ok(objectPhrases > animalPhrases);
});

test('every animal is reachable through the unchanged object word picker', () => {
  const instance = workshop(() => 0);
  for (const animal of animals) {
    const index = vocabulary.object.indexOf(animal);
    const draws = [0, 0, (index + 0.5) / vocabulary.object.length];
    instance.random = () => draws.shift();
    assert.equal(instance.candidate('stuff')[1].word, animal);
  }
});

test('animal USE selection reaches editable prompt and mocked MUNGE 30/60/90 requests', async () => {
  const instance = workshop(seededRandom(7));
  const parts = [{category: 'adjective', word: vocabulary.adjective[0]},
    {category: 'object', word: 'axolotl'}];
  instance.slots.stuff.push({id: 1, category: 'stuff', parts, busy: false});
  instance.useSlot('stuff', 1);
  assert.equal(instance.recipe.stuff[0].text, build.phrase(parts));
  assert.match(instance.currentPrompt(), /Objects: .*axolotl/);
  const editor = instance.element.querySelector('[data-prompt-editor]');
  editor.value += '\nKeep my hand-edited animal instruction.';
  for (const target of [30, 60, 90]) {
    const prompt = build.applyStoryLength(instance.currentPrompt(), target);
    let sent;
    const generated = await build.requestBuildStory(async (_url, options) => {
      sent = JSON.parse(options.body);
      return {ok: true, json: async () => ({story: 'The axolotl confiscated the moon.'})};
    }, '/build/generate', instance.recipe, target, prompt);
    assert.equal(sent.target_words, target);
    assert.match(sent.prompt, /axolotl/);
    assert.match(sent.prompt, /Keep my hand-edited animal instruction/);
    assert.match(sent.prompt, new RegExp(`Aim for approximately ${target} words`));
    assert.equal(sent.recipe.stuff[0].text, build.phrase(parts));
    assert.equal(generated.story || generated, 'The axolotl confiscated the moon.');
  }
});
