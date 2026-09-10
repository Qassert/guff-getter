/* Only MAKE sends POST. Status restoration and PLAY never request generation. */
const jingleUI = (() => {
    let revision = 0, rewrite = null, state = null, pending = false, audio = null, timer = null;
    const get = id => document.getElementById(id);
    function stop() {
        if (audio) { audio.pause(); audio.currentTime = 0; }
        get('jingleStop').hidden = true;
    }
    function render(data) {
        state = data;
        const button = get('jingleButton');
        button.disabled = pending || !(data.jingle_url || data.can_generate);
        button.textContent = data.jingle_url ? '▶ PLAY JINGLE' :
            pending || ['started', 'submitted'].includes(data.jingle_status) ? 'MAKING JINGLE…' : 'MAKE JINGLE';
        get('jingleMessage').textContent = data.text_changed ?
            'This jingle belongs to the earlier nominated text; it will not regenerate automatically.' : (data.message || '');
    }
    async function refresh(token, id, polls = 0) {
        try {
            const response = await fetch('/jingles/' + encodeURIComponent(id), {credentials: 'include', cache: 'no-store'});
            const data = await response.json();
            if (token !== revision || id !== rewrite) return;
            if (!response.ok) throw new Error(data.detail || 'Jingle status unavailable.');
            render(data);
            if (['started', 'submitted'].includes(data.jingle_status) && polls < 60) {
                timer = setTimeout(() => refresh(token, id, polls + 1), 3000);
            }
        } catch (error) {
            if (token === revision) render({message: error.message, can_generate: false});
        }
    }
    function show(data) {
        const token = ++revision;
        if (timer) clearTimeout(timer);
        stop();
        audio = null; state = null; pending = false;
        rewrite = data.nominated ? data.rewrite_id : null;
        get('jingleControls').hidden = !rewrite;
        if (!rewrite) return;
        render({message: 'Checking saved jingle…', can_generate: false});
        refresh(token, rewrite);
    }
    async function act() {
        if (pending || !rewrite || !state) return;
        if (state.jingle_url) {
            if (!audio) {
                audio = new Audio(state.jingle_url);
                audio.onended = () => { get('jingleStop').hidden = true; };
            }
            const token = revision, playing = audio;
            try {
                await playing.play();
                if (token !== revision) { playing.pause(); return; }
                get('jingleStop').hidden = false;
            } catch (_) { if (token === revision) get('jingleMessage').textContent = 'Audio could not play. Try PLAY again.'; }
            return;
        }
        if (!state.can_generate) return;
        const token = revision, id = rewrite;
        pending = true; render(state);
        try {
            const response = await fetch('/jingles/' + encodeURIComponent(id), {
                method: 'POST', credentials: 'include',
            });
            const data = await response.json();
            if (token !== revision) return;
            pending = false;
            if (!response.ok) {
                render({can_generate: false, message: data.detail || 'Jingle unavailable; nomination is unchanged.'});
                return;
            }
            render(data);
            if (['started', 'submitted'].includes(data.jingle_status)) refresh(token, id);
        } catch (_) {
            if (token !== revision) return;
            pending = false;
            render({message: 'Request outcome uncertain. Restoring status; no automatic generation retry.'});
            refresh(token, id);
        }
    }
    return {show, act, stop};
})();
