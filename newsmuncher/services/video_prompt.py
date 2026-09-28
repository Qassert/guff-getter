"""Small deterministic motion cues; no text-model call or source-article passthrough."""
import re

BASE = (
    'Preserve the original image, characters, composition and surreal style. '
    'Animate the existing scene with absurd but coherent, restrained but noticeable motion '
    'and gentle cinematic camera drift. Only animate subjects already visible in the image. '
    'Do not redesign the image, add unrelated characters or objects, add text, or significantly change faces.'
)
# Deliberately conservative: at most two scene cues for a five-second clip.
CUES = (
    (r'\bpenguins?\b', 'a penguin tilts its head in surprise'),
    (r'\bcupboards?\b', 'a cupboard door creaks open'),
    (r'\bbowling balls?\b', 'bowling balls roll a short distance'),
    (r'\b(cats?|kittens?)\b', 'a cat twitches its ears'),
    (r'\b(dogs?|pupp(?:y|ies))\b', 'a dog tilts its head'),
    (r'\b(birds?|pigeons?|ducks?)\b', 'a bird gently ruffles its feathers'),
    (r'\b(tea|soup|coffee)\b', 'a faint curl of steam rises'),
    (r'\b(trees?|flowers?|leaves)\b', 'foliage sways gently'),
    (r'\b(water|river|sea|lake)\b', 'small ripples travel across the water'),
    (r'\b(clouds?|smoke)\b', 'clouds or smoke drift slowly'),
    (r'\b(danc\w*|disco)\b', 'figures make a small rhythmic sway'),
    (r'\b(walk\w*|march\w*)\b', 'figures take one small step'),
)


def build_motion_prompt(result):
    text = ' '.join(str(result.get(k) or '')[:3500] for k in
                    ('crazyReplacement1Title', 'crazyReplacement1Extract'))
    cues = [cue for pattern, cue in CUES if re.search(pattern, text, re.I)][:2]
    return BASE + (' If visible: ' + '; '.join(cues) + '.' if cues else
                   ' Existing figures subtly react; visible materials move gently with the scene.')
