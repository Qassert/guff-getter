/* Centralised metadata line beneath the generated image.
   Renders: IMAGE STYLE: <x> - MUSIC GENRE: <y> - VOICE: <z>
   Omits any segment whose value is absent, along with its separator.
   No network calls; no generation; display only. */
(function (root) {
    'use strict';
    class CreationMeta {
        constructor(getEl) {
            this._get = getEl;
            this._style = '';
            this._genre = '';
            this._voice = '';
        }
        setStyle(value) { this._style = (value || '').trim(); this._render(); }
        setGenre(value) { this._genre = (value || '').trim(); this._render(); }
        setVoice(value) { this._voice = (value || '').trim(); this._render(); }
        reset() { this._style = ''; this._genre = ''; this._voice = ''; this._render(); }
        _render() {
            const el = this._get('creationMeta');
            if (!el) return;
            const parts = [];
            if (this._style) parts.push('IMAGE STYLE: ' + this._style.toUpperCase());
            if (this._genre) parts.push('MUSIC GENRE: ' + this._genre.toUpperCase());
            if (this._voice) parts.push('VOICE: ' + this._voice.toUpperCase());
            const text = parts.join(' \u2013 ');
            el.textContent = text;
            el.hidden = !text;
        }
    }
    if (typeof module !== 'undefined') module.exports = {CreationMeta};
    if (typeof document === 'undefined') return;
    root.creationMeta = new CreationMeta(id => document.getElementById(id));
})(typeof globalThis !== 'undefined' ? globalThis : this);
