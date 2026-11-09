# OBJECT Expansion Batches 10–19 Summary

## Scope

- Prepared **1,000** review candidates across ten themed batches (100 per batch).
- The requested ceiling was 1,500. The set stops at 1,000 because these were the candidates that met the physical-object, recognisability and distinctness threshold without padding the catalogue with weak variants.
- All **1,000 candidates were explicitly approved and imported on 20 October 2026**, including the 49 originally marked `needs_review`.

## Counts

- Objects: **636**
- Devices: **364**
- Proposed: **951**
- Needs review: **49**
- Blocking conflicts after preparation: **0**
- Advisory Classic overlaps: **10**
- Automated near-name warnings: **8**

## Batch totals

- Batch 10 — Maritime, fishing and underwater equipment: 100 candidates (55 objects, 45 devices; 95 proposed, 5 needs review).
- Batch 11 — Victorian, medieval and historical household objects: 100 candidates (100 objects, 0 devices; 95 proposed, 5 needs review).
- Batch 12 — Laboratory, chemistry and scientific apparatus: 100 candidates (51 objects, 49 devices; 95 proposed, 5 needs review).
- Batch 13 — Gardening, forestry and landscaping tools: 100 candidates (53 objects, 47 devices; 96 proposed, 4 needs review).
- Batch 14 — Festivals, carnivals, circuses and fairgrounds: 100 candidates (80 objects, 20 devices; 95 proposed, 5 needs review).
- Batch 15 — Emergency, rescue and disaster equipment: 100 candidates (57 objects, 43 devices; 95 proposed, 5 needs review).
- Batch 16 — Manufacturing, workshops and unusual machinery: 100 candidates (5 objects, 95 devices; 95 proposed, 5 needs review).
- Batch 17 — Film, photography, broadcast and media hardware: 100 candidates (56 objects, 44 devices; 95 proposed, 5 needs review).
- Batch 18 — Museums, archaeology, exploration and navigation: 100 candidates (79 objects, 21 devices; 95 proposed, 5 needs review).
- Batch 19 — Unusual furniture, architectural fittings and public fixtures: 100 candidates (100 objects, 0 devices; 95 proposed, 5 needs review).

## Validation method

- Exact, formatting, compact-whitespace and conservative singular/plural checks against the current live OBJECT vocabulary.
- Intra-batch and cross-batch checks across all staged batch CSVs.
- Near-name, British/American spelling and configured synonym checks surfaced for human review.
- Exact overlap with MUNGE CLASSIC `animalsAndObjects.csv` is advisory only; it does not reject an otherwise valid OBJECT candidate.

## Preparation replacements

- Batch 16: replaced `surface planer` with `dovetailing machine` after detecting a duplicate inside the batch.
- Batch 18: replaced `pointing trowel` with `excavation dustpan` because `pointing trowel` is already live.

## Advisory Classic overlaps

- Batch 11: **candle snuffer** overlaps **candlesnuffer**.
- Batch 11: **coin purse** overlaps **coin purse**.
- Batch 11: **oil lamp** overlaps **oil lamp**.
- Batch 11: **trivet** overlaps **trivet**.
- Batch 13: **garden fork** overlaps **garden fork**.
- Batch 15: **ceiling hook** overlaps **ceiling hook**.
- Batch 17: **audio mixer** overlaps **audio mixer**.
- Batch 18: **display case** overlaps **display case**.
- Batch 18: **dust cover** overlaps **dust cover**.
- Batch 18: **snow shovel** overlaps **snow shovel**.

## Quality and coverage notes

- Coverage is deliberately concrete: named tools, fixtures, vessels, instruments, machinery and furnishings dominate.
- The scientific and industrial batches contain more devices; the historical and furniture batches contain more passive objects. This follows the subject matter rather than an artificial category quota.
- Forty-nine entries are explicitly marked `needs_review`, chiefly for specialist terminology, unfamiliar historic names or possible ambiguity. Advisory validator findings are documented in the per-batch reports.
- Future batches should favour domains outside these ten themes and avoid generating adjective swaps around the same head noun.

## Import result

- Runtime before: **1,469** rows (806 objects, 493 devices, 170 descriptors).
- Runtime after: **2,469** rows (1,442 objects, 857 devices, 170 descriptors).
- Physical vocabulary after: **2,299** objects/devices.
- Sidecar before: **1,469** rows (1,445 confirmed, 24 historical needs review).
- Sidecar after: **2,469** rows (2,445 confirmed, 24 historical needs review).
- Exactly 1,000 runtime rows and 1,000 matching `confirmed` sidecar rows were appended in batch and source order.
- The original 1,469 rows in both files remain byte-for-byte equivalent in content and order.
- Candidate CSV statuses remain unchanged as historical review evidence.
- OBJECT reads the expanded catalogue directly. MUNGE CLASSIC dynamically merges all `object` and `device` rows with its protected legacy CSV and deduplicates overlaps at runtime.
- Revalidating Batches 10–19 after import intentionally reports all 1,000 candidates as live duplicates, preventing accidental re-import.
