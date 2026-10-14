# NewsMuncher Phase 4Q — live ingredient influence investigation

Date: 2026-10-13

## Scope and evidence

This is a diagnostic investigation only. It changes no runtime code, prompt,
selection weight, quota, ranking rule or production default. It made no provider
request and no database write.

The requested Phase 4I JSONL audit was not enabled for these three MUNGEs. The
current local JSONL ends before Phase 4P, and no `comedy_audit.jsonl` exists on
disk. Consequently, the full prompts, complete first-pass articles,
selection-time penalty snapshots and candidate-stage metrics were not retained.

The three rewrites were nevertheless matched confidently through four existing
sources:

1. the bounded Phase 4P seed/construction events;
2. the bounded Phase 4N domain events;
3. the bounded Phase 4M offered/first-pass/final lexical events;
4. the local preview SQLite store.

The lexical signatures contain the distinctive names and opening ingredients
quoted in the task. The first two preview rows are now deliberate tombstones
because later rewrites reused the same draft slot. The third preview retains its
source and complete final article. All three records belong to the same
anonymised local pet scope; no pet identifier or unrelated record is reproduced
here.

| Article | Rewrite UUID | Match confidence | Retained source/final text |
|---|---|---|---|
| A — Hattie Hobbleham | `d6ce1d6a-ffba-403f-a31e-c2f8b2a0798f` | High: unique Hattie/snail/water-diversion/longship signature in both first and final lexical stages | Preview is a tombstone; complete text and timestamp unavailable |
| B — Nora Squeezemouth | `1dea2710-a163-43e1-a6f7-5df5fc25ead8` | High: unique Nora/haddock/dimension-hopping-investigator signature in both stages | Preview is a tombstone; complete text and timestamp unavailable |
| C — Doctor Philomena Fustianholme | `4d7ff97e-81df-4128-a8ea-9629930c94e4` | Exact UUID and complete persisted preview | Source: “Devin Battley”; final article retained locally |

For A and B, lexical memory preserves unique words in order of first appearance,
not complete prose. It can establish recognisable ingredient uptake but cannot
establish exact phrase matching or recover the full articles. This report does
not invent the missing text.

## Pipeline trace

Phase 4N or Phase 4P selects four domains from bounded per-pet history. Phase 4M
then loads source-exempt lexical penalties. Phase 4P builds two concept
replacements and one role-preserving descriptor from typed seeds. This happens
after the ordinary concept and descriptor registries have assembled their
quality-ranked slates.

Each concept replacement generates twelve candidates, applies only technical
validity checks, and chooses among valid candidates using seed/construction
recency. The old compactness and proven-mechanism quality score cannot remove
the selected Phase 4P item. One ordinary noun concept, one ordinary animal-bank
concept and one ordinary descriptor are displaced.

The resulting 20 concepts and ten descriptors are inserted into the same
`RANDOM INGREDIENTS` lists as ordinary material. Phase 4P items have no separate
label, priority or placement. The prompt says to use “several” supplied words,
allows additional invention, and explicitly says comedy and readability matter
more than forcing every supplied word. Ten names plus slang and places compete
for attention as well.

The first provider pass creates the article. The second pass receives only that
article, never the source, prompt or ingredient slate. Its instruction explicitly
preserves every bizarre detail and restricts changes to grammar and flow. The
observed data agrees with that architecture: Phase 4P losses occurred before
copy editing.

## Per-article provenance

The exact prompt-visible Phase 4P phrases below are reconstructed deterministically
from the persisted seed IDs, construction IDs, recorded offered vocabulary and
the checked-in generic construction code. This is stronger than keyword
similarity. “Recognisable” means that every distinctive seed/base component is
present in the stage record; it does not claim exact wording where full prose is
missing.

### Article A — Hattie Hobbleham

Selected Phase 4N domains:

- Viking navigation
- Sewer history
- Celestial navigation
- Genetics

| Phase 4P prompt ingredient | Seeds / construction | First pass | Final |
|---|---|---|---|
| `task force in inherited variation with sewer` | genetics relationship + sewer entity; `base_relationship_entity` | Not detected | Not detected |
| `snail in water diversion with longship` | sewer-history relationship + Viking-navigation entity; `base_relationship_entity` | Recognisable, exact wording unavailable | Recognisable and transformed to the supplied opening “a snail involved in water diversion with a longship” |
| `mutation triggers brick culverts` | genetics entity + sewer-history process; `role_short_clause` | Not detected | Not detected |

Phase 4N's conservative keyword detector also found `longship` in the final,
independently supporting the second match. It found no other selected domain.

The lexical record shows at least eight complete non-Phase-4P offered identities
recognisably reused, including the cheese grater, felt bedside cabinet, parish
fund, alarm thermos, salad spinner, hand dryer, door knocker and ball cock.
Further transformed legacy material includes the gravy permit and several
occupation, powered-machine and institutional constructions. Because the full
slate and article were not logged, eight is a lower bound rather than a complete
count.

