# NewsMuncher Phase 4O — theme-informed ingredient selection investigation

Date: 2026-10-12
Status: investigation and design only

## Scope and conclusion

This investigation traced the current source-to-final pipeline, inspected the
Phase 4N implementation and existing local audits, measured generator behaviour
over 100 provider-free slates, and compared three theme-informed architectures.
It made no generation change, provider call, production-data access, default
change, commit or push.

The central finding is direct: Phase 4N themes currently influence only a short
optional first-pass prompt paragraph. They do not influence any ingredient
candidate, component choice, quality score, ranking decision, quota or name.
At the same time, the prompt contains 20 generated concepts, ten generated
descriptors, ten invented names and other word-bank material whose use is
explicitly encouraged. That concrete ingredient mass can readily outweigh four
abstract thematic suggestions.

The recommended next experiment is a **hybrid seed approach**. Give every domain
small typed banks of entities, processes, properties and relationships, then
use a few selected seeds to construct or enrich a minority of the existing
ingredient slate through generic cross-domain combinators. Keep the current
ingredients, quotas, safety checks and ranking as the baseline stratum. Do not
create one bespoke joke template per domain and do not require the model to use
the selected themes.

## Complete ingredient and rewrite journey

### 1. Source article

`prepare_prompt()` preserves the original, masks detected source identities,
filters those identities from random banks and builds the title/extract passed
to the first model (`newsmuncher/utils/clean_data.py:205-315`). Source vocabulary
can survive because the rewrite must preserve the core event, but Phase 4L and
4M source-aware measurements showed that recurring gravy, custard and similar
material often entered elsewhere. Phase 4M's source exemptions correctly stop
its lexical ledger from punishing facts required by the article.

### 2. Concepts

The generated concept path fills fixed largest-remainder category plans
(`comedy_concepts.py:29-38, 325-336`). For each 20-concept generation this means
four cheeky objects, four inventions, four creatures, three everyday-British
objects, three bureaucratic premises, one emergency item and one ceremonial
item. The registry separately enforces exact noun/animal target quotas and
leases phrases, bases, premises and species (`concept_selection.py:73-179`).

Templates choose a base plus a modifier or topic from curated component banks
(`comedy_concepts.py:222-266`). Several visible anchor phrases are literal
resources: `coup-planning` is in the concept components at line 565,
`licensed royal footman` at line 772, and `coup-planning regional governor` at
line 781. “Powered” is a first-class invention mechanism rather than merely a
model habit.

The catalogue can greatly expand bases, but it does not expand all modifier and
mechanism banks. Unique appliances or animals can therefore occupy the same
powered, official, ceremonial or office-holding construction.

### 3. Descriptors

Descriptors hard-allocate 70% of every slate to `cheeky_british` and 30% to
`broader_absurdity`, plus 30/45/25 intensity proportions and all six grammatical
roles (`comedy_descriptors.py:15-18, 275-320`). The broad candidate pool helps
availability, but its final assembly must still satisfy those constraints.

Descriptor component banks independently contain council, committee, tribunal,
royal, ceremonial, kettle, gravy and marmalade material. This means the same
reader-visible world can arrive through concepts or descriptors despite unique
complete phrases.

### 4. Names and modifiers

Name recipes choose between cheeky and absurd styles, with recipe-specific
weights (`comedy_names.py:160-166, 286-293`). Quality rewards two-to-six spoken
words, alliteration, medium length and hyphenation (`comedy_names.py:167-187`).
The title list in the scorer removes Sir, Lady, Lord, Dame, Baron and related
words before its length check. Those titles are therefore structurally cheap,
while the resource contains royal, council, kettle, gravy, custard and
marmalade components.

The name registry avoids exact names and recent sound families but does not know
the four Phase 4N domains (`name_selection.py:124-217`). It cannot prefer a
mycological name component or avoid another aristocratic social role because a
theme was selected.

### 5. Quality filtering and ranking

Concept candidates receive a high common visual score, a compact-length bonus,
an intensity bonus, another bonus for strong compact creatures, and a specific
0.5 bonus for bureaucracy (`comedy_concepts.py:245-254`). Each quota slot draws
a bounded pool and takes the highest score before considering underused bases
and themes (`comedy_concepts.py:349-392`). “Monitored recurring theme” is only an
editorial warning; it does not lower the score (`comedy_concepts.py:255-262`).

Descriptors similarly reward compactness and add 0.45 to an explicit set of
proven mechanisms including legal restriction, institutional interference,
medical advice, impossible ability, secret history and contradiction
(`comedy_descriptors.py:173-188`). In evaluation mode final assembly introduces
seeded jitter ahead of quality, but the candidate pool is already constructed
from the existing templates and banks.

Names select the maximum adjusted quality candidate from each pool
(`comedy_names.py:338-379`). Phase 4M lexical penalties affect component
probability, but Phase 4N selections never enter those calls.

