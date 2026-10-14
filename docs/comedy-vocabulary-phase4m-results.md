# NewsMuncher Phase 4M — vocabulary diversity results

Date: 2026-10-12

## Outcome

Phase 4M implements the Phase 4L recommendation as an opt-in evaluation mode.
It broadens short-window lexical exposure without banning any word, changing
the comedy style, altering Phase 4K defaults, adding a provider call, modifying
media generation or rewriting existing production records.

The feature is disabled unless:

```bash
NEWSMUNCHER_LEXICAL_DIVERSITY=evaluation
```

Unset the variable or use `NEWSMUNCHER_LEXICAL_DIVERSITY=off` for the original
path. `NEWSMUNCHER_LEXICAL_WINDOW` defaults to ten completed articles and
accepts 2–30. `NEWSMUNCHER_LEXICAL_GUIDANCE_ITEMS` defaults to four and accepts
1–8.

## Memory scope and persistence

A process-local dictionary was rejected because it would diverge across Uvicorn
workers, disappear on restart and mix unrelated users. Phase 4M uses a separate
`comedy_lexical_exposure` MongoDB collection. Each active pet gets one document
keyed by a truncated SHA-256 digest of its existing identifier. The raw pet
identifier is not stored in the ledger or audit.

Each document contains at most the configured number of completed-rewrite
events. A single atomic `$push`/`$slice` update appends an event after successful
draft persistence. The rewrite UUID predicate prevents duplicate events.
Different pets have isolated histories; all application workers share the
persistent database state. A missing ledger degrades to an empty history, and a
read or update failure cannot invalidate a successful MUNGE.

The ledger stores normalized exposure keys for:

* meaningful words of four or more characters, excluding a fixed grammatical
  stopword set;
* compact two-to-four-word identities;
* ingredients offered to the model;
* the first-pass rewrite;
* the final copy-edited article.

Words and exact identities present in the current source are removed from
selection penalties and from the stored comedy exposure for that rewrite.
Recent final use has three times the weight of an offer or first-pass use. Event
weights decay by age and disappear when the bounded window advances.

## Exposure-aware selection

Concept and descriptor component-bank draws now accept an optional lexical
penalty map. Candidate probability is proportional to
`1 / (1 + exposure)^2`. Every eligible value therefore retains a nonzero
probability. With no penalty map the code uses the original `random.choice`
path, which is regression-tested for exact seeded equivalence.

Phase 4K generated downsampling and raw CSV/catalogue selection use the same
nonzero weighted sampling when Phase 4M is enabled. Existing safety gates,
quality floors, category and intensity quotas, descriptor grammar roles,
leases, phrase cooldowns, semantic memory and topic memory remain in force.
There is no deterministic rotation, permanent blacklist or substitution table.

## Model-invented vocabulary

When final vocabulary accumulates sufficient recent exposure, Phase 4M adds one
short soft paragraph to the existing prompt. It asks for fresh wording where
the source does not require the recently prominent words and explicitly says
those words remain allowed when they inspire the best surreal joke. At most the
configured number of words appears. There is no requested replacement list,
additional response, or extra provider call.

Selector weighting is the primary control. Prompt guidance is a secondary
backstop for model-invented recurrence such as the gravy and marmalade examples
confirmed in Phase 4L.

## Diagnostic audit

When `NEWSMUNCHER_COMEDY_AUDIT_LOG=on`, a successful audit record can now include:

* the complete first-pass headline and article;
* the existing complete final headline and article;
* the recently exposed word/identity penalty snapshot used for selection;
* selected concepts, descriptors and raw identities that carried a nonzero
  exposure penalty;
* `NEWSMUNCHER_LEXICAL_DIVERSITY` in the allowlisted feature flags.

The audit remains local, optional and Git-ignored. It records no raw pet scope,
credentials, provider metadata or website-visible diagnostic field. Failed and
abandoned rewrites still produce no audit event or ledger event.

## Provider-free comparison

Command:

```bash
PYTHONPATH=. .venv/bin/python \
  scripts/diagnostics/evaluate_vocabulary_phase4m.py \
  --rewrites 250 --seed phase4m-final
```

The comparison generated 5,000 production-shaped concept ingredients per
configuration using the real expanded concept generator and hard live category
allocation. A deterministic four-concept uptake fixture populated the rolling
ten-article ledger. It made no provider or database call.

