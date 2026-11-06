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

test('Build prompt centres selected ingredients and an 80-word story', () => {
  const prompt = buildPrompt(recipe);
  assert.match(prompt, /Transparent bipolar wrench projector/);
  assert.match(prompt, /flap-mouthed bollock merchant/);
  assert.match(prompt, /no more than 80 words/);
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
  const story = await requestBuildStory(fetcher, '/build/generate', recipe);
  assert.equal(story, 'A tiny coherent disaster.');
  assert.equal(request.url, '/build/generate');
  assert.equal(request.options.method, 'POST');
  assert.deepEqual(JSON.parse(request.options.body).recipe.stuff, [{text: 'Transparent bipolar wrench projector'}]);
});

test('story request surfaces safe backend errors', async () => {
  const fetcher = async () => ({ok: false, json: async () => ({detail: 'Story generation timed out. Please try again.'})});
  await assert.rejects(requestBuildStory(fetcher, '/build/generate', recipe), /timed out/);
});
