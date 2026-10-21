(function (root) {
    'use strict';

    const CATEGORIES = ['bijv_nw', 'gilles', 'zelfs_nw', 'handelend'];
    const STRUCTURES = [
        ['bijv_nw', 'gilles', 'zelfs_nw'],
        ['bijv_nw', 'gilles', 'handelend'],
        ['bijv_nw', 'zelfs_nw', 'handelend'],
        ['gilles', 'zelfs_nw'],
        ['gilles', 'handelend'],
        ['zelfs_nw', 'handelend']
    ];

    function parseVocabularyCSV(text, categories = CATEGORIES) {
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
                row = [];
                continue;
            }
            field += char;
        }
        const vocabulary = Object.fromEntries(categories.map(category => [category, []]));
        const seen = Object.fromEntries(categories.map(category => [category, new Set()]));
        for (const columns of rows.slice(1)) {
            if (columns.length !== 2) continue;
            const category = columns[0].trim(), word = columns[1].trim();
            if (!categories.includes(category) || !word || seen[category].has(word)) continue;
            seen[category].add(word); vocabulary[category].push(word);
        }
        return vocabulary;
    }

    function parseCSV(text) { return parseVocabularyCSV(text, CATEGORIES); }

    async function copyPlainText(text, {
        clipboard = root.navigator?.clipboard,
        document = root.document
    } = {}) {
        if (!text) return false;
        if (clipboard?.writeText) {
            try { await clipboard.writeText(text); return true; }
            catch (_) {} // Continue to the same-origin legacy fallback.
        }
        if (!document?.body || typeof document.execCommand !== 'function') return false;
        const field = document.createElement('textarea');
        field.value = text; field.readOnly = true;
        field.style.position = 'fixed'; field.style.opacity = '0';
        document.body.appendChild(field); field.select();
        let copied = false;
        try { copied = document.execCommand('copy') === true; }
        catch (_) { copied = false; }
        field.remove();
        return copied;
    }

    class SwearGenerator {
        constructor(vocabulary, {
            random = Math.random,
            schedule = (callback, delay) => setTimeout(callback, delay),
            cancel = timer => clearTimeout(timer),
            reducedMotion = () => !!root.matchMedia?.('(prefers-reduced-motion: reduce)').matches,
            flickCount = 5,
            flickDelay = 100,
            retryLimit = 64,
            exactLimit = 10000,
            usedLimit = 2000,
            initialUsed = [],
            onUsed = () => {},
            display = () => {}
            , structures = STRUCTURES,
            structureWeights = null,
            emptyError = 'The swear vocabulary has no complete phrase structures.'
        } = {}) {
            this.vocabulary = vocabulary;
            this.random = random;
            this.schedule = schedule;
            this.cancelTimer = cancel;
            this.reducedMotion = reducedMotion;
            this.flickCount = flickCount;
            this.flickDelay = flickDelay;
            this.retryLimit = retryLimit;
            this.exactLimit = exactLimit;
            this.usedLimit = usedLimit;
            this.onUsed = onUsed;
            this.display = display;
            this.structures = structures;
            this.structureWeights = Array.isArray(structureWeights) &&
                structureWeights.length === structures.length ? structureWeights : null;
            this.emptyError = emptyError;
            this.used = new Set(initialUsed.filter(value => typeof value === 'string').slice(-usedLimit));
            this.timers = new Set();
            this.generation = 0;
            this.slots = [];
            this.busy = false;
            this.totalCombinations = this.structures.reduce((total, structure) =>
                total + structure.reduce((product, category) =>
                    product * (vocabulary[category]?.length || 0), 1), 0);
        }
        validStructures() {
            return this.structures.filter(structure => structure.every(category => this.vocabulary[category]?.length));
        }
        key(slots) { return slots.map(slot => slot.word).join('\u001f'); }
        pick(values) { return values[Math.floor(this.random() * values.length)]; }
        pickStructure(structures = this.validStructures()) {
            if (!this.structureWeights) return this.pick(structures);
            const weighted = structures.map(structure => ({
                structure,
                weight: Math.max(0, Number(this.structureWeights[this.structures.indexOf(structure)]) || 0)
            }));
            const total = weighted.reduce((sum, entry) => sum + entry.weight, 0);
            if (!total) return this.pick(structures);
            let target = this.random() * total;
            for (const entry of weighted) {
                target -= entry.weight;
                if (target < 0) return entry.structure;
            }
            return weighted[weighted.length - 1].structure;
        }
        candidate(structure = this.pickStructure()) {
            return structure.map(category => ({category, word: this.pick(this.vocabulary[category])}));
        }
        findExactUnused(structures) {
            if (this.totalCombinations > this.exactLimit) return null;
            for (const structure of structures) {
                const slots = [];
                const visit = index => {
                    if (index === structure.length) return this.used.has(this.key(slots))
                        ? null : slots.map(slot => ({...slot}));
                    for (const word of this.vocabulary[structure[index]]) {
                        slots.push({category: structure[index], word});
                        const found = visit(index + 1);
                        slots.pop();
                        if (found) return found;
                    }
                    return null;
                };
                const found = visit(0);
                if (found) return found;
            }
            return null;
        }
        selectPhrase() {
            const structures = this.validStructures();
            if (!structures.length) throw new Error(this.emptyError);
            if (this.used.size >= this.totalCombinations) this.used.clear();
            for (let attempt = 0; attempt < this.retryLimit; attempt++) {
                const slots = this.candidate();
                if (!this.used.has(this.key(slots))) return slots;
            }
            const exact = this.findExactUnused(structures);
            if (exact) return exact;
            // Large spaces use bounded retries. Clearing guarantees progress without
            // enumerating millions of combinations or claiming perfect detection.
            this.used.clear();
            return this.candidate();
        }
        cancel() {
            if (this.pendingReject) this.pendingReject(new DOMException('Generation replaced.', 'AbortError'));
            this.pendingReject = null;
            this.generation++;
            for (const timer of this.timers) this.cancelTimer(timer);
            this.timers.clear();
            this.busy = false;
        }
        wait(callback, delay, generation) {
            const timer = this.schedule(() => {
                this.timers.delete(timer);
                if (generation === this.generation) callback();
            }, delay);
            this.timers.add(timer);
        }
        animateSlot(index, target, generation, onOverlap, onDone) {
            const values = this.vocabulary[target.category], recent = new Set();
            let iteration = 0;
            const flick = () => {
                if (generation !== this.generation) return;
                if (iteration >= this.flickCount) { onDone(); return; }
                const final = iteration === this.flickCount - 1;
                let word = target.word;
                if (!final) {
                    let choices = values.filter(value => value !== target.word && !recent.has(value));
                    if (!choices.length) { recent.clear(); choices = values.filter(value => value !== target.word); }
                    if (choices.length) word = this.pick(choices);
                }
                recent.add(word);
                this.display({index, word, category: target.category, final, slots: this.slots});
                iteration++;
                if (iteration === this.flickCount - Math.floor(this.flickCount / 2)) onOverlap();
                this.wait(flick, this.flickDelay, generation);
            };
            flick();
        }
        finish(slots) {
            this.slots = slots.map(slot => ({...slot}));
            const key = this.key(this.slots);
            if (this.used.size >= Math.min(this.usedLimit, this.totalCombinations)) this.used.clear();
            this.used.add(key);
            this.onUsed(Array.from(this.used));
            this.busy = false;
            this.pendingReject = null;
            return this.phrase();
        }
        phrase() {
            const text = this.slots.map(slot => slot.word).join(' ');
            return text ? text[0].toUpperCase() + text.slice(1) : '';
        }
        generate() {
            this.cancel();
            const generation = this.generation, slots = this.selectPhrase();
            this.busy = true; this.slots = slots.map(slot => ({...slot}));
            if (this.reducedMotion()) {
                slots.forEach((slot, index) => this.display({index, word: slot.word,
                    category: slot.category, final: true, slots: this.slots}));
                return Promise.resolve(this.finish(slots));
            }
            return new Promise((resolve, reject) => {
                this.pendingReject = reject;
                const start = index => this.animateSlot(index, slots[index], generation,
                    () => { if (index + 1 < slots.length) start(index + 1); },
                    () => { if (index === slots.length - 1) resolve(this.finish(slots)); });
                start(0);
            });
        }
        replacement(index) {
            const current = this.slots[index];
            if (!current || this.busy) return Promise.resolve(this.phrase());
            const values = this.vocabulary[current.category];
            if (!values?.length) return Promise.resolve(this.phrase());
            let target = current.word;
            for (let attempt = 0; attempt < this.retryLimit; attempt++) {
                const proposed = this.pick(values);
                const slots = this.slots.map(slot => ({...slot}));
                slots[index].word = proposed;
                if (proposed !== current.word && !this.used.has(this.key(slots))) {
                    target = proposed; break;
                }
                if (values.length > 1 && target === current.word) target = proposed;
            }
            if (values.length > 1 && target === current.word)
                target = values.find(value => value !== current.word) || current.word;
            const generation = this.generation;
            this.busy = true;
            if (this.reducedMotion()) {
                this.slots[index].word = target;
                this.display({index, word: target, category: current.category, final: true, slots: this.slots});
                return Promise.resolve(this.finish(this.slots));
            }
            return new Promise((resolve, reject) => {
                this.pendingReject = reject;
                this.animateSlot(index, {category: current.category, word: target},
                    generation, () => {}, () => {
                        this.slots[index].word = target;
                        resolve(this.finish(this.slots));
                    });
            });
        }
    }

    async function mountGenerator(element, {
        fetcher = (url, options) => fetch(url, options),
        categories = CATEGORIES,
        structures = STRUCTURES,
        selectorPrefix = 'swear',
        storageKey = 'newsmuncher.swearGenerator.used',
        slotClass = 'swear-word-slot',
        errorClass = 'swear-generator-error',
        Generator = SwearGenerator
    } = {}) {
        const generate = element.querySelector(`[data-${selectorPrefix}-generate]`);
        const copy = element.querySelector(`[data-${selectorPrefix}-copy]`);
        const output = element.querySelector(`[data-${selectorPrefix}-output]`);
        const status = element.querySelector(`[data-${selectorPrefix}-status]`);
        const renderSlot = ({index, word, category, final}) => {
            let button = output.children[index];
            if (!button) {
                button = document.createElement('button');
                button.type = 'button'; button.className = slotClass;
                output.appendChild(button);
            }
            button.textContent = index === 0 && word ? word[0].toUpperCase() + word.slice(1) : word;
            button.dataset.category = category;
            button.disabled = !final;
        };
        let copyTimer = null;
        const resetCopy = () => {
            clearTimeout(copyTimer); copyTimer = null; copy.textContent = 'COPY';
        };
        generate.disabled = true; copy.disabled = true; status.textContent = 'Loading vocabulary…';
        try {
            const response = await fetcher(element.dataset.vocabulary, {cache: 'no-store'});
            if (!response.ok) throw new Error('Vocabulary could not be loaded.');
            const vocabulary = parseVocabularyCSV(await response.text(), categories);
            let initialUsed = [];
            try { initialUsed = JSON.parse(root.sessionStorage?.getItem(storageKey) || '[]'); }
            catch (_) { initialUsed = []; }
            if (!Array.isArray(initialUsed)) initialUsed = [];
            const generator = new Generator(vocabulary, {
                structures,
                display: renderSlot, initialUsed,
                onUsed: values => {
                    try { root.sessionStorage?.setItem(storageKey, JSON.stringify(values)); }
                    catch (_) {} // Privacy/storage restrictions do not disable generation.
                }
            });
            generate.disabled = false; status.textContent = '';
            generate.addEventListener('click', async () => {
                resetCopy(); generate.disabled = true; copy.disabled = true;
                output.replaceChildren(); status.textContent = 'Generating…';
                try { await generator.generate(); status.textContent = ''; copy.disabled = false; }
                catch (error) { if (error.name !== 'AbortError') status.textContent = error.message; }
                finally { generate.disabled = false; }
            });
            copy.addEventListener('click', async () => {
                if (copy.disabled || generator.busy) return;
                const phrase = generator.phrase();
                copy.disabled = true;
                if (await copyPlainText(phrase)) {
                    copy.textContent = 'COPIED';
                    copyTimer = setTimeout(() => { copy.textContent = 'COPY'; copy.disabled = false; }, 1200);
                } else copy.disabled = false;
            });
            output.addEventListener('click', async event => {
                const button = event.target.closest(`.${slotClass}`);
                if (!button || button.disabled || generator.busy) return;
                const index = Array.from(output.children).indexOf(button);
                resetCopy(); generate.disabled = true; copy.disabled = true;
                button.disabled = true; status.textContent = 'Replacing word…';
                await generator.replacement(index);
                status.textContent = ''; generate.disabled = false; copy.disabled = false;
                Array.from(output.children).forEach(slot => { slot.disabled = false; });
            });
            return generator;
        } catch (error) {
            status.textContent = error.message || 'Vocabulary could not be loaded.';
            element.classList.add(errorClass);
            throw error;
        }
    }

    async function mount(element, fetcher = (url, options) => fetch(url, options)) {
        return mountGenerator(element, {fetcher});
    }

    const api = {CATEGORIES, STRUCTURES, parseCSV, parseVocabularyCSV, copyPlainText,
        SwearGenerator, mountGenerator, mount};
    if (typeof module !== 'undefined' && module.exports) module.exports = api;
    root.NewsMuncherSwearGenerator = api;
    if (root.document) root.document.querySelectorAll('[data-swear-generator]').forEach(element => mount(element));
})(typeof window !== 'undefined' ? window : globalThis);
