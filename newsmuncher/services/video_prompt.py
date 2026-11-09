"""Small deterministic motion cues; no text-model call or source-article passthrough."""
import re
import random


TRANSFORMATIONS = (
    {'id': 'comic_escalation',
     'end_direction': 'Escalate the established action into coherent, harmless comic chaos; props react and the principal figures struggle to retain dignity.',
     'motion_direction': 'Build continuously from calm order into brisk, harmless comic chaos.'},
    {'id': 'surreal_object_change',
     'end_direction': 'Transform one prominent object into a surprising but harmless physical form while every principal figure, key prop and the setting remain recognisable.',
     'motion_direction': 'Make the prominent object visibly and continuously reshape into its harmless surreal end state.'},
    {'id': 'unexpected_reveal',
     'end_direction': 'Reveal an unexpected harmless detail already concealed within the established setting, prompting a clear reaction from the principal figures.',
     'motion_direction': 'Use continuous movement to reveal the concealed comic detail and the figures’ reactions.'},
    {'id': 'prop_springs_to_life',
     'end_direction': 'Bring the principal machine or prop into energetic harmless action, with secondary objects responding physically around it.',
     'motion_direction': 'Animate the principal prop springing into action and causing coherent secondary motion.'},
    {'id': 'surreal_intrusion',
     'end_direction': 'Introduce one unexpected harmless everyday object into the same scene and make it interact coherently with the existing action.',
     'motion_direction': 'Bring one harmless everyday object into view through continuous physical motion, without cuts or replacement pop-ins.'},
)


def choose_transformation(exclude=None):
    eligible = [item for item in TRANSFORMATIONS if item['id'] != exclude] or list(TRANSFORMATIONS)
    return dict(random.choice(eligible))

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


def build_transition_prompt(result, shared_visual_style=None, transformation=None):
    """Motion direction for independent first/last-frame conditioning."""
    style = (f' Both endpoint images belong to the same visual world: {shared_visual_style}. '
             'Maintain that exact artistic medium, lighting, colour treatment, era and texture '
             'throughout the animation.' if shared_visual_style else '')
    direction = (transformation or {}).get(
        'motion_direction', 'Advance the established physical action into a clear harmless comic payoff.')
    return (
        'Begin exactly from the supplied first image and finish exactly at the supplied last image. '
        'Create one continuous surreal cinematic transformation between them, never a cut or dissolve. '
        'Let visible objects morph into unrelated objects, creatures and faces transform, scenery melt '
        'and reform, objects split and merge, scale changes, textures transform, colours flow between '
        'scenes, and physical structures reshape through strange intermediate forms. Use lively camera '
        'movement where it helps the journey, while keeping the camera reasonably coherent. The middle '
        'may be wildly imaginative, but strongly preserve the supplied opening and ending frames. '
        'Corresponding objects must physically morph into each other; do not use cuts, crossfades, '
        'dissolves, scene changes, teleportation, disappearances or replacement pop-ins. '
        f'Chosen transformation: {direction}' + style
    )
