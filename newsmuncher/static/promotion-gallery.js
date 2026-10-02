/* Stored nominations only; never calls a generation endpoint. */
(function (root) {
    'use strict';
    const creatorEditUrl = (base, rewriteId) => rewriteId
        ? base + '?rewrite_id=' + encodeURIComponent(rewriteId) : base;
    class GalleryMedia {
        constructor({makeAudio = () => new Audio(), status = () => {}} = {}) {
            this.makeAudio = makeAudio;
            this.status = status;
            this.generation = 0;
            this.players = [];
            this.starting = false;
        }
        stop() {
            this.generation++;
            for (const player of this.players) {
                player.pause();
                player.removeAttribute('src');
                player.load(); // Aborts pending network/decode/play for the old item.
            }
            this.players = [];
            this.starting = false;
            this.status({available: false, blocked: false});
        }
        prepare(urls) {
            const generation = this.generation;
            this.index = 0;
            for (const url of urls) {
                const player = this.makeAudio();
                player.preload = 'auto';
                player.src = url;
                player.addEventListener('playing', () => {
                    if (generation !== this.generation) player.pause();
                });
                player.addEventListener('ended', () => {
                    // Only the active track's natural end may advance this page.
                    if (generation !== this.generation ||
                        this.players[this.index] !== player || !player.ended) return;
                    this.index++;
                    this.starting = false;
                    if (this.index < this.players.length) this.play();
                });
                this.players.push(player);
            }
        }
        activate(item) {
            this.stop();
            this.prepare([item.jingle_url, item.narration_url].filter(Boolean));
            this.status({available: this.players.length > 0, blocked: false});
            return this.play();
        }
        async play() {
            const player = this.players[this.index];
            if (this.starting || !player) return;
            const generation = this.generation;
            this.starting = true;
            let blocked = false;
            try {
                await player.play();
                if (generation !== this.generation) player.pause();
            } catch (error) {
                blocked = error.name === 'NotAllowedError';
            }
            // A previous track's late promise must not update the next track's UI.
            if (generation !== this.generation || this.players[this.index] !== player) return;
            this.starting = false;
            this.status({available: true, blocked});
        }
        pause() {
            // STOP discards pending starts. PLAY restarts the current track, keeping
            // only its remaining sequence (never replaying an already-ended jingle).
            const urls = this.players.slice(this.index).map(player => player.src);
            this.stop();
            this.prepare(urls);
            this.status({available: this.players.length > 0, blocked: true});
        }
    }
    class GalleryVideo {
        constructor({makeVideo = () => document.createElement('video'), mount = () => {}, reveal = () => {},
                     reduced = () => !!root.matchMedia?.('(prefers-reduced-motion: reduce)').matches,
                     schedule = (fn, delay) => setTimeout(fn, delay),
                     cancel = (timer) => clearTimeout(timer)} = {}) {
            Object.assign(this, {makeVideo, mount, reveal, reduced, schedule, cancel});
            this.generation = 0;
        }
        stop() {
            this.generation++;
            this.cancel(this.timer);
            if (this.player) {
                this.player.pause(); this.player.removeAttribute('src'); this.player.load(); this.player.remove();
                this.player = null;
            }
            this.reveal(false);
        }
        activate(item, imageReady = Promise.resolve(true)) {
            this.stop();
            if (!item.image_url || !item.video_url || this.reduced()) return;
            const generation = this.generation;
            Promise.resolve(imageReady).then(loaded => {
                if (!loaded || generation !== this.generation || this.reduced()) return;
                // Count the delay from the still's load, so a slow image is shown first.
                this.timer = this.schedule(() => this.play(item.video_url, generation), 1500);
            }).catch(() => {}); // Failed still images retain the existing text-only fallback.
        }
        async play(url, generation) {
            if (generation !== this.generation || this.reduced()) return;
            const player = this.makeVideo();
            this.player = player;
            player.muted = true; player.defaultMuted = true; player.playsInline = true;
            player.loop = true; player.preload = 'auto'; player.src = url;
            player.setAttribute('aria-hidden', 'true');
            player.addEventListener('playing', () => {
                if (generation !== this.generation) { player.pause(); return; }
                if (this.reduced()) { this.stop(); return; }
                this.reveal(true); // Fade only when decoded frames are actually playing.
            });
            player.addEventListener('error', () => { if (generation === this.generation) this.stop(); });
            this.mount(player);
            try {
                await player.play();
                if (generation !== this.generation) player.pause();
            } catch (_) {
                if (generation === this.generation) this.stop(); // Keep the still on autoplay failure.
            }
        }
    }
    class GalleryBackdrop {
        constructor({makeVideo = () => document.createElement('video'), mount = () => {},
                     showImage = () => {}, reveal = () => {},
                     reduced = () => !!root.matchMedia?.('(prefers-reduced-motion: reduce)').matches} = {}) {
            Object.assign(this, {makeVideo, mount, showImage, reveal, reduced});
            this.generation = 0;
        }
        clearVideo() {
            this.generation++;
            if (this.player) {
                this.player.pause(); this.player.removeAttribute('src'); this.player.load(); this.player.remove();
                this.player = null;
            }
            this.reveal(false);
        }
        stop() {
            this.clearVideo();
            this.showImage(null);
        }
        activate(item) {
            this.stop();
            this.showImage(item.image_url || null);
            if (!item.video_url || this.reduced()) return;
            const generation = this.generation, player = this.makeVideo();
            this.player = player;
            player.muted = true; player.defaultMuted = true; player.playsInline = true;
            player.loop = true; player.controls = false; player.preload = 'auto';
            player.setAttribute('aria-hidden', 'true');
            const fail = () => { if (generation === this.generation) this.clearVideo(); };
            player.addEventListener('playing', () => {
                if (generation !== this.generation) { player.pause(); return; }
                if (this.reduced()) { this.clearVideo(); return; }
                this.reveal(true);
            });
            player.addEventListener('error', fail);
            this.mount(player);
            player.src = item.video_url;
            player.load();
            try {
                Promise.resolve(player.play()).then(() => {
                    if (generation !== this.generation) player.pause();
                }).catch(fail);
            } catch (_) { fail(); }
        }
    }
    class PromotionGallery {
        constructor({view, fetcher = (url, options) => fetch(url, options), afterDisplay = () => Promise.resolve(), media = new GalleryMedia(), visual = new GalleryVideo(), backdrop = new GalleryBackdrop()}) {
            this.view = view;
            this.media = media;
            this.visual = visual;
            this.backdrop = backdrop;
            this.fetcher = fetcher;
            this.afterDisplay = afterDisplay;
            this.sequence = 0;
            this.current = null;
            this.receipt = null;
            this.acknowledging = null;
        }
        async request(path, options = {}) {
            const response = await this.fetcher('/promotion-gallery' + path, {
                credentials: 'same-origin', cache: 'no-store', ...options,
                headers: {'Content-Type': 'application/json', 'X-Gallery-Request': '1'}
            });
            if (!response.ok) {
                const error = new Error(response.status === 401
                    ? 'Please sign in again to open the Promotion Gallery.'
                    : 'The collection could not be loaded. Please try again.');
                error.status = response.status;
                throw error;
            }
            return response.json();
        }
        acknowledge() {
            if (this.acknowledging) return this.acknowledging;
            if (!this.receipt) return Promise.resolve();
            const token = this.receipt;
            this.acknowledging = this.request('/displayed', {
                method: 'POST', body: JSON.stringify({view_token: token})
            }).then(() => { if (this.receipt === token) this.receipt = null; })
                .catch(error => {
                    // Deleted items and expired receipts must not strand navigation.
                    if ([404, 409].includes(error.status) && this.receipt === token) this.receipt = null;
                    throw error;
                })
                .finally(() => { this.acknowledging = null; });
            return this.acknowledging;
        }
        async next() {
            const sequence = ++this.sequence;
            this.media.stop();
            this.visual.stop();
            this.backdrop.stop();
            if (this.abort) this.abort.abort();
            this.abort = new AbortController();
            this.view.loading();
            try {
                // Do not select again until the previous displayed item is counted.
                await this.acknowledge();
                if (sequence !== this.sequence) return;
                const previous = this.current ? '?previous=' + encodeURIComponent(this.current.id) : '';
                const data = await this.request('/next' + previous, {signal: this.abort.signal});
                if (sequence !== this.sequence) return;
                this.current = data.item;
                if (!data.item) { this.view.empty(); return; }
                this.view.show(data.item);
                this.backdrop.activate(data.item);
                await this.afterDisplay();
                if (sequence !== this.sequence) return;
                this.media.activate(data.item);
                this.visual.activate(data.item, this.view.imageReady);
                this.receipt = data.view_token;
                await this.acknowledge();
            } catch (error) {
                if (sequence === this.sequence && error.name !== 'AbortError') this.view.error(error.message);
            }
        }
        async promote() {
            const item = this.current, sequence = this.sequence;
            if (!item || item.promoted || this.promoting) return;
            this.promoting = true;
            this.view.promoting(true);
            try {
                await this.request('/items/' + item.id + '/promote', {method: 'POST'});
                if (sequence === this.sequence) {
                    item.promoted = true;
                    this.view.promoted();
                }
            } catch (error) {
                if (sequence === this.sequence) this.view.error(error.message);
            } finally {
                this.promoting = false;
                if (sequence === this.sequence) this.view.promoting(false);
            }
        }
        leave() {
            this.sequence++;
            this.media.stop();
            this.visual.stop();
            this.backdrop.stop();
            if (this.abort) this.abort.abort();
        }
    }
    root.PromotionGallery = PromotionGallery;
    if (typeof module !== 'undefined') module.exports = {PromotionGallery, GalleryMedia, GalleryVideo, GalleryBackdrop, creatorEditUrl};
    if (typeof document === 'undefined' || !document.getElementById('galleryPage')) return;
    const get = id => document.getElementById(id);
    const page = get('galleryPage'), status = get('galleryStatus'), promote = get('galleryPromote');
    const edit = get('galleryEdit'), creationUrl = document.querySelector('.promotion-gallery').dataset.creationUrl;
    const view = {
        loading() { status.textContent = 'Turning the page…'; promote.disabled = true; page.setAttribute('aria-busy', 'true'); },
        empty() { page.hidden = true; page.setAttribute('aria-busy', 'false'); status.textContent = 'The collection is waiting for its first nomination. Head back to NewsMuncher to nominate a creation.'; },
        show(item) {
            get('galleryBody').textContent = item.body || 'No saved text for this creation.';
            get('galleryPromoted').hidden = !item.promoted;
            promote.textContent = item.promoted ? 'PROMOTED' : 'PROMOTE';
            promote.disabled = item.promoted;
            edit.hidden = !item.rewrite_id;
            edit.href = creatorEditUrl(creationUrl, item.rewrite_id);
            // A fresh image prevents a late error from an old URL hiding the new page.
            const image = document.createElement('img');
            image.id = 'galleryImage'; image.alt = ''; image.decoding = 'async';
            get('galleryImage').replaceWith(image);
            this.imageReady = new Promise(resolve => {
                image.addEventListener('load', () => resolve(true), {once: true});
                image.addEventListener('error', () => resolve(false), {once: true});
                if (!item.image_url) resolve(false);
            });
            image.addEventListener('error', () => {
                if (get('galleryImage') === image) {
                    get('galleryIllustration').hidden = true;
                    page.classList.remove('has-image');
                }
            });
            page.classList.toggle('has-image', !!item.image_url);
            get('galleryIllustration').hidden = !item.image_url;
            if (item.image_url) image.src = item.image_url;
            page.hidden = false;
            page.classList.remove('turning');
            void page.offsetWidth;
            page.classList.add('turning');
            page.setAttribute('aria-busy', 'false');
            status.textContent = '';
        },
        error(message) { status.textContent = message; page.setAttribute('aria-busy', 'false'); },
        promoting(busy) { promote.disabled = busy || !!gallery.current?.promoted; },
        promoted() { get('galleryPromoted').hidden = false; promote.textContent = 'PROMOTED'; promote.disabled = true; }
    };
    const afterDisplay = () => new Promise(resolve => {
        const painted = () => requestAnimationFrame(() => requestAnimationFrame(resolve));
        if (!document.hidden) painted();
        else document.addEventListener('visibilitychange', function visible() {
            if (!document.hidden) { document.removeEventListener('visibilitychange', visible); painted(); }
        });
    });
    const media = new GalleryMedia({status({available, blocked}) {
        get('galleryAudio').hidden = !available;
        get('galleryPlayAudio').hidden = !blocked;
        get('galleryAudioStatus').textContent = blocked ? 'Press PLAY AUDIO to listen.' : 'Saved audio';
    }});
    const visual = new GalleryVideo({
        mount(player) { get('galleryIllustration').appendChild(player); },
        reveal(playing) {
            get('galleryIllustration').classList.toggle('animation-playing', playing);
        }
    });
    const backdropElement = get('galleryBackdrop'), backdropImage = get('galleryBackdropImage');
    const backdrop = new GalleryBackdrop({
        mount(player) { backdropElement.appendChild(player); },
        showImage(url) {
            backdropImage.hidden = !url;
            if (url) backdropImage.src = url;
            else backdropImage.removeAttribute('src');
        },
        reveal(playing) { backdropElement.classList.toggle('animation-playing', playing); }
    });
    const motionPreference = window.matchMedia('(prefers-reduced-motion: reduce)');
    motionPreference.addEventListener('change', event => {
        if (event.matches) { visual.stop(); backdrop.clearVideo(); }
    });
    const gallery = new PromotionGallery({view, afterDisplay, media, visual, backdrop});
    get('galleryPlayAudio').addEventListener('click', () => media.play());
    get('galleryStopAudio').addEventListener('click', () => media.pause());
    page.addEventListener('animationend', () => page.classList.remove('turning'));
    get('galleryNext').addEventListener('click', () => gallery.next());
    promote.addEventListener('click', () => gallery.promote());
    window.addEventListener('pagehide', () => gallery.leave());
    gallery.next();
})(typeof globalThis !== 'undefined' ? globalThis : this);
