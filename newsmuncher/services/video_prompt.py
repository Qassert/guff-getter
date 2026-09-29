"""Small deterministic motion cues; no text-model call or source-article passthrough."""
import re

BASE = (
    'Preserve the original image, characters, composition and surreal style. '
    'Animate with deliberately brisk, comic-book energy: movement at roughly 1.2x natural speed, '
    'physically coherent but slightly accelerated for comic effect. '
    'Begin action in the very first frame — no slow establishing start. '
    'Pack noticeably more actions, reactions and movement into the full 8 seconds: '
    'characters react to each other, objects shift and settle, secondary details flutter or bounce. '
    'Avoid long pauses, static poses, slow motion and slow camera movements. '
    'Use a lively cinematic camera — slight push, pan or dutch-tilt — that keeps changing. '
    'Only animate subjects already visible in the image. '
    'Do not redesign the image, add unrelated characters or objects, add text, or significantly change faces.'
)
# Up to three scene cues for the 8-second clip.
CUES = (
    (r'\bpenguins?\b', 'a penguin snaps its head round in surprise then waddles one step'),
    (r'\bcupboards?\b', 'a cupboard door swings open and a second door rattles'),
    (r'\bbowling balls?\b', 'bowling balls roll briskly across the frame'),
    (r'\b(cats?|kittens?)\b', 'a cat twitches its ears, flicks its tail and glances sharply sideways'),
    (r'\b(dogs?|pupp(?:y|ies))\b', 'a dog tilts its head then spins a tight half-circle'),
    (r'\b(birds?|pigeons?|ducks?)\b', 'a bird ruffles its feathers, hops and pecks briskly'),
    (r'\b(tea|soup|coffee)\b', 'steam rises in a quick swirl; the cup rattles on its saucer'),
    (r'\b(trees?|flowers?|leaves)\b', 'foliage whips in a sudden gust then settles'),
    (r'\b(water|river|sea|lake)\b', 'ripples race across the water surface'),
    (r'\b(clouds?|smoke)\b', 'clouds or smoke billow and churn quickly'),
    (r'\b(danc\w*|disco)\b', 'figures break into a rapid, exaggerated rhythmic sway'),
    (r'\b(walk\w*|march\w*)\b', 'figures stride briskly, arms swinging with comic purpose'),
)


def build_motion_prompt(result):
    text = ' '.join(str(result.get(k) or '')[:3500] for k in
                    ('crazyReplacement1Title', 'crazyReplacement1Extract'))
    cues = [cue for pattern, cue in CUES if re.search(pattern, text, re.I)][:3]
    return BASE + (' If visible: ' + '; '.join(cues) + '.' if cues else
                   ' Existing figures react expressively to each other; visible materials bounce, '
                   'shift and settle with brisk comic energy throughout.')
