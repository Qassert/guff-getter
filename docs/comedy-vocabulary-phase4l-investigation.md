# NewsMuncher Phase 4L — linguistic variety investigation

Date: 2026-10-12

## Scope

This phase investigated why a small set of words and constructions remains
prominent despite large vocabulary banks. It made no generator, selector,
prompt, memory, configuration or production-data change. It made no provider
call. The evidence is the completed Phase 4K run, earlier local comedy audits,
the current resources and the current source code. All recommendations remain
unimplemented.

The creative target is unchanged: surreal collisions, innuendo, obscure
objects, unusual creatures, deadpan escalation and spontaneous inventions are
features. Coherence and conventionality are not optimisation goals here.

## Evidence and limitations

The Phase 4K experiment contains 28 final articles: seven fixed sources through
each of A, B, C and D. It records the complete source, offered generated
concepts and descriptors, offered names, raw hybrid ingredients, exact final
matches and final copy-edited article. Each variant had fresh memory and seven
sequential articles within that memory.

The experiment did not retain the first-pass draft. Therefore this report can
prove that a word was in the source, an offer, or the post-copy-edit article.
When a final word appears in neither source nor recorded offers, attribution is
limited to “model-generated in either pass or an unrecorded prompt influence.”
The copy editor was instructed to introduce no new ideas, but that instruction
is evidence of intent rather than proof of compliance. First-pass versus
copy-edit attribution is consequently unknown.

Simple token and n-gram measurements below are case-insensitive and normalize
spaces/hyphens for the six requested expressions. “Recurring content word” is
a lexical heuristic, not a full part-of-speech analysis. Counts include title
and body. Source words are separated when assessing likely comedy repetition.

## Requested-word provenance

None of the seven fixed sources contains gravy, custard, marmalade, cucumber
slicer, crumpet or milk float. Their final appearances therefore all enter via
the comedy supply or model behaviour.

| Expression | Final articles | Final occurrences | Confirmed generated offer | Confirmed raw offer | No same-article recorded offer |
|---|---:|---:|---:|---:|---:|
| gravy | 9 | 13 | 5 articles | 0 | 4 articles |
| custard | 7 | 7 | 4 articles | 2 articles | 1 article |
| marmalade | 6 | 8 | 2 articles | 0 | 4 articles |
| cucumber slicer | 3 | 4 | 3 articles | 0 | 0 |
| crumpet | 3 | 3 | 3 articles | 0 | 0 |
| milk float | 1 | 1 | 0 | 1 article | 0 |

The confirmed traces are specific:

* **Gravy** came from offers such as “salad spinner of constitutional gravy
  service,” “identify counterfeit gravy,” “gravy boat for official tea-break
  observance,” “parish subcommittee for gravy procurement” and
  “constitutionally gravy-invested.” Four other final articles used gravy even
  though that article’s source and recorded offers did not. This is confirmed
  model-side reintroduction, with the generating pass uncertain.
* **Custard** came from generated offers including “custard containment” and
  “custard ladle.” Two D articles used raw hybrid ingredients containing
  custard. One C article introduced it without a same-article source or offer.
* **Marmalade** was supplied by “marmalade-launching radio-controlled aircraft”
  and “parish certificate for marmalade smuggling.” Four other articles
  introduced it without a same-article source or recorded offer.
* **Cucumber slicer** was always traceable to a generated concept: variants
  included “professionally throbbing,” “with adjustable firmness” and “capable
  of unauthorised swelling.”
* **Crumpet** was always traceable to generated concepts or names in the same
  article. The name resources themselves repeatedly contain Crumpet titles,
  surnames and places.
* **Milk float** occurred once, in D, as an expanded-catalogue raw ingredient.
  The final spelling was hyphenated. No milk-float recurrence occurred within
  this 28-article run, although earlier audits observed it repeatedly.

The resources make these words available through several independent routes.
The concept component file contains 16 gravy, six custard, five marmalade, four
crumpet, three milk-float and one cucumber-slicer occurrence. The descriptor
component file adds seven gravy, three marmalade, one custard and one crumpet
occurrence. The name component file adds nine crumpet, five gravy, two custard
and two marmalade occurrences. The expanded catalogue mirrors many of those
same curated components. A word can therefore re-enter through a concept base,
modifier, descriptor subject, title component, raw catalogue identity, or the
model’s learned comic vocabulary.

## Effective diversity versus catalogue size

The raw Phase 4K pools are genuinely broad. The noun route has 1,403 legacy and
928 eligible catalogue records, with 2,331 unique combined texts. The historical
animals route has 2,110 legacy mixed identities and 560 eligible catalogue
animals, with 2,575 unique combined texts. B and D sample these pools by seeded
shuffle and alternate legacy/catalogue sources. There is no alphabetical-first
or catalogue-order selection in that path.