### 6. Prompt construction

The route selects themes before concepts, proving that theme-informed selection
is architecturally possible without another read or provider call
(`previews.py:244-257`). It then discards that context for ingredient purposes:
concepts receive topic and lexical penalties, descriptors receive concept-theme,
topic and lexical penalties, and names receive name-family recency. Only at
`previews.py:370-383` is `thematic_guidance` joined with the other optional
guidance.

The fixed prompt tells the model to replace most names, places, significant
nouns, adjectives and adverbs, to use several supplied words, and to invent
additional bizarre language (`resources/prompts/rewrite.txt:15-26, 46-80`).
Twenty concepts and ten descriptors are therefore concrete high-salience
choices. Four thematic springboards compete with them but have no guaranteed
ingredient embodiment.

### 7. First-pass generation

The first pass is the only model stage that sees source, ingredients and Phase
4N guidance. Phase 4M live evidence established that it independently
introduced familiar vocabulary even without a same-article offer. Repetition
is therefore jointly caused by ingredient supply and the model's learned
interpretation of British surreal comedy.

### 8. Copy-editing

The copy editor receives only the first-pass extract and is instructed to
preserve every strange object, event and relationship while introducing no new
subjects, objects, events or ideas (`clean_data.py:399-469`). Phase 4M found
that none of its six watched expressions originated in this pass. Copy editing
can remove or rephrase a thematic trace, but it is not the main source of the
familiar constructions.

### 9. Final article and memory

After successful persistence, exact concept/descriptor/name memory, topic
memory, lexical memory and thematic memory are updated. Phase 4N records the
selected IDs/families and conservatively detects selected-domain keywords in
final text that were absent from the source (`thematic_diversity.py:67-88`,
`previews.py:522-565`). This can measure literal survival, not paraphrased or
conceptual influence.

## Where repetition originates

The component catalogues contain multiple independent copies of the familiar
palette. Literal token-family counts in the three core resources are:

| Anchor | Concepts | Descriptors | Names |
|---|---:|---:|---:|
| royal | 12 | 3 | 3 |
| council | 4 | 3 | 10 |
| committee | 4 | 7 | 0 |
| tribunal | 3 | 2 | 0 |
| ceremonial* | 22 | 16 | 1 |
| parliament* | 18 | 0 | 0 |
| kettle | 6 | 7 | 4 |
| gravy | 16 | 7 | 6 |
| custard | 6 | 1 | 2 |
| marmalade | 5 | 3 | 2 |

These are resource occurrences rather than selection probabilities, but they
show why phrase memory alone cannot remove the shared palette.

A provider-free 100-slate sample made the ranking effect visible. Its 2,000
concepts contained the exact hard category counts expected from configuration.
The most selected templates were `strong_compact_creature` 344 times,
`self_acting_device` 209, `cheeky_modifier_object` 201, `powered_device` 169,
`document_for_absurdity` 153 and `body_for_absurdity` 147. The top mechanisms
were unexpected behaviour 470, British innuendo 304, absurd capability 209,
improbable power 169 and the two institutional mechanisms 300 combined.

The production-shaped descriptor assembly sample contained the hard 700/300
category split. Of 1,000 outputs, class/etiquette accounted for 93, peculiar
habit 88, cosmic motivation 86, competition-ban secret history 78, comic
contradiction 76, disproportionate emotion 73 and ritual status 71. Mistaken
relationship appeared once, irrational fear five times and petty grievance six
times. Phase 4F's diversified assembly spreads mechanisms much better than raw
highest-score generation, but effective use remains unequal.

The model adds a third source. Phase 4L found four gravy articles and four
marmalade articles with no same-article source or recorded offer. Phase 4M
confirmed first-pass model invention and found that ingredient diversity gains
transmitted only partially into final text. Source inheritance is real for
source-required vocabulary but does not explain the recurring comic anchors in
the neutral fixtures.

## What Phase 4N currently changes

The 100-domain catalogue stores only `id`, `family`, `label`, one inspiration
string and influence keywords. It has no typed entities, processes, properties,
relationships, grammar or ingredient compatibility metadata.

Current effects are:

1. select four domains with soft domain/family recency;
2. render their inspiration strings as optional first-pass guidance;
3. after successful persistence, record the selection;
4. detect literal final keywords absent from the source;
5. optionally include selection and influence metadata in the local audit.

Current non-effects are equally important: themes do not alter concept or
descriptor candidate pools, raw identities, names, modifiers, category quotas,
scores, ranking, leases or cooldowns.

No existing local JSONL audit contains a `thematic_diversity` record. The Phase
4I, 4K and 4M records all predate Phase 4N. Consequently there is no actual
article evidence yet for theme uptake. The offline Phase 4N audit proves fair
domain rotation only; it cannot show that prompt mention influences final copy.

