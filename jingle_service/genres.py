"""Editable jingle arrangement presets, not definitive genre tempo classifications.

BPMs are conservative representative targets, not measured facts. Broad styles
(Opera, Jazz, Gospel, Ambient, Flamenco, Heavy Metal, Hardcore) are especially
approximate; Flamenco uses a simple 4/4 tangos arrangement, not a 12-beat compas.
All presets choose 4/4 deliberately for these short jingles. No genre redraw at
inference: the full selected profile is persisted in the brief.
"""
from jingle_service.contract import GenreProfile

# Retain historical profiles for direct references and stored experiments.
_PRESETS = [
    ('Drum and Bass', 174, 'fast broken drums; rolling sub bass; chopped vocal hook'),
    ('Opera', 90, 'prominent clear operatic lead vocal; orchestral strings; sustained sung phrases'),
    ('Heavy Metal', 140, 'distorted guitar riffs; electric bass; double-kick drums; clear forceful sung/shouted lead vocal'),
    ('Jazz', 120, 'swung ride cymbal; upright bass; piano comping; brass; sung hook'),
    ('Synthwave', 100, 'analog synth arpeggios; gated snare; pulsing synth bass; sung hook'),
    ('Reggae', 80, 'one-drop drums; offbeat guitar skank; deep bass; clear relaxed sung lead vocal'),
    ('Flamenco', 100, 'tangos rhythm; nylon-string guitar; palmas; expressive singing'),
    ('Techno', 130, 'four-on-the-floor kick; sequenced synth; metallic percussion; sparse vocals'),
    ('Gospel', 100, 'prominent clear sung lead vocal; backing choir call-and-response; Hammond organ; piano; handclaps'),
    ('Ambient', 70, 'slow evolving pads; sustained drones; spacious sparse vocals; minimal percussion'),
    ('Neurofunk', 174, 'broken drums; modulated reese bass; precise syncopation; chopped vocals'),
    ('Speed Garage', 135, 'swung four-on-the-floor drums; wobbling sub bass; pitched vocal chops'),
    ('Liquid Funk', 174, 'rolling breakbeats; warm sub bass; soulful keys; melodic vocals'),
    ('Jump Up', 175, 'drum-and-bass breaks; bouncy bass stabs; short vocal chants'),
    ('Footwork', 160, 'syncopated drum-machine kicks; rapid claps; repeated vocal chops'),
    ('Jungle', 165, 'chopped Amen breaks; dub sub bass; reggae vocal fragments'),
    ('Tech House', 125, 'four-on-the-floor drums; tight bass loop; percussion; sparse vocal hook'),
    ('Deep House', 120, 'four-on-the-floor drums; warm chords; rounded bass; soulful vocal hook'),
    ('Acid House', 125, 'dominant Roland TB-303 acid bassline; TR-909 four-on-the-floor drums; open hats and clap; repetitive hypnotic groove; sparse vocal chants'),
    ('Psytrance', 145, 'rolling sixteenth-note bass; four-on-the-floor kick; squelchy synth sequences; sparse vocals'),
    ('Uplifting Trance', 138, 'four-on-the-floor kick; supersaw lead; arpeggios; melodic vocal hook'),
    ('Hardstyle', 150, 'pitched distorted kicks; reverse bass; supersaw melody; shouted hook'),
    ('Gabber', 180, 'distorted pounding kicks; hoover synth; rapid percussion; shouted chants'),
    ('Dubstep', 140, 'halftime snare; sub bass; modulated bass growls; sparse vocal hook'),
    ('Riddim', 140, 'halftime drums; repetitive syncopated bass motif; sparse vocal chops'),
    ('Glitch Hop', 100, 'halftime funk drums; glitch edits; syncopated bass; chopped vocals'),
    ('Breakbeat', 130, 'syncopated sampled breaks; driving bass; short vocal hook'),
    ('Big Beat', 125, 'heavy sampled drum breaks; distorted bass; synth riff; repeated vocal hook'),
    ('UK Funky', 130, 'syncopated house drums; congas; sub bass; call-and-response vocals'),
    ('Grime', 140, 'sparse syncopated drums; square-wave bass; sharp synth stabs; rhythmic rap'),
    ('2-Step Garage', 130, 'skipping two-step drums; swung hats; sub bass; chopped soulful vocals'),
    ('Hardcore', 175, 'rave synth stabs; distorted electronic kicks; fast percussion; shouted hook'),
    ('Frenchcore', 200, 'fast distorted offbeat kicks; pitched bass; rave synth; brief shouted hook'),
    ('Minimal Techno', 125, 'four-on-the-floor kick; sparse clicks; repeating bass pulse; minimal vocals'),
    ('Electro Swing', 125, 'swung brass samples; walking bass; electronic kick; jazzy vocal hook'),
    ('Country', 110, 'clear storytelling lead vocal; acoustic guitar; fiddle and pedal steel; steady drums'),
    ('Folk', 95, 'clear intimate sung lead vocal; fingerpicked acoustic guitar; acoustic bass'),
    ('Punk Rock', 165, 'clear energetic sung lead vocal; power-chord guitars; driving bass and drums'),
    ('Pop Rock', 120, 'clear melodic sung lead vocal; guitar chords; electric bass; steady drums'),
    ('Indie Rock', 115, 'clear conversational sung lead vocal; jangling guitars; bass; live drums'),
    ('Glam Rock', 125, 'clear theatrical sung lead vocal; stomping drums; crunchy guitars; backing harmonies'),
    ('Blues', 90, 'clear expressive sung lead vocal; shuffle drums; blues guitar; walking bass'),
    ('Soul', 100, 'clear soulful sung lead vocal; warm organ; bass groove; drums; backing harmonies'),
    ('Funk', 110, 'clear rhythmic sung lead vocal; syncopated bass; clipped guitar; tight drums'),
    ('Ska', 145, 'clear upbeat sung lead vocal; offbeat guitar; walking bass; brass; brisk drums'),
    ('Rockabilly', 150, 'clear rhythmic sung lead vocal; twangy guitar; slapped upright bass; snare'),
    ('Bluegrass', 140, 'clear storytelling sung lead vocal; banjo rolls; fiddle; mandolin; upright bass'),
    ('Musical Theatre', 110, 'clear theatrical sung lead vocal with crisp diction; piano; orchestral accompaniment'),
    ('Power Ballad', 75, 'clear soaring sung lead vocal; piano; sustained electric guitar; slow rock drums'),
    ('Disco', 120, 'clear melodic sung lead vocal; four-on-the-floor drums; octave bass; strings; rhythm guitar'),
    ('Electro-pop', 115, 'clear melodic sung lead vocal; synth chords; electronic drums; pulsing bass'),
]
GENRE_PROFILES = {
    label: GenreProfile(label=label, bpm=bpm, timesignature='4', cues=cues,
                        avoid='pop, rock or orchestral arrangement' if label == 'Acid House' else '')
    for label, bpm, cues in _PRESETS
}
# Production selection only. Existing serialized profile snapshots remain unchanged.
GENRES = [
    'Country', 'Folk', 'Heavy Metal', 'Punk Rock', 'Pop Rock', 'Indie Rock',
    'Glam Rock', 'Blues', 'Soul', 'Funk', 'Gospel', 'Ska', 'Reggae',
    'Rockabilly', 'Bluegrass', 'Musical Theatre', 'Opera', 'Power Ballad',
    'Disco', 'Electro-pop',
]