The generated path is much narrower in the dimensions readers notice. It has
24 concept templates, 37 component banks and hard per-slate category quotas.
Every 20-item baseline slate reserves six impossible-technology slots or close
equivalents through the two target banks, six institutional slots in the noun
bank, four ridiculous-creature slots, and four innuendo slots. A large base pool
changes the object inside those frames; the joke-bearing modifiers and topics
come from far smaller curated banks.

Across the real A run, all 140 offered concept phrases were unique and 138/140
bases were unique. Exact phrase and base variety were therefore functioning.
The semantic distribution was still concentrated: 32 institutional-control,
26 impossible-technology, 22 innuendo and 21 unexpected-behaviour concepts.
Together those four themes account for 101/140 offers (72.1%). B, C and D show
the same concentration after downsampling. This is the clearest demonstration
that nominal phrase capacity is not effective creative diversity.

Concept construction uses deterministic randomness, but each requested slot
draws multiple candidates and normally selects the highest score. Scores favour
visual categories, three-to-six-word phrases, strong compact creatures and
bureaucratic conflict. Category quotas are hard. The seed changes candidates,
but scoring and quotas repeatedly expose the same productive stratum. Recent
offer penalties reorder complete phrase/base/premise candidates after they have
already been built; they do not penalize a component word such as gravy shared
across different premises.

Descriptor evaluation mode improved this situation: it constructs a pool of at
least 644 candidates and uses seeded jitter before quality within the eligible
stratum. The real run offered 279 unique descriptor phrases out of 280. It still
enforces category, intensity and all six role quotas, and its curated component
banks contain the same favourite lexemes. Exact descriptor diversity can thus
coexist with repeated subjects or word families.

Raw hybrid selection is the broadest lexical sampler. Across B and D it offered
140 raw identities, 139 of them unique. It does not use recent history across
articles, however; each call reshuffles the complete pool independently. The
probability of an immediate exact repeat is low, but there is no explicit
short-window protection for semantic domains or lexical heads.

Fallback logic is not the primary cause in this run. Concept selection can
relax base and premise cooldowns only after strict saturation, while exact
phrase cooldown and active leases remain hard. Descriptor selection can relax
subject/premise cooldowns after a strict slate is impossible, while exact phrase
cooldown remains hard. The Phase 4K run had ample fresh phrases and shows
concentration without requiring exact-phrase reuse.

## Prompt and model effects

The main rewrite prompt contains no gravy, custard, marmalade, cucumber slicer,
crumpet or milk-float example. Generated-concept, descriptor, invented-name and
hybrid guidance also contain none. Those specific words are not being copied
from a fixed prompt example.

The prompt does strongly shape uptake. It asks the model to replace most nouns,
adjectives and adverbs; use several supplied words; use at least one supplied
animal/object; invent additional bizarre language; deliver bizarre specificity;
and escalate absurd situations. This intentionally gives ingredients high
salience and gives the model permission to add its own familiar British-surreal
vocabulary. The repeated institutional and powered constructions are reinforced
both by the offered slate and by broad style cues such as deadpan seriousness,
ridiculous motivations and stupid consequences. These instructions are not
wrong for the product, but they amplify whatever lexical and structural modes
are most available.

The 28 articles prove a model contribution beyond direct ingredient uptake.
Four of nine gravy articles and four of six marmalade articles have no
same-article source or recorded offer containing that word. Conversely,
cucumber slicer, crumpet and milk float were fully explained by offers. Repeated
vocabulary therefore originates in both layers:

1. ingredient construction repeatedly supplies a curated favourite palette;
2. the model has its own stable interpretation of “British surreal comedy” and
   sometimes selects the same palette without a supplied trigger.

The first cause is strongest for exact distinctive objects such as cucumber
slicer. The second is material for generic comic foods such as gravy and
marmalade. The evidence does not support assigning all repetition to either
layer.

## Objective final-output diversity

Article length differs by variant, so raw counts alone are misleading.

| Variant | Final tokens | Unique word types | Type/token ratio | Cross-article recurring-word excess | Excess per 1,000 tokens | Repeated 2–3 word phrases |
|---|---:|---:|---:|---:|---:|---:|
| A | 1,146 | 688 | 0.600 | 86 | 75.0 | 3 |
| B | 974 | 589 | 0.605 | 49 | 50.3 | 3 |
| C | 956 | 575 | 0.601 | 41 | 42.9 | 0 |
| D | 917 | 556 | 0.606 | 37 | 40.3 | 0 |

