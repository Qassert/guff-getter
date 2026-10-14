# NewsMuncher Phase 4N — provider-free thematic diversity results

Date: 2026-10-12
Status: default-off experiment ready for review

## Implementation

Phase 4N adds `NEWSMUNCHER_THEMATIC_DIVERSITY=evaluation`. Unset or `off`
preserves the previous route: it performs no thematic database read, selection,
prompt addition or write.

When enabled, one bounded Mongo-shaped record is scoped by a truncated SHA-256
of the active pet identity. It retains the last 20 successful rewrites by
default. Each rewrite selects four domains by seeded weighted sampling without
replacement. Domain frequency and recency reduce the weight; recent family
exposure and duplicate families within the current slate add softer penalties.
An exploration floor of 12% preserves a meaningful chance of reuse. There is no
rotation, ban or mandatory domain quota.

The selected inspirations are appended to the existing first-pass optional
guidance. The text explicitly permits the model to ignore, combine, distort or
reinterpret them and says they are neither subjects nor requirements. The core
prompt, concept and descriptor slates, copy-edit pass and provider-call count
are unchanged.

Memory is written only after successful draft persistence. The atomic update is
bounded, duplicate rewrite UUIDs are idempotent, and concurrent first writes
retry after a unique-key race. Read, selection and update failures emit a short
warning and do not invalidate a paid-for successful rewrite.

Phase 4I logging, when independently enabled, records selected domains, current
selection penalties and conservative keyword evidence of domains found in the
final article but absent from the source. A keyword match is evidence of likely
influence, not proof of causation. No audit content is shown to website users or
uploaded.

## Catalogue

`newsmuncher/resources/vocabulary/thematic_domains.json` contains exactly 100
unique domains across 11 families. Ten families contain nine domains and field
practices contains ten. It includes all subject areas requested for review and
also oral traditions, puppetry, circus history, bookbinding, dyeing,
horology, vernacular architecture, disaster archaeology, sensory science,
game theory, speleology and polar exploration.

Each entry provides a stable ID, family, human label, short inspiration and at
least three conservative influence keywords. The prompts receive the
inspiration text. IDs, families and keywords remain local diagnostic metadata.

## 500-generation measurements

Command:

```bash
PYTHONPATH=. .venv/bin/python \
  scripts/diagnostics/evaluate_thematic_diversity_phase4n.py \
  --generations 500 --seed phase4n-final
```

The run performed 2,000 domain selections without provider or production
database access.

| Metric | Result |
|---|---:|
| Domains available / seen | 100 / 100 |
| Families seen | 11 |
| Selections per domain, mean | 20.0 |
| Selections per domain, min / max | 9 / 33 |
| Domain coefficient of variation | 0.2131 |
| Largest domain share | 1.65% |
| Largest family share | 9.95% |
| Mean distinct families per four-domain slate | 3.504 |
| Rolling-five repeated domains per slate | 0.710 |
| Equivalent uniform baseline | 0.782 |
| Rolling-ten repeated domains per slate | 1.296 |
| Equivalent uniform baseline | 1.398 |
| Persisted events after 500 rewrites | 20 |

Family totals ranged from 167 to 199 of 2,000 selections. No scientific,
historical or artistic family dominated. Recency weighting reduced short-window
reuse without forcing deterministic rotation, while all domains remained
reachable and appeared during the run.

## Configuration

Enable Phase 4N alone:

```bash
NEWSMUNCHER_THEMATIC_DIVERSITY=evaluation \
PYTHONPATH=. .venv/bin/python -B -m uvicorn newsmuncher.main:app --reload
```

Enable it alongside Phase 4M and local diagnostics:

```bash
NEWSMUNCHER_THEMATIC_DIVERSITY=evaluation \
NEWSMUNCHER_LEXICAL_DIVERSITY=evaluation \
NEWSMUNCHER_COMEDY_AUDIT_LOG=on \
PYTHONPATH=. .venv/bin/python -B -m uvicorn newsmuncher.main:app --reload
```

Optional controls are `NEWSMUNCHER_THEMATIC_COUNT=3|4|5` and
`NEWSMUNCHER_THEMATIC_WINDOW=10..50`. Disable with
`NEWSMUNCHER_THEMATIC_DIVERSITY=off` or by removing the variable.

## Validation and limitations

Focused tests cover exact catalogue shape, default-off behaviour, deterministic
selection, decaying recency penalties, nonzero reuse, bounded restart
persistence, per-pet isolation, duplicate UUIDs, concurrent appends, source-
exempt influence detection, audit provenance, Phase 4M independence and the
500-generation concentration gates.

The offline audit measures what is selected, not what a language model would
use. Exact keyword detection misses paraphrases and can attribute coincidental
matches. The system intentionally offers inspiration rather than enforcing it,
so domain uptake may be low. Conversely, a live model may repeatedly favour a
subset of the suggestions. No default promotion is justified until complete
articles receive blind human review and actual influence is measured.

No paid provider call, production database write, commit or push was performed.
