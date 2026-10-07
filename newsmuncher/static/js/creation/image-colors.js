/* One small sample per loaded image; animation is entirely CSS-driven. */
function representativeColors(pixels) {
    const buckets = new Map();
    for (let i = 0; i < pixels.length; i += 4) {
        const [r, g, b, a] = pixels.slice(i, i + 4);
        const brightness = (r + g + b) / 3;
        if (a < 192 || brightness < 30 || brightness > 225) continue;
        const key = [r, g, b].map(v => Math.floor(v / 32)).join(',');
        const entry = buckets.get(key) || {count: 0, rgb: [0, 0, 0]};
        entry.count++;
        entry.rgb[0] += r; entry.rgb[1] += g; entry.rgb[2] += b;
        buckets.set(key, entry);
    }
    const ranked = [...buckets.values()].sort((a, b) => b.count - a.count)
        .map(v => v.rgb.map(c => Math.round(c / v.count)));
    if (!ranked.length) return null;
    const first = ranked[0];
    const second = ranked.find(color => color.reduce((sum, c, i) => sum + (c - first[i]) ** 2, 0) > 6400);
    // For monochrome art, use a distinct muted fallback from the page palette.
    const distance = color => color.reduce((sum, c, i) => sum + (c - first[i]) ** 2, 0);
    const fallback = [[190, 183, 169], [103, 68, 180], [80, 130, 110]]
        .sort((a, b) => distance(b) - distance(a))[0];
    return [first, second || fallback];
}

function applyImageColors(img, isCurrent) {
    if (!isCurrent()) return;
    try {
        const canvas = document.createElement('canvas');
        canvas.width = canvas.height = 32;
        const ctx = canvas.getContext('2d', {willReadFrequently: true});
        ctx.drawImage(img, 0, 0, 32, 32);
        const colors = representativeColors(ctx.getImageData(0, 0, 32, 32).data);
        if (!colors || !isCurrent()) return;
        const layer = document.getElementById('imageAmbient');
        if (!layer) return;
        const groups = layer.children;
        const previous = groups[0].classList.contains('active') ? groups[0] : groups[1];
        const incoming = previous === groups[0] ? groups[1] : groups[0];
        incoming.classList.remove('active', 'spread');
        const rect = img.getBoundingClientRect();
        incoming.style.setProperty('--image-color-1', `rgb(${colors[0].join(',')})`);
        incoming.style.setProperty('--image-color-2', `rgb(${colors[1].join(',')})`);
        incoming.style.setProperty('--wash-x', `${Math.max(0, Math.min(window.innerWidth, rect.left + rect.width / 2))}px`);
        incoming.style.setProperty('--wash-y', `${Math.max(0, Math.min(window.innerHeight, rect.top + rect.height / 2))}px`);
        // Two fixed buffers crossfade; the previous wash remains visible while
        // the new pair spreads. No permanent layers accumulate.
        void incoming.offsetWidth;
        previous.classList.remove('active');
        incoming.classList.add('active', 'spread');
    } catch (_) {
        // Canvas/security/decoding failures must never affect the image or rewrite.
    }
}
