# NewsMuncher Phase 4W — rolling noun exclusion proof of concept

Date: 2026-10-13

## Outcome

The approach is feasible for provenance-backed comic nouns and phrases. The
offline prototype extracts identities that were offered and then appeared
exactly in the finished article, protects source words, names and places, and
stores per-pet entries in a bounded FIFO. Compound entries retain their complete
identity and block distinctive components: `gravy boat` creates
`phrase:gravy boat` and `noun:gravy`, but not `noun:boat`.

Filtering is independent of ingredient origin, so the same function can reject
legacy, generated, raw or thematic candidates and continue through a larger
candidate queue to refill vacancies. The representative refill test rejected
`gravy pump` and selected the next two eligible candidates without shortage.
Production quota-specific exhaustion was not simulated; a future integration
would need the existing bounded candidate pools and an explicit controlled
failure if a hard category truly ran out.

## Local estimate

The diagnostic examined 28 unique existing local audit records. It extracted
559 conservative phrase/anchor entries: mean 19.96 and median 20 per article.
At that observed rate, a 5,000-entry FIFO would begin releasing its oldest
entries after approximately **250 articles**. This is an estimate, because one
compound can contribute both a phrase and a distinctive anchor and the audit
sample is small.

## Extraction limits

Existing audit provenance makes high-precision extraction practical, but it
misses novel model inventions that were never offered. Once a noun is already
in the exclusion list, an exact boundary scan can detect the model independently
reintroducing it in first-pass or final text without another provider call. That
detection happens after generation, so it can audit a violation but cannot
prevent it unless the exclusion is also presented to the model or a paid retry
is introduced.

General local noun inference from unrestricted prose is less reliable without a
part-of-speech model: verbs and adjectives can look noun-like, while unusual
comic inventions may be absent from dictionaries. The prototype therefore
chooses precision over recall. A production design should start with exact
provenance-backed identities and measured false negatives rather than block all
"meaningful words."

## Concurrency and failure

The prototype reserves selected identity anchors under one lock. Concurrent
generations for the same pet cannot select the same reserved identity; separate
pets do not share exclusions. A failed generation releases its reservation and
does not change the FIFO. Only successful completion commits entries. A real
implementation would need equivalent atomic persistent reservations and FIFO
updates, rather than this deliberately in-memory diagnostic class.

## Recommendation

The smallest practical implementation would be a default-off, per-pet persistent
ledger using the existing Mongo-shaped memory pattern:

1. Filter candidate phrases by exact blocked phrase and distinctive component
   anchors, with source/name/place exemptions.
2. Reserve anchors atomically while assembling the existing slate and refill
   from its current bounded candidate pool.
3. Release reservations on failure; after successful persistence, commit only
   exact final uses into a 5,000-entry FIFO.
4. Audit exact first-pass/final appearances of excluded anchors introduced by
   the model. Do not retry or add a provider call automatically.

Before production integration, review extraction precision on a larger human-
labelled sample and measure hard-quota availability. The proof of concept does
not justify changing prompts or live generation yet.

## Files and validation

- `scripts/diagnostics/evaluate_rolling_noun_exclusion.py`
- `tests/python/test_rolling_noun_exclusion.py`

Focused validation: 8 tests passed, covering compound anchors, source
protection, vacancy refill, FIFO eviction, per-pet isolation, failure release,
concurrent reservation and detection of model-invented reuse. No provider call,
production database write or production runtime change occurred.
