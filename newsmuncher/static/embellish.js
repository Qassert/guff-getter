/* Coordinate media claims while each controller owns provider safety and status. */
(function(root) {
    class Embellish {
        constructor({media, image, persist=async()=>{}, render, loading=()=>{},
                     schedule=(fn, ms)=>setTimeout(fn, ms), cancel=id=>clearTimeout(id)}) {
            Object.assign(this, {media, image, persist, render, loading, schedule, cancel});
            this.revision = 0;
        }
        show(data) {
            this.revision++;
            this.cancel(this.timer);
            this.data = data;
            this.running = false;
            this.render({available:!!(data?.nominated && data?.image_url), message:''});
        }
        terminal(state, kind) {
            if (state?.[kind + '_url']) return true;
            const busy = state?.pending || ['queued','started','submitted'].includes(state?.[kind + '_status']);
            return !busy && (state?.can_generate === false || !!state?.message);
        }
        maybeAutoplay(token) {
            if (token !== this.revision || this.autoStarted) return;
            const media = this.media();
            if (media.Narration.isPlaying?.() || media.Jingle.isPlaying?.()) {
                this.autoStarted = true;
                return;
            }
            const narration = media.Narration.snapshot();
            const jingle = media.Jingle.snapshot();
            const player = narration?.narration_url ? media.Narration :
                jingle?.jingle_url ? media.Jingle : null;
            if (player) {
                this.autoStarted = true;
                player.playForEmbellish?.();
            }
        }
        wait(token, polls=0) {
            if (token !== this.revision) return;
            this.maybeAutoplay(token);
            const media = this.media();
            const done = this.terminal(media.Narration.snapshot(), 'narration') &&
                this.terminal(media.Jingle.snapshot(), 'jingle') &&
                this.terminal(media.Video.snapshot(), 'video');
            if (done || polls >= 720) return this.finish(token);
            this.timer = this.schedule(()=>this.wait(token, polls + 1), 1000);
        }
        async run(replace=false) {
            if (this.running || !this.data?.rewrite_id) return;
            this.running = true;
            this.errors = '';
            this.autoStarted = false;
            const token = ++this.revision;
            const id = this.data.rewrite_id;
            const sequence = root.creationContext?.().sequence ?? this.data.sequence;
            const media = this.media();
            this.loading(true);
            this.render({available:false, message:''});

            if (replace) {
                media.Narration.pause();
                try {
                    await this.persist();
                    await media.Narration.show({nominated:true, rewrite_id:id});
                } catch (_) {
                    this.errors = 'Edited text could not be saved; media was not replaced.';
                    return this.finish(token);
                }
            }

            const audio = replace ? [media.Narration.replaceIfChanged(), media.Jingle.replace()] :
                [media.Narration.ensure(), media.Jingle.ensure()];
            audio.forEach(work => Promise.resolve(work)
                .then(()=>this.maybeAutoplay(token))
                .catch(()=>{ if (token === this.revision) this.errors = 'Some audio is unavailable.'; }));

            let prepared = null;
            try {
                prepared = await this.image(id, sequence, replace);
                if (token !== this.revision) return;
                await prepared.reveal();
            } catch (_) {
                this.errors = 'Image unavailable. Existing media retained.';
            }
            if (token !== this.revision) return;
            this.loading(false);

            if (prepared) {
                await media.Video.show({nominated:true, rewrite_id:id});
                Promise.resolve(media.Video.ensure()).catch(()=>{
                    if (token === this.revision) this.errors = 'Animation is unavailable.';
                });
            }
            this.wait(token);
        }
        nominate(data) {
            this.data = {nominated:true, ...data};
            return this.run(false);
        }
        reembellish() { return this.run(true); }
        finish(token) {
            if (token !== this.revision) return;
            this.running = false;
            this.loading(false);
            this.render({available:true, message:this.errors || ''});
            this.maybeAutoplay(token);
        }
    }
    if (typeof module !== 'undefined') module.exports = {Embellish};
    if (typeof document === 'undefined') return;
    root.embellishUI = new Embellish({
        media:()=>({Narration:narrationUI, Jingle:jingleUI, Video:root.videoUI}),
        image:(...args)=>root.generateCreationImage(...args),
        persist:()=>root.persistCreationText(),
        loading(active) {
            if (active) { showLoader(); imageLoading.start(); }
            else { hideLoader(); imageLoading.stop(); }
        },
        render({available, message}) {
            const button=document.getElementById('embellishButton');
            const status=document.getElementById('embellishStatus');
            button.hidden=!available;
            button.textContent='RE-EMBELLISH';
            status.hidden=!message;
            status.textContent=message || '';
        }
    });
})(typeof globalThis !== 'undefined' ? globalThis : this);
