/* Only ANIMATE IMAGE posts. Restore, polling and preview are retrieval-only. */
(function (root) {
    'use strict';
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
            this.view.render(state, this.pending);
        }
        stop() {
            this.revision++;
            this.cancel(this.timer);
            this.key = null;
            this.pending = false;
            this.state = null;
            this.view.stop();
        }
        async show(data) {
            this.stop();
            if (!data?.rewrite_id) { this.render({}); return; }
            this.key = data.rewrite_id;
            this.render({message: 'Checking saved animation…'});
            await this.refresh(this.revision);
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
        async act() {
            if (!this.key || this.pending || !this.state?.can_generate) return;
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
    if (typeof module !== 'undefined') module.exports = {AnimationUI};
    if (typeof document === 'undefined' || !document.getElementById('animationControls')) return;
    const get = id => document.getElementById(id);
    root.videoUI = new AnimationUI({view: {
        stop() {
            const video = get('animationPreview');
            video.pause(); video.removeAttribute('src'); video.load(); video.hidden = true;
        },
        render(data, pending) {
            const busy = pending || ['queued', 'started'].includes(data.video_status);
            const ready = !!data.video_url;
            const failed = data.video_status === 'failed_or_uncertain';
            const button = get('animationButton');
            get('animationControls').hidden = !(data.can_generate || busy || ready || failed || data.message);
            button.hidden = ready || failed || (!busy && !data.can_generate);
            button.disabled = busy || !data.can_generate;
            button.textContent = busy ? 'ANIMATING…' : 'ANIMATE IMAGE';
            get('animationMessage').textContent = ready ? 'ANIMATION READY' : failed
                ? 'ANIMATION FAILED — operator review needed; no regeneration.'
                : data.message || (busy ? 'Animating your image. You can leave this page.'
                    : 'Optional: one 5-second animation, approximately $0.05. Uses the saved rewritten scene.');
            const video = get('animationPreview');
            if (ready && video.getAttribute('src') !== data.video_url) video.src = data.video_url;
            video.hidden = !ready;
        }
    }});
    get('animationButton').addEventListener('click', () => root.videoUI.act());
    root.addEventListener('pagehide', () => root.videoUI.stop());
})(typeof globalThis !== 'undefined' ? globalThis : this);
