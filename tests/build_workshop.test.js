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
  assert.deepEqual(build.INITIAL_COUNTS, {stuff: 3, swear: 2, modifier: 5, person: 1});
});

test('provider prompt assembly groups the recipe and defaults to the 60-word target', () => {
  const prompt = build.buildPrompt({
    stuff: [{text: 'Transparent bipolar wrench projector'}],
    swear: [{text: 'Right old turnip licker'}],
    modifier: [{text: 'Suspiciously', grammar: 'adverb'}],
    person: [{text: 'Agatha Crumble'}],
  });
  assert.match(prompt, /Objects: Transparent bipolar wrench projector/);
  assert.match(prompt, /People: Agatha Crumble/);
  assert.match(prompt, /dangerously unhinged comedy writer/);
  assert.match(prompt, /raw genetic material for a comedic monstrosity/);
  assert.match(prompt, /Make the impossible inevitable/);
  assert.match(prompt, /Finish with a detonation/);
  assert.match(prompt, /Aim for 54–66 words/);
  assert.match(prompt, /never exceeding 66/);
});

test('Build template is isolated and exposes bounded MUNGE generation', () => {
  const template = fs.readFileSync('newsmuncher/templates/build.html', 'utf8');
  assert.match(template, /data-build-workshop/);
  assert.match(template, /data-slot-list="stuff"/);
  assert.match(template, /data-prompt-editor/);
  assert.match(template, /data-reset-prompt>RESET PROMPT/);
  assert.doesNotMatch(template, /data-prompt-preview|Complete prompt preview/);
  assert.match(template, /data-generate-url="\/build\/generate"/);
  assert.match(template, /for target in \(30, 60, 90\)/);
  assert.match(template, /class="funky-button munch-button" data-munge data-munge-target="\{\{ target \}\}" disabled/);
  assert.match(template, />MUNGE \{\{ target \}\}<\/button>/);
  assert.match(template, /data-build-result/);
  assert.match(template, /block footer %}{% endblock/);
  assert.doesNotMatch(template, /shizzalise_data|generate_image|confirm_data/);
});

test('Build teat controls are cosmetic and reuse Create interaction controllers', () => {
  const template = fs.readFileSync('newsmuncher/templates/build.html', 'utf8');
  assert.match(template, /id="sourceUdder" class="source-udder"/);
  assert.match(template, /js\/creation\/source-udder\.js/);
  assert.match(template, /js\/creation\/udder-sounds\.js/);
  assert.doesNotMatch(template, /fetchAndDisplay|data-source=/);
  assert.match(template, /js\/creation\/script\.js/);
  assert.match(template, /<h1>BUILD A MUNGE<\/h1>/);
});

test('Build background is the existing read-only Create background controller', () => {
  const template = fs.readFileSync('newsmuncher/templates/build.html', 'utf8');
  const controller = fs.readFileSync('newsmuncher/static/js/creation/image-background.js', 'utf8');
  assert.match(template, /id="initialBackground"/);
  assert.match(template, /id="generatedBackdrop"/);
  assert.match(template, /js\/creation\/image-background\.js/);
  assert.match(controller, /fetch\('\/profile-background', \{cache: 'no-store'\}\)/);
  assert.doesNotMatch(controller, /POST|generate_image/);
});
