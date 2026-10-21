# OBJECT expansion Batches 02–09 — overall review

> **Imported 20 October 2026.** The user explicitly approved all 800 entries,
> including the 41 originally marked `needs_review`. Pre-import validation found no
> automatic conflicts. The live sidecar records all 800 as `confirmed`; the candidate
> statuses below remain unchanged as historical review evidence.

This collection contains **800** manually curated physical-object candidates. The requested ceiling was 2,000, but the collection stops 1,200 short rather than filling the files with ambiguous dictionary senses, trivial variants or weakly recognisable specialist terms.

| Batch | Theme | Candidates | Proposed | Needs review | Automatic rejects |
|---:|---|---:|---:|---:|---:|
| 02 | Historical, medieval and ceremonial objects | 100 | 96 | 4 | 0 |
| 03 | Transport, maritime and aviation | 100 | 95 | 5 | 0 |
| 04 | Construction, engineering and infrastructure | 100 | 94 | 6 | 0 |
| 05 | Computing, electronics and robotics | 100 | 95 | 5 | 0 |
| 06 | Sports, recreation and unusual toys | 100 | 95 | 5 | 0 |
| 07 | Theatre, entertainment and specialist equipment | 100 | 94 | 6 | 0 |
| 08 | Clothing, accessories and unusual domestic objects | 100 | 95 | 5 | 0 |
| 09 | Space, security, archaeology and miscellaneous equipment | 100 | 95 | 5 | 0 |

- Total candidates: **800**
- Proposed: **759**
- Needs review: **41**
- Automatic duplicates remaining in candidate files: **0**
- Pre-file editorial rejections documented across reports: **32 examples**.

All accepted names were unique across the eight candidate files, including across `object` and `device` categories, and absent from the 669-entry pre-import catalogue. `dustpan` was rejected during validation as a whitespace-format duplicate of live `dust pan` and replaced with the independently validated `vacuum storage bag`.

Local Open English WordNet data was used only to check physical meanings and expose ambiguity. Its broad artefact tree was not used as an automatic candidate source because inspection showed unsuitable senses such as “bottom” for cargo ship and “technical” for an armed truck. This quality threshold is the reason for the documented shortfall.

Run each batch with:

```bash
python3 scripts/validate_object_expansion.py docs/object-expansion-batch-NN.csv
```

The expected post-import result is 100 live-vocabulary duplicate rejections for each
batch. The live catalogue now contains 1,469 entries: 1,299 physical objects/devices
and 170 descriptors.
