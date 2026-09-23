/* Stored nominations only; never calls a generation endpoint. */
(function (root) {
    'use strict';
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
        activate(item) {
            this.stop();
            const generation = this.generation;
            for (const url of [item.jingle_url, item.narration_url].filter(Boolean)) {
                const player = this.makeAudio();
                player.preload = 'auto';
                player.src = url;
                player.addEventListener('playing', () => {
                    if (generation !== this.generation) player.pause();
                });
                this.players.push(player);
            }
            this.status({available: this.players.length > 0, blocked: false});
            return this.play();
        }
        async play() {
            if (this.starting || !this.players.length) return;
            const generation = this.generation;
            this.starting = true;
            // Both calls occur in this same event turn; neither waits for the other.
            const starts = this.players.map(player => {
                try {
                    return Promise.resolve(player.play()).then(() => {
                        if (generation !== this.generation) player.pause();
                        return false;
                    }, error => generation === this.generation && error.name === 'NotAllowedError');
                } catch (error) {
                    return Promise.resolve(error.name === 'NotAllowedError');
                }
            });
            const blocked = await Promise.all(starts);
            if (generation !== this.generation) return;
            this.starting = false;
            this.status({available: true, blocked: blocked.some(Boolean)});
        }
        pause() {
            // Keep this page's URLs so a deliberate PLAY AUDIO can resume them.
            this.generation++;
            this.players.forEach(player => player.pause());
            // Pending starts must not revive playback after the user stops it.
            const urls = this.players.map(player => player.src);
            this.players.forEach(player => { player.removeAttribute('src'); player.load(); });
            this.players = [];
            this.starting = false;
            const generation = this.generation;
            for (const url of urls) {
                const player = this.makeAudio();
                player.src = url;
                player.addEventListener('playing', () => {
                    if (generation !== this.generation) player.pause();
                });
                this.players.push(player);
            }
            this.status({available: this.players.length > 0, blocked: true});
        }
    }
    class PromotionGallery {
        constructor({view, fetcher = fetch, afterDisplay = () => Promise.resolve(), media = new GalleryMedia()}) {
            this.view = view;
            this.media = media;
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
            if (!response.ok) throw new Error(response.status === 401
                ? 'Please sign in again to open the Promotion Gallery.'
                : 'The collection could not be loaded. Please try again.');
            return response.json();
        }
        acknowledge() {
            if (this.acknowledging) return this.acknowledging;
            if (!this.receipt) return Promise.resolve();
            const token = this.receipt;
            this.acknowledging = this.request('/displayed', {
                method: 'POST', body: JSON.stringify({view_token: token})
            }).then(() => { if (this.receipt === token) this.receipt = null; })
                .finally(() => { this.acknowledging = null; });
            return this.acknowledging;
        }
        async next() {
            const sequence = ++this.sequence;
            this.media.stop();
            if (this.abort) this.abort.abort();
            this.abort = new AbortController();
            this.view.loading();
            try {
                // Do not select again until the previous displayed item is counted.
                await this.acknowledge();
                if (sequence !== this.sequence) return;
                const data = await this.request('/next', {signal: this.abort.signal});
                if (sequence !== this.sequence) return;
                this.current = data.item;
                if (!data.item) { this.view.empty(); return; }
                this.view.show(data.item);
                await this.afterDisplay();
                if (sequence !== this.sequence) return;
                this.media.activate(data.item);
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
            if (this.abort) this.abort.abort();
        }
    }
    root.PromotionGallery = PromotionGallery;
    if (typeof module !== 'undefined') module.exports = {PromotionGallery, GalleryMedia};
    if (typeof document === 'undefined' || !document.getElementById('galleryPage')) return;
    const get = id => document.getElementById(id);
    const page = get('galleryPage'), status = get('galleryStatus'), promote = get('galleryPromote');
    const view = {
        loading() { status.textContent = 'Turning the page…'; promote.disabled = true; page.setAttribute('aria-busy', 'true'); },
        empty() { page.hidden = true; page.setAttribute('aria-busy', 'false'); status.textContent = 'The collection is waiting for its first nomination. Head back to NewsMuncher to nominate a creation.'; },
        show(item) {
            get('galleryTitle').textContent = item.title || 'Untitled creation';
            get('galleryBody').textContent = item.body || 'No saved text for this creation.';
            get('galleryPromoted').hidden = !item.promoted;
            promote.textContent = item.promoted ? 'PROMOTED' : 'PROMOTE';
            promote.disabled = item.promoted;
            // A fresh image prevents a late error from an old URL hiding the new page.
            const image = document.createElement('img');
            image.id = 'galleryImage'; image.alt = ''; image.decoding = 'async';
            get('galleryImage').replaceWith(image);
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
    const gallery = new PromotionGallery({view, afterDisplay, media});
    get('galleryPlayAudio').addEventListener('click', () => media.play());
    get('galleryStopAudio').addEventListener('click', () => media.pause());
    page.addEventListener('animationend', () => page.classList.remove('turning'));
    get('galleryNext').addEventListener('click', () => gallery.next());
    promote.addEventListener('click', () => gallery.promote());
    window.addEventListener('pagehide', () => gallery.leave());
    gallery.next();
})(typeof globalThis !== 'undefined' ? globalThis : this);
