# OBJECT vocabulary expansion — Batch 01 review

> **Imported 20 October 2026.** The user approved all 250 candidates, including the
> 16 editorial review entries. All were appended to the live OBJECT vocabulary and
> added to the classification sidecar as `confirmed`. The analysis below is retained
> as the permanent pre-import review record.

Batch 01 originally staged **250** physical-object candidates outside the live generator. It is
balanced at 50 entries per requested domain and contains 125 `object` and 125 `device`
rows. Validation reports 234 `proposed`, 16 `needs_review`, and zero automatic
duplicates. The batch is ready for human review, not live import.

## Domain totals and examples

| Domain | Count | Examples |
|---|---:|---|
| Industrial machinery and engineering | 50 | `hydraulic press`, `gantry crane`, `flywheel`, `vernier caliper`, `anvil` |
| Scientific and laboratory equipment | 50 | `Bunsen burner`, `spectrometer`, `cloud chamber`, `microtome`, `diffraction grating` |
| Agriculture and farming | 50 | `combine harvester`, `grain auger`, `cattle crush`, `broadfork`, `pitchfork` |
| Medical and surgical equipment | 50 | `stethoscope`, `defibrillator`, `laparoscope`, `surgical retractor`, `kidney dish` |
| Musical instruments and audio equipment | 50 | `bassoon`, `timpani`, `vibraphone`, `mixing console`, `reel-to-reel recorder` |

## Entries requiring review

Sixteen candidates are retained but explicitly marked `needs_review`:

- `pillar drill`, `guillotine shear`, and `industrial boiler`: terminology or form may
  vary by workshop and region.
- `laboratory incubator`, `glove box`, and `laboratory hot plate`: qualifiers are needed
  to avoid familiar non-laboratory meanings; editorial review should confirm readability.
- `seed drill`, `cultivator`, and `silage clamp`: each has a potentially misleading
  everyday sense or a debatable apparatus/fixture classification.
- `tuning fork`, `surgical drill`, `surgical light`, and `steam steriliser`: these cross
  medical and broader instrument/tool domains; `surgical drill` is also related to the
  live generic `drill`.
- `accordion`, `triangle`, and `turntable`: each has a common non-instrument meaning or
  a name resembling an existing live term (`accordion file`).

## Duplicate review

The reusable validator dynamically compared all 250 rows with the live OBJECT `object`
and `device` rows and with the whole batch. It found:

- automatic rejections: **0**;
- live exact, formatting or singular/plural matches: **0**;
- intra-batch duplicates: **0**;
- other staged-batch conflicts: **0**;
- validator-generated synonym/spelling warnings: **0**.

The 16 review statuses above are editorial judgements and are counted even though the
mechanical heuristics did not flag them. Likely-synonym detection is intentionally
conservative and incomplete; it uses a small reviewed equivalence table plus name
similarity and cannot replace human semantic review.

During curation, **20** unsuitable shortlist terms were rejected before the candidate
file was written. Examples include `power drill` (likely synonym of electric/generic
drill), `anesthesia machine` (American variant), `combine` (ambiguous shorthand),
`grand piano` and `upright piano` (unnecessary variants for this first batch),
`mortar and pestle` (food-preparation overlap), `centrifuge` (over-broad when the more
specific laboratory term is available), `medicine cabinet` (domestic rather than
medical apparatus), and brand-derived instrument names. Rejected terms are documented
here rather than placed in the proposed import CSV.

## Sources and recommendation

Candidates were manually curated using domain knowledge, the existing local OBJECT
catalogue and its domain audit. No broad WordNet artefact dump or external generative
API was used. Names were checked for immediately understandable physical meanings and
British terminology; specialised entries still require the human review described
above.

Approval was subsequently granted for all 250 rows. To confirm that the imported words
are now protected from future re-import, run:

```bash
python3 scripts/validate_object_expansion.py docs/object-expansion-batch-01.csv
```

The expected post-import result is 250 live-vocabulary duplicate rejections.
