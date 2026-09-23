/* Stored nominations only; never calls a generation endpoint. */
(function (root) {
    'use strict';
    class PromotionGallery {
        constructor({view, fetcher = fetch, afterDisplay = () => Promise.resolve()}) {
            this.view = view;
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
            if (this.abort) this.abort.abort();
        }
    }
    root.PromotionGallery = PromotionGallery;
    if (typeof module !== 'undefined') module.exports = {PromotionGallery};
    if (typeof document === 'undefined' || !document.getElementById('galleryPage')) return;
    const get = id => document.getElementById(id);
    const page = get('galleryPage'), status = get('galleryStatus'), promote = get('galleryPromote');
    const view = {
        loading() { status.textContent = 'Turning the page…'; promote.disabled = true; page.setAttribute('aria-busy', 'true'); },
        empty() { page.hidden = true; status.textContent = 'The collection is waiting for its first nomination. Head back to NewsMuncher to nominate a creation.'; },
        show(item) {
            get('galleryTitle').textContent = item.title || 'Untitled creation';
            get('galleryBody').textContent = item.body || 'No saved text for this creation.';
            get('galleryPromoted').hidden = !item.promoted;
            promote.textContent = item.promoted ? 'PROMOTED' : 'PROMOTE';
            promote.disabled = item.promoted;
            const image = get('galleryImage');
            image.removeAttribute('src');
            get('galleryIllustration').hidden = !item.image_url;
            if (item.image_url) image.src = item.image_url;
            page.hidden = false;
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
    const gallery = new PromotionGallery({view, afterDisplay});
    get('galleryImage').addEventListener('error', () => { get('galleryIllustration').hidden = true; });
    get('galleryNext').addEventListener('click', () => gallery.next());
    promote.addEventListener('click', () => gallery.promote());
    window.addEventListener('pagehide', () => gallery.leave());
    gallery.next();
})(typeof globalThis !== 'undefined' ? globalThis : this);