Existing ingredients can overwhelm the guidance because they are numerous,
fully phrased, explicitly labelled as material to use, and reinforced by
quality-selected constructions. A broad phrase such as “fungal networks” has
less operational weight than a ready-made `coup-planning regional governor`.

## Quality ranking: validity versus familiarity

The present system can distinguish several technical defects: blocked terms,
bad word count, repeated words, missing bases, invalid roles/templates,
awkward joins and scores below a minimum. Those gates should remain hard.

It does not reliably distinguish familiar from surprising. Familiarity is often
positively correlated with score because compact, visual and proven templates
were deliberately rewarded. Conversely, an unfamiliar but grammatical
cross-domain construction may be longer than six words and lose the compactness
bonus, or exceed eight words and receive a two-point concept penalty. The
`monitored recurring theme` warning has no ranking consequence.

Future experimentation should separate three axes rather than replace the
quality score:

* **validity gate:** grammar, blocked content, visible base, length ceiling and
  template compatibility;
* **editorial quality stratum:** the existing score within a deliberately broad
  acceptable band;
* **exploration preference:** soft domain relevance, cross-domain novelty and
  recent exposure, with a nonzero baseline probability.

This avoids treating unfamiliarity as malformedness. Theme relevance should
not be a permanent score bonus, because that would repeatedly elevate the same
seed whenever its domain returns.

## Architectural options

| Approach | Diversity potential | Main risk | Complexity | Existing-system fit |
|---|---|---|---|---|
| A. Tag existing ingredients | Moderate. Can surface underused catalogue entries already relevant to a domain. | Sparse/subjective tags and little help for processes or relationships; tagging favourite phrases may preserve their structures. | High editorial migration across large resources. | Good for selectors and Phase 4M; weak alone. |
| B. Domain-specific conceptual seeds | High. Adds processes, properties and relationships absent from object banks. | A fixed domain-to-joke mapping could create 100 new clichés; grammar metadata and safety review are required. | Moderate catalogue work, new generic composition layer. | Good with Phase 4N; needs careful generator integration. |
| C. Hybrid seeds plus current catalogues | Highest practical potential. New conceptual material collides with existing objects, creatures and raw identities while proven ingredients remain. | More moving parts and possible prompt density; poor combinators could produce malformed phrases. | Moderate to high, but isolated behind an evaluation flag. | Best fit with Phase 4M, Phase 4N, registries and A/B diagnostics. |
| D. Prompt guidance only | Low and already implemented. | Model ignores it or maps broad themes back to familiar comedy. | Lowest. | Safe but insufficiently measurable at ingredient stage. |

### Recommendation

Use C, with B as the new data source and a limited form of A later where tags
already exist naturally. Extend each domain with compact typed seed lists:

* `entities`: objects, organisms, materials or practices;
* `processes`: transformations and behaviours;
* `properties`: observable or impossible traits;
* `relationships`: symbiosis, interference, inheritance, resonance and similar
  links;
* optional `contexts`: vocabulary that disambiguates a seed without prescribing
  a joke.

Each item should carry grammar, familiarity, provenance/licence and review
status where applicable. Domain data should contain concepts, not finished
jokes. Generic cross-domain recipes should combine one seed with an unrelated
existing base or, occasionally, seeds from two selected domains. For example,
the reusable relationship “symbiosis” may collide with a ticket machine,
opera singer or weather balloon; the marine-biology entry should not hardcode a
glowing-jellyfish punchline.

Only a minority of offered concepts/descriptors should be theme-informed in the
first experiment. Existing generators remain the quality anchor, and the model
still receives raw identities and freedom to invent. Downstream registries need
stable `domain_ids`, `seed_ids`, construction IDs and premise keys so exact and
semantic memory remain explainable.

## Safeguards for a subsequent implementation

* Add a separate default-off mode, distinct from `NEWSMUNCHER_THEMATIC_DIVERSITY`,
  so prompt-only Phase 4N and ingredient-informed behaviour can be compared.
* Preserve the exact disabled call path and all hard grammar/safety checks.
* Use the domains already selected by Phase 4N; do not select another thematic
  slate or add another provider call.
* Keep theme contribution soft: construct a candidate pool, then admit a small
  bounded number. Never require any domain in final text.
* Keep every legacy ingredient reachable and every thematic seed reusable after
  decay. Apply Phase 4M lexical exposure where enabled, without requiring it.
* Penalize recent seed and construction identities separately from domain
  rotation so one domain does not always emit its most obvious seed.
* Prefer cross-domain pairings probabilistically, with caps inside one slate.
  Avoid a fixed domain-to-template lookup.
* Do not add coherence, plausibility, politeness or conventional-comedy scores.
* Log all candidate stages locally: proposed, validity-rejected, quality-gated,
  theme-preferred, selected, prompt-offered, first-pass-found and final-found.
