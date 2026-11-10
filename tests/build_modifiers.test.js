const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const build = require('../newsmuncher/static/build-page.js');
const vocabulary = build.parseCSV(fs.readFileSync('newsmuncher/static/data/build-modifiers.csv', 'utf8'));
const preserved = ["magnificently ridiculous", "deeply inappropriate", "alarmingly moist", "politically radioactive", "structurally embarrassed", "ceremonially damp", "medically inadvisable", "aggressively beige", "socially feral", "professionally haunted", "administratively impossible", "needlessly baroque", "emotionally laminated", "unexpectedly sentient", "legally questionable", "heroically underqualified", "chronically overdecorated", "terminally pompous", "deeply suspicious", "alarmingly sincere", "unreasonably buoyant", "catastrophically polite", "strategically naked", "geometrically unstable", "spiritually congested", "meticulously grubby", "violently ornamental", "permanently bewildered", "royally inconvenient", "ethically inflatable", "mechanically jealous", "romantically bankrupt", "biologically optimistic", "deliberately wonky", "financially translucent", "furiously upholstered", "ominously municipal", "impossibly fragrant", "hauntingly practical"];

function workshop() {
  let seed = 20261108;
  const random = () => {
    seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0;
    return seed / 4294967296;
  };
  const nodes = new Map();
  const element = {
    querySelector(selector) {
      // No mounted slot DOM: exercise the controller's full-render fallback.
      if (selector.startsWith('[data-slot-category=')) return null;
      if (!nodes.has(selector)) nodes.set(selector, {
        value: '', style: {}, scrollHeight: 100,
        classList: {contains: () => false}
      });
      return nodes.get(selector);
    },
    querySelectorAll: () => []
  };
  const instance = new build.BuildWorkshop(element, {random, reducedMotion: () => true});
  instance.vocabularies = {modifier: vocabulary};
  return instance;
}

function checkPart(part) {
  assert.equal(part.word.trim().split(/\s+/).length, 2);
  assert.ok(['adverb', 'adjective'].includes(part.category));
  assert.ok(vocabulary[part.category].includes(part.word));
}

test('every selectable modifier is a unique complete two-word phrase with the existing labels', () => {
  assert.deepEqual(Object.keys(vocabulary), ['adverb', 'adjective']);
  assert.equal(vocabulary.adverb.length, 40);
  assert.equal(vocabulary.adjective.length, 80);
  const all = Object.values(vocabulary).flat();
  assert.equal(new Set(all).size, 120);
  for (const [category, words] of Object.entries(vocabulary)) {
    for (const word of words) checkPart({category, word});
  }
  for (const phrase of preserved) assert.ok(vocabulary.adjective.includes(phrase), phrase);
  assert.ok(vocabulary.adjective.includes('liturgically unhinged'));
  assert.ok(!all.includes('unhinged'));
  assert.ok(!all.includes('suspiciously'));
});

test('adverb labels cover complete adverbial phrases rather than adjective phrases', () => {
  // Editorial grammar guard: prepositional adjuncts or whole adverb phrases.
  const prepositions = new Set(['without', 'under', 'through', 'with', 'beyond',
    'against', 'amid', 'despite', 'aboard', 'between', 'beneath', 'after',
    'before', 'during', 'via', 'inside', 'outside', 'past']);
  for (const phrase of vocabulary.adverb) {
    const [first, second] = phrase.split(' ');
    assert.ok(prepositions.has(first) ||
      ['ceremonially', 'loudly', 'tenderly', 'sideways', 'downstairs', 'reluctantly'].includes(second), phrase);
  }
  for (const phrase of vocabulary.adjective) {
    assert.match(phrase.split(' ')[0], /ly$/, phrase);
  }
});

test('random selection keeps each complete phrase atomic and every entry reachable', () => {
  const instance = workshop();
  const seen = new Set();
  for (let i = 0; i < 3000; i++) {
    const parts = instance.candidate('modifier');
    assert.equal(parts.length, 1);
    checkPart(parts[0]);
    seen.add(parts[0].word);
  }
  assert.equal(seen.size, 120);
  for (const [categoryIndex, category] of Object.keys(vocabulary).entries()) {
    for (const [index, word] of vocabulary[category].entries()) {
      const draws = [(categoryIndex + 0.5) / 2, (index + 0.5) / vocabulary[category].length];
      instance.random = () => draws.shift();
      assert.deepEqual(instance.candidate('modifier'), [{category, word}]);
    }
  }
});

test('SPIN, individual phrase spin, USE, remove and + SLOT preserve two-word modifiers', async () => {
  const instance = workshop();
  const first = instance.addSlot('modifier');
  const second = instance.addSlot('modifier');
  assert.equal(instance.slots.modifier.length, 2);
  for (let i = 0; i < 20; i++) {
    await instance.randomiseSlot('modifier', first.id);
    assert.equal(first.busy, false);
    assert.equal(first.parts.length, 1);
    checkPart(first.parts[0]);
    const previous = first.parts[0].word;
    await instance.randomisePart('modifier', first.id, 0);
    checkPart(first.parts[0]);
    assert.notEqual(first.parts[0].word, previous);
  }
  const html = instance.slotMarkup(first);
  assert.ok(html.includes(`<small>${first.parts[0].category}</small>`));
  assert.match(html, />SPIN<|>SPIN<\/button>/);
  assert.match(html, />USE<\/button>/);
  instance.useSlot('modifier', first.id);
  const selected = instance.recipe.modifier[0];
  assert.equal(selected.text, build.phrase(first.parts));
  assert.equal(selected.grammar, first.parts[0].category);
  assert.ok(instance.currentPrompt().includes(selected.text));
  instance.removeRecipe('modifier', selected.id);
  assert.equal(instance.recipe.modifier.length, 0);
  instance.removeSlot('modifier', second.id);
  assert.equal(instance.slots.modifier.length, 1);
  instance.removeSlot('modifier', first.id);
  assert.equal(instance.slots.modifier.length, 1);
  instance.addSlot('modifier');
  assert.equal(instance.slots.modifier.length, 2);
});

test('both grammatical types reach editable prompt and mocked MUNGE 30/60/90 unchanged', async () => {
  const instance = workshop();
  for (const category of ['adverb', 'adjective']) {
    const slot = instance.addSlot('modifier');
    slot.parts = [{category, word: vocabulary[category][0]}];
    instance.useSlot('modifier', slot.id);
  }
  for (const target of [30, 60, 90]) {
    const prompt = build.applyStoryLength(instance.currentPrompt(), target);
    let sent;
    await build.requestBuildStory(async (_url, options) => {
      sent = JSON.parse(options.body);
      return {ok: true, json: async () => ({story: 'The bishop had other ideas.'})};
    }, '/build/generate', instance.recipe, target, prompt);
    assert.equal(sent.target_words, target);
    assert.deepEqual(sent.recipe.modifier, instance.recipe.modifier.map(({text, grammar}) => ({text, grammar})));
    for (const selected of instance.recipe.modifier) assert.ok(sent.prompt.includes(selected.text));
    assert.match(sent.prompt, new RegExp(`Aim for approximately ${target} words`));
  }
});
