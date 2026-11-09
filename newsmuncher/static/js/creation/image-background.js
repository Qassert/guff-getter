/* Reuses stored image URLs only. Two crossfade slots, independent of scrolling. */
const generatedBackground = (() => {
    let active = -1;
    let revision = 0;
    let lastURL = null;
    const layer = () => document.getElementById('generatedBackdrop');

    function preload(url, isCurrent) {
        if (!isCurrent() || !layer()) return;
        const token = ++revision;
        if (url === lastURL) return;
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
        };
        image.onerror = () => {}; // Keep the previous artwork; never expose a broken slot.
        image.src = url;
    }

    async function loadInitial() {
        const initial = document.getElementById('initialBackground');
        if (!initial) return;
        try {
            const response = await fetch('/profile-background', {cache: 'no-store'});
            if (!response.ok) return;
            const data = await response.json();
            if (!data || !data.image_url || active >= 0) return;
            const image = new Image();
            image.alt = '';
            image.onload = () => {
                // A late startup request must not replace newer generated artwork.
                if (active >= 0) return;
                initial.replaceChildren(image);
                if (typeof applyImageColors === 'function') {
                    applyImageColors(image, () => active < 0);
                }
            };
            image.onerror = () => {}; // Warm paper remains if the file disappeared.
            image.src = data.image_url;
        } catch (_) {
            // A failed metadata request must never affect the working page.
        }
    }

    window.addEventListener('DOMContentLoaded', loadInitial);
    return {preload};
})();
