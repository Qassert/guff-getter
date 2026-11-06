const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const build = require('../newsmuncher/static/build-page.js');

test('Build parses quoted CSV vocabulary without losing category information', () => {
  const data = build.parseCSV('category,word\nadverb,suspiciously\nadjective,"deeply, gloriously wrong"\n');
  assert.deepEqual(data.adverb, ['suspiciously']);
  assert.deepEqual(data.adjective, ['deeply, gloriously wrong']);
});

test('Stuff keeps established structures and weighted long-form selection', () => {
  assert.equal(build.STUFF_STRUCTURES.length, 8);
  assert.deepEqual(build.STUFF_STRUCTURES[6], ['adjective', 'surreal_descriptor', 'object', 'device']);
  assert.deepEqual(build.weightedStructure(build.STUFF_STRUCTURES, build.STUFF_WEIGHTS, () => 0.99), build.STUFF_STRUCTURES[7]);
  assert.deepEqual(build.weightedStructure(build.STUFF_STRUCTURES, build.STUFF_WEIGHTS, () => 0), build.STUFF_STRUCTURES[0]);
});

test('Swear preserves all six original phrase structures and flick timing', () => {
  assert.equal(build.SWEAR_STRUCTURES.length, 6);
  assert.equal(build.FLICK_COUNT, 5);
  assert.equal(build.FLICK_DELAY, 100);
});

test('Build starts with requested independent selector counts', () => {
  assert.deepEqual(build.INITIAL_COUNTS, {stuff: 3, swear: 2, modifier: 5, person: 1, theme: 1});
});

test('prompt preview groups structured recipe and enforces the 80-word limit', () => {
  const prompt = build.buildPrompt({
    stuff: [{text: 'Transparent bipolar wrench projector'}],
    swear: [{text: 'Right old turnip licker'}],
    modifier: [{text: 'Suspiciously', grammar: 'adverb'}],
    person: [{text: 'Agatha Crumble'}],
    theme: [{text: 'A disastrous royal banquet'}]
  });
  assert.match(prompt, /Objects: Transparent bipolar wrench projector/);
  assert.match(prompt, /People: Agatha Crumble/);
  assert.match(prompt, /Theme or setting: A disastrous royal banquet/);
  assert.match(prompt, /80 words or fewer/);
});

test('Build template is isolated and generation is honestly marked pending', () => {
  const template = fs.readFileSync('newsmuncher/templates/build.html', 'utf8');
  assert.match(template, /data-build-workshop/);
  assert.match(template, /data-slot-list="stuff"/);
  assert.match(template, /data-prompt-preview/);
  assert.match(template, /class="funky-button munch-button" disabled/);
  assert.doesNotMatch(template, /shizzalise_data|generate_image|confirm_data/);
});
