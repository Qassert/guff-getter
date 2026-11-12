/* Explicitly opted-in parchment text shares one helper; no generation calls. */
(function(root) {
    'use strict';
    const KEY = 'newsmuncher.madHelper.enabled';
    const choose = (items, previous, random = Math.random) => {
        const pool = items.filter(item => item !== previous);
        return (pool.length ? pool : items)[Math.floor(random() * (pool.length || items.length))];
    };
    const idleDelay = (duration, frequency, random = Math.random) =>
        duration * 1000 * (1 - frequency) / frequency * (.6 + .8 * random());

    const anchorOf = text => {const value = Number(text.dataset.madHelperAnchor ?? .5); return Number.isFinite(value) && value >= 0 && value <= 1 ? value : .5;};
    const contentOf = text => typeof text.value === 'string' ? text.value : (text.textContent || '');
    const discoverPlacements = doc => Array.from(doc.querySelectorAll('[data-mad-helper-text]'), text => ({
        text, dock: text.dataset.madHelperDock ? doc.querySelector(text.dataset.madHelperDock) : null, anchor: anchorOf(text), vertical: text.dataset.madHelperVertical || 'text', flip: text.dataset.madHelperFlip === 'true', paper: text.closest('[data-mad-helper-paper]'),
        avoid: text.dataset.madHelperAvoid ? Array.from(doc.querySelectorAll(text.dataset.madHelperAvoid)) : []
    })).filter(placement => placement.paper);

    const dockMargin = (naturalTop, textBottom, width, mobile) => mobile ? 12 : Math.max(-width * .4, textBottom + 12 - naturalTop);

    function avoidControls(geometry, obstacles, gap = 12) {
        const result = {...geometry}, half = result.width / 2;
        for (const box of obstacles) {
            if (result.x + half <= box.left || result.x - half >= box.right ||
                    result.y + half + gap <= box.top || result.y - half - (result.bubbleExtra || 0) - gap >= box.bottom) continue;
            const above = box.top - half - gap, below = box.bottom + half + gap + (result.bubbleExtra || 0);
            result.y = above - half - (result.bubbleExtra || 0) >= 4 && Math.abs(above - geometry.y) < Math.abs(below - geometry.y) ? above : below;
        }
        return result;
    }

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

    function placementGeometry({paper, text, padding = 0, textHeight, viewportWidth, size = 217.6, gap = 10, anchor = .5, vertical = 'text', scrollY = 0}) {
        // On narrow screens shift inward just enough to keep the outer half reachable.
        const width = Math.min(size, viewportWidth < 620 ? size * 76 / 128 : size);
        const x = Math.max(paper.left, width / 2 + 4) + (vertical === 'paper-start' ? 65 : 0);
        const y = vertical === 'paper-start' && viewportWidth >= 621
            ? Math.max(paper.top + scrollY + width * .36, width / 2 + 12) - scrollY
            : text.top + Math.min(text.height, textHeight || text.height) * anchor;
        return {width, x, y,
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
                     bubbleText = 'SQUIRT', bubbleDuration = 2500, size = 217.6, gap = 10, position = placementGeometry,
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
            for (const {paper, text, dock = null, avoid = [], anchor = .5, vertical = 'text', flip = false} of placements) {
                const host = doc.createElement('div'); host.className = 'mad-helper-place'; host.classList.toggle('mad-helper-flipped', flip); host.classList.toggle('mad-helper-docked', !!dock); host.hidden = true;
                const button = doc.createElement('button'); button.type = 'button'; button.className = 'mad-helper-button'; button.setAttribute('aria-label', 'Mad Helper: ' + bubbleText);
                const image = doc.createElement('img'); image.src = png; image.alt = ''; image.draggable = false;
                const bubble = doc.createElement('span'); bubble.className = 'mad-helper-bubble'; bubble.textContent = bubbleText; bubble.hidden = true;
                button.append(image); host.append(button, bubble); doc.body.append(host);
                const node = {paper, text, dock, avoid, anchor, vertical, host, button, image, bubble, padding: text.style.paddingLeft,
                    basePadding: parseFloat(root.getComputedStyle(text).paddingLeft) || 0};
                button.addEventListener('click', () => this.click(node)); this.nodes.push(node);
            }
            this.scheduleLayout = () => {
                if (!this.enabled || this.doc.hidden || this.frame) return;
                this.frame = root.requestAnimationFrame(() => {
                    this.frame = null; this.layout();
                    if (this.nodes.some(node => node.moving)) this.scheduleLayout();
                });
            };
            this.visibility = () => {
                if (doc.hidden) {for (const node of this.nodes) node.moving = false; if (this.frame) root.cancelAnimationFrame(this.frame); this.frame = null; this.cycle.stop(); this.stopPlayback(); this.hideBubble(); this.stopSound();}
                else {this.scheduleLayout(); this.cycle.schedule();}
            };
            this.motionStart = event => {
                const node = this.nodes.find(node => node.paper === event.target);
                if (node) {node.moving = true; this.scheduleLayout();}
            };
            this.motionEnd = event => {
                for (const node of this.nodes) if (node.paper === event.target) node.moving = false;
                this.scheduleLayout();
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
            for (const key of ['fontFamily','fontSize','fontWeight','fontStyle','lineHeight','letterSpacing','wordSpacing','textIndent','tabSize','whiteSpace','wordBreak','overflowWrap']) mirror.style[key] = style[key];
            const padding = (parseFloat(style.paddingLeft) || 0) + (parseFloat(style.paddingRight) || 0);
            mirror.style.width = Math.max(1, text.clientWidth - padding) + 'px';
            mirror.textContent = contentOf(text) || ' ';
            return {height: mirror.getBoundingClientRect().height, top: parseFloat(style.paddingTop) || 0,
                bottom: parseFloat(style.paddingBottom) || 0};
        }
        layout() {
            if (!this.enabled) return;
            for (const node of this.nodes) {
                const {paper, text, host} = node, rect = text.getBoundingClientRect();
                if (!rect.width || !rect.height || !text.getClientRects().length) {host.hidden = true; continue;}
                const measured = this.measure(text);
                let geometry = avoidControls({...this.position({paper:paper.getBoundingClientRect(), text:{left:rect.left, top:rect.top+measured.top,
                    height:Math.max(0, text.clientHeight-measured.top-measured.bottom)}, padding:node.basePadding,
                    textHeight:contentOf(text) ? measured.height : null, viewportWidth:root.innerWidth, size:this.size, gap:this.gap, anchor:node.anchor, vertical:node.vertical, scrollY:root.scrollY}), bubbleExtra:52},
                    node.avoid.filter(element => element.getClientRects().length).map(element => element.getBoundingClientRect()));
                if (node.dock) {
                    const dock = node.dock, width = geometry.width;
                    dock.parentElement.style.setProperty('--mad-helper-dock-size', width + 'px');
                    const baseRight = dock.getBoundingClientRect().right - (node.dockShift || 0);
                    const shift = Math.max(0, paper.getBoundingClientRect().right - 24 - baseRight);
                    if (Math.abs(shift - (node.dockShift || 0)) > .5) {
                        node.dockShift = shift; dock.style.transform = `translateX(${shift}px)`;
                    }
                    const oldMargin = parseFloat(dock.style.marginTop) || 0;
                    const naturalTop = dock.getBoundingClientRect().top - oldMargin;
                    const textBottom = rect.top + measured.top + Math.min(measured.height, text.clientHeight - measured.top - measured.bottom);
                    const margin = dockMargin(naturalTop, textBottom, width, root.innerWidth < 621);
                    if (Math.abs(margin - oldMargin) > .5) dock.style.marginTop = margin + 'px';
                    const box = dock.getBoundingClientRect();
                    geometry = {...geometry, x:box.left + width / 2, y:box.top + width / 2, clearance:0};
                }
                const padding = node.basePadding + geometry.clearance;
                if (Math.abs((parseFloat(text.style.paddingLeft)||0) - padding) > .5) {
                    text.style.paddingLeft = padding + 'px'; root.autoResize?.(text); this.scheduleLayout();
                }
                host.style.setProperty('--mad-helper-size', geometry.width + 'px');
                host.classList.toggle('mad-helper-bubble-below', geometry.y - geometry.width / 2 < 56);
                host.style.width = geometry.width + 'px'; host.style.height = geometry.width + 'px';
                host.style.left = geometry.x + root.scrollX + 'px'; host.style.top = geometry.y + root.scrollY + 'px';
                host.hidden = false;
            }
            if (this.owner?.host.hidden) {this.stopPlayback(); this.hideBubble(); this.stopSound();}
            if (!this.visible().length) this.cycle.stop();
            else if (!this.cycle.timer && !this.owner) this.cycle.schedule();
        }
        listen(enabled) {
            const method = enabled ? 'addEventListener' : 'removeEventListener';
            for (const name of ['resize','scroll']) root[method](name, this.onLayout, {passive:true});
            this.doc[method]('input', this.onLayout, true);
            this.doc[method]('visibilitychange', this.visibility);
            for (const paper of new Set(this.nodes.map(node => node.paper))) {
                paper[method]('animationstart', this.motionStart);
                paper[method]('animationend', this.motionEnd);
                paper[method]('animationcancel', this.motionEnd);
                paper[method]('transitionend', this.onLayout);
            }
            if (enabled) {
                this.resizeObserver = new root.ResizeObserver(this.onLayout);
                this.mutationObserver = new root.MutationObserver(this.onLayout);
                for (const node of this.nodes) {
                    this.resizeObserver.observe(node.text); this.resizeObserver.observe(node.paper);
                    if (node.dock) this.resizeObserver.observe(node.dock);
                    // Do not observe the udder/rotor subtree, which animates independently.
                    for (const target of new Set([node.paper, node.text, node.text.parentElement])) {
                        this.mutationObserver.observe(target, {attributes:true, attributeFilter:['style','class','hidden'],
                            childList:target === node.text, characterData:target === node.text, subtree:target === node.text});
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
                node.host.hidden = true; node.moving = false;
                if (!this.enabled) {
                    if (node.dock) {node.dock.style.marginTop = ''; node.dock.style.transform = ''; node.dockShift = 0; node.dock.parentElement.style.removeProperty('--mad-helper-dock-size');}
                    node.text.style.paddingLeft = node.padding; root.autoResize?.(node.text);
                }
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
            const assetURL = name => {const url = new URL(name, base); if (manifest.revision) url.searchParams.set('v', manifest.revision); return url.href;};
            const animations = manifest.animations.map(clip => ({...clip,
                webm:assetURL(clip.webm), fallback:assetURL(clip.fallback)}));
            const helper = new MadHelper({png:assetURL(manifest.png), animations, toggle,
                sounds: JSON.parse(toggle.dataset.sounds), placements:discoverPlacements(root.document)});
            root.NewsMuncherMadHelper = helper;
            // Probe once, only on an enabled helper. WebP remains the conservative default.
            if (helper.enabled) helper.alpha = await supportsAlpha(new URL('alpha-probe.webm', base));
            root.addEventListener('pagehide', () => {for (const node of helper.nodes) node.moving = false; if (helper.frame) root.cancelAnimationFrame(helper.frame); helper.frame = null; helper.cycle.stop(); helper.stopPlayback(); helper.stopSound(); helper.hideBubble();});
            root.addEventListener('pageshow', () => {helper.scheduleLayout(); helper.cycle.schedule();});
        } catch (_) {toggle.checked = false; toggle.disabled = true; toggle.title = 'Mad Helper assets could not be loaded';}
    }
    const api = {MadHelper, AnimationCycle, placementGeometry, avoidControls, discoverPlacements, anchorOf, dockMargin, contentOf, choose, idleDelay, supportsAlpha, KEY};
    root.NewsMuncherMadHelperComponent = api;
    if (typeof module !== 'undefined') module.exports = api;
    if (root.document) mount();
})(typeof window !== 'undefined' ? window : globalThis);
