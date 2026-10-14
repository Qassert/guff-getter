# NewsMuncher Phase 4N — thematic diversity investigation

Date: 2026-10-12

## Scope

This investigation used the existing prompts, catalogues, selectors, Phase 4L
evidence and Phase 4M live results. It made no provider call and touched no
production data. Comedy quality, coherence and offensiveness were not scored.
The creative target remains surreal, rude, specific and unpredictable.

## Where the present themes enter

The fixed rewrite prompt does not name gravy, custard, marmalade, bunting,
parliament, councils or milk floats as examples. Its explicit thematic content
is broad: deadpan seriousness, bizarre specificity, ridiculous motivations,
strange consequences, mundane details, rapid escalation and tabloid headlines.
It also tells the model to replace most important nouns and to invent additional
bizarre language. Those instructions strongly encourage ingredient uptake and
model improvisation, but they do not prescribe the familiar vocabulary.

The narrow themes enter chiefly through generated ingredients. Concept
selection fills hard category quotas from seven categories. A 20-concept slate
therefore repeatedly reserves space for cheeky objects, impossible inventions,
ridiculous creatures, bureaucracy, emergency equipment and ceremonial objects.
Its seven current category templates branch into more mechanisms, but many
joke-bearing modifier banks still contain only three entries. Large base-object
and creature banks consequently produce unique phrases inside familiar comic
frames.

Descriptor selection has 24 templates and much larger subject/component banks,
but fixes 70% of its slate to `cheeky_british`, 30% to `broader_absurdity`, and
also fills all six grammatical roles. Its quality score explicitly rewards
legal restriction, institutional interference, secret history, medical advice,
impossible abilities and related mechanisms. This gives reliable grammatical
and comic output while repeatedly exposing a limited set of worlds.

Invented names, the expanded catalogue and the historical CSV banks add broad
surface vocabulary through independent routes. Phase 4L counted 2,331 unique
noun texts and 2,575 unique historical mixed animal/object texts. Those banks
are not the limiting capacity. Selection templates and prompt salience turn a
large lexical pool into a much smaller effective conceptual pool.

## Evidence from actual articles

The Phase 4K evidence contained nearly unique offers: baseline A offered 140
unique concept phrases and 138 unique bases, and 279 of 280 descriptors across
the experiment were unique. Even so, 72.1% of A's concept offers belonged to
four themes: institutional control, impossible technology, innuendo and
unexpected behaviour. Exact uniqueness was therefore masking thematic
concentration.

Phase 4M's 36 finished articles broadened offered meaningful vocabulary by
7.34%, but final unique meaningful words rose only 1.90%. Final gravy and
custard article counts were unchanged. Some watched words had no same-article
source or ingredient occurrence and were already present in the first-pass
rewrite. The model therefore independently returns to a learned interpretation
of British surreal comedy as well as amplifying supplied ingredients.

The copy-edit pass receives only the first-pass article and is instructed to
preserve its ideas. Phase 4M found that it introduced none of the six watched
expressions. The least disruptive intervention point is consequently the
existing optional guidance section of the first-pass prompt, before model-side
invention occurs. It can add conceptual territory without changing the core
prompt, the two-pass architecture or provider-call count.

## Sampling, quotas and memory

Concept and descriptor generators use seeded randomness, but candidate quality,
hard category quotas and grammatical-role constraints narrow the candidates
that reach the prompt. Ranking is thus a material cause even where raw sampling
is random. Phase 4M makes component selection exposure-aware, but its lexical
ledger operates on words and compact identities rather than broad conceptual
territory.

Existing phrase, base, premise, semantic, topic, final-joke and lexical memories
serve separate purposes. None maintains a complete rotating inventory of
botany, theatre, metallurgy, navigation, acoustics or other conceptual domains.
A new layer should remain advisory so it does not interfere with their leases,
cooldowns, hard quotas or source exemptions.

## Design conclusion

The evidence supports an additive, default-off thematic sampler at the existing
first-pass guidance insertion point. It should select a few unrelated domains,
retain every domain at a nonzero weight, penalize recent domains and families,
and remember selections per anonymized pet in bounded persistent storage. The
model must be free to ignore or distort every suggestion. This targets missing
conceptual breadth while preserving the engine that currently produces the
humour.

The catalogue must also be balanced above the individual-domain level. A
hundred scientific labels alone would merely create a new formula. The Phase 4N
catalogue therefore spans 11 families: living systems; cosmos and physics;
earth and atmosphere; past societies; culture and language; built systems;
medicine and mind; abstract technology; performance arts; crafts and materials;
and field practices.

Offline selection measurements can establish coverage, concentration,
persistence and recency behaviour. They cannot establish that thematic hints
appear in provider output or that readers find the resulting articles funnier.
That requires a separately approved blind live experiment after review.
