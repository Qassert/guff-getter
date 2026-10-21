/* One persistent mute authority for every NewsMuncher audio path. */
(function (root) {
    'use strict';
    const STORAGE_KEY = 'newsmuncher.masterMuted';

    class MasterAudioController {
        constructor({storage = root.localStorage, MediaClass = root.HTMLMediaElement,
                     documentRef = root.document} = {}) {
            this.storage = storage; this.MediaClass = MediaClass; this.document = documentRef;
            this.media = new Set(); this.mediaState = new WeakMap(); this.gains = new Set();
            this.muted = this.read();
            this.patchPlayback();
        }
        read() {
            try { return this.storage?.getItem(STORAGE_KEY) === 'true'; }
            catch (_) { return false; }
        }
        persist() {
            try { this.storage?.setItem(STORAGE_KEY, String(this.muted)); }
            catch (_) {}
        }
        patchPlayback() {
            const prototype = this.MediaClass?.prototype;
            if (!prototype?.play || prototype.play.__newsmuncherMasterMute) return;
            const controller = this, nativePlay = prototype.play;
            function play(...args) {
                controller.registerMedia(this);
                return nativePlay.apply(this, args);
            }
            play.__newsmuncherMasterMute = true;
            play.__newsmuncherNativePlay = nativePlay;
            prototype.play = play;
        }
        registerMedia(element) {
            if (!element) return element;
            this.media.add(element);
            if (!this.mediaState.has(element)) {
                this.mediaState.set(element, {forced: false, previousMuted: false});
                const release = () => this.media.delete(element);
                element.addEventListener?.('ended', release, {once: true});
                element.addEventListener?.('error', release, {once: true});
            }
            this.applyMedia(element);
            return element;
        }
        applyMedia(element) {
            const state = this.mediaState.get(element) || {forced: false, previousMuted: false};
            this.mediaState.set(element, state);
            if (this.muted) {
                if (!state.forced) { state.previousMuted = !!element.muted; state.forced = true; }
                element.muted = true;
            } else if (state.forced) {
                element.muted = state.previousMuted;
                state.forced = false;
            }
        }
        registerGain(node, normalValue = 1) {
            if (!node?.gain) return node;
            const record = {node, normalValue}; this.gains.add(record);
            this.applyGain(record); return node;
        }
        unregisterGain(node) {
            for (const record of this.gains) if (record.node === node) this.gains.delete(record);
        }
        applyGain(record) {
            const parameter = record.node.gain, value = this.muted ? 0 : record.normalValue;
            parameter.cancelScheduledValues?.(0);
            parameter.setValueAtTime?.(value, 0);
            if (!parameter.setValueAtTime) parameter.value = value;
        }
        setMuted(muted, {persist = true} = {}) {
            this.muted = !!muted;
            if (persist) this.persist();
            for (const element of [...this.media]) this.applyMedia(element);
            this.document?.querySelectorAll?.('audio,video').forEach(element => this.registerMedia(element));
            for (const record of this.gains) this.applyGain(record);
            this.render();
            return this.muted;
        }
        toggle() { return this.setMuted(!this.muted); }
        unmuteForExplicitPlayback() { return this.setMuted(false); }
        bind(button) {
            if (!button || button.dataset.masterMuteBound === 'true') return;
            button.dataset.masterMuteBound = 'true';
            button.addEventListener('click', () => this.toggle());
            this.button = button; this.render();
        }
        render() {
            if (!this.button) return;
            this.button.setAttribute('aria-pressed', String(this.muted));
            this.button.setAttribute('aria-label', this.muted ? 'Unmute all sound' : 'Mute all sound');
            this.button.title = this.button.getAttribute('aria-label');
            this.button.textContent = this.muted ? '🔇' : '🔊';
            this.button.classList.toggle('is-muted', this.muted);
        }
    }

    if (typeof module !== 'undefined') module.exports = {MasterAudioController, STORAGE_KEY};
    if (!root.document) return;
    const controller = new MasterAudioController();
    root.NewsMuncherAudio = controller;
    const mount = () => controller.bind(root.document.getElementById('masterMuteButton'));
    if (root.document.readyState === 'loading') root.document.addEventListener('DOMContentLoaded', mount, {once: true});
    else mount();
})(typeof globalThis !== 'undefined' ? globalThis : this);
