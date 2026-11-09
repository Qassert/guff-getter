/* Adoption status always comes from the server; sessionStorage holds work only. */
(function (root) {
    'use strict';
    class AdoptionAccess {
        constructor({storage, fetcher, location, notify}) {
            Object.assign(this, {storage, fetcher, location, notify});
            this.mode = null;
            this.adapter = null;
        }
        register(mode, adapter) { this.mode = mode; this.adapter = adapter; }
        key() { return `newsmuncher.work.v1.${this.mode}`; }
        save() {
            if (!this.adapter) return true;
            try {
                this.storage.setItem(this.key(), JSON.stringify(this.adapter.snapshot()));
                return true;
            } catch (_) {
                this.notify('Your browser could not save this draft. Stay on this page and retry; your current work is still here.');
                return false;
            }
        }
        read() {
            try { return JSON.parse(this.storage.getItem(this.key()) || 'null'); }
            catch (_) { return null; }
        }
        restore() {
            if (!this.adapter) return false;
            try {
                const value = this.read();
                if (!value) return false;
                this.adapter.restore(value);
                return true;
            } catch (_) { return false; }
        }
        redirect(url) {
            // Only the existing same-origin adoption experience is a valid destination.
            if (!/^\/pets\/view_pets\?next=/.test(url || '')) return false;
            if (!this.save()) return false;
            this.location.assign(url);
            return true;
        }
        async ensure() {
            try {
                const next = this.location.pathname + (this.location.search || '');
                const response = await this.fetcher('/pets/adoption-status?next=' + encodeURIComponent(next),
                    {credentials: 'same-origin', cache: 'no-store'});
                if (!response.ok) throw new Error('status unavailable');
                const result = await response.json();
                if (result.adopted === true) return true;
                this.redirect(result.adoption_url);
            } catch (_) {
                this.notify('Could not check your pet. Your work is still here; please retry.');
            }
            return false;
        }
    }
    if (typeof module !== 'undefined') module.exports = {AdoptionAccess};
    if (!root.document) return;
    const notify = message => {
        let panel = root.document.getElementById('adoptionMessage');
        if (!panel) {
            panel = root.document.createElement('p');
            panel.id = 'adoptionMessage'; panel.setAttribute('role', 'alert');
            root.document.getElementById('main-content').prepend(panel);
        }
        panel.textContent = message;
    };
    // Accessing sessionStorage itself can throw in privacy-restricted browsers.
    const storage = {getItem: key => root.sessionStorage.getItem(key),
        setItem: (key, value) => root.sessionStorage.setItem(key, value)};
    const access = root.adoptionAccess = new AdoptionAccess({storage,
        fetcher: (...args) => root.fetch(...args), location: root.location, notify});
    root.addEventListener('pagehide', () => access.save());
    root.addEventListener('pageshow', event => { if (event.persisted && /^\/(build\/?$|create\/?$|pets\/pet_profile\/|promotion-gallery\/?$)/.test(root.location.pathname)) access.ensure(); });
    root.document.addEventListener('input', () => access.save());
    root.document.addEventListener('change', () => access.save());
    root.document.addEventListener('click', event => {
        if (event.target.closest?.('.mode-nav-button[href]') && !access.save()) event.preventDefault();
    }, true);
})(typeof window !== 'undefined' ? window : globalThis);
