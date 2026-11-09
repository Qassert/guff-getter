# OBJECT vocabulary expansion workflow

OBJECT expansion is a two-stage editorial process. A candidate batch is reviewed and
approved before a separate import change is considered. Candidate files do not affect
the live generator.

## Protected and live data

Never edit the six MUNGE CLASSIC files in `newsmuncher/resources/words/` during OBJECT
work: `slang.csv`, `nouns.csv`, `adverbs.csv`, `animalsAndObjects.csv`, `names.csv`, and
`places.csv`.

The live OBJECT data is the two-column
`newsmuncher/static/data/object-generator-vocabulary.csv`. Its metadata sidecar is
`newsmuncher/static/data/object-generator-domains.csv`. The validator reads the live
file each time; it does not embed a snapshot of its contents.

## Preparing a batch

Create `docs/object-expansion-batch-NN.csv` with these columns in this order:

```text
category,word,domain,form,source_file,review_status
```

- Use `object` for passive objects, hand tools, components, containers, fixtures and
  furnishings. Use `device` for powered apparatus and measuring instruments where it
  best matches the existing generator grammar.
- Keep names concise, recognisable and physically concrete. Prefer one to four words.
  Do not inflate a batch with plurals, spelling variants or adjective-prefixed versions.
- Select a specific domain from the validator's `VALID_DOMAINS` and a grammatical form
  from `VALID_FORMS`. Extend those controlled values only when the batch introduces a
  genuinely new editorial domain or form.
- Use accurate provenance. `curated_batch_NN` is appropriate for an editorially curated
  list; never attribute copied words to a Classic file unless that is their real source.
- Set clear candidates to `proposed`. Set ambiguous meanings, possible synonyms,
  debatable categories or uncertain forms to `needs_review`.

## Validation

From the repository root, run:

```bash
python3 scripts/validate_object_expansion.py docs/object-expansion-batch-NN.csv
```

Add `--json` for machine-readable deterministic output. The validator compares the
batch with the current live `object` and `device` rows, its own rows, and every other
matching batch in `docs/`. Rows marked `approved` or `imported` in an earlier batch are
blocking; overlaps with pending batches are review warnings.

Automatic rejection is deliberately limited to exact or formatting-normalised matches
and conservative singular/plural matches. British/American spelling variants, curated
synonym pairs and strong name similarities are warnings. These heuristics cannot prove
semantic equivalence: an editor must review every warning and also look for conceptual
duplicates the tool misses. Shared words alone do not make two objects duplicates.

Malformed CSV, missing values and unknown metadata make a batch unready. Output order is
stable, so an unchanged batch produces the same report.

## Review and approval

Review the generated findings alongside the batch, paying particular attention to:

1. whether each term has a familiar physical-object meaning;
2. whether its category and form read naturally in every OBJECT phrase structure;
3. whether spelling follows British usage where practical;
4. whether a specialised object is still recognisable without niche context;
5. whether two candidates name the same implement despite different wording.

Approval is a distinct human decision. Do not interpret a zero exit code as permission
to import. Approved rows may later be appended to the live two-column vocabulary and
mirrored in the classification sidecar in a dedicated, separately reviewed change.
That future import must rerun validation against the then-current live file and verify
the Classic file hashes. This workflow intentionally provides no automatic importer.

## Import history

- **Batch 01 — imported 20 October 2026:** all 250 reviewed rows were explicitly
  approved. They were appended to the live two-column vocabulary and classification
  sidecar without rewriting the original 419 rows. All imported sidecar rows are
  `confirmed`; the 24 historical `needs_review` rows remain unchanged. The resulting
  catalogue contains 669 entries: 170 descriptors and 499 physical objects/devices.
  Revalidating Batch 01 now intentionally reports all 250 rows as live duplicates,
  preventing accidental re-import.
- **Batches 02–09 — imported 20 October 2026:** all 800 rows were explicitly approved,
  including the 41 candidate rows originally marked `needs_review`. The live sidecar
  stores all 800 imported classifications as `confirmed`; candidate CSV statuses remain
  intact as historical review evidence. The catalogue now contains 1,469 entries:
  170 descriptors and 1,299 physical objects/devices. Revalidating any imported batch
  now reports its 100 rows as live duplicates.
- **Batches 10–19 — imported 20 October 2026:** all 1,000 rows were explicitly
  approved, including the 49 candidates originally marked `needs_review`. Exactly 636
  objects and 364 devices were appended in original batch order; all imported sidecar
  rows are `confirmed`, while candidate CSV statuses remain intact as historical review
  evidence. The catalogue now contains 2,469 entries: 170 descriptors and 2,299 physical
  objects/devices. OBJECT reads these rows directly, and MUNGE CLASSIC includes them via
  its shared physical-vocabulary loader while deduplicating the ten acknowledged legacy
  overlaps. Revalidation now identifies every imported row as a live duplicate.
- **Batches 20–29 — pending review:** 500 candidates were prepared across ten comedy-first
  physical-object themes. Thirteen initial live conflicts were replaced and final
  validation found no blocking duplicates or malformed rows. The smaller 500-entry set
  was retained instead of padding to the 1,000-entry ceiling. Nothing from these batches
  has been imported into the runtime vocabulary or sidecar.
