# NewsMuncher Phase 4M — live off/on results

Date: 2026-10-12
Status: live run complete; blind review awaiting Andy

## Experiment design

The harness uses the first six neutral Phase 4K fixtures. Each source receives
three baseline outputs and three Phase 4M outputs: 36 finished articles and 72
existing two-pass provider calls. Both groups use `gpt-6-sol`, Phase 4K variant
A and the same Phase 4J feature settings. Group order alternates for every
source/repetition pair.

Each group has isolated in-memory registries. All 18 sequential articles in a
group share that group's phrase, semantic, topic, final-joke and lexical state.
The enabled group's lexical collection persists for the complete run and stays
bounded at ten events. The disabled group creates no lexical document. These
stores are experimental only and never access production MongoDB or user data.

The runner writes all artifacts beneath the Git-ignored directory
`local_audits/phase4m_live_experiment/`:

* `blind_comparison.md` contains all complete articles without group labels;
* `answer_key.csv` is separate and must remain unopened until review;
* `combined.jsonl`, `group_off.jsonl` and `group_evaluation.jsonl` retain the
  complete audit evidence;
* `vocabulary_measurements.json` contains machine-readable objective results;
* `run_manifest.json` records schedule, settings, memory policy and validation.

The console completion message deliberately prints only the run directory,
output count and blind-comparison path. It does not print group measurements or
the answer key.

## Preflight finding and correction

The first complete dry run exposed concept exhaustion in the enabled group
after one accumulated article. Although the original inverse-square sampling
gave every exposed item a mathematically nonzero probability, high accumulated
penalties effectively collapsed deterministic candidate pools onto too few
unexposed premises.

Phase 4M now retains an 8% exploration floor. Exposure still reduces selection
weight, while the full vocabulary remains meaningfully reachable and the hard
slate quotas can be filled. A complete 36-output dry run then succeeded with
18 records per group, one bounded lexical document for the enabled group and
none for the disabled group.

All 14 focused live-harness, lexical-memory and Phase 4K compatibility tests
pass. Python compilation and `git diff --check` also pass.

The corrected 250-rewrite offline comparison produced 5,000 ingredients per
configuration with zero exhaustion. Unique meaningful words rose from 1,431 to
1,466, rolling-five repetition fell from 83.70 to 57.95, and rolling-ten fell
from 276.33 to 188.37. Hard category counts were identical and mean quality
moved from 7.311 to 7.304. These remain ingredient-level results only.

## Cost estimate and approval boundary

The Phase 4K run did not retain provider token usage. Its 28 first-pass prompts
averaged 13,148 characters, approximately 3,300 input tokens. Copy-edit input
adds the fixed editing instructions and a roughly 136-word first-pass article.
For 36 articles, the expected volume is approximately 140,000–165,000 input
tokens and 15,000–30,000 output tokens. The configured hard ceiling is 54,000
output tokens across 72 calls.

The repository's `gpt-6-sol` alias does not expose billing rates locally, so an
exact monetary quote cannot be recovered from the previous run. A prudent
approval cap is **USD $2.00** for the complete experiment; the expected charge
is below that cap under recent text-model rates. The paid command must not run
until Andy explicitly approves this estimate.

## Provider-free commands

Focused validation:

```bash
PYTHONPATH=. .venv/bin/python -m pytest -q \
  tests/python/test_phase4m_live_experiment.py \
  tests/python/test_lexical_exposure.py \
  tests/python/test_phase4k_experiment.py
```

Create a provider-free artifact set:

```bash
PYTHONPATH=. .venv/bin/python \
  scripts/diagnostics/run_comedy_phase4m_live_experiment.py \
  --dry-run \
  --output-dir local_audits/phase4m_live_experiment/<preflight-name>
```

## Paid command after approval

```bash
PYTHONPATH=. .venv/bin/python \
  scripts/diagnostics/run_comedy_phase4m_live_experiment.py \
  --output-dir local_audits/phase4m_live_experiment/<live-run-name>
```

## Live execution

The approved run completed all 36 finished articles: 18 baseline and 18 Phase
4M. Exactly 72 planned provider calls were made. There were no provider errors,
retries, substitutions or missing records. Both groups contained three outputs
for each of the six sources. Their final meaningful-word totals were almost
identical, 1,720 versus 1,719, so the normalized comparison is not driven by
article length.

The provider response wrapper does not return usage metadata. The exact billed
amount therefore cannot be confirmed from the artifacts; the call count and
configured token ceilings remained within the approved experiment design.

## Finished-article results

| Metric | Baseline | Phase 4M | Change |
|---|---:|---:|---:|
| Unique meaningful words | 1,104 | 1,125 | +1.90% |
| Unique meaningful words per 1,000 | 641.86 | 654.45 | +1.96% |
| Rolling-five repeated words | 16.28 | 13.50 | -17.08% |
| Rolling-ten repeated words | 28.78 | 25.11 | -12.75% |
| Rolling-five repeated bigrams | 0.44 | 0.56 | +27.27% |
| Rolling-ten repeated bigrams | 3.39 | 2.39 | -29.50% |
| Repeated word occurrences per 1,000 | 358.14 | 345.55 | -3.52% |
| Top-15 recurring-word share | 6.34% | 5.41% | -0.93 points |
| Model-introduced unique words | 387 | 431 | +11.37% |

