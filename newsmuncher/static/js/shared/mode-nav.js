/* Preserve native navigation while giving the furry controls one brief tactile press. */
(() => {
    const reduced = () => window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    const hoverVoices = new Map();
    const playHoverVoice = url => {
        let audio = hoverVoices.get(url);
        if (!audio) { audio = new Audio(url); hoverVoices.set(url, audio); }
        audio.pause();
        try { audio.currentTime = 0; } catch (_) {}
        audio.play().catch(() => {});
    };
    window.NewsMuncherHoverVoice = {play: playHoverVoice};
    // Capture pointerenter at the document boundary so both link and active-span
    // variants use the same wiring even when page-specific scripts are deferred.
    document.addEventListener('pointerenter', event => {
        if (event.pointerType === 'touch' || !event.target?.matches?.('.mode-nav-button[data-hover-voice]')) return;
        playHoverVoice(event.target.dataset.hoverVoice);
    }, true);
    const pools = {
        CREATE: ['CREATE_01_mad_science_zap.wav', 'CREATE_02_cartoon_spell.wav', 'CREATE_03_chaos_portal.wav'],
        BUILD: ['BUILD_01_clank_clank_boing.wav', 'BUILD_02_robotic_assembly.wav', 'BUILD_03_wobbly_toolbox.wav'],
        GALLERY: ['GALLERY_01_tada_squeak.wav', 'GALLERY_02_tiny_kazoo_fanfare.wav', 'GALLERY_03_silly_reveal.wav']
    };
    // Resolve against the shared script so URL prefixes and escaped spaces survive.
    const navigationVoices = new Map(), lastPlayed = new Map();
    let currentVoice;
    const voice = filename => {
        if (!navigationVoices.has(filename)) {
            const audioBase = new URL('../../audio/bonkers_button_sounds/',
                document.currentScript?.src || new URL('/static/js/shared/mode-nav.js', document.baseURI));
            const audio = new Audio(new URL(filename, audioBase).href);
            audio.preload = 'auto';
            navigationVoices.set(filename, audio);
        }
        return navigationVoices.get(filename);
    };
    const playNavigationSound = mode => {
        const pool = pools[mode];
        if (!pool) return;
        const key = `newsmuncher.navigationSound.${mode}`;
        let previous = lastPlayed.get(mode);
        try { previous = previous || window.sessionStorage?.getItem(key); } catch (_) {}
        const candidates = pool.filter(filename => filename !== previous);
        const filename = candidates[Math.floor(Math.random() * candidates.length)];
        lastPlayed.set(mode, filename);
        try { window.sessionStorage?.setItem(key, filename); } catch (_) {}
        currentVoice?.pause();
        if (currentVoice) { try { currentVoice.currentTime = 0; } catch (_) {} }
        currentVoice = voice(filename);
        try { currentVoice.currentTime = 0; } catch (_) {}
        // Native Audio.play uses the existing shared master-mute controller.
        try { currentVoice.play().catch(() => {}); } catch (_) {}
    };
    document.querySelectorAll('.mode-nav-button').forEach(link => {
        (pools[link.dataset.navSound] || []).forEach(voice);
        link.addEventListener('click', async event => {
            if (event.defaultPrevented || event.button > 0 || event.metaKey || event.ctrlKey ||
                    event.shiftKey || event.altKey) return;
            playNavigationSound(link.dataset.navSound);
            if (!link.href) return; // The current-page span remains non-navigating.
            event.preventDefault();
            try { await window.creationTextSaver?.flush(); }
            catch (_) { return; }
            link.classList.add('mode-nav-clicked');
            window.setTimeout(() => window.location.assign(link.href), reduced() ? 0 : 170);
        });
    });
})();