* Enforce strict prompt-size bounds. Replace a few existing ingredients rather
  than continually appending more material.

## Provider-free evaluation methodology

Run at least 500 equivalent-seed generations for four configurations:

1. current Phase 4N prompt-only baseline;
2. domain-tagged existing ingredients;
3. domain seed candidates without existing-item tags;
4. the recommended hybrid.

Use the same selected four domains and the same concept/descriptor/name seeds
for every configuration. Do not model final prose or assign a humour score.

Record at candidate creation, validity gate, quality gate and final slate:

* unique meaningful words and multiword identities;
* domain and broad-family coverage;
* percentage of selected domains represented before and after ranking;
* seed/entity/process/property/relationship coverage;
* within-article and rolling-five/ten construction reuse;
* cross-domain pair count and distinct pair coverage;
* concentration of institutional, ceremonial, powered, kitchen/household,
  official-animal and aristocratic-name families;
* candidates and domains lost at each ranking stage, grouped by rejection reason;
* score distributions for baseline, valid unusual and rejected candidates;
* exact category, intensity, role and name-style distributions;
* lexical breadth, Phase 4M penalties and any new concentration;
* prompt characters and estimated tokens;
* completion/exhaustion rate, time and local database operations;
* default-off byte-for-byte prompt equality, memory isolation and boundedness.

The key ranking test is counterfactual: for each valid theme candidate, retain
its pre-ranking metadata and report whether it lost to a familiar candidate
because of compactness, mechanism bonus, quota scarcity or recent exposure.
This distinguishes poor grammar from a valid surprise that the scoring function
never allowed into the slate.

Offline success should require broader domain/seed/construction coverage,
lower familiar-family concentration, unchanged hard-quota validity, no
exhaustion, bounded overhead and no large fall in the existing quality stratum.
It cannot establish finished-article diversity or humour.

After offline review, the smallest useful live check is six neutral fixed
sources with one baseline and one hybrid output each, balanced in order: 12
finished articles and 24 existing two-pass calls. Audit source, offers,
first-pass and final text; review the articles blind before opening the key.
That paid run requires a separate cost estimate and explicit approval.

## Specific code locations for the next phase

* `newsmuncher/resources/vocabulary/thematic_domains.json`: add versioned typed
  seed references or split seeds into a separately validated catalogue.
* New `newsmuncher/services/thematic_ingredients.py`: validate seeds, construct
  generic cross-domain candidates and retain stage diagnostics.
* `newsmuncher/services/thematic_diversity.py`: expose selected domain metadata
  to the ingredient layer; keep selection/memory behaviour unchanged.
* `newsmuncher/services/comedy_concepts.py`: accept optional theme candidates at
  candidate-pool level while preserving validity gates and current baseline.
* `newsmuncher/services/comedy_descriptors.py`: admit typed theme descriptors
  with explicit roles rather than interpolating arbitrary text.
* `newsmuncher/services/comedy_variants.py`: mix a bounded theme-informed subset
  into an evaluation slate and preserve raw/generated provenance.
* `newsmuncher/api/previews.py`: pass the already selected domains into the
  optional ingredient builder before concept/descriptor overrides.
* `newsmuncher/services/comedy_audit.py`: record proposal, ranking and uptake
  provenance separately from prompt-only thematic influence.
* New provider-free diagnostic and focused tests under `scripts/diagnostics/`
  and `tests/python/`; no production collection or provider client is needed.

Names should initially remain a control rather than receive forced domain
mapping. The current aristocratic skew is real, but simultaneously changing
names, concepts and descriptors would obscure which intervention broadened the
articles. A later tagged-name experiment can use the same evidence framework.

## Implementation sequence for a subsequent phase

1. Define a versioned schema and hand-curate representative typed seeds for all
   100 domains, with automated duplication, grammar, provenance and safety
   validation.
2. Build generic seed-to-concept and seed-to-descriptor combinators that record
   every candidate stage; do not connect them to the live route.
3. Run the four-way 500-generation comparison and reject recipes that create
   domain-specific catchphrases or systematic malformedness.
4. Add a default-off theme-informed variant that replaces only a small bounded
   fraction of the existing slate and reuses Phase 4N selections.
5. Verify Phase 4M on/off compatibility, registries, retry identity, concurrent
   memory, audit provenance, prompt bounds and exact disabled behaviour.
6. Review provider-free results and complete examples editorially.
7. Only after separate approval, run the 12-article blind live check. Do not
   promote a configuration from offline proxies alone.

The expected result is not a marine-biology mode or a more sensible article.
It is a larger set of valid ingredients capable of making hydrothermal pressure,
Bronze casting, fungal communication or acoustic resonance collide with any
other NewsMuncher material, while gravy, royal footmen and powered machinery
remain available when their return is surprising again.
