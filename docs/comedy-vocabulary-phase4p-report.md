# NewsMuncher Phase 4P — theme-informed ingredient implementation

Date: 2026-10-12

## Scope

Phase 4P implements the default-off hybrid recommended by the Phase 4O
investigation. It expands the conceptual material offered to the existing
rewrite while preserving NewsMuncher's current style, quotas, source handling,
registries, two-pass provider flow and production defaults. Implementation and
testing made no provider request and no production database write.

Enable it with:

```bash
NEWSMUNCHER_THEME_INGREDIENTS=evaluation
```

Unset the variable or set it to `off` for the exact existing path. Phase 4M and
Phase 4N remain independent switches:

```bash
NEWSMUNCHER_LEXICAL_DIVERSITY=evaluation \
NEWSMUNCHER_THEMATIC_DIVERSITY=evaluation \
NEWSMUNCHER_THEME_INGREDIENTS=evaluation \
PYTHONPATH=. .venv/bin/python -B -m uvicorn newsmuncher.main:app --reload
```

This command only starts the server. A MUNGE still uses the existing two paid
provider calls, so live testing requires separate approval.

## Architecture

`thematic_ingredient_seeds.json` extends every one of the 100 Phase 4N domains
with four entities, four processes, four properties and four relationships:
1,600 typed seeds in total. The resource is reproducibly built from the
reviewed Phase 4N domain catalogue, reviewed family pools and explicit domain
overrides. Each seed records grammar, internal provenance, licence state,
review and safety state. The licence remains honestly marked
`INTERNAL-UNVERIFIED`; the material is original repository content rather than
an imported third-party vocabulary.

The combinator implements nine possible construction IDs: three generic concept
patterns and six role-preserving descriptor patterns. The provider-free sample
observed seven additional construction identities rather than exercising every
available ID. These are generic constructions rather than domain-specific
joke templates. It crosses selected domains with an existing object or creature
base and creates a descriptor in the same grammatical role and category as the
item it replaces. Entities, processes, properties and relationships all appear
in the measured output. The selected domains remain optional inspiration; no
domain is required to appear in the finished article.

The conservative default replaces at most:

- one of ten noun concepts;
- one of ten animal-bank concepts;
- one of ten descriptors.

It therefore never appends an unbounded list or changes the existing 20-concept
and 10-descriptor prompt sizes. Existing names remain a control, as Phase 4O
recommended. When Phase 4N is enabled, Phase 4P reuses its selected four
domains. When Phase 4P runs alone, it uses the same selector under an isolated
per-pet scope, so enabling it does not require Phase 4N prompt guidance or
pollute Phase 4N-only history.

Technical validity and creative preference are deliberately separate. The
builder enforces compactness, base visibility, unique words and descriptor-role
validity. It does not apply the existing subjective compactness or
proven-mechanism score, which could immediately discard unfamiliar but valid
material. Among valid candidates, recent seed and construction exposure changes
weighted probability with a 12% exploration floor. No seed is banned.

## Memory, concurrency and auditability

The new memory is a bounded Mongo-shaped event stream keyed by a hash of the
active pet. It stores at most 20 successful rewrite events by default, survives
worker restart, isolates pets, rejects duplicate rewrite UUIDs and handles
concurrent first inserts. It is updated only after the draft was successfully
persisted. Read or write failure produces a concise warning and cannot fail a
successful MUNGE.

The memory records seed, construction and domain identities. Phase 4M lexical
penalties also influence seed choice when Phase 4M is enabled. The existing
concept, descriptor, semantic, topic and final-joke memories are unchanged.

With Phase 4I logging enabled, records now include selected theme ingredients,
domain IDs, seed IDs and kinds, construction IDs, provenance, cross-domain
status, active penalties and proposal/validity/ranking counts. First-pass and
final text remain separately available through the existing audit schema, so a
later approved live evaluation can measure actual uptake.

## Provider-free four-way comparison

Command:

```bash
PYTHONPATH=. .venv/bin/python \
  scripts/diagnostics/evaluate_thematic_ingredients_phase4p.py \
  --generations 500 \
  --output docs/comedy-vocabulary-phase4p-results.json
```

