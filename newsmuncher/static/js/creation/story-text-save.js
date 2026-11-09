/* Existing nominations save text independently of paid media/nomination actions. */
(function (root) {
    'use strict';
    class StoryTextSaver {
        constructor({snapshot, saved, notify, fetcher = (...args) => root.fetch(...args)}) {
            Object.assign(this, {snapshot, saved, notify, fetcher});
            this.timer = null;
            this.pending = null;
        }
        schedule() {
            clearTimeout(this.timer);
            if (this.snapshot()) this.timer = setTimeout(() => this.flush().catch(() => {}), 350);
        }
        flush() {
            clearTimeout(this.timer);
            if (this.pending) return this.pending;
            this.pending = this.write().finally(() => { this.pending = null; });
            return this.pending;
        }
        async write() {
            try {
                let draft;
                while ((draft = this.snapshot())) {
                    this.notify('Saving story changes…');
                    const response = await this.fetcher(`/temp/creation/${encodeURIComponent(draft.rewrite_id)}/text`, {
                        method: 'PATCH', credentials: 'include', keepalive: true,
                        headers: {'Content-Type': 'application/json'}, body: JSON.stringify(draft.text)
                    });
                    if (!response.ok) throw new Error('Story changes could not be saved. Your draft is kept in this tab; please retry before leaving.');
                    this.saved(draft);
                    this.notify('Story changes saved.');
                }
            } catch (error) {
                this.notify('Story changes could not be saved. Your draft is kept in this tab; please retry before leaving.');
                throw error;
            }
        }
    }
    root.NewsMuncherStoryText = {StoryTextSaver};
    if (typeof module !== 'undefined') module.exports = {StoryTextSaver};
})(typeof window !== 'undefined' ? window : globalThis);
