/* Only READ ALOUD posts. Status, discovery and playback never synthesize. */
const narrationUI = (() => {
    let revision = 0, entry = null, state = null, pending = false, timer = null, lookup = Promise.resolve(), available = false;
    const get = id => document.getElementById(id);
    function message(text) { get('narrationMessage').textContent = text; }
    function stop() {
        const audio = get('narrationAudio');
        audio.pause();
        audio.removeAttribute('src');
        audio.load();
        audio.hidden = true;
        const stopButton=get('narrationStop');if(stopButton)stopButton.hidden=true;
    }
    function render(data) {
        state = data;
        const button = get('narrationButton'), audio = get('narrationAudio');
        const hasAudio = Boolean(data.narration_url);
        button.hidden = !available;
        button.disabled = pending || !(data.narration_url || data.can_generate);
        button.textContent = hasAudio ? '▶ PLAY NARRATION' : pending || data.narration_status === 'started' ? 'GENERATING NARRATION…' : 'READ ALOUD';
        if (hasAudio) {
            if (audio.getAttribute('src') !== data.narration_url) audio.src = data.narration_url;
            audio.hidden = true;
        }
        // Voice name goes to the shared meta line; narrationMessage carries only status text.
        if (typeof creationMeta !== 'undefined') creationMeta.setVoice(data.voice_name || '');
        message(data.text_changed ? 'Narration uses the earlier text; it will not regenerate.' :
            data.narration_url ? '' : (data.message || ''));
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
        available = !!(data?.nominated && data?.rewrite_id);
        get('narrationControls').hidden = !available;
        if (!available) {
            render({});
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
        return {title:get('responseTitleDraft').value,body:get('responseBodyDraft').value};
    }
    async function act() {
        if (!entry || !state || pending) return;
        if (state.narration_url) {
            const audio = get('narrationAudio');
            if (!audio.paused) { audio.pause(); return; }
            if (typeof jingleUI !== 'undefined') jingleUI.stop();
            const token = revision;
            try { await audio.play(); if (token !== revision) audio.pause(); else get('narrationStop').hidden=false; } catch (_) { if (token === revision) message('Playback blocked. Try PLAY NARRATION again.'); }
            return;
        }
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
    return {
        show(data) { lookup = show(data); return lookup; }, act,
        pause() { get('narrationAudio').pause(); const button=get('narrationStop');if(button)button.hidden=true; },
        snapshot: () => ({...state, pending}),
        async ensure() {
            const token = revision;
            await lookup;
            if (token !== revision || state?.narration_url || pending || state?.narration_status === 'started') return;
            await act();
        },
        async playForEmbellish() {
            const token = revision;
            await lookup;
            if (token !== revision || !state?.narration_url) return false;
            const audio = get('narrationAudio');
            if (typeof jingleUI !== 'undefined') jingleUI.stop();
            return new Promise(resolve => {
                let settled = false;
                const finish = played => {
                    if (settled) return;
                    settled = true;
                    audio.removeEventListener?.('ended', ended);
                    audio.removeEventListener?.('error', failed);
                    const button=get('narrationStop');if(button)button.hidden=true;
                    resolve(played);
                };
                const ended = () => finish(token === revision);
                const failed = () => finish(false);
                audio.addEventListener?.('ended', ended, {once:true});
                audio.addEventListener?.('error', failed, {once:true});
                Promise.resolve(audio.play()).then(() => {
                    if (token !== revision) { audio.pause(); finish(false); }
                    else { const button=get('narrationStop');if(button)button.hidden=false; }
                }).catch(() => finish(false));
            });
        }
    };
})();
