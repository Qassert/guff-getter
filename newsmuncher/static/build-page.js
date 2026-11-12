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
    person: 'People', custom: 'Custom Ingredients'
  };
  const INITIAL_COUNTS = {stuff: 3, swear: 2, modifier: 5, person: 1};
  const FLICK_COUNT = 5;
  const FLICK_DELAY = 100;
  const DEFAULT_CREATIVE_PROMPT = `You are a dangerously unhinged comedy writer with impeccable comic timing and absolutely no respect for reality.

Your job is to produce a tiny, gloriously ridiculous piece of fiction that feels like someone has accidentally combined a fever dream, a filthy British comedy sketch and a catastrophic misunderstanding of how the universe works.

**The rules of lunacy:**

- **Mutate everything.** The ingredients are raw genetic material for a comedic monstrosity. Fuse them, corrupt them, misunderstand them and invent things that should never have existed. Nothing needs to retain its original purpose.
- **Start in the middle of madness.** The opening sentence should immediately establish something spectacularly stupid as an ordinary fact of life. No introductions, explanations or scene-setting.
- **Make the impossible inevitable.** Every ridiculous event must cause an even more ridiculous consequence. The logic can be insane, but the chain reaction must be understandable.
- Make every story outrageously dramatic. Treat trivial events as catastrophic turning points, exaggerate emotions and consequences to ludicrous extremes, and build towards an explosive, ridiculous climax. Deliver the chaos with absolute conviction and deadpan seriousness.
- **Commit to the stupidity.** Characters must take the most outrageously inappropriate actions with absolute conviction. Nobody should acknowledge how bizarre anything is.
- **Weaponise specificity.** Ridiculously precise details, revolting physical transformations, petty grievances, bodily indignities and wildly disproportionate punishments are your friends.
- **Be magnificently inappropriate.** Embrace vulgarity, grotesque slapstick, dark humour, humiliation, stupidity, bad taste and outrageous social transgressions whenever they make the joke funnier.
- Do not make the resulting answer be set in any particular place.
- Do not mention vicars, priests or religious references. Transform any religious ingredient or setting into a secular alternative.
- **Surprise yourself.** Avoid predictable surrealism, talking household appliances, corporate satire, existential philosophy, random royalty and anything that resembles a conventional whimsical fairy tale.
- **Don't explain the joke.** No moral, no reflection, no clever concluding observation. Let the absurdity speak for itself.
- **Finish with a detonation.** The final sentence should deliver a brutally funny reversal, escalation or revelation that makes the preceding nonsense even more ridiculous. A proper comic payoff, not a random non sequitur.`;

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

  function storyLengthInstruction(targetWords) {
    const pacing = {30: 'Keep it punchy and compressed.', 60: 'Give the absurd situation room to escalate.', 90: 'Develop a more elaborate absurd situation while keeping every sentence useful.'}[targetWords];
    return `Story length: Aim for approximately ${targetWords} words. You may go slightly over when it improves the story's coherence, comedic timing or final punchline. Prioritise a complete, funny story over hitting an exact word count. If there are too many ingredients, use fewer rather than forcing everything into the story. ${pacing}`;
  }

  function limitFurtherInstructions(value) {
    const text = String(value || '').slice(0, 5000);
    const words = [...text.matchAll(/\S+/g)];
    return words.length > 100 ? text.slice(0, words[100].index).trimEnd() : text;
  }

  function selectedIngredientLines(recipe) {
    return [
      ['Objects', 'stuff'], ['Swear words', 'swear'], ['People', 'person'], ['Modifiers', 'modifier'], ['Custom Ingredients', 'custom']
    ].flatMap(([label, key]) => {
      const values = (recipe[key] || []).map(item => item.text).filter(Boolean);
      return values.length ? [`${label}: ${values.join('; ')}`] : [];
    });
  }

  function buildPrompt(recipe, targetWords = 60, creativePrompt = DEFAULT_CREATIVE_PROMPT) {
    const ingredientLines = selectedIngredientLines(recipe);
    return [
      creativePrompt.trim(),
      '',
      '**Selected ingredients:**',
      '',
      ...ingredientLines,
      '',
      '**Ingredient handling:**',
      '',
      'Use whichever ingredients produce the most explosive comedy. Combine several into one hideous invention if necessary. Never mechanically list or name-drop them. The ingredients should be responsible for the disaster, not merely present at the scene.',
      '',
      '**Output:**',
      '',
      'Write exactly one miniature comic catastrophe. Every sentence must earn its place through a joke, escalation or payoff.',
      '',
      'Return only the story. No title, commentary or explanation.',
      storyLengthInstruction(targetWords)
    ].join('\n');
  }

  function syncPromptIngredients(prompt, recipe, target = 60) {
    const section = '\n\n' + selectedIngredientLines(recipe).join('\n') + '\n\n';
    const pattern = /^\*\*Selected ingredients:\*\*$[\s\S]*?(?=^\*\*Ingredient handling:\*\*$)/m;
    if (pattern.test(prompt)) return prompt.replace(pattern, () => '**Selected ingredients:**' + section);
    const canonical = buildPrompt(recipe, target);
    const creative = String(prompt).split('**Selected ingredients:**')[0].trimEnd();
    return creative + '\n\n' + canonical.slice(canonical.indexOf('**Selected ingredients:**'));
  }

  function applyStoryLength(prompt, targetWords) {
    const cleaned = String(prompt || '').replace(/^Story length:.*(?:\n|$)/gm, '').trimEnd();
    return `${cleaned}\n\n${storyLengthInstruction(targetWords)}`;
  }

  function wait(delay) { return new Promise(resolve => setTimeout(resolve, delay)); }

  function serialiseRecipe(recipe) {
    return Object.fromEntries(Object.entries(recipe).map(([category, items]) => [category,
      items.map(item => ({text: item.text, ...(item.grammar ? {grammar: item.grammar} : {})}))]));
  }

  async function requestBuildStory(fetcher, url, recipe, targetWords, prompt, signal, furtherInstructions = '') {
    const response = await fetcher(url, {
      method: 'POST', credentials: 'same-origin', signal,
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({recipe: serialiseRecipe(recipe), target_words: targetWords, prompt, ...(furtherInstructions ? {further_instructions: furtherInstructions} : {})})
    });
    let payload = {};
    try { payload = await response.json(); } catch (_) {}
    if (response.status === 401 && payload.adoption_url) root.adoptionAccess?.redirect(payload.adoption_url);
    if (!response.ok) throw new Error(payload.detail || 'Story generation failed. Please try again.');
    if (typeof payload.story !== 'string' || !payload.story.trim()) {
      throw new Error('Story generation returned no text. Please try again.');
    }
    return {
      story: payload.story.trim(),
      headline: typeof payload.headline === 'string' ? payload.headline.trim() : ''
    };
  }

  function displayBuildStory(element, story) {
    const result = element.querySelector('[data-build-result]');
    const editor = element.querySelector('[data-build-story]');
    if (!result || !editor) throw new Error('The generated story could not be displayed. Please try again.');
    editor.value = story;
    result.hidden = false;
    result.style.display = 'block';
    root.autoResize?.(editor);
  }

  async function requestBuildDraft(fetcher, url, story, headline = '', headlineStory = '') {
    const response = await fetcher(url, {
      method: 'POST', credentials: 'same-origin', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({story, headline, headline_story: headlineStory})
    });
    const payload = await response.json().catch(() => ({}));
    if (response.status === 401 && payload.adoption_url) root.adoptionAccess?.redirect(payload.adoption_url);
    if (!response.ok) throw new Error(payload.detail || 'Nomination could not be prepared.');
    return payload;
  }

  class BuildWorkshop {
    constructor(element, options = {}) {
      this.element = element;
      this.random = options.random || Math.random;
      this.fetcher = options.fetcher || root.fetch?.bind(root);
      this.reducedMotion = options.reducedMotion || (() => !!root.matchMedia?.('(prefers-reduced-motion: reduce)').matches);
      this.vocabularies = {};
      this.slots = {stuff: [], swear: [], modifier: [], person: []};
      this.recipe = {stuff: [], swear: [], modifier: [], person: [], custom: []};
      this.nextId = 1;
      this.generating = false;
      this.generateController = null;
      this.promptDirty = false;
      this.promptTarget = 60;
      this.generatedHeadline = '';
      this.headlineStory = '';
      this.recent = {stuff: new Set(), swear: new Set(), modifier: new Set(), person: new Set()};
    }

    async load() {
      const sources = {
        stuff: this.element.dataset.stuffUrl, swear: this.element.dataset.swearUrl,
        modifier: this.element.dataset.modifierUrl, person: this.element.dataset.personUrl
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
        root.adoptionAccess?.register('build', {
          snapshot: () => ({slots: this.slots, recipe: this.recipe, nextId: this.nextId,
            prompt: this.currentPrompt(), promptTarget: this.promptTarget, promptDirty: this.promptDirty, furtherInstructions: this.furtherInstructions(),
            story: this.element.querySelector('[data-build-story]')?.value || '',
            generatedHeadline: this.generatedHeadline, headlineStory: this.headlineStory}),
          restore: draft => {
            if (!draft.slots || !draft.recipe) return;
            this.slots = draft.slots; this.recipe = {...draft.recipe, custom: draft.recipe.custom || []}; this.nextId = draft.nextId;
            for (const slots of Object.values(this.slots)) {
              for (const slot of slots) { slot.busy = false; slot.generation++; }
            }
            this.promptTarget = draft.promptTarget || 60;
            this.generatedHeadline = draft.generatedHeadline || '';
            this.headlineStory = draft.headlineStory || '';
            this.promptDirty = !!draft.promptDirty;
            this.element.querySelector('[data-prompt-editor]').value = draft.prompt || '';
            const instructions = this.element.querySelector('[data-further-instructions]');
            if (instructions) instructions.value = limitFurtherInstructions(draft.furtherInstructions);
            if (draft.story) {
              displayBuildStory(this.element, draft.story);
              const nominate = this.element.querySelector('[data-build-nominate]');
              if (nominate) { nominate.hidden = false; nominate.disabled = false; }
              root.updateCopyButton?.();
            }
          }
        });
        root.adoptionAccess?.restore();
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

    async spinAll() {
      if (this.spinningAll) return;
      this.spinningAll = true;
      const button = this.element.querySelector('[data-spin-all]');
      if (button) button.disabled = true;
      try {
        await Promise.all(Object.entries(this.slots).flatMap(([category, slots]) =>
          slots.map(slot => this.randomiseSlot(category, slot.id, true))));
      } finally {
        this.spinningAll = false;
        if (button) button.disabled = false;
      }
    }

    async randomiseSlot(category, id, avoidRepeat = false) {
      const slot = this.slots[category].find(item => item.id === id);
      if (!slot || slot.busy) return;
      slot.busy = true; const generation = ++slot.generation;
      let targets = this.candidate(category, id);
      if (avoidRepeat) {
        const previous = phrase(slot.parts);
        for (let attempt = 0; attempt < 5 && phrase(targets) === previous; attempt++) {
          targets = this.candidate(category, id);
        }
      }
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
      if (!text) return;
      const selected = this.recipe[category].find(item => item.text === text);
      if (selected) return this.removeRecipe(category, selected.id);
      if (Object.values(this.recipe).flat().some(item => item.text.toLowerCase() === text.toLowerCase())) return;
      this.recipe[category].push({id: `${category}-${Date.now()}-${this.nextId++}`, text,
        grammar: category === 'modifier' ? slot.parts[0].category : undefined});
      this.renderRecipe();
    }

    removeRecipe(category, id) {
      this.recipe[category] = this.recipe[category].filter(item => item.id !== id);
      this.renderRecipe();
    }

    furtherInstructions() {
      return limitFurtherInstructions(this.element.querySelector('[data-further-instructions]')?.value);
    }

    updateInstructions() {
      const field = this.element.querySelector('[data-further-instructions]');
      if (field) field.value = limitFurtherInstructions(field.value);
      const count = this.element.querySelector('[data-instructions-count]');
      if (count) count.textContent = `${(this.furtherInstructions().match(/\S+/g) || []).length} / 100 words`;
    }

    addCustomIngredient() {
      const input = this.element.querySelector('[data-custom-ingredient]');
      const text = input.value.replace(/\s+/g, ' ').trim();
      const duplicate = Object.values(this.recipe).flat().some(item => item.text.toLowerCase() === text.toLowerCase());
      const custom = this.recipe.custom || (this.recipe.custom = []);
      const error = !text ? 'Enter an ingredient.' : text.length > 160 ? 'Use 160 characters or fewer.' :
        duplicate ? 'That ingredient is already selected.' : custom.length >= 12 ? 'Use at most 12 custom ingredients.' : '';
      input.setCustomValidity(error);
      if (error) { input.reportValidity(); return false; }
      custom.push({id: `custom-${this.nextId++}`, text});
      input.value = '';
      this.renderRecipe();
      root.adoptionAccess?.save();
      return true;
    }

    bind() {
      this.element.querySelector('[data-custom-ingredient-form]')?.addEventListener('submit', event => {
        event.preventDefault(); this.addCustomIngredient();
      });
      this.element.querySelector('[data-custom-ingredient]')?.addEventListener('input', event => event.target.setCustomValidity(''));
      this.element.querySelector('[data-further-instructions]')?.addEventListener('input', () => {
        this.updateInstructions(); root.adoptionAccess?.save();
      });
      this.element.querySelector('[data-clear-instructions]')?.addEventListener('click', () => {
        this.element.querySelector('[data-further-instructions]').value = '';
        this.updateInstructions(); root.adoptionAccess?.save();
      });
      this.element.querySelector('[data-advanced-prompt]')?.addEventListener('toggle', () => this.resizePromptEditor());
      const promptEditor = this.element.querySelector('[data-prompt-editor]');
      promptEditor?.addEventListener('input', () => {
        this.promptDirty = true;
        this.resizePromptEditor();
      });
      (root.requestAnimationFrame || (callback => callback()))(() => this.resizePromptEditor());
      this.element.addEventListener('click', event => {
        const resetPrompt = event.target.closest('[data-reset-prompt]');
        if (resetPrompt) return this.resetPrompt();
        const nominate = event.target.closest('[data-build-nominate]');
        if (nominate) return this.nominateStory();
        const munge = event.target.closest('[data-munge]');
        if (munge) return this.generateStory(Number(munge.dataset.mungeTarget));
        const spinAll = event.target.closest('[data-spin-all]');
        if (spinAll) return this.spinAll();
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
          <button type="button" class="mini-action use-action" data-use-slot="${slot.id}" data-category="${slot.category}" ${slot.busy ? 'disabled' : ''} aria-pressed="${this.recipe[slot.category].some(item => item.text === phrase(slot.parts))}">USE</button>
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
      this.element.querySelector('[data-custom-ingredient]')?.setCustomValidity?.('');
      const populated = Object.values(this.recipe).some(items => items.length);
      const panel = this.element.querySelector('[data-recipe-panel]');
      panel.hidden = false;
      this.element.querySelector('[data-recipe-empty]').hidden = populated;
      const container = this.element.querySelector('[data-recipe-categories]');
      container.innerHTML = Object.entries(this.recipe).filter(([, items]) => items.length).map(([category, items]) =>
        `<section class="recipe-category"><h3>${LABELS[category]}</h3><div class="recipe-items">${items.map(item =>
          `<span class="recipe-chip">${escapeHTML(item.text)}${item.grammar ? ` <small>(${escapeHTML(item.grammar)})</small>` : ''}<button type="button" data-remove-recipe="${item.id}" data-category="${category}" aria-label="Remove ${escapeHTML(item.text)}">×</button></span>`).join('')}</div></section>`).join('');
      if (!this.promptDirty) this.resetPrompt();
      else {
        const editor = this.element.querySelector('[data-prompt-editor]');
        editor.value = syncPromptIngredients(editor.value, this.recipe, this.promptTarget);
      }
      this.updateInstructions();
      this.element.querySelectorAll('[data-use-slot]').forEach(button => {
        const slot = this.slots[button.dataset.category]?.find(item => item.id === Number(button.dataset.useSlot));
        if (slot) button.setAttribute('aria-pressed', String(this.recipe[slot.category].some(item => item.text === phrase(slot.parts))));
      });
      const buttons = this.element.querySelectorAll('[data-munge]');
      buttons.forEach(button => { button.disabled = !populated || this.generating; });
      if (!this.generating) {
        buttons.forEach(button => { button.textContent = `MUNGE ${button.dataset.mungeTarget}`; });
        const status = this.element.querySelector('[data-munge-status]');
        if (!populated) status.textContent = 'Choose at least one ingredient to MUNGE.';
        else if (!status.classList.contains('is-error')) status.textContent = 'Ready to turn this recipe into a miniature story.';
      }
    }

    currentPrompt() {
      return this.element.querySelector('[data-prompt-editor]')?.value || '';
    }

    resetPrompt() {
      const editor = this.element.querySelector('[data-prompt-editor]');
      if (!editor) return;
      editor.value = buildPrompt(this.recipe, this.promptTarget);
      this.promptDirty = false;
      this.resizePromptEditor();
    }

    resizePromptEditor() {
      const editor = this.element.querySelector('[data-prompt-editor]');
      if (!editor) return;
      editor.style.height = 'auto';
      editor.style.height = `${editor.scrollHeight}px`;
    }

    async nominateStory() {
      const story = this.element.querySelector('[data-build-story]')?.value.trim();
      if (!story) return;
      const sequence = root.creationContext?.().sequence;
      const isCurrent = () => root.creationContext?.().sequence === sequence &&
        this.element.querySelector('[data-build-story]')?.value.trim() === story;
      const button = this.element.querySelector('[data-build-nominate]');
      button.disabled = true; button.textContent = 'NOMINATING…';
      try {
        if (!root.creationActions?.hasDraft?.()) {
          const data = await requestBuildDraft(this.fetcher, this.element.dataset.draftUrl, story,
            this.generatedHeadline, this.headlineStory);
          if (!isCurrent()) {
            // Bank the clicked snapshot, never attach an old draft to the new story.
            await root.creationActions.nominate({rewrite_id: data.rewrite_id, sequence,
              text: {crazyReplacement1Title: data.crazyReplacement1Title || '',
                crazyReplacement1Extract: story}});
            return;
          }
          root.creationActions?.attachDraft?.(data);
        }
        if (typeof root.creationActions?.nominate !== 'function') {
          throw new Error('Nomination controls are unavailable. Please reload and try again.');
        }
        root.creationActions.nominate();
      } catch (error) {
        if (!isCurrent()) return;
        const status = this.element.querySelector('[data-munge-status]');
        status.classList.add('is-error');
        status.textContent = error.message || 'Nomination failed. Your story is still here.';
        button.disabled = false; button.textContent = 'NOMINATE';
      }
    }

    async generateStory(targetWords) {
      if (this.checkingAdoption) return;
      this.checkingAdoption = true;
      try {
        if (root.adoptionAccess && !await root.adoptionAccess.ensure()) return;
      } finally { this.checkingAdoption = false; }
      const populated = Object.values(this.recipe).some(items => items.length);
      if (!populated || this.generating) return;
      this.generating = true;
      this.promptTarget = targetWords;
      const editor = this.element.querySelector('[data-prompt-editor]');
      editor.value = applyStoryLength(syncPromptIngredients(editor.value, this.recipe, targetWords), targetWords);
      this.resizePromptEditor();
      const buttons = this.element.querySelectorAll('[data-munge]');
      const button = this.element.querySelector(`[data-munge-target="${targetWords}"]`);
      const status = this.element.querySelector('[data-munge-status]');
      buttons.forEach(item => { item.disabled = true; }); button.textContent = 'MUNGING…';
      status.classList.remove('is-error');
      status.textContent = 'Munging your ingredients into fresh nonsense…';
      this.generateController?.abort();
      this.generateController = new AbortController();
      const timeout = root.setTimeout(() => this.generateController?.abort(), 35000);
      try {
        const generated = await requestBuildStory(this.fetcher, this.element.dataset.generateUrl, this.recipe,
          targetWords, this.currentPrompt(), this.generateController.signal, this.furtherInstructions());
        root.creationActions?.reset?.();
        this.generatedHeadline = generated.headline;
        this.headlineStory = generated.story;
        displayBuildStory(this.element, generated.story);
        root.updateCopyButton?.();
        const nominate = this.element.querySelector('[data-build-nominate]');
        nominate.hidden = false; nominate.disabled = false; nominate.textContent = 'NOMINATE';
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

  const api = {syncPromptIngredients, parseCSV, weightedStructure, phrase, buildPrompt, applyStoryLength, serialiseRecipe, requestBuildStory, displayBuildStory, requestBuildDraft, BuildWorkshop, mount,
    DEFAULT_CREATIVE_PROMPT, STUFF_STRUCTURES, STUFF_WEIGHTS, SWEAR_STRUCTURES, INITIAL_COUNTS, FLICK_COUNT, FLICK_DELAY};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  root.NewsMuncherBuild = api;
  if (root.document) root.document.querySelectorAll('[data-build-workshop]').forEach(element => mount(element));
})(typeof window !== 'undefined' ? window : globalThis);
