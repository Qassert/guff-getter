"""Offline derivatives only: preserve supplied originals; requires ffmpeg, numpy, scipy.

Usage: python prepare_mad_helper.py SOURCE_DIRECTORY OUTPUT_DIRECTORY
No network or model calls. Runtime application has no additional dependencies.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import numpy as np
from scipy import ndimage

SIZE = 320
FPS = 20


def matte(rgb):
    """Remove neutral background, including sheltered hair and leg-gap cavities.

    Enclosed eyes/teeth remain opaque. Unmatte the thin antialiased boundary
    against white; do not globally key out the character's white details.
    """
    low, high = rgb.min(axis=2), rgb.max(axis=2)
    candidate = (low > 210) & ((high.astype(int) - low) < 28)
    seeds = np.zeros_like(candidate)
    seeds[[0, -1], :] = candidate[[0, -1], :]
    seeds[:, [0, -1]] = candidate[:, [0, -1]]
    background = ndimage.binary_propagation(seeds, mask=candidate)
    # White regions enclosed by hair loops and the legs cannot reach the canvas edge.
    # Restrict extra seeds to the supplied character's hair/leg-gap geometry, never
    # the eyes, teeth or torso. Narrow, tall lower components distinguish the gap
    # from bright buttons/cuffs; propagation handles its grey matte boundary.
    neutral = high.astype(int) - low
    bright = (low > 235) & (neutral < 22)
    labels, _ = ndimage.label(bright)
    extra = np.zeros_like(background)
    height, width = low.shape
    for label, bounds in enumerate(ndimage.find_objects(labels), 1):
        if bounds is None:
            continue
        ys, xs = bounds
        count = np.count_nonzero(labels[bounds] == label)
        hair_gap = ys.stop < height * .22 and count >= 12
        leg_gap = (ys.start >= height * .78 and ys.stop >= height * .90
            and ys.stop - ys.start >= height * .08
            and xs.stop - xs.start <= width * .16
            and xs.start >= width * .25 and xs.stop <= width * .75 and count >= 12)
        if hair_gap or leg_gap:
            extra[bounds] |= labels[bounds] == label
    yy, xx = np.indices(low.shape)
    lower_corridor = (yy >= height * .78) & (xx >= width * .25) & (xx <= width * .75)
    relaxed = candidate | (lower_corridor & (low > 190) & (neutral < 36))
    background |= ndimage.binary_propagation(extra, mask=relaxed)
    edge = ndimage.binary_dilation(background, iterations=2) & ~background
    alpha = np.ones(low.shape, dtype=np.float32)
    alpha[background] = 0
    alpha[edge] = np.clip((255 - low[edge].astype(float)) / 55, 0, 1)
    colour = rgb.astype(np.float32)
    visible = alpha > 0
    colour[visible] = (colour[visible] - 255 * (1 - alpha[visible, None])) / alpha[visible, None]
    colour[~visible] = 0
    return np.dstack((np.clip(colour, 0, 255).astype('uint8'), (alpha * 255).astype('uint8')))


def frames(source):
    decoder = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', str(source), '-vf',
        f'fps={FPS},scale={SIZE}:{SIZE}:flags=lanczos', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], stdout=subprocess.PIPE)
    try:
        while True:
            raw = decoder.stdout.read(SIZE * SIZE * 3)
            if not raw:
                break
            if len(raw) != SIZE * SIZE * 3:
                raise RuntimeError('Incomplete decoded frame')
            yield matte(np.frombuffer(raw, dtype='uint8').reshape(SIZE, SIZE, 3)).tobytes()
    finally:
        decoder.stdout.close()
        if decoder.wait():
            raise RuntimeError(f'Failed decoding {source.name}')


def prepare(source, output):
    source, output = Path(source), Path(output)
    pngs, clips = sorted(source.glob('*.png')), sorted(source.glob('*.mp4'))
    if len(pngs) != 1 or len(clips) != 16:
        raise ValueError('Expected one PNG and sixteen MP4 originals')
    output.mkdir(parents=True, exist_ok=True)
    common = ['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgba', '-s', f'{SIZE}x{SIZE}', '-r', str(FPS), '-i', '-']
    base = next(frames(pngs[0]))
    subprocess.run(common + ['-frames:v', '1', str(output / 'idle.png')], input=base, check=True)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i',
        'color=white:s=16x16:d=0.2,format=rgba,colorchannelmixer=aa=0', '-an',
        '-c:v', 'libvpx-vp9', '-pix_fmt', 'yuva420p', str(output / 'alpha-probe.webm')], check=True)
    manifest = {'revision': 'refined-3', 'png': 'idle.png', 'width': SIZE, 'height': SIZE, 'fps': FPS, 'animations': [],
                'originals': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in pngs + clips}}
    for index, clip in enumerate(clips, 1):
        name = f'animation-{index:02d}'
        encoders = [
            subprocess.Popen(common + ['-an', '-c:v', 'libvpx-vp9', '-pix_fmt', 'yuva420p', '-crf', '32', '-b:v', '0', '-deadline', 'good', '-cpu-used', '4', '-threads', '2', str(output / (name + '.webm'))], stdin=subprocess.PIPE),
            subprocess.Popen(common + ['-an', '-c:v', 'libwebp_anim', '-quality', '80', '-loop', '1', str(output / (name + '.webp'))], stdin=subprocess.PIPE)
        ]
        count = 0
        try:
            for raw in frames(clip):
                for encoder in encoders:
                    encoder.stdin.write(raw)
                count += 1
        finally:
            for encoder in encoders:
                encoder.stdin.close()
            codes = [encoder.wait() for encoder in encoders]
        if any(codes) or not count:
            raise RuntimeError(f'Failed encoding {clip.name}')
        manifest['animations'].append({'webm': name + '.webm', 'fallback': name + '.webp', 'duration': count / FPS})
        print(f'{index}/16 {clip.name}: {count/FPS:.2f}s', flush=True)
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')


if __name__ == '__main__':
    prepare(*sys.argv[1:])