### Article B — Nora Squeezemouth

Selected Phase 4N domains:

- Fluid dynamics
- Quantum physics
- Roman engineering
- Clockwork machinery

| Phase 4P prompt ingredient | Seeds / construction | First pass | Final |
|---|---|---|---|
| `aqueduct gradients-adapted signal-controlled food processor` | Roman-engineering process + clockwork property; `process_adapted_base` | Not detected | Not detected |
| `escapements-adapted dynastic laminator` | clockwork process + Roman-engineering property; `process_adapted_base` | Recognisable; exact phrase cannot be proved from token-only memory | Recognisable; exact phrase cannot be proved from token-only memory |
| `through vortices with clockwork` | fluid-dynamics process + clockwork entity; `role_adverbial` | Not detected | Not detected |

The final retained at least seven complete non-Phase-4P offered identities:
laundry basket, allotment bench, letterbox haunted by seventeen accountants,
weather-sensitive deckchair, trouser hanger, knicker press and basting brush.
It also used the legacy haddock occupation, seaside clairvoyants, lobster
occupation, civic charter and pension/paperwork material in transformed forms.
Again, seven is a conservative lower bound.

### Article C — Doctor Philomena Fustianholme

Selected Phase 4N domains:

- Thermodynamics
- Architecture
- Canal engineering
- Cartography

| Phase 4P prompt ingredient | Seeds / construction | First pass | Final |
|---|---|---|---|
| `flying buttresses-adapted cantilevered clipboard` | architecture process + canal-engineering property; `process_adapted_base` | Not detected | Not present in the retained final |
| `interlocking food processor using islands` | architecture property + cartography process; `property_base_process` | Recognisable in the first-pass lexical sequence | Exact wording survives in the retained final article |
| `contour triggers flying buttresses` | cartography entity + architecture process; `role_short_clause` | Not detected | Not present in the retained final |

The final article exactly used at least ten ordinary generated concepts recorded
as accepted: an octopus divorce mediator, the village-biscuit mole, the defence
teapot, the tea-duty lawn mower, lightning-powered parking meter, village pickle
licence, three-fines peacock, government-pension magpie, moist marrow polisher
and marmalade-smuggling compliance form. It also used the ordinary
`domestically tea-sworn` descriptor, plus recognisable umbrella-stand and bread-bin
material that conservative exact acceptance did not record after inflection.

The source was a short factual biography about motorcycle businessman and racer
Devin Battley. Its chronological career structure is recognisable, but it did
not prevent one Phase 4P ingredient and many ordinary ingredients from entering
the article.

## Stage-by-stage influence

| Stage | Article A | Article B | Article C | Combined |
|---|---:|---:|---:|---:|
| Phase 4P candidates selected | 3 | 3 | 3 | 9 |
| Selected Phase 4P concepts / prompt concepts | 2/20 (10%) | 2/20 (10%) | 2/20 (10%) | 6/60 (10%) |
| Selected Phase 4P descriptors / prompt descriptors | 1/10 (10%) | 1/10 (10%) | 1/10 (10%) | 3/30 (10%) |
| Selected items confirmed prompt-visible | 3 | 3 | 3 | 9/9 (100%) |
| Recognisable in first pass | 1 | 1 | 1 | 3/9 (33.3%) |
| Recognisable in final | 1 | 1 | 1 | 3/9 (33.3%) |
| First-pass uses lost in copy edit | 0 | 0 | 0 | 0/3 |
| Omitted before first pass | 2 | 2 | 2 | 6/9 (66.7%) |

Only Article C supports a confirmed exact final Phase 4P phrase. Article A is a
confirmed semantic transformation of the supplied phrase. Article B is a
high-confidence recognisable match, but exactness is unavailable without its
full text. The report therefore does not present “3 exact uses” as fact.

The live candidate-stage acceptance and rejection rates are unavailable. The
code proposed 24 concept alternatives and one descriptor candidate per article,
but the absent Phase 4I record was the only place that would have retained how
many failed technical validity and how many valid alternatives lost weighted
selection. The bounded Phase 4P event intentionally stores only selected IDs.
All nine selected items were accepted into the prompt, so existing concept or
descriptor quality ranking did not suppress them after selection.

Selection-time Phase 4M penalty snapshots are also unavailable. Its event log
proves that Phase 4M was enabled and records offered/first/final exposure. It
does not retain the prior penalty map. Article A was the first retained lexical
event in this sequence; B and C had recent history, but source exemptions prevent
reconstructing their exact active scores safely from the remaining records.

## Generic-construction repetition

Across the nine selected ingredients, the construction distribution was:

| Construction | Selections | Recognisable finals |
|---|---:|---:|
| `process_adapted_base` | 3 | 2 |
| `base_relationship_entity` | 2 | 1 |
| `role_short_clause` | 2 | 0 |
| `property_base_process` | 1 | 1 |
| `role_adverbial` | 1 | 0 |

