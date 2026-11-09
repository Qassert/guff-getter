# NewsMuncher Phase B specialist vocabulary expansion

The remaining 90 thematic domains were generated in nine batches. Every entry remains separate from production and has `candidate_unreviewed` approval metadata. Automated acceptance means only that local structural screening passed; it is not factual approval.

Model: `gpt-5.4-mini`. Additional API cost: **$0.817522**. Input/output tokens: **93,753/166,046**.

## Counts

- Proposed: **3,150**
- Passed automated screening: **2,067 (65.62%)**
- Rejected: **274 (8.70%)**
- Needs human verification: **809 (25.68%)**
- Accepted distinct entity phrases: **803**
- Accepted new single-token noun heads: **785**

| Type | Proposed | Passed | Rejected | Verify |
|---|---:|---:|---:|---:|
| entity | 1,620 | 803 | 119 | 698 |
| process | 810 | 692 | 62 | 56 |
| property | 540 | 419 | 80 | 41 |
| relationship | 180 | 153 | 13 | 14 |

## Domain coverage

All 90 non-pilot domains were covered. The excluded pilot domains were
mycology, acoustics, aurora science, industrial archaeology, divination
practices, history of surgery, topology, puppet theatre, glassmaking and
experimental archaeology. The scaled set therefore completes the original
100-domain taxonomy without replacing or regenerating the pilot.

Coverage by family: living systems 8; cosmos/physics 8; earth/atmosphere 8;
past societies 8; culture/language 8; built systems 9; medicine/mind 8;
abstract technology 8; performance arts 8; craft/material 8; field practices
9.

## Batches

| Batch | Domains | Passed | Rejected | Verify | New heads |
|---|---:|---:|---:|---:|---:|
| 1 | 10 | 283 | 16 | 51 | 126 |
| 2 | 10 | 249 | 23 | 78 | 98 |
| 3 | 10 | 253 | 25 | 72 | 114 |
| 4 | 10 | 223 | 30 | 97 | 89 |
| 5 | 10 | 206 | 35 | 109 | 59 |
| 6 | 10 | 232 | 18 | 100 | 73 |
| 7 | 10 | 208 | 28 | 114 | 66 |
| 8 | 10 | 195 | 47 | 108 | 67 |
| 9 | 10 | 218 | 52 | 80 | 93 |

## Growth profile

Strongest domains by locally passed candidates: marine-biology (33), linguistics (33), celestial-navigation (33), microbiology (32), botany (32), extremophile-life (32), geology (32), pharmacology (32), roman-engineering (31), electromagnetism (30).
Weakest domains by locally passed candidates: radio-drama (10), stage-magic (12), canal-engineering (13), beekeeping (15), falconry (15), games-and-play (16), folklore-customs (17), stage-machinery (17), experimental-cinema (17), ancient-egypt (18).

The greatest noun growth comes from biological structures, physical instruments, historical artefacts, craft tools and built-system components. The weakest area remains relationships: the stricter two-per-domain quota reduced generic filler, but these records still need the most semantic scrutiny. Cultural and historical proper terms, eponyms and transliterations account for much of the verification queue.

## Screening

Rejection reasons: `existing_or_pilot_normalised_duplicate` 259, `scaled_normalised_duplicate` 103, `invalid_or_overlong` 11.
Verification flags: `noun_head_collision_review` 751, `specialist_factual_review` 249, `historical_provenance_review` 29.

Representative unusual survivors: `siphonophore`, `statocyst`, `ostracon`, `palimpsest`, `voussoir`, `caisson`, `cryptic plumage`, `astrolabe`, `ocellus`.

## Before production integration

1. Specialist human/source review for every verification-flagged term and a representative audit of each domain’s locally passed terms.
2. Resolve head collisions by retaining distinct compounds while removing aliases and generic-head restatements.
3. Correct classification, spelling, plural handling, transliteration and culturally specific provenance.
4. Re-run exclusion-aware capacity and category tests on only the approved subset.
5. Integrate through a versioned catalogue migration only after review; do not treat model confidence or this automated pass as editorial approval.
