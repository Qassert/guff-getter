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
            this.url = null;
            this.starting = false;
            this.status({available: false, blocked: false, playing: false});
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
                    else this.status({available: true, blocked: false, playing: true});
                });
                player.addEventListener('ended', () => {
                    // Only the active track's natural end may advance this page.
                    if (generation !== this.generation ||
                        this.players[this.index] !== player || !player.ended) return;
                    this.index++;
                    this.starting = false;
                    if (this.index < this.players.length) this.play();
                    else this.status({available: true, blocked: false, playing: false});
                });
                this.players.push(player);
            }
        }
        activate(item, autoplay = true) {
            this.stop();
            this.url = item.jingle_url || null;
            this.prepare(this.url ? [this.url, this.url] : []);
            this.status({available: this.players.length > 0, blocked: false, playing: false});
            if (autoplay) return this.play();
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
            this.status({available: true, blocked, playing: !blocked});
        }
        pause() {
            // STOP discards pending starts. A deliberate PLAY begins a fresh two-play sequence.
            const url = this.url;
            this.stop();
            this.url = url;
            this.prepare(url ? [url, url] : []);
            this.status({available: this.players.length > 0, blocked: false, playing: false});
        }
        restart() {
            const url = this.url;
            this.stop();
            this.url = url;
            this.prepare(url ? [url, url] : []);
            this.status({available: this.players.length > 0, blocked: false, playing: false});
            return this.play();
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
        switchSource(url) {
            if (!url || this.reduced()) return;
            this.cancel(this.timer); this.timer = null;
            const player = this.player;
            if (!player) { this.play(url, this.generation); return; }
            player.pause(); player.src = url; player.load();
            Promise.resolve(player.play()).catch(() => {
                if (player === this.player) this.stop();
            });
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
        switchSource(url) {
            if (!url || this.reduced()) return;
            const player = this.player;
            if (!player) return;
            player.pause(); player.src = url; player.load();
            Promise.resolve(player.play()).catch(() => {
                if (player === this.player) this.clearVideo();
            });
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
            this.history = [];
            this.receipt = null;
            this.acknowledging = null;
        }
        stopPingPongPoll() {
            clearTimeout(this.pingPongTimer);
            this.pingPongTimer = null;
            if (this.pingPongAbort) this.pingPongAbort.abort();
            this.pingPongAbort = null;
        }
        watchForPingPong(item, sequence) {
            this.stopPingPongPoll();
            if (!item?.video_url || !item.video_url.includes('?v=original-')
                    || ['failed', 'unavailable'].includes(item.video_derivative_status)) return;
            const itemId = item.id;
            const poll = async () => {
                if (sequence !== this.sequence || this.current?.id !== itemId) return;
                this.pingPongAbort = new AbortController();
                try {
                    const latest = await this.storedItem(item, this.pingPongAbort.signal);
                    if (sequence !== this.sequence || this.current?.id !== itemId) return;
                    if (latest.video_url?.includes('?v=pingpong-')) {
                        this.stopPingPongPoll();
                        this.current.video_url = latest.video_url;
                        console.info('[pingpong] derivative became available - switching Gallery playback');
                        this.visual.switchSource(latest.video_url);
                        this.backdrop.switchSource(latest.video_url);
                        return;
                    }
                    if (['failed', 'unavailable'].includes(latest.video_derivative_status)) {
                        this.stopPingPongPoll();
                        return;
                    }
                    this.pingPongAbort = null;
                    this.pingPongTimer = setTimeout(poll, 2000);
                } catch (error) {
                    if (error.name !== 'AbortError' && sequence === this.sequence)
                        this.pingPongTimer = setTimeout(poll, 2000);
                }
            };
            this.pingPongTimer = setTimeout(poll, 2000);
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
            const previousItem = this.current;
            this.stopPingPongPoll();
            if (this.completionAbort) this.completionAbort.abort();
            this.completing = false;
            this.view.completing(false);
            this.view.progress('');
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
                if (!data.item) { this.view.empty(); return; }
                if (previousItem && previousItem.id !== data.item.id) this.history.push(previousItem);
                this.current = data.item;
                this.view.show(data.item);
                this.view.backAvailable?.(this.history.length > 0);
                this.backdrop.activate(data.item);
                await this.afterDisplay();
                if (sequence !== this.sequence) return;
                this.media.activate(data.item);
                this.visual.activate(data.item, this.view.imageReady);
                this.watchForPingPong(data.item, sequence);
                this.receipt = data.view_token;
                await this.acknowledge();
            } catch (error) {
                if (sequence === this.sequence && error.name !== 'AbortError') this.view.error(error.message);
            }
        }
        async previous() {
            if (!this.history.length) return;
            const sequence = ++this.sequence;
            this.stopPingPongPoll();
            if (this.completionAbort) this.completionAbort.abort();
            this.completing = false;
            this.view.completing(false);
            this.view.progress('');
            this.media.stop();
            this.visual.stop();
            this.backdrop.stop();
            if (this.abort) this.abort.abort();
            this.receipt = null;
            const item = this.history.pop();
            this.current = item;
            this.view.show(item);
            this.view.backAvailable?.(this.history.length > 0);
            this.backdrop.activate(item);
            await this.afterDisplay();
            if (sequence !== this.sequence || this.current?.id !== item.id) return;
            this.media.activate(item);
            this.visual.activate(item, this.view.imageReady);
            this.watchForPingPong(item, sequence);
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
        async providerRequest(path, options = {}) {
            const response = await this.fetcher(path, {
                credentials: 'same-origin', cache: 'no-store', ...options,
                headers: {'Content-Type': 'application/json', 'X-Gallery-Request': '1', ...(options.headers || {})}
            });
            const data = await response.json().catch(() => ({}));
            if (!response.ok) {
                const detail = data.detail;
                const error = new Error((detail && typeof detail === 'object' ? detail.message : detail) ||
                    'Missing media could not be completed.');
                error.httpStatus = response.status;
                error.mediaState = data;
                if (detail?.code === 'image_outcome_uncertain') error.imageRecovery = detail;
                throw error;
            }
            return data;
        }
        completionFailure(stage, error) {
            if (error.completionMessage) return error.completionMessage;
            const state = error.mediaState || {};
            const detail = String(error.message || '').toLowerCase();
            const unresolved = /uncertain|pending|processing|submitted|already started|operator review|no automatic retry/.test(detail);
            if (stage === 'display') return 'Saved media is ready, but the Gallery display could not be refreshed.';
            if (stage === 'image') {
                if (unresolved || error.httpStatus === 409 || error.httpStatus === 502)
                    return 'Image outcome is pending or uncertain — no retry was submitted.';
                return 'Image generation failed — try again later.';
            }
            if (stage === 'video') {
                if (['queued', 'started'].includes(state.video_status)) return 'Video generation is still in progress.';
                if (state.video_status === 'failed_or_uncertain' || unresolved) return state.end_image_status === 'complete'
                    ? 'Video outcome is uncertain — no retry was submitted.'
                    : 'End image outcome is uncertain — no retry was submitted.';
                return 'Video could not be started safely — no retry was submitted.';
            }
            if (stage === 'jingle') {
                const status = state.jingle_status;
                if (['started', 'submitted', 'uncertain'].includes(status) || unresolved)
                    return 'Jingle outcome is pending or uncertain — no retry was submitted.';
                return 'Jingle generation failed — try again later.';
            }
            return error.name === 'AbortError'
                ? 'Completion cancelled.'
                : 'Creation status could not be checked — completion stopped.';
        }
        async storedItem(item, signal) {
            return this.request('/items/' + item.id, {signal});
        }
        async waitForVideo(rewriteId, signal) {
            for (;;) {
                const state = await this.providerRequest('/videos/' + encodeURIComponent(rewriteId), {signal});
                if (state.video_url || state.video_status === 'complete') return;
                if (!['queued', 'started'].includes(state.video_status)) {
                    const error = new Error(state.message || 'Video generation did not complete.');
                    error.mediaState = state;
                    throw error;
                }
                this.view.progress(state.end_image_status === 'complete'
                    ? 'Waiting for video…' : 'Creating end image…');
                await new Promise((resolve, reject) => {
                    const timer = setTimeout(resolve, 5000);
                    signal.addEventListener('abort', () => {
                        clearTimeout(timer); reject(new DOMException('Aborted', 'AbortError'));
                    }, {once: true});
                });
            }
        }
        async refresh(item, sequence, autoplayAudio = false) {
            if (sequence !== this.sequence) return;
            this.current = item;
            this.media.stop(); this.visual.stop(); this.backdrop.stop();
            this.view.show(item);
            this.backdrop.activate(item);
            await this.afterDisplay();
            if (sequence !== this.sequence) return;
            this.media.activate(item, autoplayAudio);
            this.visual.activate(item, this.view.imageReady);
            this.watchForPingPong(item, sequence);
        }
        async complete() {
            const original = this.current, sequence = this.sequence;
            if (!original?.id || this.completing) return;
            this.completing = true;
            this.completionAbort = new AbortController();
            const signal = this.completionAbort.signal, failures = [];
            this.view.completing(true);
            this.view.progress('Checking creation…');
            try {
                // Always run the idempotent local hydration. Legacy items may already
                // have a UUID while still lacking modern nomination/ownership state.
                let item = await this.request('/items/' + original.id + '/prepare-completion', {
                    method: 'POST', signal, body: '{}'
                });
                if (sequence !== this.sequence) return;
                this.current = item;
                item = await this.storedItem(item, signal);
                const initiallyComplete = item.image_url && item.video_url && item.jingle_url;
                if (initiallyComplete) {
                    this.view.completed(true);
                    return;
                }
                if (!item.image_url) {
                    let phase = 'image';
                    try {
                        if (!item.image_url) {
                            if (!String(item.body || '').trim()) {
                                const missing = new Error('Historical rewrite body is missing.');
                                missing.completionMessage = 'Cannot create image — this older creation has no saved rewritten description.';
                                throw missing;
                            }
                            this.view.progress('Creating image…');
                            await this.providerRequest('/temp/generate_image', {
                                method: 'POST', signal, body: JSON.stringify({rewrite_id: item.rewrite_id})
                            });
                        }
                        item = await this.storedItem(item, signal);
                        if (!item.image_url) {
                            const unavailable = new Error('Image outcome is uncertain.');
                            unavailable.httpStatus = 502;
                            throw unavailable;
                        }
                        phase = 'display';
                        await this.refresh(item, sequence);
                    } catch (error) {
                        if (error.imageRecovery && await this.view.confirmImageRetry()) {
                            try {
                                this.view.progress('Retrying image…');
                                await this.providerRequest('/temp/retry_uncertain_image', {
                                    method: 'POST', signal, body: JSON.stringify({
                                        rewrite_id: error.imageRecovery.rewrite_id,
                                        attempt_id: error.imageRecovery.attempt_id,
                                        confirmed: true
                                    })
                                });
                                item = await this.storedItem(item, signal);
                                if (item.image_url) await this.refresh(item, sequence);
                            } catch (retryError) {
                                failures.push(this.completionFailure('image', retryError));
                            }
                        } else if (error.imageRecovery) {
                            failures.push('Image retry cancelled; the uncertain attempt remains unchanged.');
                        } else failures.push(this.completionFailure(phase, error));
                    }
                }
                item = await this.storedItem(original, signal);
                if (!item.video_url && item.image_url) {
                    let phase = 'video';
                    try {
                        this.view.progress('Checking video…');
                        if (!item.video_url) {
                            let state = await this.providerRequest('/videos/' + encodeURIComponent(item.rewrite_id), {signal});
                            if (!state.video_url && state.video_status === 'none' && state.can_generate) {
                                item = await this.storedItem(original, signal);
                                if (!item.video_url) {
                                    this.view.progress('Creating end image…');
                                    state = await this.providerRequest(
                                        '/videos/' + encodeURIComponent(item.rewrite_id), {method: 'POST', signal});
                                }
                            }
                            if (!state.video_url && ['queued', 'started'].includes(state.video_status)) {
                                await this.waitForVideo(item.rewrite_id, signal);
                            } else if (!state.video_url && state.video_status !== 'complete') {
                                const unavailable = new Error(state.message || 'Video generation could not be started safely.');
                                unavailable.mediaState = state;
                                throw unavailable;
                            }
                            item = await this.storedItem(item, signal);
                            if (!item.video_url) {
                                const unavailable = new Error('Video outcome is uncertain.');
                                unavailable.mediaState = state;
                                throw unavailable;
                            }
                            phase = 'display';
                            await this.refresh(item, sequence);
                        }
                    } catch (error) {
                        const recovery = error.mediaState?.end_image_retry_attempt_id;
                        if (recovery && await this.view.confirmEndImageRetry()) {
                            try {
                                this.view.progress('Retrying end image…');
                                const state = await this.providerRequest(
                                    '/videos/' + encodeURIComponent(item.rewrite_id) + '/retry-uncertain-end-image', {
                                        method: 'POST', signal, body: JSON.stringify({
                                            attempt_id: recovery, confirmed: true
                                        })
                                    });
                                if (!state.video_url && ['queued', 'started'].includes(state.video_status)) {
                                    await this.waitForVideo(item.rewrite_id, signal);
                                }
                                item = await this.storedItem(item, signal);
                                if (item.video_url) await this.refresh(item, sequence);
                            } catch (retryError) {
                                failures.push(this.completionFailure('video', retryError));
                            }
                        } else if (recovery) {
                            failures.push('End-image retry cancelled; the uncertain attempt remains unchanged.');
                        } else failures.push(this.completionFailure(phase, error));
                    }
                } else if (!item.video_url && !item.image_url) failures.push('Video is waiting for a usable main image.');
                item = await this.storedItem(original, signal);
                if (!item.jingle_url) {
                    let phase = 'jingle';
                    try {
                        if (!item.jingle_url) {
                            if (!String(item.title || '').trim()) {
                                const missing = new Error('Historical title is missing.');
                                missing.completionMessage = 'Cannot create jingle — this older creation has no saved title.';
                                throw missing;
                            }
                            this.view.progress('Creating jingle…');
                            const jingleState = await this.providerRequest('/jingles/' + encodeURIComponent(item.rewrite_id), {method: 'POST', signal});
                            if (!jingleState.jingle_url && ['started', 'submitted', 'uncertain', 'brief_failed'].includes(jingleState.jingle_status)) {
                                const unavailable = new Error(jingleState.message || 'Jingle was not completed.');
                                unavailable.mediaState = jingleState;
                                throw unavailable;
                            }
                        }
                        item = await this.storedItem(item, signal);
                        if (!item.jingle_url) throw new Error('No usable saved jingle is available.');
                        phase = 'display';
                        await this.refresh(item, sequence);
                    } catch (error) { failures.push(this.completionFailure(phase, error)); }
                }
                item = await this.storedItem(original, signal);
                const mediaChanged = ['image_url', 'video_url', 'jingle_url'].some(
                    field => item[field] !== this.current?.[field]);
                if (mediaChanged) await this.refresh(item, sequence);
                else this.current = item;
                if (sequence !== this.sequence) return;
                if (failures.length) {
                    this.view.progress(failures.join(' '));
                    this.view.error('Completed what was available. ' + failures.join(' · '));
                }
                else this.view.completed(false);
            } catch (error) {
                if (sequence === this.sequence && error.name !== 'AbortError') {
                    this.view.progress(this.completionFailure('orchestration', error));
                    this.view.error(error.message);
                }
            } finally {
                this.completing = false;
                this.completionAbort = null;
                if (sequence === this.sequence) this.view.completing(false);
            }
        }
        leave() {
            this.sequence++;
            this.stopPingPongPoll();
            this.media.stop();
            this.visual.stop();
            this.backdrop.stop();
            if (this.abort) this.abort.abort();
            if (this.completionAbort) this.completionAbort.abort();
        }
    }
    root.PromotionGallery = PromotionGallery;
    if (typeof module !== 'undefined') module.exports = {PromotionGallery, GalleryMedia, GalleryVideo, GalleryBackdrop, creatorEditUrl};
    if (typeof document === 'undefined' || !document.getElementById('galleryPage')) return;
    const get = id => document.getElementById(id);
    const page = get('galleryPage'), status = get('galleryStatus'), promote = get('galleryPromote');
    const complete = get('galleryComplete'), completionStatus = get('galleryCompletionStatus');
    const edit = get('galleryEdit'), creationUrl = document.querySelector('.promotion-gallery').dataset.creationUrl;
    const illustration = get('galleryIllustration');
    const retryDialog = get('galleryImageRetryDialog');
    const endRetryDialog = get('galleryEndImageRetryDialog');
    let retryConfirmation = null;
    let endRetryConfirmation = null;
    const closeRetryDialog = confirmed => {
        if (typeof retryDialog.close === 'function') retryDialog.close();
        else retryDialog.removeAttribute('open');
        const resolve = retryConfirmation;
        retryConfirmation = null;
        if (resolve) resolve(confirmed);
    };
    const closeEndRetryDialog = confirmed => {
        if (typeof endRetryDialog.close === 'function') endRetryDialog.close();
        else endRetryDialog.removeAttribute('open');
        const resolve = endRetryConfirmation;
        endRetryConfirmation = null;
        if (resolve) resolve(confirmed);
    };
    const alignFurControls = () => {
        if (!page.classList.contains('has-image') || illustration.hidden) {
            page.style.removeProperty('--gallery-image-centre-x');
            return;
        }
        const pageBox = page.getBoundingClientRect(), imageBox = illustration.getBoundingClientRect();
        // Absolute children use the page padding box as their positioning origin.
        // With four equal columns, centring the row here puts this line through
        // the exact middle gap between PROMOTE and EDIT.
        page.style.setProperty('--gallery-image-centre-x',
            `${imageBox.left + imageBox.width / 2 - pageBox.left - page.clientLeft}px`);
    };
    const view = {
        loading() { status.textContent = 'Turning the page…'; promote.disabled = true; page.setAttribute('aria-busy', 'true'); },
        empty() { page.hidden = true; page.setAttribute('aria-busy', 'false'); status.textContent = 'The collection is waiting for its first nomination. Head back to NewsMuncher to nominate a creation.'; },
        show(item) {
            get('galleryBody').textContent = item.body || 'No saved text for this creation.';
            get('galleryPromoted').hidden = !item.promoted;
            promote.classList.toggle('is-promoted', !!item.promoted);
            promote.setAttribute('aria-label', item.promoted ? 'Creation promoted' : 'Promote creation');
            promote.disabled = item.promoted;
            edit.href = creatorEditUrl(creationUrl, item.rewrite_id);
            // A fresh image prevents a late error from an old URL hiding the new page.
            const image = document.createElement('img');
            image.id = 'galleryImage'; image.alt = ''; image.decoding = 'async';
            get('galleryImage').replaceWith(image);
            this.imageReady = new Promise(resolve => {
                image.addEventListener('load', () => { alignFurControls(); resolve(true); }, {once: true});
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
            requestAnimationFrame(alignFurControls);
            page.classList.remove('turning');
            void page.offsetWidth;
            page.classList.add('turning');
            page.setAttribute('aria-busy', 'false');
            status.textContent = '';
        },
        backAvailable(available) { get('galleryBack').hidden = !available; },
        error(message) { status.textContent = message; page.setAttribute('aria-busy', 'false'); },
        promoting(busy) { promote.disabled = busy || !!gallery.current?.promoted; },
        promoted() {
            get('galleryPromoted').hidden = false;
            promote.classList.add('is-promoted');
            promote.setAttribute('aria-label', 'Creation promoted');
            promote.disabled = true;
        },
        completing(busy) { complete.disabled = busy; complete.setAttribute('aria-busy', busy ? 'true' : 'false'); },
        progress(message) {
            completionStatus.textContent = message;
            completionStatus.hidden = !message;
        },
        completed(alreadyComplete) {
            this.progress(alreadyComplete ? 'This creation is already complete.' : 'Complete');
        },
        confirmImageRetry() {
            if (retryConfirmation) return Promise.resolve(false);
            if (typeof retryDialog.showModal === 'function') retryDialog.showModal();
            else retryDialog.setAttribute('open', '');
            return new Promise(resolve => { retryConfirmation = resolve; });
        },
        confirmEndImageRetry() {
            if (endRetryConfirmation) return Promise.resolve(false);
            if (typeof endRetryDialog.showModal === 'function') endRetryDialog.showModal();
            else endRetryDialog.setAttribute('open', '');
            return new Promise(resolve => { endRetryConfirmation = resolve; });
        }
    };
    const afterDisplay = () => new Promise(resolve => {
        const painted = () => requestAnimationFrame(() => requestAnimationFrame(resolve));
        if (!document.hidden) painted();
        else document.addEventListener('visibilitychange', function visible() {
            if (!document.hidden) { document.removeEventListener('visibilitychange', visible); painted(); }
        });
    });
    const music = get('galleryMusic');
    const media = new GalleryMedia({status({available, playing}) {
        music.hidden = false;
        music.setAttribute('aria-pressed', playing ? 'true' : 'false');
        music.setAttribute('aria-label', playing ? 'Mute music' : 'Play music');
        music.title = playing ? 'Mute music' : 'Play music';
        music.classList.toggle('is-playing', !!playing);
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
    const galleryRoot = document.querySelector('.promotion-gallery');
    const universalClickSound = galleryRoot.dataset.clickSound;
    const arrowClickPlayer = new Audio(galleryRoot.dataset.arrowClickSound);
    const playUiSound = url => {
        const sound = new Audio(url);
        sound.play().catch(() => {});
    };
    const playArrowClickSound = () => {
        arrowClickPlayer.pause();
        try { arrowClickPlayer.currentTime = 0; } catch (_) {}
        arrowClickPlayer.play().catch(() => {});
    };
    const hoverVoicePlayers = new Map();
    const playHoverVoice = url => {
        if (root.NewsMuncherHoverVoice?.play) return root.NewsMuncherHoverVoice.play(url);
        let sound = hoverVoicePlayers.get(url);
        if (!sound) { sound = new Audio(url); hoverVoicePlayers.set(url, sound); }
        sound.pause();
        try { sound.currentTime = 0; } catch (_) {}
        sound.play().catch(() => {});
    };
    [music, promote, edit, complete].forEach(control => {
        control.addEventListener('click', () => playUiSound(universalClickSound));
    });
    [get('galleryNext'), get('galleryBack')].forEach(control => {
        control.addEventListener('click', playArrowClickSound);
    });
    const hoverSounds = new Map([
        [get('galleryNext'), '/static/audio/effects/ui/farty_button_squelch.wav'],
        [get('galleryBack'), '/static/audio/effects/ui/farty_button_squelch.wav']
    ]);
    hoverSounds.forEach((url, control) => control.addEventListener('pointerenter', event => {
        if (event.pointerType !== 'touch') playUiSound(url);
    }));
    promote.addEventListener('pointerenter', event => {
        if (event.pointerType !== 'touch') playHoverVoice(galleryRoot.dataset.promoteHover);
    });
    edit.addEventListener('pointerenter', event => {
        if (event.pointerType !== 'touch') playHoverVoice(galleryRoot.dataset.editHover);
    });
    complete.addEventListener('pointerenter', event => {
        if (event.pointerType !== 'touch') playHoverVoice(galleryRoot.dataset.enhanceHover);
    });
    music.addEventListener('pointerenter', event => {
        if (event.pointerType === 'touch') return;
        playHoverVoice(music.classList.contains('is-playing')
            ? galleryRoot.dataset.muteHover : galleryRoot.dataset.playHover);
    });
    music.addEventListener('click', () => {
        music.classList.remove('is-pressed'); void music.offsetWidth; music.classList.add('is-pressed');
        if (music.classList.contains('is-playing')) media.pause();
        else media.restart();
    });
    page.addEventListener('animationend', () => page.classList.remove('turning'));
    const nextButton = get('galleryNext');
    let nextTimer = null;
    nextButton.addEventListener('click', () => {
        if (nextButton.disabled) return;
        gallery.stopPingPongPoll();
        nextButton.disabled = true;
        nextButton.classList.remove('is-pressed');
        void nextButton.offsetWidth;
        nextButton.classList.add('is-pressed');
        nextTimer = setTimeout(() => {
            nextButton.classList.remove('is-pressed');
            nextButton.disabled = false;
            gallery.next();
            nextTimer = null;
        }, motionPreference.matches ? 0 : 560);
    });
    const animateControl = control => {
        control.classList.remove('is-pressed'); void control.offsetWidth; control.classList.add('is-pressed');
    };
    let promotePending = false;
    let promoteTimer = null;
    promote.addEventListener('click', () => {
        if (promotePending) return;
        promotePending = true;
        animateControl(promote);
        promoteTimer = setTimeout(() => {
            promote.classList.remove('is-pressed');
            promotePending = false;
            gallery.promote();
            promoteTimer = null;
        }, motionPreference.matches ? 0 : 620);
    });
    let editPending = false;
    let editTimer = null;
    edit.addEventListener('click', event => {
        if (event.defaultPrevented || editPending) return;
        event.preventDefault();
        gallery.stopPingPongPoll();
        editPending = true;
        animateControl(edit);
        const target = edit.href;
        editTimer = setTimeout(() => { window.location.href = target; }, motionPreference.matches ? 0 : 560);
    });
    get('galleryBack').addEventListener('click', () => gallery.previous());
    complete.addEventListener('click', () => {
        if (complete.disabled) return;
        animateControl(complete);
        gallery.complete();
    });
    get('galleryConfirmImageRetry').addEventListener('click', () => closeRetryDialog(true));
    get('galleryCancelImageRetry').addEventListener('click', () => closeRetryDialog(false));
    retryDialog.addEventListener('cancel', event => {
        event.preventDefault(); closeRetryDialog(false);
    });
    get('galleryConfirmEndImageRetry').addEventListener('click', () => closeEndRetryDialog(true));
    get('galleryCancelEndImageRetry').addEventListener('click', () => closeEndRetryDialog(false));
    endRetryDialog.addEventListener('cancel', event => {
        event.preventDefault(); closeEndRetryDialog(false);
    });
    window.addEventListener('pagehide', () => {
        clearTimeout(nextTimer);
        clearTimeout(promoteTimer);
        clearTimeout(editTimer);
        gallery.leave();
    });
    window.addEventListener('resize', alignFurControls);
    gallery.next();
})(typeof globalThis !== 'undefined' ? globalThis : this);
