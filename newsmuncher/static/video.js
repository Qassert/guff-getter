/* Only ANIMATE IMAGE posts. Restore, polling and preview are retrieval-only. */
(function (root) {
    'use strict';
    // Same lifecycle as GalleryVideo: keep the still until playing, invalidate late
    // events/promises on stop, and unload old media. No generation/network API here.
    class CreationVideo {
        constructor({makeVideo, hasImage, mount, reveal, reduced, status = () => {}}) {
            Object.assign(this, {makeVideo, hasImage, mount, reveal, reduced, status});
            this.generation = 0;
        }
        clearPlayer() {
            this.generation++;
            if (this.player) {
                this.player.pause(); this.player.removeAttribute('src'); this.player.load(); this.player.remove();
                this.player = null;
            }
            this.reveal(false);
        }
        stop() {
            this.clearPlayer();
            this.url = null;
            this.attempted = false;
        }
        show(url) {
            if (!url || url === this.url) return;
            this.stop();
            this.url = url;
            this.ready();
        }
        ready() {
            if (!this.url || this.attempted || this.reduced() || !this.hasImage()) return;
            this.attempted = true;
            const generation = this.generation, player = this.makeVideo();
            this.player = player;
            player.muted = true; player.defaultMuted = true; player.playsInline = true;
            player.loop = true; player.controls = false; player.preload = 'auto';
            player.setAttribute('aria-hidden', 'true');
            const fail = () => {
                if (generation !== this.generation) return;
                this.clearPlayer(); // Keep attempted/url: another status read cannot retry playback.
                this.status('Animation saved; showing the still image.');
            };
            let starting = false;
            const play = async () => {
                if (generation !== this.generation || starting) return;
                if (this.reduced()) { this.clearPlayer(); return; }
                starting = true;
                try {
                    await player.play();
                    if (generation !== this.generation) player.pause();
                } catch (_) { fail(); }
            };
            player.addEventListener('canplay', play);
            player.addEventListener('playing', () => {
                if (generation !== this.generation) { player.pause(); return; }
                if (this.reduced()) { this.clearPlayer(); return; }
                this.reveal(true);
            });
            player.addEventListener('error', fail);
            this.mount(player);
            player.src = this.url;
            player.load();
            if (player.readyState >= 3) play();
        }
    }
    class AnimationUI {
        constructor({view, fetcher = (url, options) => fetch(url, options),
                     schedule = (fn, delay) => setTimeout(fn, delay),
                     cancel = (timer) => clearTimeout(timer)}) {
            Object.assign(this, {view, fetcher, schedule, cancel});
            this.revision = 0;
            this.key = null;
            this.pending = false;
        }
        async request(method, key) {
            const response = await this.fetcher('/videos/' + encodeURIComponent(key), {
                method, credentials: 'same-origin', cache: 'no-store',
                headers: {'X-Gallery-Request': '1'}
            });
            if (!response.ok) throw new Error(response.status === 401
                ? 'Sign in to your pet again to animate this image.'
                : 'Animation unavailable. Your rewrite and image are unchanged.');
            return response.json();
        }
        render(state) {
            this.state = state;
            this.view.render({...state, nominated: this.nominated}, this.pending);
        }
        stop() {
            this.revision++;
            this.cancel(this.timer);
            this.key = null;
            this.nominated = false;
            this.pending = false;
            this.state = null;
            this.view.stop();
        }
        async show(data) {
            this.stop();
            if (!data?.rewrite_id) { this.render({}); return; }
            this.nominated = data.nominated === true;
            this.key = data.rewrite_id;
            this.render({message: 'Checking saved animation…'});
            this.lookup = this.refresh(this.revision);
            await this.lookup;
        }
        async refresh(token, polls = 0) {
            const key = this.key;
            if (!key || token !== this.revision) return;
            try {
                const result = await this.request('GET', key);
                if (token !== this.revision) return;
                this.render(result);
                if (['queued', 'started'].includes(result.video_status) && polls < 360) {
                    this.cancel(this.timer);
                    this.timer = this.schedule(() => this.refresh(token, polls + 1), 5000);
                }
            } catch (error) {
                if (token === this.revision) this.render({message: error.message});
            }
        }
        snapshot() { return {...this.state, pending: this.pending}; }
        async ensure() {
            const token = this.revision;
            await this.lookup;
            if (token !== this.revision || this.state?.video_url || this.pending || ['queued', 'started'].includes(this.state?.video_status)) return;
            await this.act();
        }
        async act() {
            if (!this.nominated || !this.key || this.pending || !this.state?.can_generate) return;
            const key = this.key, token = this.revision;
            this.pending = true;
            this.render(this.state);
            try {
                const result = await this.request('POST', key);
                if (token !== this.revision) return;
                this.pending = false;
                this.render(result);
                if (['queued', 'started'].includes(result.video_status)) await this.refresh(token);
            } catch (error) {
                if (token !== this.revision) return;
                this.pending = false;
                this.render({message: error.message + ' Checking saved status; no generation retry.'});
                // Recover a lost POST response with GET only, never another submission.
                await this.refresh(token);
            }
        }
    }
    if (typeof module !== 'undefined') module.exports = {AnimationUI, CreationVideo};
    if (typeof document === 'undefined' || !document.getElementById('animationControls')) return;
    const get = id => document.getElementById(id);
    const visual = new CreationVideo({
        makeVideo: () => document.createElement('video'),
        hasImage: () => !!get('imagePanel').querySelector('.generated-image.loaded'),
        mount(player) { player.className = 'creation-animation'; get('imagePanel').appendChild(player); },
        reveal(playing) {
            get('imagePanel').classList.toggle('animation-playing', playing);
        },
        reduced: () => !!root.matchMedia?.('(prefers-reduced-motion: reduce)').matches,
        status(message) { get('animationMessage').textContent = message; }
    });
    root.videoUI = new AnimationUI({view: {
        stop() {
            visual.stop();
        },
        render(data, pending) {
            const busy = pending || ['queued', 'started'].includes(data.video_status);
            const ready = !!data.video_url;
            const failed = data.video_status === 'failed_or_uncertain';
            const button = get('animationButton');
            get('animationControls').hidden = !data.nominated || !(data.can_generate || busy || ready || failed || data.message);
            button.hidden = ready || failed || (!busy && !data.can_generate);
            button.disabled = busy || !data.can_generate;
            button.textContent = busy ? 'ANIMATING…' : 'ANIMATE IMAGE';
            get('animationMessage').textContent = ready ? 'ANIMATION READY' : failed
                ? 'ANIMATION FAILED — operator review needed; no regeneration.'
                : data.message || (busy ? 'Animating your image. You can leave this page.'
                    : 'Optional: one 5-second animation, approximately $0.05. Uses the saved rewritten scene.');
            if (ready) visual.show(data.video_url);
        }
    }});
    root.videoUI.imageReady = () => visual.ready();
    root.matchMedia?.('(prefers-reduced-motion: reduce)').addEventListener('change', event => {
        if (event.matches) visual.clearPlayer();
    });
    get('animationButton').addEventListener('click', () => root.videoUI.act());
    root.addEventListener('pagehide', () => root.videoUI.stop());
})(typeof globalThis !== 'undefined' ? globalThis : this);
