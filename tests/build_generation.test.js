'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const {buildPrompt, applyStoryLength, serialiseRecipe, requestBuildStory, displayBuildStory, requestBuildDraft} = require('../newsmuncher/static/build-page.js');

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
    assert.match(prompt, /dangerously unhinged comedy writer/);
    assert.match(prompt, /raw genetic material for a comedic monstrosity/);
    assert.match(prompt, /Start in the middle of madness/);
    assert.match(prompt, /Finish with a detonation/);
    assert.match(prompt, /Never mechanically list or name-drop them/);
    assert.match(prompt, new RegExp(`Aim for ${Math.round(target * 0.9)}–${maximum} words`));
    assert.match(prompt, new RegExp(`never exceeding ${maximum}`));
  }
});

test('Build prompt omits every unselected category instead of saying None selected', () => {
  const prompt = buildPrompt({
    stuff: [{text: 'Leaf trowel espresso machine'}],
    swear: [{text: 'Waffle prodder'}],
    modifier: [{text: 'Romantically bankrupt'}],
    person: []
  }, 60);
  assert.match(prompt, /Objects: Leaf trowel espresso machine/);
  assert.match(prompt, /Swear words: Waffle prodder/);
  assert.match(prompt, /Modifiers: Romantically bankrupt/);
  assert.doesNotMatch(prompt, /People:/);
  assert.doesNotMatch(prompt, /Theme or setting:/);
  assert.doesNotMatch(prompt, /None selected/);
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
    return {ok: true, json: async () => ({
      story: 'A tiny coherent disaster.',
      headline: 'Tiny Disaster Upholsters The Parish Council With Weaponised Custard And Unlicensed Ferrets'
    })};
  };
  const editedPrompt = 'Apply malicious pastry physics.\n\nStory length: custom old value';
  const submittedPrompt = applyStoryLength(editedPrompt, 90);
  const generated = await requestBuildStory(fetcher, '/build/generate', recipe, 90, submittedPrompt);
  assert.equal(generated.story, 'A tiny coherent disaster.');
  assert.match(generated.headline, /Weaponised Custard/);
  assert.equal(request.url, '/build/generate');
  assert.equal(request.options.method, 'POST');
  const body = JSON.parse(request.options.body);
  assert.deepEqual(body.recipe.stuff, [{text: 'Transparent bipolar wrench projector'}]);
  assert.equal(body.target_words, 90);
  assert.equal(body.prompt, submittedPrompt);
});

test('story request surfaces safe backend errors', async () => {
  const fetcher = async () => ({ok: false, json: async () => ({detail: 'Story generation timed out. Please try again.'})});
  await assert.rejects(requestBuildStory(fetcher, '/build/generate', recipe, 30, 'Keep it odd.'), /timed out/);
});

test('all three MUNGE lengths visibly render successful stories in the editable result', async () => {
  const fitted = [];
  globalThis.autoResize = editor => fitted.push(editor);
  for (const target of [30, 60, 90]) {
    const story = `Visible editable ${target}-word story.`;
    const headline = `A Purpose-Written ${target}-Word Catastrophe Receives Its Own Filthy Musical Tabloid Hook`;
    const fetcher = async () => ({ok: true, json: async () => ({story, headline})});
    const generated = await requestBuildStory(fetcher, '/build/generate', recipe, target,
      applyStoryLength(buildPrompt(recipe, 60), target));
    const result = {hidden: true, style: {display: ''}};
    const editor = {value: ''};
    const element = {querySelector: selector => selector === '[data-build-result]' ? result : editor};
    displayBuildStory(element, generated.story);
    assert.equal(editor.value, story);
    assert.equal(generated.headline, headline);
    assert.equal(result.hidden, false);
    assert.equal(result.style.display, 'block');
    assert.equal(fitted.at(-1), editor);
  }
  delete globalThis.autoResize;
});

test('missing, blank and malformed story responses fail visibly instead of rendering', async () => {
  for (const payload of [{}, {story: '   '}, {story: {text: 'wrong shape'}}]) {
    const fetcher = async () => ({ok: true, json: async () => payload});
    await assert.rejects(
      requestBuildStory(fetcher, '/build/generate', recipe, 60, buildPrompt(recipe, 60)),
      /returned no text/
    );
  }
});

test('length switching preserves all manual prompt edits and keeps one instruction', () => {
  let prompt = buildPrompt(recipe, 60).replace('Transparent bipolar wrench projector', 'Hand-edited gazebo');
  prompt = applyStoryLength(prompt, 30);
  assert.match(prompt, /Hand-edited gazebo/);
  assert.match(prompt, /Aim for 27–33 words/);
  prompt = applyStoryLength(prompt, 90);
  assert.match(prompt, /Hand-edited gazebo/);
  assert.doesNotMatch(prompt, /Aim for 27–33 words/);
  assert.match(prompt, /Aim for 81–99 words/);
  assert.equal((prompt.match(/Story length:/g) || []).length, 1);
});

test('nomination preparation sends the latest edited story and headline relationship', async () => {
  let request;
  const fetcher = async (url, options) => {
    request = {url, options};
    return {ok: true, json: async () => ({rewrite_id: 'draft-1'})};
  };
  const result = await requestBuildDraft(fetcher, '/build/draft',
    'The user-edited final story.', 'Generated musical headline', 'The generated original story.');
  assert.equal(result.rewrite_id, 'draft-1');
  assert.equal(request.url, '/build/draft');
  assert.deepEqual(JSON.parse(request.options.body), {
    story: 'The user-edited final story.',
    headline: 'Generated musical headline',
    headline_story: 'The generated original story.'
  });
});

test('missing or malformed headline data never prevents story display', async () => {
  for (const headline of [undefined, null, {wrong: 'shape'}]) {
    const fetcher = async () => ({ok: true, json: async () => ({story: 'Usable story.', headline})});
    const generated = await requestBuildStory(
      fetcher, '/build/generate', recipe, 60, buildPrompt(recipe, 60));
    assert.equal(generated.story, 'Usable story.');
    assert.equal(generated.headline, '');
  }
});

test('all MUNGE controls share one loading lock and preserve their targets', () => {
  const source = require('node:fs').readFileSync(require('node:path').join(__dirname, '../newsmuncher/static/build-page.js'), 'utf8');
  assert.match(source, /querySelectorAll\('\[data-munge\]'\)/);
  assert.match(source, /buttons\.forEach\(item => \{ item\.disabled = true; \}\)/);
  assert.match(source, /generateStory\(Number\(munge\.dataset\.mungeTarget\)\)/);
  assert.match(source, /button\.textContent = 'MUNGING…'/);
  assert.match(source, /catch \(error\) \{[\s\S]*status\.classList\.add\('is-error'\)/);
  assert.match(source, /finally \{[\s\S]*this\.generating = false;[\s\S]*this\.renderRecipe\(\)/);
});

test('edited story and CREATE-compatible action row remain authoritative', () => {
  const source = require('node:fs').readFileSync(require('node:path').join(__dirname, '../newsmuncher/static/build-page.js'), 'utf8');
  assert.match(source, /querySelector\('\[data-build-story\]'\)\?\.value\.trim\(\)/);
  assert.match(source, /JSON\.stringify\(\{story, headline, headline_story: headlineStory\}\)/);
  assert.match(source, /this\.generatedHeadline, this\.headlineStory/);
  assert.match(source, /target_words: targetWords, prompt/);
  assert.match(source, /creationActions\?\.attachDraft/);
  assert.match(source, /creationActions\.nominate\(\)/);
  assert.doesNotMatch(source, /root\.bankThisBeauty/);
});