Each configuration used 500 equivalent-seed generations and exactly 15,000
ingredients. Baseline means the current selection path. Phase 4N adds its
prompt-only domain rotation, Phase 4P adds typed ingredients without Phase 4N
guidance, and combined enables both. The provider-free fixture cannot model the
effect of guidance on final prose, so Phase 4N is correctly ingredient-identical
to baseline and combined is ingredient-identical to Phase 4P.

| Measurement | Baseline | Phase 4N | Phase 4P | Combined |
|---|---:|---:|---:|---:|
| Unique ingredient phrases | 10,420 | 10,420 | 11,110 | 11,110 |
| Unique meaningful words | 2,323 | 2,323 | 3,480 | 3,480 |
| Conceptual domains represented in ingredients | 0 | 0 | 100 | 100 |
| Cross-domain ingredients | 0 | 0 | 1,499 | 1,499 |
| Unique construction identities | 47 | 47 | 54 | 54 |
| Rolling-five exact phrase repeats | 0.300 | 0.300 | 0.238 | 0.238 |
| Rolling-ten exact phrase repeats | 0.624 | 0.624 | 0.498 | 0.498 |
| Rolling-five construction repeats | 15.540 | 15.540 | 16.250 | 16.250 |
| Familiar-word share | 1.908% | 1.908% | 1.741% | 1.741% |
| Mean ingredient characters/generation | 1,159.29 | 1,159.29 | 1,170.29 | 1,170.29 |
| Mean local transformation time | 0.152 ms | 0.491 ms | 1.106 ms | 1.078 ms |

All 11 broad domain families appeared. The 1,499 selected theme ingredients
used entities 823 times, processes 1,175, properties 676 and relationships 324;
an ingredient can use two kinds. One of the possible 1,500 replacements failed
the compact technical gate and retained its baseline descriptor. There was no
exhaustion. Domain and ingredient histories both remained bounded at 20 events.

The candidate stage proposed twelve alternatives for each concept replacement.
It recorded 10,970 technically valid alternatives not selected. These are
exploration choices, not failures caused by the old quality ranking. The
implementation preserves this distinction in its diagnostics.

The results meet the narrow offline objective: substantially more vocabulary,
all thematic domains represented, more exact ingredient identities and lower
short-window exact phrase reuse with unchanged hard counts. The slight increase
in construction repetition is a real trade-off: the sample exercised seven of
the nine available generic construction IDs, and these recipes are now
visible often enough to increase mechanism overlap even while their contents
broaden. A future reviewed iteration could expand generic grammar recipes, but
Phase 4P does not add more templates or penalties pre-emptively.

## Tests and files

Core implementation files:

- `newsmuncher/services/thematic_ingredients.py`
- `newsmuncher/resources/vocabulary/thematic_ingredient_seeds.json`
- `scripts/diagnostics/build_thematic_seed_catalogue.py`
- `scripts/diagnostics/evaluate_thematic_ingredients_phase4p.py`
- `tests/python/test_thematic_ingredients.py`
- `tests/python/test_thematic_ingredients_diagnostic.py`
- `newsmuncher/api/previews.py`
- `newsmuncher/services/comedy_audit.py`
- `docs/comedy-vocabulary-phase4p-results.json`

Coverage includes default-off equality, configuration independence, Phase 4M
compatibility, Phase 4N reuse, complete typed catalogue coverage, reproducible
building, cross-domain output, role and quota preservation, unfamiliar-valid
selection, decaying non-ban penalties, persistence, restart, per-pet isolation,
duplicate updates, concurrent writes, bounded history and local-audit
provenance. Full final suite results are recorded in `CURRENT_WORK.md`.

## Limitations

- Offline ingredient breadth cannot establish humour, surprise in finished
  prose or model uptake. No configuration is promoted.
- The seed catalogue uses compact conceptual labels. Some combinations will be
  stranger or rougher than others by design; technical validity is not a humour
  score.
- The generic recipe set is intentionally small for the first experiment and
  slightly increases measured construction overlap.
- Phase 4P alone must select a thematic slate because no Phase 4N slate exists;
  that selection uses the same algorithm in an isolated scope. Combined mode
  does not select a second slate.
- Exact seed/construction memory does not infer semantic equivalence between
  unrelated seed labels.
- A blind live comparison would use existing provider calls and requires a new
  cost estimate and explicit approval.

All Phase 4P work remains uncommitted and unpushed.
