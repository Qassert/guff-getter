/* Only READ ALOUD posts. Status, discovery and playback never synthesize. */
const narrationUI = (() => {
    let revision = 0, entry = null, state = null, pending = false, timer = null;
    let saved = [], discovery = 0;
    const get = id => document.getElementById(id);
    function message(text) { get('narrationMessage').textContent = text; }
    function stop() {
        const audio = get('narrationAudio');
        audio.pause();
        audio.removeAttribute('src');
        audio.load();
        audio.hidden = true;
    }
    function render(data) {
        state = data;
        const button = get('narrationButton');
        button.disabled = pending || !(data.narration_url || data.can_generate);
        button.textContent = data.narration_url ? 'PLAY narration' :
            pending || data.narration_status === 'started' ? 'GENERATING NARRATION…' : 'READ ALOUD';
        message((data.voice_name ? `Voice: ${data.voice_name}. ` : '') +
            (data.text_changed ? 'Narration uses the earlier text; it will not regenerate.' : (data.message || '')));
    }
    async function refresh(token, polls = 0) {
        if (!entry) return;
        try {
            const response = await fetch('/narrations/' + encodeURIComponent(entry), {credentials: 'include', cache: 'no-store'});
            const data = await response.json();
            if (token !== revision) return;
            if (!response.ok) throw new Error(data.detail || 'Narration status unavailable.');
            render(data);
            if (data.narration_url) discover();
            if (data.narration_status === 'started' && polls < 20) {
                timer = setTimeout(() => refresh(token, polls + 1), 3000);
            }
        } catch (error) {
            if (token === revision) render({message: error.message});
        }
    }
    async function show(data) {
        const token = ++revision;
        clearTimeout(timer);
        stop(); entry = null; state = null; pending = false;
        if (!data || !data.nominated || !data.rewrite_id) {
            render({message: 'Nominate this rewrite before using READ ALOUD.'});
            return;
        }
        render({message: 'Checking saved narration…'});
        try {
            const response = await fetch('/narrations/for-rewrite/' + encodeURIComponent(data.rewrite_id),
                {credentials: 'include', cache: 'no-store'});
            const result = await response.json();
            if (token !== revision) return;
            if (!response.ok) throw new Error(result.detail || 'Narration status unavailable.');
            entry = result.entry_id;
            render(result);
            if (result.narration_status === 'started') refresh(token);
        } catch (error) {
            if (token === revision) render({message: error.message});
        }
    }
    function displayed() {
        const editing = !get('responseEditor').hidden;
        const title = get('crazyTitleBox').textContent;
        return {title: editing ? get('responseTitleDraft').value : (title ? title.slice(3, -3) : ''),
            body: editing ? get('responseBodyDraft').value : get('crazyExtractBox').value};
    }
    async function play(data) {
        const audio = get('narrationAudio'), token = revision;
        audio.src = data.narration_url;
        audio.hidden = false;
        message(`Voice: ${data.voice_name || data.voice}. ` +
            (data.text_changed ? 'Narration uses the earlier text.' : ''));
        try {
            await audio.play();
            if (token !== revision) audio.pause();
        } catch (_) {
            if (token === revision) message('Use the audio controls to play narration.');
        }
    }
    async function act() {
        if (!entry || !state || pending) return;
        if (state.narration_url) { await play(state); return; }
        if (!state.can_generate) return;
        const token = revision, id = entry;
        pending = true; render(state);
        try {
            const response = await fetch('/narrations/' + encodeURIComponent(id), {
                method: 'POST', credentials: 'include', headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(displayed())
            });
            const data = await response.json();
            if (token !== revision) return;
            pending = false;
            if (!response.ok) throw new Error(data.detail || 'Narration unavailable; story unchanged.');
            render(data);
            discover();
            if (data.narration_status === 'started') refresh(token);
        } catch (error) {
            if (token !== revision) return;
            pending = false;
            render({message: error.message + ' Checking status; no generation retry.'});
            refresh(token);
        }
    }
    async function discover() {
        const token = ++discovery;
        try {
            const response = await fetch('/narrations/', {credentials: 'include', cache: 'no-store'});
            if (!response.ok) return;
            const data = await response.json();
            if (token !== discovery) return;
            saved = data.narrations || [];
            const select = get('savedNarrations');
            select.replaceChildren();
            for (const item of saved) {
                const option = document.createElement('option');
                option.value = item.entry_id;
                option.textContent = `${item.title} — ${item.voice_name}`;
                select.appendChild(option);
            }
            get('savedNarrationControls').hidden = !saved.length;
        } catch (_) {} // Optional discovery never alters current rewritten text or ownership.
    }
    async function playSaved() {
        const id = get('savedNarrations').value, token = revision;
        try {
            const response = await fetch('/narrations/' + encodeURIComponent(id), {credentials: 'include', cache: 'no-store'});
            const data = await response.json();
            if (token !== revision) return;
            if (!response.ok || !data.narration_url) throw new Error();
            await play(data);
        } catch (_) { if (token === revision) message('Saved narration is unavailable.'); }
    }
    return {show, act, discover, playSaved};
})();
