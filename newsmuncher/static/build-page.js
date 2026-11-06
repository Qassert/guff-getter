(function (root) {
  'use strict';

  const STUFF_STRUCTURES = [
    ['adjective', 'object'], ['adjective', 'device'], ['object', 'device'],
    ['adjective', 'object', 'device'], ['adjective', 'surreal_descriptor', 'object'],
    ['adjective', 'surreal_descriptor', 'device'],
    ['adjective', 'surreal_descriptor', 'object', 'device'],
    ['surreal_descriptor', 'adjective', 'object', 'device']
  ];
  const STUFF_WEIGHTS = [7.5, 7.5, 7.5, 7.5, 17.5, 17.5, 17.5, 17.5];
  const SWEAR_STRUCTURES = [
    ['bijv_nw', 'gilles', 'zelfs_nw'], ['bijv_nw', 'gilles', 'handelend'],
    ['bijv_nw', 'zelfs_nw', 'handelend'], ['gilles', 'zelfs_nw'],
    ['gilles', 'handelend'], ['zelfs_nw', 'handelend']
  ];
  const LABELS = {
    stuff: 'Stuff / Objects', swear: 'Swear words', modifier: 'Modifiers',
    person: 'People', theme: 'Theme / Scene'
  };
  const INITIAL_COUNTS = {stuff: 3, swear: 2, modifier: 5, person: 1, theme: 1};
  const FLICK_COUNT = 5;
  const FLICK_DELAY = 100;

  function parseCSV(text) {
    const rows = [];
    let row = [], field = '', quoted = false;
    const source = String(text || '').replace(/^\uFEFF/, '');
    for (let index = 0; index <= source.length; index++) {
      const char = source[index] || '\n';
      if (quoted && char === '"' && source[index + 1] === '"') {
        field += '"'; index++; continue;
      }
      if (char === '"') { quoted = !quoted; continue; }
      if (!quoted && char === ',') { row.push(field); field = ''; continue; }
      if (!quoted && (char === '\n' || char === '\r')) {
        if (char === '\r' && source[index + 1] === '\n') index++;
        row.push(field); field = '';
        if (row.some(value => value.trim())) rows.push(row);
        row = []; continue;
      }
      field += char;
    }
    const vocabulary = {};
    for (const columns of rows.slice(1)) {
      if (columns.length < 2) continue;
      const category = columns[0].trim();
      const word = columns.slice(1).join(',').trim();
      if (!category || !word) continue;
      if (!vocabulary[category]) vocabulary[category] = [];
      if (!vocabulary[category].includes(word)) vocabulary[category].push(word);
    }
    return vocabulary;
  }

  function pick(values, random = Math.random, excluded = new Set()) {
    const eligible = values.filter(value => !excluded.has(value));
    const pool = eligible.length ? eligible : values;
    return pool[Math.floor(random() * pool.length)];
  }

  function weightedStructure(structures, weights, random = Math.random) {
    const total = weights.reduce((sum, weight) => sum + weight, 0);
    let target = random() * total;
    for (let index = 0; index < structures.length; index++) {
      target -= weights[index];
      if (target < 0) return structures[index];
    }
    return structures[structures.length - 1];
  }

  function capitalise(text) {
    const clean = String(text || '').trim();
    return clean ? clean[0].toUpperCase() + clean.slice(1) : '';
  }

  function phrase(parts) { return capitalise(parts.map(part => part.word).join(' ')); }

  function buildPrompt(recipe) {
    const line = (label, key) => `${label}: ${(recipe[key] || []).map(item => item.text).join('; ') || 'None selected'}`;
    return [
      'You are an inventive, irreverent absurdist comedy writer. Write one coherent, genuinely funny miniature story using the selected ingredients as creative inspiration.',
      '',
      'Selected ingredients:',
      '',
      line('Objects', 'stuff'),
      line('Swear words', 'swear'),
      line('People', 'person'),
      line('Modifiers', 'modifier'),
      line('Theme or setting', 'theme'),
      '',
      'Creative rules:',
      '- Transform, do not merely insert. Treat ingredients as creative seeds rather than mandatory phrases. Reinterpret, mutate and combine them so they become integral to the characters, objects, events or absurd logic.',
      '- Never satisfy the recipe by simply making a character say an insult, occupation or unusual phrase. Avoid lazy dialogue; build jokes from what the ingredients become and do.',
      '- Invent unexpected connections between ingredients. Begin with a peculiar situation, add a surprising complication, then escalate through a twisted but recognisable chain of cause and effect.',
      '- Prioritise comedy over completeness. Transform or omit an ingredient when literal inclusion would make the story weaker.',
      '- Be boldly irreverent: use deadpan narration, vivid specificity, dark humour, grotesque imagery, vulgarity, stupidity and wildly inappropriate consequences when funny.',
      '- Avoid tired surrealist clichés, especially generic existential dread, arbitrary promotions and sentient bureaucracy.',
      '- End with a surprising punchline that pays off or recontextualises an earlier detail instead of becoming random.',
      '',
      'Aim for 60 to 80 words and never exceed 80 words. Return only the story, with no title, introduction or explanation.'
    ].join('\n');
  }

  function wait(delay) { return new Promise(resolve => setTimeout(resolve, delay)); }

  function serialiseRecipe(recipe) {
    return Object.fromEntries(Object.entries(recipe).map(([category, items]) => [category,
      items.map(item => ({text: item.text, ...(item.grammar ? {grammar: item.grammar} : {})}))]));
  }

  async function requestBuildStory(fetcher, url, recipe, signal) {
    const response = await fetcher(url, {
      method: 'POST', credentials: 'same-origin', signal,
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({recipe: serialiseRecipe(recipe)})
    });
    let payload = {};
    try { payload = await response.json(); } catch (_) {}
    if (!response.ok) throw new Error(payload.detail || 'Story generation failed. Please try again.');
    if (!payload.story) throw new Error('Story generation returned no text. Please try again.');
    return payload.story;
  }

  class BuildWorkshop {
    constructor(element, options = {}) {
      this.element = element;
      this.random = options.random || Math.random;
      this.fetcher = options.fetcher || root.fetch?.bind(root);
      this.reducedMotion = options.reducedMotion || (() => !!root.matchMedia?.('(prefers-reduced-motion: reduce)').matches);
      this.vocabularies = {};
      this.slots = {stuff: [], swear: [], modifier: [], person: [], theme: []};
      this.recipe = {stuff: [], swear: [], modifier: [], person: [], theme: []};
      this.nextId = 1;
      this.generating = false;
      this.generateController = null;
      this.recent = {stuff: new Set(), swear: new Set(), modifier: new Set(), person: new Set(), theme: new Set()};
    }

    async load() {
      const sources = {
        stuff: this.element.dataset.stuffUrl, swear: this.element.dataset.swearUrl,
        modifier: this.element.dataset.modifierUrl, person: this.element.dataset.personUrl,
        theme: this.element.dataset.themeUrl
      };
      try {
        const entries = await Promise.all(Object.entries(sources).map(async ([key, url]) => {
          const response = await this.fetcher(url, {credentials: 'same-origin'});
          if (!response.ok) throw new Error(`Could not load ${key} ingredients.`);
          return [key, parseCSV(await response.text())];
        }));
        this.vocabularies = Object.fromEntries(entries);
        for (const [category, count] of Object.entries(INITIAL_COUNTS)) {
          for (let index = 0; index < count; index++) this.addSlot(category, false);
        }
        this.bind(); this.render();
        this.element.querySelector('[data-build-loading]').hidden = true;
        this.element.querySelector('[data-build-controls]').hidden = false;
      } catch (error) {
        this.element.querySelector('[data-build-loading]').hidden = true;
        const panel = this.element.querySelector('[data-build-error]');
        panel.textContent = error.message || 'The ingredient cupboards failed to open.';
        panel.hidden = false;
      }
    }

    categoriesFor(category) {
      if (category === 'stuff') return weightedStructure(STUFF_STRUCTURES, STUFF_WEIGHTS, this.random);
      if (category === 'swear') return SWEAR_STRUCTURES[Math.floor(this.random() * SWEAR_STRUCTURES.length)];
      if (category === 'modifier') {
        const options = Object.keys(this.vocabularies.modifier);
        return [pick(options, this.random)];
      }
      return [category];
    }

    bank(category, partCategory) {
      if (category === 'person') return this.vocabularies.person.person || [];
      if (category === 'theme') return this.vocabularies.theme.theme || [];
      return this.vocabularies[category][partCategory] || [];
    }

    activeWords(category, exceptId) {
      return new Set(this.slots[category].filter(slot => slot.id !== exceptId)
        .flatMap(slot => slot.parts.map(part => part.word)));
    }

    candidate(category, exceptId) {
      const excluded = this.activeWords(category, exceptId);
      const parts = this.categoriesFor(category).map(partCategory => ({
        category: partCategory,
        word: pick(this.bank(category, partCategory), this.random, excluded)
      }));
      return parts;
    }

    addSlot(category, rerender = true) {
      const slot = {id: this.nextId++, category, parts: this.candidate(category), busy: false, generation: 0};
      this.slots[category].push(slot);
      if (rerender) this.render();
      return slot;
    }

    removeSlot(category, id) {
      if (this.slots[category].length <= 1) return;
      const slot = this.slots[category].find(item => item.id === id);
      if (slot) slot.generation++;
      this.slots[category] = this.slots[category].filter(item => item.id !== id);
      this.render();
    }

    async flickPart(slot, index, target, generation, delay = 0) {
      if (delay && !this.reducedMotion()) await wait(delay);
      const bank = this.bank(slot.category, target.category);
      const count = this.reducedMotion() ? 1 : FLICK_COUNT;
      for (let flick = 0; flick < count; flick++) {
        if (slot.generation !== generation) return;
        const final = flick === count - 1;
        slot.parts[index] = {...target, word: final ? target.word : pick(bank, this.random, new Set([target.word]))};
        this.renderSlot(slot);
        if (!final) await wait(FLICK_DELAY);
      }
    }

    async randomiseSlot(category, id) {
      const slot = this.slots[category].find(item => item.id === id);
      if (!slot || slot.busy) return;
      slot.busy = true; const generation = ++slot.generation;
      const targets = this.candidate(category, id);
      slot.parts = targets.map(target => ({...target}));
      this.renderSlot(slot);
      await Promise.all(targets.map((target, index) => this.flickPart(slot, index, target, generation, index * 200)));
      if (slot.generation === generation) { slot.busy = false; this.remember(slot); this.renderSlot(slot); }
    }

    async randomisePart(category, id, index) {
      const slot = this.slots[category].find(item => item.id === id);
      if (!slot || slot.busy || !slot.parts[index]) return;
      slot.busy = true; const generation = ++slot.generation;
      const current = slot.parts[index];
      const excluded = this.activeWords(category, id); excluded.add(current.word);
      const target = {...current, word: pick(this.bank(category, current.category), this.random, excluded)};
      await this.flickPart(slot, index, target, generation);
      if (slot.generation === generation) { slot.busy = false; this.remember(slot); this.renderSlot(slot); }
    }

    remember(slot) {
      const key = phrase(slot.parts).toLocaleLowerCase();
      const recent = this.recent[slot.category];
      recent.add(key);
      if (recent.size > 200) recent.delete(recent.values().next().value);
    }

    useSlot(category, id) {
      const slot = this.slots[category].find(item => item.id === id);
      if (!slot || slot.busy) return;
      const text = phrase(slot.parts);
      if (!text || this.recipe[category].some(item => item.text === text)) return;
      this.recipe[category].push({id: `${category}-${Date.now()}-${this.nextId++}`, text,
        grammar: category === 'modifier' ? slot.parts[0].category : undefined});
      this.renderRecipe();
    }

    removeRecipe(category, id) {
      this.recipe[category] = this.recipe[category].filter(item => item.id !== id);
      this.renderRecipe();
    }

    bind() {
      this.element.addEventListener('click', event => {
        const munge = event.target.closest('[data-munge]');
        if (munge) return this.generateStory();
        const add = event.target.closest('[data-add-slot]');
        if (add) return this.addSlot(add.dataset.addSlot);
        const remove = event.target.closest('[data-remove-slot]');
        if (remove) return this.removeSlot(remove.dataset.category, Number(remove.dataset.removeSlot));
        const shuffle = event.target.closest('[data-randomise-slot]');
        if (shuffle) return this.randomiseSlot(shuffle.dataset.category, Number(shuffle.dataset.randomiseSlot));
        const part = event.target.closest('[data-randomise-part]');
        if (part) return this.randomisePart(part.dataset.category, Number(part.dataset.slotId), Number(part.dataset.randomisePart));
        const use = event.target.closest('[data-use-slot]');
        if (use) return this.useSlot(use.dataset.category, Number(use.dataset.useSlot));
        const recipe = event.target.closest('[data-remove-recipe]');
        if (recipe) return this.removeRecipe(recipe.dataset.category, recipe.dataset.removeRecipe);
      });
    }

    slotMarkup(slot) {
      const words = slot.parts.map((part, index) =>
        `<button type="button" class="ingredient-word" data-randomise-part="${index}" data-category="${slot.category}" data-slot-id="${slot.id}" ${slot.busy ? 'disabled' : ''} title="Randomise only this word"><span>${escapeHTML(part.word)}</span><small>${escapeHTML(part.category.replaceAll('_', ' '))}</small></button>`).join(' ');
      return `<article class="ingredient-slot${slot.busy ? ' is-busy' : ''}" data-slot="${slot.id}" data-slot-category="${slot.category}">
        <div class="ingredient-phrase">${words}</div>
        <div class="slot-actions">
          <button type="button" class="mini-action" data-randomise-slot="${slot.id}" data-category="${slot.category}" ${slot.busy ? 'disabled' : ''}>SPIN</button>
          <button type="button" class="mini-action use-action" data-use-slot="${slot.id}" data-category="${slot.category}" ${slot.busy ? 'disabled' : ''}>USE</button>
          <button type="button" class="remove-action" data-remove-slot="${slot.id}" data-category="${slot.category}" aria-label="Remove ${slot.category} slot" ${this.slots[slot.category].length <= 1 ? 'disabled' : ''}>×</button>
        </div>
      </article>`;
    }

    renderSlot(slot) {
      const existing = this.element.querySelector(`[data-slot-category="${slot.category}"][data-slot="${slot.id}"]`);
      if (!existing) return this.render();
      const wrapper = document.createElement('div'); wrapper.innerHTML = this.slotMarkup(slot);
      existing.replaceWith(wrapper.firstElementChild);
    }

    render() {
      for (const [category, slots] of Object.entries(this.slots)) {
        const list = this.element.querySelector(`[data-slot-list="${category}"]`);
        if (list) list.innerHTML = slots.map(slot => this.slotMarkup(slot)).join('');
      }
      this.renderRecipe();
    }

    renderRecipe() {
      const populated = Object.values(this.recipe).some(items => items.length);
      const panel = this.element.querySelector('[data-recipe-panel]');
      panel.hidden = false;
      this.element.querySelector('[data-recipe-empty]').hidden = populated;
      const container = this.element.querySelector('[data-recipe-categories]');
      container.innerHTML = Object.entries(this.recipe).filter(([, items]) => items.length).map(([category, items]) =>
        `<section class="recipe-category"><h3>${LABELS[category]}</h3><div class="recipe-items">${items.map(item =>
          `<span class="recipe-chip">${escapeHTML(item.text)}${item.grammar ? ` <small>(${escapeHTML(item.grammar)})</small>` : ''}<button type="button" data-remove-recipe="${item.id}" data-category="${category}" aria-label="Remove ${escapeHTML(item.text)}">×</button></span>`).join('')}</div></section>`).join('');
      this.element.querySelector('[data-prompt-preview]').textContent = buildPrompt(this.recipe);
      const button = this.element.querySelector('[data-munge]');
      button.disabled = !populated || this.generating;
      if (!this.generating) {
        button.textContent = 'MUNGE';
        const status = this.element.querySelector('[data-munge-status]');
        if (!populated) status.textContent = 'Choose at least one ingredient to MUNGE.';
        else if (!status.classList.contains('is-error')) status.textContent = 'Ready to turn this recipe into a miniature story.';
      }
    }

    async generateStory() {
      const populated = Object.values(this.recipe).some(items => items.length);
      if (!populated || this.generating) return;
      this.generating = true;
      const button = this.element.querySelector('[data-munge]');
      const status = this.element.querySelector('[data-munge-status]');
      button.disabled = true; button.textContent = 'MUNGING…';
      status.classList.remove('is-error');
      status.textContent = 'Munging your ingredients into fresh nonsense…';
      this.generateController?.abort();
      this.generateController = new AbortController();
      const timeout = root.setTimeout(() => this.generateController?.abort(), 35000);
      try {
        const story = await requestBuildStory(this.fetcher, this.element.dataset.generateUrl, this.recipe, this.generateController.signal);
        const result = this.element.querySelector('[data-build-result]');
        this.element.querySelector('[data-build-story]').textContent = story;
        result.hidden = false;
        status.textContent = 'MUNGE complete. Press MUNGE again for another version.';
      } catch (error) {
        status.classList.add('is-error');
        status.textContent = error.name === 'AbortError'
          ? 'Story generation timed out. Your recipe is safe; please try again.'
          : (error.message || 'Story generation failed. Your recipe is safe; please try again.');
      } finally {
        root.clearTimeout(timeout);
        this.generateController = null;
        this.generating = false;
        this.renderRecipe();
      }
    }
  }

  function escapeHTML(value) {
    return String(value).replace(/[&<>'"]/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char]));
  }

  function mount(element, options) {
    const workshop = new BuildWorkshop(element, options);
    workshop.load(); return workshop;
  }

  const api = {parseCSV, weightedStructure, phrase, buildPrompt, serialiseRecipe, requestBuildStory, BuildWorkshop, mount,
    STUFF_STRUCTURES, STUFF_WEIGHTS, SWEAR_STRUCTURES, INITIAL_COUNTS, FLICK_COUNT, FLICK_DELAY};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  root.NewsMuncherBuild = api;
  if (root.document) root.document.querySelectorAll('[data-build-workshop]').forEach(element => mount(element));
})(typeof window !== 'undefined' ? window : globalThis);
