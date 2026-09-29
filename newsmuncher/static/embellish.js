/* One explicit action coordinates existing controllers; this module never fetches. */
(function(root) {
    class Embellish {
        constructor({media, render, schedule=(fn, ms)=>setTimeout(fn, ms), cancel=id=>clearTimeout(id)}) {
            Object.assign(this, {media, render, schedule, cancel});
            this.revision = 0;
        }
        show(data) {
            this.revision++;
            this.cancel(this.timer);
            this.available = data?.nominated === true && !!data?.rewrite_id;
            this.started = false; this.waiting = false; this.errors = {};
            this.render({available:this.available, label:'EMBELLISH', disabled:false, message:''});
        }
        update(token, polls=0) {
            if (token !== this.revision) return;
            let working = this.waiting, complete = true;
            const messages = Object.entries(this.media()).flatMap(([name, ui]) => {
                const state = ui.snapshot(), kind = name.toLowerCase();
                const ready = !!state[kind + '_url'];
                const busy = state.pending || ['queued','started','submitted'].includes(state[kind + '_status']);
                working ||= busy;
                complete &&= ready;
                return this.errors[name] ? [`${name}: unavailable — use its individual control for details.`] : [];
            });
            if (polls >= 720) working = false;
            this.render({available:this.available, disabled:true,
                label: working ? 'EMBELLISHING…' : complete ? 'EMBELLISHED' : 'EMBELLISH — CHECK STATUS',
                message:messages.join(' ')});
            this.cancel(this.timer);
            if (working) this.timer = this.schedule(()=>this.update(token, polls+1), 1000);
        }
        async act() {
            if (!this.available || this.started) return;
            this.started = true; this.waiting = true;
            const token = this.revision;
            this.update(token);
            await Promise.allSettled(Object.entries(this.media()).map(async ([name, ui]) => {
                try { await ui.ensure(); }
                catch (_) { if (token === this.revision) this.errors[name] = true; }
            }));
            if (token !== this.revision) return;
            this.waiting = false;
            this.update(token);
        }
    }
    if (typeof module !== 'undefined') module.exports = {Embellish};
    if (typeof document === 'undefined') return;
    root.embellishUI = new Embellish({
        media:()=>({Narration:narrationUI, Video:root.videoUI, Jingle:jingleUI}),
        render({available,label,disabled,message}) {
            const button=document.getElementById('embellishButton'), status=document.getElementById('embellishStatus');
            button.hidden=!available; button.disabled=disabled; button.textContent=label;
            status.hidden=!available || !message; status.textContent=message;
        }
    });
    root.addEventListener('pagehide', ()=>root.embellishUI.show(null));
})(typeof globalThis !== 'undefined' ? globalThis : this);
