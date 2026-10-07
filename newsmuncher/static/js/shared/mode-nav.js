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
    document.querySelectorAll('.mode-nav-button[href]').forEach(link => {
        link.addEventListener('click', event => {
            if (event.defaultPrevented || event.button > 0 || event.metaKey || event.ctrlKey ||
                    event.shiftKey || event.altKey) return;
            const sound = link.dataset.squelch;
            if (sound) {
                const audio = new Audio(sound);
                audio.play().catch(() => {});
            }
            if (reduced()) return;
            event.preventDefault();
            link.classList.add('mode-nav-clicked');
            window.setTimeout(() => window.location.assign(link.href), 170);
        });
    });
})();
