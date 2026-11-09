const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const build = require('../newsmuncher/static/build-page.js');

function workshop() {
  let seed = 41;
  const nodes = new Map();
  const element = {
    querySelector(selector) {
      if (!nodes.has(selector)) nodes.set(selector, {
        value: '', style: {}, scrollHeight: 100, disabled: false,
        addEventListener() {}, classList: {contains: () => false}
      });
      return nodes.get(selector);
    },
    addEventListener(type, handler) { this[type] = handler; },
    querySelectorAll: () => []
  };
  const instance = new build.BuildWorkshop(element, {
    reducedMotion: () => true,
    random: () => {
      seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0;
      return seed / 4294967296;
    },
    fetcher: () => { throw new Error('SPIN ALL must not make network requests'); }
  });
  for (const [category, file] of Object.entries({stuff: 'stuff', swear: 'swear', modifier: 'modifiers', person: 'people'})) {
    instance.vocabularies[category] = build.parseCSV(fs.readFileSync(`newsmuncher/static/data/build-${file}.csv`, 'utf8'));
  }
  // Replace only DOM painting; use real selection, flick, history and slot logic.
  instance.renderSlot = slot => { instance.slotMarkup(slot); };
  for (const [category, count] of Object.entries(build.INITIAL_COUNTS)) {
    for (let i = 0; i < count; i++) instance.addSlot(category, false);
  }
  return instance;
}

test('SPIN ALL sits immediately before Stuff + SLOT and uses existing mini-action styling', () => {
  const template = fs.readFileSync('newsmuncher/templates/build.html', 'utf8');
  const stuff = template.split('data-category="stuff"')[1].split('</section>')[0];
  assert.match(stuff, /class="ingredient-heading-actions"><button type="button" class="mini-action" data-spin-all[^>]*>SPIN ALL<\/button><button type="button" class="mini-action" data-add-slot="stuff">\+ SLOT<\/button>/);
  assert.equal((template.match(/data-spin-all/g) || []).length, 1);
  const css = fs.readFileSync('newsmuncher/static/build-page.css', 'utf8');
  assert.match(css, /\.ingredient-heading-actions\s*\{[^}]*flex-wrap: wrap/);
});

test('SPIN ALL refreshes all categories and preserves slot IDs, recipe, prompt and story state', async () => {
  const instance = workshop();
  instance.addSlot('person', false); // Respect user-added rows too.
  instance.slots.modifier.pop(); // Respect removed rows too.
  for (const category of Object.keys(instance.recipe)) {
    instance.recipe[category].push(Object.freeze({id: `saved-${category}`, text: `Kept ${category}`}));
    Object.freeze(instance.recipe[category]);
  }
  Object.freeze(instance.recipe);
  const recipe = instance.recipe;
  const snapshot = JSON.stringify(recipe);
  instance.promptDirty = true;
  instance.promptTarget = 90;
  instance.generatedHeadline = 'Saved headline';
  instance.headlineStory = 'Saved story';
  instance.element.querySelector('[data-prompt-editor]').value = 'My edited prompt';
  instance.element.querySelector('[data-build-story]').value = 'My edited story';
  instance.element.querySelector('[data-build-result]').hidden = false;
  const before = Object.fromEntries(Object.entries(instance.slots).map(([category, slots]) =>
    [category, slots.map(slot => ({id: slot.id, text: build.phrase(slot.parts)}))]));
  const pending = instance.spinAll();
  assert.equal(instance.element.querySelector('[data-spin-all]').disabled, true);
  await pending;
  assert.equal(instance.element.querySelector('[data-spin-all]').disabled, false);
  for (const [category, slots] of Object.entries(instance.slots)) {
    assert.deepEqual(slots.map(slot => slot.id), before[category].map(slot => slot.id));
    for (const [index, slot] of slots.entries()) {
      assert.notEqual(build.phrase(slot.parts), before[category][index].text);
      assert.equal(slot.busy, false);
      for (const part of slot.parts) assert.ok(instance.bank(category, part.category).includes(part.word));
    }
  }
  assert.equal(instance.recipe, recipe);
  assert.equal(JSON.stringify(recipe), snapshot);
  assert.equal(instance.currentPrompt(), 'My edited prompt');
  assert.equal(instance.element.querySelector('[data-build-story]').value, 'My edited story');
  assert.equal(instance.element.querySelector('[data-build-result]').hidden, false);
  assert.equal(instance.promptDirty, true);
  assert.equal(instance.promptTarget, 90);
  assert.equal(instance.generatedHeadline, 'Saved headline');
  assert.equal(instance.headlineStory, 'Saved story');
});

test('SPIN ALL dispatches every row concurrently through individual SPIN and ignores repeated clicks', async () => {
  const instance = workshop();
  const calls = [], releases = [];
  instance.randomiseSlot = (category, id, avoidRepeat) => {
    calls.push([category, id, avoidRepeat]);
    return new Promise(resolve => releases.push(resolve));
  };
  const pending = instance.spinAll();
  const expected = Object.entries(instance.slots).flatMap(([category, slots]) => slots.map(slot => [category, slot.id, true]));
  assert.deepEqual(calls, expected);
  await instance.spinAll();
  assert.deepEqual(calls, expected);
  releases.forEach(resolve => resolve());
  await pending;
  assert.equal(instance.spinningAll, false);
});

test('repeat avoidance retries existing selection but terminates for a one-combination pool', async () => {
  const instance = workshop();
  const slot = instance.slots.person[0];
  const original = structuredClone(slot.parts);
  const alternative = [{category: 'person', word: 'An alternative person'}];
  let count = 0;
  instance.candidate = () => ++count === 1 ? original : alternative;
  await instance.randomiseSlot('person', slot.id, true);
  assert.equal(count, 2);
  assert.deepEqual(slot.parts, alternative);
  count = 0;
  instance.candidate = () => { count++; return alternative; };
  await instance.randomiseSlot('person', slot.id, true);
  assert.equal(count, 6);
  assert.equal(slot.busy, false);
  count = 0;
  await instance.randomiseSlot('person', slot.id); // Existing individual SPIN unchanged.
  assert.equal(count, 1);
});

test('SPIN ALL honours existing busy-row protection and restores its button after failures', async () => {
  const instance = workshop();
  const slot = instance.slots.person[0];
  slot.busy = true;
  const before = structuredClone(slot);
  await instance.spinAll();
  assert.deepEqual(slot, before);
  instance.randomiseSlot = async () => { throw new Error('Test failure'); };
  await assert.rejects(instance.spinAll(), /Test failure/);
  assert.equal(instance.element.querySelector('[data-spin-all]').disabled, false);
  assert.equal(instance.spinningAll, false);
});

test('delegated SPIN ALL click reaches the controller', async () => {
  const instance = workshop();
  let called = 0;
  instance.spinAll = async () => { called++; };
  instance.bind();
  await instance.element.click({target: {closest: selector => selector === '[data-spin-all]' ? {} : null}});
  assert.equal(called, 1);
});