“Recurring-word excess” sums, for content words present in multiple articles,
the number of article appearances after the first. It is source-aware only in
the detailed provenance analysis and should not be treated as a humour score.
The repeated phrases were “band powered,” “competitive queueing” and “biscuit
dunking” in A, and “band powered,” “toast rack” and “hot water” in B. No repeated
content bigram or trigram crossed C’s or D’s seven articles under this exact
tokenization.

All variants have nearly identical type/token ratios. A’s larger absolute
vocabulary is substantially explained by longer articles. Its normalized
cross-article reuse is higher and aligns with its larger number of
preconstructed premises. This supports the Phase 4K density hypothesis without
establishing a quality winner.

The most persistent non-source words also reveal structure rather than exact
phrase reuse. In A, powered appeared in six articles, municipal and biscuit in
five, and royal and ceremonial in four. In B, powered appeared in five. In C,
powered and ceremonial appeared in five. In D, ceremonial appeared in four and
powered, municipal, custard and rescue in three. Exact offered phrases remained
almost wholly unique throughout.

## Existing repetition controls

### Effective within their stated boundary

* Phrase leases and 30-day accepted-use cooldowns prevent exact accepted concept
  and descriptor phrases from immediately returning.
* Concept base and premise keys prevent duplicates inside one slate and cool
  exact accepted bases/premises. Animal records provide an additional species
  path.
* Descriptor subject, premise and semantic-family records join some exact and
  close constructions; role and mechanism balancing prevents one slate from
  collapsing to a single form.
* Name exact cooldown and sound-family memory broaden invented identities.
* Topic memory penalizes recently offered complete phrases, premises and bases,
  and detects seven named subjects plus six named constructions in final text.
* Final-joke memory protects numbered-group gags and queue-containment variants.
* Source exemptions correctly avoid penalizing vocabulary required by the news
  story.

The Phase 4K audit confirms these controls’ success at exact identity: A offered
140 unique concept phrases and 138 bases; every variant offered unique generated
concept phrases; 279/280 descriptors were unique.

### Insufficient for the observed problem

* There is no general individual-word or lexical-head memory. Gravy in
  “constitutional gravy service,” “counterfeit gravy,” “gravy procurement” and
  “gravy-invested” has different phrase, premise, subject and sometimes
  mechanism keys.
* Topic memory recognizes gravy, custard within a broad dessert family, milk
  floats and a few other manually enumerated subjects, but final guidance only
  activates after two detections in five articles. It is a narrow detector, not
  a vocabulary-frequency system.
* Completed offers enter topic-memory ranking, but component words inside newly
  assembled phrases do not receive independent recency penalties.
* Unused offers are released from strict registries. This is correct for finite
  availability, but repeated exposure can recur because selection remembers
  only the complete offer fields recorded by topic memory.
* Exact accepted matching misses inflection, hyphenation and paraphrase. It also
  misses a model-invented familiar word when no offered phrase maps to it.
* Final-joke memory is deliberately conservative and covers only two forms. It
  cannot see “another municipal food inspection” as structurally close to an
  earlier gravy council.
* Mentioning recent topics in avoidance guidance can itself prime those words.
  The current bounded threshold reduces that risk, but it is one reason not to
  solve general lexical repetition chiefly in the prompt.

Yes: “municipal gravy inspection” can bypass the controls after a different
gravy construction. Its full phrase can be new; its base can be inspection;
its premise may encode a different modifier or theme; no generic word record is
consulted; and final guidance may not activate until the gravy detector has
already observed two recent uses.

## Confirmed causes, ranked by evidential strength

1. **Memory granularity is coarser than reader perception.** Controls protect
   full phrases, bases, selected premises, a few semantic families and a small
   topic list. Readers notice individual lexical anchors such as gravy and
   structural blends such as municipal food regulation.
2. **Curated favourite words are duplicated across independent resources.** A
   word can be drawn through concepts, descriptors, names, expanded catalogue
   records and model invention. The catalogue is large, but joke-bearing banks
   repeat a much smaller editorial palette.
3. **Hard category quotas concentrate mechanisms.** In the baseline real run,
   four themes formed 72.1% of concepts. Large base banks cannot undo that
   allocation.
4. **Quality selection favours a compact productive stratum.** Multiple random
   candidates are generated, then short, visual, bureaucratic or strong compact
   forms receive systematic advantages. Seeds vary the surface result while the
   preference landscape stays stable.
5. **The model independently reuses a learned British-surreal palette.** The
   no-offer occurrences of gravy and marmalade confirm this. Broad prompt
   permission to invent and escalate makes that behaviour visible.
6. **High premise density increases opportunities for recurrence.** A had the
   highest normalized cross-article word reuse and 20 generated premises per
   article; C and D supplied fewer. This is a small experiment and does not
   establish which density is funniest.
