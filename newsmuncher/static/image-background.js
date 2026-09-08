/* Reuses stored image URLs only. Two slots, one passive scroll listener. */
const generatedBackground = (() => {
    let active = -1;
    let revision = 0;
    let queued = false;
    let lastURL = null;
    const layer = () => document.getElementById('generatedBackdrop');

    function updateScroll() {
        queued = false;
        if (active < 0 || !layer()) return;
        const result = document.getElementById('outputContainer');
        const y = window.scrollY || 0;
        const viewport = window.innerHeight;
        const resultTop = result.getBoundingClientRect().top + y;
        const available = Math.max(1, document.documentElement.scrollHeight - viewport);
        const end = Math.max(1, Math.min(available, resultTop - viewport * .35));
        const progress = Math.max(0, Math.min(1, y / end));
        document.body.style.setProperty('--generated-background-progress', String(progress));
    }

    function scheduleScroll() {
        if (queued) return;
        queued = true;
        requestAnimationFrame(updateScroll);
    }

    function preload(url, isCurrent) {
        if (!isCurrent() || !layer()) return;
        const token = ++revision;
        if (url === lastURL) { updateScroll(); return; }
        const image = new Image();
        image.alt = '';
        image.onload = () => {
            if (token !== revision || !isCurrent()) return;
            const slots = layer().children;
            const next = active === 0 ? 1 : 0;
            const incoming = slots[next];
            const outgoing = active < 0 ? null : slots[active];
            // Reuse the loaded Image itself so activation cannot expose an unloaded src.
            incoming.style.transition = 'none';
            incoming.style.opacity = '0';
            incoming.style.zIndex = '1';
            incoming.replaceChildren(image);
            if (outgoing) {
                outgoing.style.zIndex = '0';
                outgoing.style.opacity = '1';
            }
            void incoming.offsetWidth;
            incoming.style.transition = '';
            incoming.style.opacity = '1';
            active = next;
            lastURL = url;
            // Handles arrival after the user has already scrolled to the result.
            updateScroll();
        };
        image.onerror = () => {}; // Keep the previous artwork; never expose a broken slot.
        image.src = url;
    }

    window.addEventListener('scroll', scheduleScroll, {passive: true});
    window.addEventListener('resize', scheduleScroll);
    window.addEventListener('pageshow', scheduleScroll);
    return {preload};
})();
