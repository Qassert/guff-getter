/* CREATE opts in; the component itself is reusable and has no generation calls. */
(function(root) {
    'use strict';
    const KEY = 'newsmuncher.madHelper.enabled';
    const choose = (items, previous, random = Math.random) => {
        const pool = items.filter(item => item !== previous);
        return (pool.length ? pool : items)[Math.floor(random() * (pool.length || items.length))];
    };
    const idleDelay = (duration, frequency, random = Math.random) =>
        duration * 1000 * (1 - frequency) / frequency * (.6 + .8 * random());

    class AnimationCycle {
        constructor({clips, frequency = .2, random = Math.random, timers = root,
                     onPlay, onIdle = () => {}, canRun = () => true}) {
            if (!clips.length || frequency <= 0 || frequency >= 1) throw new TypeError('Invalid helper animation configuration');
            Object.assign(this, {clips, frequency, random, timers, onPlay, onIdle, canRun});
        }
        stop() { this.timers.clearTimeout(this.timer); this.timer = null; }
        schedule() {
            this.stop();
            if (!this.canRun()) return;
            const next = choose(this.clips, this.previous, this.random);
            this.timer = this.timers.setTimeout(() => this.play(next), idleDelay(next.duration, this.frequency, this.random));
        }
        play(clip) {
            this.stop();
            if (!this.canRun()) return;
            this.previous = clip;
            this.onPlay(clip);
        }
        trigger() { this.play(choose(this.clips, this.previous, this.random)); }
        complete() { this.onIdle(); this.schedule(); }
    }

    function placementGeometry({paper, text, padding = 0, textHeight, viewportWidth, size = 128, gap = 10}) {
        // On narrow screens shift inward just enough to keep the outer half reachable.
        const width = Math.min(size, viewportWidth < 620 ? 76 : size);
        const x = Math.max(paper.left, width / 2 + 4);
        return {width, x, y: text.top + Math.min(text.height, textHeight || text.height) / 2,
            clearance: Math.max(0, x + width / 2 + gap - text.left - padding)};
    }

    // canPlayType alone is insufficient: Safari can decode WebM without its alpha.
    async function supportsAlpha(url, doc = root.document) {
        const video = doc.createElement('video');
        video.muted = true; video.playsInline = true; video.preload = 'auto';
        return new Promise(resolve => {
            let done = false;
            const finish = value => {
                if (done) return; done = true; root.clearTimeout(timeout);
                video.pause(); video.removeAttribute('src'); video.load(); resolve(value);
            };
            const timeout = root.setTimeout(() => finish(false), 2500);
            video.onloadeddata = () => {
                try {
                    const canvas = doc.createElement('canvas'); canvas.width = canvas.height = 2;
                    const context = canvas.getContext('2d', {willReadFrequently: true});
                    context.drawImage(video, 0, 0, 2, 2);
                    finish(context.getImageData(0, 0, 1, 1).data[3] < 10);
                } catch (_) { finish(false); }
            };
            video.onerror = () => finish(false);
            video.src = url; video.load();
        });
    }

    class MadHelper {
        constructor({png, animations, placements, toggle, sounds = [], frequency = .2,
                     bubbleText = 'SQUIRT', bubbleDuration = 2500, size = 128, gap = 10, position = placementGeometry,
                     enabled = true, alpha = false, storage, doc = root.document,
                     random = Math.random, reducedMotion = root.matchMedia?.('(prefers-reduced-motion: reduce)').matches} = {}) {
            if (storage === undefined) {try {storage = root.localStorage;} catch (_) {storage = null;}}
            Object.assign(this, {png, animations, placements, toggle, sounds, bubbleText,
                bubbleDuration, size, gap, position, alpha, storage, doc, random, reducedMotion});
            this.voices = new Map(); this.nodes = []; this.token = 0;
            this.cycle = new AnimationCycle({clips: animations, frequency, random,
                canRun: () => this.enabled && !this.doc.hidden && !this.reducedMotion && this.visible().length > 0,
                onPlay: clip => this.play(clip, this.clicked || choose(this.visible(), null, random)),
                onIdle: () => this.stopPlayback()});
            this.video = doc.createElement('video');
            this.video.muted = this.video.defaultMuted = true;
            this.video.playsInline = true; this.video.preload = 'none';
            this.video.className = 'mad-helper-animation'; this.video.hidden = true;
            this.fallback = doc.createElement('img'); this.fallback.alt = ''; this.fallback.className = 'mad-helper-animation'; this.fallback.hidden = true;
            this.mirror = doc.createElement('div'); this.mirror.className = 'mad-helper-measure'; this.mirror.setAttribute('aria-hidden', 'true'); doc.body.append(this.mirror);
            for (const {paper, text} of placements) {
                const host = doc.createElement('div'); host.className = 'mad-helper-place'; host.hidden = true;
                const button = doc.createElement('button'); button.type = 'button'; button.className = 'mad-helper-button'; button.setAttribute('aria-label', 'Mad Helper: ' + bubbleText);
                const image = doc.createElement('img'); image.src = png; image.alt = ''; image.draggable = false;
                const bubble = doc.createElement('span'); bubble.className = 'mad-helper-bubble'; bubble.textContent = bubbleText; bubble.hidden = true;
                button.append(image); host.append(button, bubble); doc.body.append(host);
                const node = {paper, text, host, button, image, bubble, padding: text.style.paddingLeft,
                    basePadding: parseFloat(root.getComputedStyle(text).paddingLeft) || 0};
                button.addEventListener('click', () => this.click(node)); this.nodes.push(node);
            }
            this.scheduleLayout = () => {
                if (!this.enabled || this.doc.hidden || this.frame) return;
                this.frame = root.requestAnimationFrame(() => {this.frame = null; this.layout();});
            };
            this.visibility = () => {
                if (doc.hidden) {if (this.frame) root.cancelAnimationFrame(this.frame); this.frame = null; this.cycle.stop(); this.stopPlayback(); this.hideBubble(); this.stopSound();}
                else {this.scheduleLayout(); this.cycle.schedule();}
            };
            this.change = () => this.setEnabled(toggle.checked);
            toggle.addEventListener('change', this.change);
            this.onLayout = () => this.scheduleLayout();
            let preferred = enabled;
            try {const saved = storage?.getItem(KEY); if (saved != null) preferred = saved !== 'false';} catch (_) {}
            this.setEnabled(preferred, false);
        }
        visible() {
            return this.nodes.filter(node => !node.host.hidden && node.text.getBoundingClientRect().bottom > 0 && node.text.getBoundingClientRect().top < root.innerHeight);
        }
        measure(text) {
            const style = root.getComputedStyle(text), mirror = this.mirror;
            for (const key of ['fontFamily','fontSize','fontWeight','fontStyle','lineHeight','letterSpacing','wordSpacing','textIndent','tabSize']) mirror.style[key] = style[key];
            const padding = (parseFloat(style.paddingLeft) || 0) + (parseFloat(style.paddingRight) || 0);
            mirror.style.width = Math.max(1, text.clientWidth - padding) + 'px';
            mirror.textContent = text.value || ' ';
            return {height: mirror.getBoundingClientRect().height, top: parseFloat(style.paddingTop) || 0,
                bottom: parseFloat(style.paddingBottom) || 0};
        }
        layout() {
            if (!this.enabled) return;
            for (const node of this.nodes) {
                const {paper, text, host} = node, rect = text.getBoundingClientRect();
                if (!rect.width || !rect.height || !text.getClientRects().length) {host.hidden = true; continue;}
                const measured = this.measure(text);
                const geometry = this.position({paper:paper.getBoundingClientRect(), text:{left:rect.left, top:rect.top+measured.top,
                    height:Math.max(0, text.clientHeight-measured.top-measured.bottom)}, padding:node.basePadding,
                    textHeight:text.value ? measured.height : null, viewportWidth:root.innerWidth, size:this.size, gap:this.gap});
                const padding = node.basePadding + geometry.clearance;
                if (Math.abs((parseFloat(text.style.paddingLeft)||0) - padding) > .5) {
                    text.style.paddingLeft = padding + 'px'; root.autoResize?.(text); this.scheduleLayout();
                }
                host.style.width = geometry.width + 'px'; host.style.height = geometry.width + 'px';
                host.style.left = geometry.x + root.scrollX + 'px'; host.style.top = geometry.y + root.scrollY + 'px';
                host.hidden = false;
            }
            if (!this.cycle.timer && !this.owner && this.visible().length) this.cycle.schedule();
        }
        listen(enabled) {
            const method = enabled ? 'addEventListener' : 'removeEventListener';
            for (const name of ['resize','scroll']) root[method](name, this.onLayout, {passive:true});
            this.doc[method]('input', this.onLayout, true);
            this.doc[method]('visibilitychange', this.visibility);
            if (enabled) {
                this.resizeObserver = new root.ResizeObserver(this.onLayout);
                this.mutationObserver = new root.MutationObserver(this.onLayout);
                for (const node of this.nodes) {
                    this.resizeObserver.observe(node.text); this.resizeObserver.observe(node.paper);
                    // Do not observe the udder/rotor subtree, which animates independently.
                    for (const target of new Set([node.paper, node.text, node.text.parentElement])) {
                        this.mutationObserver.observe(target, {attributes:true, attributeFilter:['style','class','hidden']});
                    }
                }
                this.doc.fonts?.ready.then(this.onLayout).catch(() => {});
            } else {this.resizeObserver?.disconnect(); this.mutationObserver?.disconnect();}
        }
        setEnabled(enabled, persist = true) {
            this.enabled = !!enabled; this.toggle.checked = this.enabled;
            this.doc.body?.classList?.toggle('mad-helper-enabled', this.enabled);
            if (persist) {try {this.storage?.setItem(KEY, String(this.enabled));} catch (_) {}}
            this.cycle.stop(); this.stopPlayback(); this.hideBubble(); this.stopSound();
            this.listen(false);
            if (this.frame) root.cancelAnimationFrame(this.frame); this.frame = null;
            for (const node of this.nodes) {
                node.host.hidden = true;
                if (!this.enabled) {node.text.style.paddingLeft = node.padding; root.autoResize?.(node.text);}
            }
            if (this.enabled) {this.listen(true); this.scheduleLayout();}
        }
        stopSound() {
            this.sound?.pause(); if (this.sound) {try {this.sound.currentTime = 0;} catch (_) {}}
        }
        hideBubble() {
            root.clearTimeout(this.bubbleTimer);
            for (const node of this.nodes) node.bubble.hidden = true;
        }
        click(node) {
            if (!this.enabled || this.doc.hidden) return;
            this.hideBubble(); this.stopSound(); this.clicked = node;
            // Explicit clicks remain interactive with reduced motion; autonomous playback does not.
            this.cycle.stop(); this.cycle.previous = choose(this.animations, this.cycle.previous, this.random);
            this.play(this.cycle.previous, node); this.clicked = null;
            node.bubble.hidden = false; this.bubbleTimer = root.setTimeout(() => this.hideBubble(), this.bubbleDuration);
            if (this.sounds.length) {
                const url = choose(this.sounds, this.previousSound, this.random); this.previousSound = url;
                if (!this.voices.has(url)) {const audio = new root.Audio(url); audio.preload = 'auto'; this.voices.set(url, audio);}
                this.sound = this.voices.get(url);
                try {this.sound.currentTime = 0; this.sound.play().catch(() => {});} catch (_) {}
            }
        }
        stopPlayback() {
            this.token++; root.clearTimeout(this.playTimer); root.clearTimeout(this.watchdog);
            this.video.onplaying = this.video.onended = this.video.onerror = null;
            this.video.pause(); this.video.removeAttribute('src'); this.video.load(); this.video.hidden = true;
            this.fallback.onload = this.fallback.onerror = null; this.fallback.removeAttribute('src'); this.fallback.hidden = true;
            if (this.owner) this.owner.image.style.visibility = '';
            this.owner = null;
        }
        play(clip, node) {
            this.stopPlayback();
            if (!node || !this.enabled || this.doc.hidden) {this.cycle.schedule(); return;}
            const token = this.token; this.owner = node;
            const current = () => token === this.token && this.enabled && !this.doc.hidden;
            const complete = () => {if (current()) this.cycle.complete();};
            const show = element => {if (current()) {node.image.style.visibility = 'hidden'; element.hidden = false;}};
            let fallbackStarted = false;
            const fallback = () => {
                if (!current() || fallbackStarted) return;
                fallbackStarted = true;
                this.video.pause(); this.video.hidden = true; node.image.style.visibility = '';
                node.button.append(this.fallback);
                this.fallback.onload = () => {if (!current()) return; show(this.fallback); this.playTimer = root.setTimeout(complete, clip.duration * 1000);};
                this.fallback.onerror = complete; this.fallback.src = clip.fallback;
            };
            this.watchdog = root.setTimeout(complete, clip.duration * 1000 + 8000);
            if (!this.alpha) {fallback(); return;}
            node.button.append(this.video);
            this.video.onplaying = () => {if (!fallbackStarted) show(this.video);}; this.video.onended = complete; this.video.onerror = fallback;
            this.video.src = clip.webm;
            try {this.video.play().catch(fallback);} catch (_) {fallback();}
        }
        destroy() {
            this.setEnabled(false, false); this.toggle.removeEventListener('change', this.change);
            for (const node of this.nodes) node.host.remove(); this.mirror.remove();
        }
    }

    async function mount() {
        const toggle = root.document.querySelector('[data-mad-helper-toggle]');
        if (!toggle) return;
        try {
            const base = new URL(toggle.dataset.assets, root.document.baseURI);
            const response = await root.fetch(new URL('manifest.json', base));
            if (!response.ok) throw new Error('Helper manifest unavailable');
            const manifest = await response.json();
            const animations = manifest.animations.map(clip => ({...clip,
                webm:new URL(clip.webm, base).href, fallback:new URL(clip.fallback, base).href}));
            const helper = new MadHelper({png:new URL(manifest.png, base).href, animations, toggle,
                sounds: JSON.parse(toggle.dataset.sounds), placements:[
                    {paper:root.document.querySelector('.profile-container'), text:root.document.getElementById('sourceBodyDraft')},
                    {paper:root.document.getElementById('outputContainer'), text:root.document.getElementById('responseBodyDraft')}
                ]});
            root.NewsMuncherMadHelper = helper;
            // Probe once, only on an enabled helper. WebP remains the conservative default.
            if (helper.enabled) helper.alpha = await supportsAlpha(new URL('alpha-probe.webm', base));
            root.addEventListener('pagehide', () => {helper.cycle.stop(); helper.stopPlayback(); helper.stopSound(); helper.hideBubble();});
            root.addEventListener('pageshow', () => {helper.scheduleLayout(); helper.cycle.schedule();});
        } catch (_) {toggle.checked = false; toggle.disabled = true; toggle.title = 'Mad Helper assets could not be loaded';}
    }
    const api = {MadHelper, AnimationCycle, placementGeometry, choose, idleDelay, supportsAlpha, KEY};
    root.NewsMuncherMadHelperComponent = api;
    if (typeof module !== 'undefined') module.exports = api;
    if (root.document) mount();
})(typeof window !== 'undefined' ? window : globalThis);