7. **Fallback relaxation is a reliability trade-off, not the observed primary
   driver.** Concentration exists even with unique phrases and bases.

## Ranked remedies for review

No remedy below is implemented.

### 1. Add a decaying lexical-exposure ledger used as a soft sampling penalty

Extract salient content heads from offered ingredients and successfully
persisted final articles. Record source-exempt normalized forms, including
hyphen/inflection aliases, for a short article window. Apply a bounded penalty
when sampling component banks and raw identities; never make an item illegal.
Distinguish “offered recently” from “used in final,” with final use weighted
more strongly and both decaying to zero.

Advantages: directly matches the reader-visible problem; covers model-introduced
words after their first appearance; retains every word; works before prompt
construction; avoids priming the model with an avoidance list; can protect both
raw and generated routes.

Disadvantages: token/head extraction needs careful compound handling; overly
broad stemming could suppress innocent uses; local memory adds bounded storage
and ranking work; source exemptions and concurrency need the same care as the
existing topic system.

### 2. Make component selection exposure-aware before phrase construction

Maintain recency counts for the small modifier/topic banks and use weighted
sampling without replacement or an exploration bonus. Apply it separately
within category/intensity compatibility, after safety and grammar eligibility.
Keep quality as a floor, then sample across the eligible stratum instead of
always maximizing it.

Advantages: addresses the narrowest effective pool; preserves curated humour;
creates new combinations from existing material; avoids permanent bans and
does not require model cooperation.

Disadvantages: some low-frequency components may be weaker; requires calibrated
quality floors and deterministic tests; could shift rather than eliminate a
repetitive structural pattern if hard quotas stay unchanged.

### 3. Add a small exploration allocation to mechanism/category planning

Keep the strong core quotas, but make a minority of slots rotate among
underexposed eligible mechanisms over a recent window. Do not optimize for
uniformity and do not remove innuendo, bureaucracy or powered objects.

Advantages: addresses the 72.1% theme concentration while retaining familiar
high-performing mechanisms; promotes semantic-domain breadth rather than mere
noun churn.

Disadvantages: quota changes affect the comic mix and therefore carry more
quality risk than lexical penalties; sparse mechanisms may need more component
depth; offline diversity gains cannot prove humour.

### 4. De-duplicate editorial lexemes across resource roles, using aliases

Inventory repeated anchors across concepts, descriptors, names and catalogue
imports. Give shared anchors one canonical lexical family for recency accounting
while leaving every occurrence and creative role intact.

Advantages: stops the same word bypassing memory through another resource;
improves observability; requires no blacklist.

Disadvantages: curation and migration effort; canonical families can become too
broad; by itself it does not alter the model’s independent inventions.

### 5. Retain first-pass text in local audit mode only

When diagnostic logging is enabled, optionally record the first-pass article
alongside the final copy edit, with the same local-only warnings and secret
exclusions.

Advantages: resolves the present attribution gap and reveals whether copy
editing preserves or introduces recurring vocabulary.

Disadvantages: larger sensitive local logs; diagnostic benefit only; does not
reduce repetition.

### 6. Use bounded prompt guidance only as a secondary backstop

If a final lexical family remains prominent despite selector changes, describe
a small number of recent semantic families rather than repeat the exact words,
and activate only at a clear threshold.

Advantages: can affect model-invented repetition that selectors cannot prevent.

Disadvantages: avoidance prompts may prime the forbidden idea, consume prompt
space or steer tone. It depends on model compliance and should not be the main
control.

Permanent blacklists, global word removal, strict semantic bans and coherence
filters are rejected. They would discard useful future choices, flatten the
voice or suppress the bizarre combinations the user values.

## Recommended approach

The best next implementation candidate is a two-level, soft, decaying exposure
system: lexical-head memory across offers/finals, plus exposure-aware sampling
inside component banks. It should operate before prompt construction, exempt
source-required words, normalize compounds conservatively, decay over roughly
five to ten completed articles, and always leave a nonzero selection probability.
Final use should carry more weight than an unused offer. A small exploration
bonus should choose among already safe and quality-qualified candidates rather
than reward obscurity or nonsense.

Keep the model prompt, surreal direction, innuendo, unusual creatures, obscure
objects and existing strong premise machinery unchanged for the first trial.
Measure lexical heads, mechanisms, semantic domains, offer-to-final uptake and
article-length-normalized reuse against the Phase 4K records. Human review must
decide whether surprise improved without losing the existing humour.

This approach targets the confirmed granularity gap while preserving every word
for later reuse. It also separates diversity control from editorial taste: the
system changes how recently exposed material is sampled, not what NewsMuncher
is allowed to find funny.
