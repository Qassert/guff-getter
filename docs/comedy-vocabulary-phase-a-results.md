# NewsMuncher Phase A everyday vocabulary expansion

All records remain `candidate_unreviewed`, non-production-selectable and separate from runtime catalogues. “Passed” means local structural screening passed; it is not editorial or factual approval.

Model: `gpt-5.4-mini`. API cost: **$1.162027**. Input/output tokens: **153,985/232,564**.

## Results

- Generated: **3,800**
- Passed: **474**
- Rejected: **3,256**
- Needs human verification: **70**
- Passed distinct entity phrases: **187**
- Passed new exclusion-compatible heads: **187**
- Familiar entities among passed entities: **111/187 (59.36%)**

The generated entity allocation was 84% familiar by construction, but the
post-screening set did **not** meet the requested 80% familiar target. Familiar
terms overlapped heavily with production vocabulary, Phase B, or earlier Phase
A domains, while genuinely new unusual compounds survived more often. No
duplicate rule was relaxed to improve this percentage.

| Type | Proposed | Passed | Rejected | Verify |
|---|---:|---:|---:|---:|
| entity | 2,500 | 187 | 2,244 | 69 |
| process | 800 | 214 | 585 | 1 |
| property | 400 | 23 | 377 | 0 |
| relationship | 100 | 50 | 50 | 0 |

## Everyday category coverage

| Category | Proposed | Passed | Example |
|---|---:|---:|---|
| household | 280 | 23 | wrapped parcel |
| animal | 324 | 12 | ladybird |
| occupation | 288 | 55 | ornithologist |
| clothing | 274 | 16 | broadcloth |
| food_kitchen | 291 | 36 | sourdough starter |
| transport_machinery | 262 | 22 | skateboard |
| gardening_diy | 299 | 19 | camel thorn |
| hobby_leisure | 254 | 21 | birdwatching |
| shop_workplace_public | 256 | 22 | bookstall |
| human_activity | 696 | 187 | breathing |
| material_state | 576 | 61 | cardboard |

Representative surviving material includes `sofa`, `ladybird`, `beekeeper`,
`spectacles`, `sourdough starter`, `skateboard`, `spade`, `crossword`,
`bookstall`, `measuring`, and `broadcloth`. These are reusable ingredients,
not prewritten jokes.

## Screening observations

Rejection reasons: `existing_or_phase_b_normalised_duplicate` 1992, `existing_singular_plural_or_order_variant` 1989, `existing_noun_identity` 2140, `vague_or_generic_filler` 36, `phase_a_singular_plural_or_order_variant` 2604, `phase_a_normalised_duplicate` 2594, `excluded_comedy_cliche` 1.
Verification flags: `compound_noun_head_collision_review` 151, `specialist_familiarity_review` 3.

Four IDs were duplicated within rejected output: two rejected `bucket`
proposals shared one ID, and four rejected `none` placeholders shared another.
They do not affect the surviving candidate set, but should be removed during
editorial packaging.

The entity schema met the familiarity target before screening by construction. Head collisions are conservatively queued for review when a compound may still denote a distinct object; single-token repeats are rejected. Familiarity metadata is recorded only and does not affect runtime selection.

## Weaknesses and next steps

- Human review should focus first on compound head collisions, category mistakes and any proper-name or brand-like entries.
- Several domains naturally converged on the same everyday heads. Integration should select the strongest identity per concept rather than preserving every modifier variant.
- Blind generation is now a poor way to reach an 80% *new familiar* entity
  target: the reviewed resources already contain much of the obvious everyday
  vocabulary. A future pass should start from explicit category/head gaps and
  human-review the compound-collision queue, rather than generate more broad
  familiar lists or weaken identity screening.
- Relationships remain deliberately sparse and should receive semantic review before use.
- After editorial approval, measure category balance and exclusion-aware selection capacity before designing any familiarity weighting.
- Do not integrate candidates or alter the 10-noun/10-animal quotas until that separate evaluation is complete.