Phase 4M produced a modest but consistent improvement in finished-article word
breadth, short-window word recurrence, ten-article phrase recurrence and
top-word concentration. It did not improve every proxy: rolling-five repeated
bigrams increased from 0.44 to 0.56 per article. These are very small absolute
counts, but they prevent a claim of universal improvement.

## Ingredient improvement versus final-copy improvement

The ingredient effect was larger than the final-copy effect:

| Offered-ingredient metric | Baseline | Phase 4M | Change |
|---|---:|---:|---:|
| Unique meaningful words | 1,499 | 1,609 | +7.34% |
| Rolling-five repeated words | 40.17 | 30.06 | -25.17% |
| Rolling-ten repeated words | 56.39 | 43.44 | -22.97% |

The model transmitted part of that gain into final articles: final breadth rose
1.9% and rolling recurrence fell 13–17%. The smaller final effect confirms that
model improvisation remains a material bottleneck rather than a pure ingredient
selection problem.

The enabled group introduced 431 unique final words absent from its sources and
recorded ingredients, compared with 387 at baseline. First-pass model-created
vocabulary was also broader, 462 versus 415 unique words. Copy editing added 36
unique words in Phase 4M and 43 at baseline. None of the six watched expressions
was introduced during copy editing; their recurrence originated in ingredients
or first-pass model generation.

## Watched vocabulary provenance

None of the six watched expressions appeared in the neutral sources.

| Expression | Baseline offered / first / final articles | Phase 4M offered / first / final articles |
|---|---:|---:|
| gravy | 5 / 6 / 6 | 4 / 6 / 6 |
| custard | 4 / 5 / 5 | 2 / 5 / 5 |
| marmalade | 6 / 6 / 5 | 5 / 4 / 3 |
| cucumber slicer | 2 / 1 / 0 | 2 / 2 / 2 |
| crumpet | 6 / 1 / 1 | 8 / 2 / 2 |
| milk float | 1 / 1 / 1 | 3 / 3 / 3 |

Phase 4M reduced final marmalade use but did not reduce gravy or custard. Gravy
was independently introduced by the first-pass model in two articles in each
group. Custard was independently introduced in two baseline articles and three
Phase 4M articles. This is direct evidence that ingredient penalties alone do
not control the model's familiar vocabulary.

Cucumber slicer, crumpet and milk float increased in this sample because they
were offered more often. The ledger did not merely replace every old favourite
with a uniformly broader output. This small sample shows expected stochastic
movement and some new local concentrations.

## Semantic families and recurring patterns

Detected powered constructions fell from 15 to 11 articles, queue material from
9 to 5 and tea material from 11 to 9. Gravy and pudding/dessert detections were
unchanged at 6 and 8. Municipal-authority material moved from 10 to 11,
allotment material from 3 to 6 and milk-float detections from 1 to 3. The lower
top-15 word share indicates broader distribution overall, while these family
counts show that short experiments can still exchange one concentration for
another.

The most frequent baseline content word was `biscuit` at 11 occurrences. The
enabled group reduced it to 7, but `royal` increased from 7 to 9. The complete
noun-candidate and two-word-phrase tables are retained in
`vocabulary_measurements.json`. Noun identification is a conservative suffix
heuristic rather than a full part-of-speech model, so ambiguous entries should
be editorially reviewed.

## Source exemptions and memory verification

Source vocabulary was excluded from exposure penalties. Final articles retained
93 distinct source words at baseline and 88 with Phase 4M; this small difference
does not establish reduced source fidelity. The six fixed sources and three
repetitions allow source-matched reading in the blind comparison.

The live manifest confirms one bounded lexical document for the enabled group
and none for the disabled group. Eighteen sequential enabled articles shared
one scope, so the ten-event window decayed normally rather than resetting per
generation. The groups used separate stores, and no production MongoDB record
or user data was read or changed. Existing unit tests separately cover restart
persistence, per-pet isolation, concurrent updates, duplicate UUIDs and bounded
growth.

## Interpretation

Phase 4M meaningfully improved aggregate lexical variety in finished articles,
but the effect was moderate rather than transformative. Ingredient breadth rose
more sharply than final-copy breadth. Gravy and custard survived unchanged, and
milk floats, crumpets and allotment language became more prominent in this run.
The feature is technically ready for broader opt-in testing: it completed every
rewrite, preserved article length, stayed bounded and reduced most aggregate
repetition measures. It is not ready for default promotion from this evidence
alone.

The blind document remains the gate for comedy and surprise. Objective metrics
cannot establish whether the enabled articles are funnier, stranger or more
enjoyable. Read `blind_comparison.md` before opening `answer_key.csv`; the main
report deliberately does not map any individual version to its group.

## Post-run validation

* Python: 484 passed, 0 failed, 105 subtests passed.
* JavaScript: 84 passed, 0 failed.
* Python compilation passed.
* Production JavaScript syntax checks passed.
* `git diff --check` passed.
* No production database, production user record or media-generation path was
  accessed.