| Metric | Baseline | Phase 4M | Change |
|---|---:|---:|---:|
| Unique complete phrases | 4,367 | 4,374 | +0.16% |
| Unique bases | 1,220 | 1,233 | +1.07% |
| Unique meaningful words | 1,431 | 1,466 | +2.45% |
| Rolling-five word repetitions | 83.70 | 57.95 | -30.76% |
| Rolling-ten word repetitions | 276.33 | 188.37 | -31.83% |
| Top-15 word share | 8.16% | 8.04% | -0.12 points |
| Mean generated quality score | 7.311 | 7.304 | -0.007 |
| Exhaustion events | 0 | 0 | unchanged |

The live-experiment preflight found that an unboundedly steep penalty curve
could collapse a deterministic candidate pool after one accumulated article.
An 8% exploration floor now guarantees meaningful access to the complete pool,
in addition to mathematical nonzero probability. With that correction, phrase,
base and meaningful-word breadth all increased. Short-window word repetition
fell by about 31% while the quality proxy moved by 0.007, and 250 selections
completed without exhaustion.

Hard category counts were exactly identical:

| Category | Baseline | Phase 4M |
|---|---:|---:|
| everyday British | 750 | 750 |
| cheeky object | 1,000 | 1,000 |
| absurd invention | 1,000 | 1,000 |
| ridiculous creature | 1,000 | 1,000 |
| bureaucratic nonsense | 750 | 750 |
| emergency equipment | 250 | 250 |
| ceremonial object | 250 | 250 |

The dominant semantic themes also remained close: institutional control was
1,093 versus 1,089; impossible technology 928 versus 932; innuendo 783 versus
799; and unexpected behaviour 1,150 versus 1,137. Phase 4M did not replace the
existing comic mix with a new narrow category. The top-15 lexical share fell,
while rare compatible themes such as absurd dispute and principled refusal
appeared once in Phase 4M’s deterministic sample.

Offline scoring cannot establish funniness, model compliance or final-article
quality. No Phase 4K variant is promoted. A later paid or live comparison still
requires separate approval.

## Tests

Focused coverage includes:

* repeated words across otherwise different phrases;
* frequency and age decay;
* recovery after the bounded window;
* nonzero probability for exposed vocabulary;
* source-required exemptions;
* multiword identities and grammatical stopwords;
* bounded concurrent writes and duplicate rewrite UUIDs;
* per-pet isolation and restart persistence;
* exact default-off seeded behavior;
* Phase 4K hybrid compatibility;
* first-pass/final/penalty audit fields;
* 30-rewrite deterministic breadth, repetition, category and quality gates.

Run focused tests with:

```bash
PYTHONPATH=. .venv/bin/python -m pytest -q \
  tests/python/test_lexical_exposure.py \
  tests/python/test_comedy_audit.py \
  tests/python/test_comedy_variants.py \
  tests/python/test_concept_selection.py \
  tests/python/test_descriptor_selection.py
```

Full safe validation completed with 481 Python tests passed, zero failed and
105 subtests passed; 84 JavaScript tests passed with zero failures. Python
compilation, JavaScript syntax checks and `git diff --check` also passed.

## Local evaluation startup

Use the same Phase 4J settings on both sides of a comparison and change only
the lexical flag. An enabled example is:

```bash
NEWSMUNCHER_EXPANDED_VOCABULARY=evaluation \
NEWSMUNCHER_EXPANDED_DESCRIPTORS=evaluation \
NEWSMUNCHER_COMEDY_SEMANTIC_MEMORY=evaluation \
NEWSMUNCHER_FINAL_JOKE_MEMORY=evaluation \
NEWSMUNCHER_COMEDY_TOPIC_MEMORY=evaluation \
NEWSMUNCHER_LEXICAL_DIVERSITY=evaluation \
NEWSMUNCHER_COMEDY_AUDIT_LOG=on \
./.venv/bin/python -m uvicorn newsmuncher.main:app --reload
```

Use `NEWSMUNCHER_LEXICAL_DIVERSITY=off` for the comparator. Phase 4K remains A
unless explicitly set otherwise. No additional provider call is made per MUNGE.

## Limitations

Lexical extraction is deliberately conservative and English-oriented. It does
not perform full linguistic parsing, embeddings or fuzzy semantic inference.
Compound normalization handles hyphens and compact identities but will not join
every paraphrase. Separate pet scopes prevent one user’s private history from
steering another user, so globally repeated model habits can still occur across
different pets. The bounded prompt hint can theoretically prime a named word;
its threshold and size are intentionally small, and selector weighting does the
main work.
