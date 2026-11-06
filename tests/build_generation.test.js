'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const {buildPrompt, serialiseRecipe, requestBuildStory} = require('../newsmuncher/static/build-page.js');

const recipe = {
  stuff: [{id: 'local-1', text: 'Transparent bipolar wrench projector'}],
  swear: [{id: 'local-2', text: 'flap-mouthed bollock merchant'}],
  modifier: [{id: 'local-3', text: 'ceremonially', grammar: 'adverb'}],
  person: [{id: 'local-4', text: 'Dame Edith Crumble'}],
  theme: [{id: 'local-5', text: 'a flooded village fete'}]
};

test('Build prompt shares its creative rules across all three length targets', () => {
  const expectations = [[30, 33], [60, 66], [90, 99]];
  for (const [target, maximum] of expectations) {
    const prompt = buildPrompt(recipe, target);
    assert.match(prompt, /Transparent bipolar wrench projector/);
    assert.match(prompt, /flap-mouthed bollock merchant/);
    assert.match(prompt, /creative seeds rather than mandatory phrases/);
    assert.match(prompt, /Avoid lazy dialogue/);
    assert.match(prompt, /generic existential dread, arbitrary promotions and sentient bureaucracy/);
    assert.match(prompt, /surprising punchline/);
    assert.match(prompt, new RegExp(`Aim for about ${target} words`));
    assert.match(prompt, new RegExp(`never exceed ${maximum} words`));
  }
});

test('serialised recipe omits local ids and retains grammar', () => {
  const output = serialiseRecipe(recipe);
  assert.deepEqual(output.modifier, [{text: 'ceremonially', grammar: 'adverb'}]);
  assert.deepEqual(output.stuff, [{text: 'Transparent bipolar wrench projector'}]);
});

test('story request posts structured recipe and returns provider story', async () => {
  let request;
  const fetcher = async (url, options) => {
    request = {url, options};
    return {ok: true, json: async () => ({story: 'A tiny coherent disaster.'})};
  };
  const story = await requestBuildStory(fetcher, '/build/generate', recipe, 90);
  assert.equal(story, 'A tiny coherent disaster.');
  assert.equal(request.url, '/build/generate');
  assert.equal(request.options.method, 'POST');
  const body = JSON.parse(request.options.body);
  assert.deepEqual(body.recipe.stuff, [{text: 'Transparent bipolar wrench projector'}]);
  assert.equal(body.target_words, 90);
});

test('story request surfaces safe backend errors', async () => {
  const fetcher = async () => ({ok: false, json: async () => ({detail: 'Story generation timed out. Please try again.'})});
  await assert.rejects(requestBuildStory(fetcher, '/build/generate', recipe, 30), /timed out/);
});

test('all MUNGE controls share one loading lock and preserve their targets', () => {
  const source = require('node:fs').readFileSync(require('node:path').join(__dirname, '../newsmuncher/static/build-page.js'), 'utf8');
  assert.match(source, /querySelectorAll\('\[data-munge\]'\)/);
  assert.match(source, /buttons\.forEach\(item => \{ item\.disabled = true; \}\)/);
  assert.match(source, /generateStory\(Number\(munge\.dataset\.mungeTarget\)\)/);
  assert.match(source, /button\.textContent = 'MUNGING…'/);
});
