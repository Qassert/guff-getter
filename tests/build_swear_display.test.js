const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const build = require('../newsmuncher/static/build-page.js');
const vocabulary = build.parseCSV(fs.readFileSync('newsmuncher/static/data/build-swear.csv', 'utf8'));

function workshop() {
  let seed = 318;
  const nodes = new Map();
  const element = {
    querySelector(selector) {
      if (selector.startsWith('[data-slot-category=')) return null;
      if (!nodes.has(selector)) nodes.set(selector, {
        value: '', style: {}, scrollHeight: 100, classList: {contains: () => false}
      });
      return nodes.get(selector);
    },
    querySelectorAll: () => []
  };
  const instance = new build.BuildWorkshop(element, {
    random: () => {
      seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0;
      return seed / 4294967296;
    },
    reducedMotion: () => true
  });
  instance.vocabularies = {swear: vocabulary};
  return instance;
}

test('label suppression is scoped exclusively to SWEAR component labels', () => {
  const css = fs.readFileSync('newsmuncher/static/build-page.css', 'utf8');
  assert.match(css, /\.ingredient-group\[data-category="swear"\] \.ingredient-word small\s*\{\s*display:\s*none;\s*\}/);
  assert.match(css, /\.ingredient-word small\s*\{[^}]*text-transform: uppercase;/);
  const template = fs.readFileSync('newsmuncher/templates/build.html', 'utf8');
  assert.match(template, /class="ingredient-group" data-category="swear"/);
  assert.match(template, /data-add-slot="swear"/);
  const instance = workshop();
  for (const [category, partCategory] of [['stuff', 'object'], ['modifier', 'adjective'], ['person', 'person']]) {
    const html = instance.slotMarkup({id: 1, category, parts: [{category: partCategory, word: 'Example'}]});
    assert.ok(html.includes(`<small>${partCategory}</small>`));
    assert.ok(!html.includes('data-category="swear"'));
  }
});

test('all six insult structures preserve metadata and render every component and action', () => {
  assert.deepEqual(Object.keys(vocabulary).sort(), ['bijv_nw', 'gilles', 'handelend', 'zelfs_nw']);
  const instance = workshop();
  for (let index = 0; index < build.SWEAR_STRUCTURES.length; index++) {
    instance.random = () => (index + 0.5) / build.SWEAR_STRUCTURES.length;
    const parts = instance.candidate('swear');
    assert.deepEqual(parts.map(part => part.category), build.SWEAR_STRUCTURES[index]);
    const html = instance.slotMarkup({id: 1, category: 'swear', parts});
    for (const part of parts) {
      assert.ok(vocabulary[part.category].includes(part.word));
      assert.ok(html.includes('<span>'));
      assert.ok(build.phrase(parts).toLowerCase().includes(part.word.toLowerCase()));
    }
    assert.equal((html.match(/class="ingredient-word"/g) || []).length, parts.length);
    assert.match(html, />SPIN<\/button>/);
    assert.match(html, />USE<\/button>/);
    assert.match(html, /data-remove-slot="1"/);
  }
});

test('SWEAR SPIN, word spin, USE, remove and + SLOT keep working with hidden labels', async () => {
  const instance = workshop();
  const slot = instance.addSlot('swear');
  const second = instance.addSlot('swear');
  assert.equal(instance.slots.swear.length, 2);
  for (let index = 0; index < 12; index++) {
    await instance.randomiseSlot('swear', slot.id);
    assert.equal(slot.busy, false);
    assert.ok(build.SWEAR_STRUCTURES.some(structure => JSON.stringify(structure) === JSON.stringify(slot.parts.map(part => part.category))));
    const previous = slot.parts[0].word;
    await instance.randomisePart('swear', slot.id, 0);
    assert.notEqual(slot.parts[0].word, previous);
    for (const part of slot.parts) assert.ok(vocabulary[part.category].includes(part.word));
  }
  instance.useSlot('swear', slot.id);
  const selected = instance.recipe.swear[0];
  assert.equal(selected.text, build.phrase(slot.parts));
  assert.ok(instance.currentPrompt().includes(selected.text));
  assert.equal(selected.grammar, undefined);
  instance.removeRecipe('swear', selected.id);
  assert.equal(instance.recipe.swear.length, 0);
  instance.removeSlot('swear', second.id);
  instance.removeSlot('swear', slot.id);
  assert.equal(instance.slots.swear.length, 1);
  instance.addSlot('swear');
  assert.equal(instance.slots.swear.length, 2);
});

test('selected insults reach editable prompts and mocked MUNGE 30/60/90 requests', async () => {
  const instance = workshop();
  const slot = instance.addSlot('swear');
  instance.useSlot('swear', slot.id);
  const selected = instance.recipe.swear[0].text;
  assert.ok(instance.currentPrompt().includes(`Swear words: ${selected}`));
  for (const target of [30, 60, 90]) {
    let sent;
    const prompt = build.applyStoryLength(instance.currentPrompt(), target);
    await build.requestBuildStory(async (_url, options) => {
      sent = JSON.parse(options.body);
      return {ok: true, json: async () => ({story: 'The bishop regretted his outburst.'})};
    }, '/build/generate', instance.recipe, target, prompt);
    assert.equal(sent.target_words, target);
    assert.equal(sent.recipe.swear[0].text, selected);
    assert.ok(sent.prompt.includes(selected));
    assert.match(sent.prompt, new RegExp(`Aim for approximately ${target} words`));
  }
});
