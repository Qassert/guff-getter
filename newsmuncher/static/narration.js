/* Only READ ALOUD posts. Status, discovery and playback never synthesize. */
const narrationUI = (() => {
    let revision = 0, entry = null, state = null, pending = false, timer = null;
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
        const button = get('narrationButton'), audio = get('narrationAudio');
        const hasAudio = Boolean(data.narration_url);
        button.hidden = hasAudio;
        button.disabled = pending || !(data.narration_url || data.can_generate);
        button.textContent = pending || data.narration_status === 'started' ? 'GENERATING NARRATION…' : 'READ ALOUD';
        if (hasAudio) {
            if (audio.getAttribute('src') !== data.narration_url) audio.src = data.narration_url;
            audio.hidden = false;
        }
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
    async function act() {
        if (!entry || !state || pending) return;
        if (state.narration_url) return;
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
            if (data.narration_status === 'started') refresh(token);
        } catch (error) {
            if (token !== revision) return;
            pending = false;
            render({message: error.message + ' Checking status; no generation retry.'});
            refresh(token);
        }
    }
    return {show, act};
})();