The two adapted-base successes are the strongest early sign of a potentially
recognisable new formula, although one was not used and the sample contains only
three articles. The relationship construction produced Hattie's conspicuous
opening. Short-clause and adverbial descriptor constructions had zero uptake.

There is a documentation discrepancy worth correcting in a later implementation
phase: the Phase 4P report and this task describe seven generic patterns, while
the code defines three concept patterns and six role-specific descriptor
patterns, nine possible construction IDs. The provider-free run observed seven
additional identities; that observation is not the same as seven implemented
patterns. This discrepancy does not alter the present articles.

The successful Phase 4P constructions do not directly reproduce the older
powered-machine, official-animal or municipal-bureaucracy templates. However,
they are surrounded by those legacy mechanisms, and adapted-base wording can
itself become formulaic if representation rises without broader live evidence.

## Diagnosis

### 1. Low representation — confirmed, strongest structural cause

Phase 4P contributes exactly 10% of concepts and 10% of descriptors. Each
article offers three Phase 4P ingredients alongside 27 ordinary concepts and
descriptors, ten names, and additional slang and place material. Six of nine
Phase 4P ingredients disappeared before the first-pass output.

### 2. Prompt dilution — confirmed, closely coupled to low representation

Phase 4P material is mixed anonymously into the same comma-separated banks.
Nothing tells the model which three ingredients carry the new conceptual space.
The prompt asks only for “several” items and explicitly permits the model to
choose comedy/readability over coverage. Ordinary British-surreal ingredients
are more numerous and often read as complete, immediately deployable jokes.

### 3. Model preference — supported, but not cleanly separable from dilution

The model used one of three Phase 4P items per article while adopting many more
ordinary supplied identities and mechanisms. That is evidence of preferential
uptake at the prompt-to-first-pass stage. It does not prove an independent
learned preference for gravy, bureaucracy or household machinery, because the
prompt itself supplies much more of that material in more polished forms.

### 4. Source structure — unresolved, probably secondary

Only Article C retains its source. The biography's chronological structure
survived, yet it accommodated substantial surreal replacement and one Phase 4P
ingredient. The missing A/B sources prevent a three-article comparison.

### 5. Ranking suppression — not supported as the cause of these losses

Phase 4P runs after ordinary quality ranking and directly replaces three slate
positions. Every persisted Phase 4P selection reached the prompt. Internal
candidate alternatives do lose weighted selection, but that cannot explain why
the nine winners were omitted by the model. Live rejection details are
unavailable because audit logging was off.

### 6. Copy-edit loss — contradicted in this sample

The same three recognisable Phase 4P uses appear in first-pass and final lexical
records. No first-pass Phase 4P use disappeared during copy editing. Copy edits
changed inflection and phrasing, especially Hattie's opening, but preserved the
conceptual material.

## Smallest useful next experiment

Test prompt salience before changing counts, ranking or memory.

Keep the same two Phase 4P concepts, one Phase 4P descriptor, domains, seeds,
ordinary slate, model, provider-call count and copy-edit instructions. In the
experimental arm only, present the same three selected items once in a compact
adjacent `OPTIONAL FRESH THEME SPARKS` block immediately before the source text,
and remove those three from their anonymous bank positions so they are not
duplicated. State that they remain optional and may be altered, combined or
ignored; add no required-use quota and no substitute vocabulary.

This is a small reversible test of the leading explanation:

- if uptake rises without changing ingredients, anonymous prompt dilution was
  material;
- if uptake remains near one of three, model preference or construction utility
  becomes the stronger target;
- if article quality drops in human review, revert without touching selection.

A later controlled comparison should use identical neutral sources, balanced
order, Phase 4I logging enabled and separate memory scopes. Primary measures
should be exact and recognisable Phase 4P uptake at first pass and final, not a
humour score. No such paid comparison was run in Phase 4Q; it requires a cost
estimate and explicit approval.

Do not increase representation or expand construction patterns in the same
experiment. Changing both would prevent attribution. The current three-article
evidence also does not justify new bans, topic penalties, coherence rules or
domain-specific joke templates.

## Unresolved questions

- Complete A/B source, first-pass and final prose are no longer retained.
- Exact B phrase matching cannot be established from token-only memory.
- Live validity rejection and within-builder selection-loss counts were not
  persisted because Phase 4I logging was disabled.
- Exact selection-time Phase 4M penalty maps are unavailable.
- Three articles cannot establish whether `process_adapted_base` has become
  recognisably repetitive.
- Final uptake of optional Phase 4N prompt guidance cannot be separated from
  uptake caused by Phase 4P seeds when both flags are enabled.

The evidence supports investigating presentation before adding ingredients:
Phase 4P successfully expands the prompt's conceptual space, but two thirds of
its selected material is ignored by the first pass, while copy editing preserves
the novel material that does get used.
