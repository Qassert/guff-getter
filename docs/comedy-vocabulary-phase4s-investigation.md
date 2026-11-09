# NewsMuncher Phase 4S — Targeted Vocabulary Replacement Investigation

Date: 2026-10-13

## Scope

This investigation used checked-in code, the Phase 4M–4R reports and three
complete local Phase 4R audit records. It made no provider call, database write
or runtime change. The intended comedy remains dense, rude, surreal and
structurally faithful to the source. Only predictable reuse is in scope.

## Current copy-editor architecture

Every successful rewrite normally makes two `Responses API` calls. Both use
`gpt-6-sol`, `reasoning={"effort": "none"}`, structured JSON, a 750-output-token
ceiling, no provider storage, no automatic retry and a 30-second timeout.

The first pass receives the masked source, complete comedy prompt, word banks,
generated concepts and descriptors, optional memories and Phase 4N/4P/4R
material. The second pass receives only the sanitised first-pass **extract** as
JSON. It does not receive:

- the source;
- the preliminary title;
- selected or unused ingredients;
- lexical-exposure scores or recent events;
- semantic/topic/final-joke memory;
- Phase 4N domains or Phase 4P sparks.

Its system instruction accepts every event as literally true and preserves
absurdity, rude language, strange names, imagery, relationships and details.
It may repair grammar, broken sentence structure, agreement, flow and
readability. It must finish the extract first and derive a 12–18-word title
using only words in that extract. It is explicitly told to “Fix only” those
editorial defects and to introduce no new subjects, objects, events or ideas.
If the request fails, the route safely retains pass one. A later deterministic
title step may retain the edited title or derive another title from the final
extract; it does not rewrite the body.

The model can linguistically perform substitutions, but the present contract
does not permit creative vocabulary replacement. Supplying alternatives
without a narrow instruction change would create contradictory directions.

## Available repetition signals

### Exact words and compact identities

Phase 4M provides the strongest reusable signal. Its bounded Mongo event stream
is persistent across workers and restarts and isolated by a hashed per-pet
scope. It retains 2–30 successful articles, ten by default. Each event records
source-exempt normalized keys from offers, first pass and final. Recent final
use has weight three; first-pass use and offers have weight one. Age decays the
score, the window eventually removes it, and selection always retains an 8%
exploration floor.

Individual content words are reliable exact evidence. The current “identity”
key is the complete input when that input contains two to four meaningful
words. This captures compact ingredient phrases, but a whole article has more
than four words, so the ledger does **not** extract final-text noun phrases.
It also deduplicates each key inside an event. Its score therefore represents
recent article exposure, stage and recency, rather than repeated occurrences
inside one article.

The existing `guidance()` selects the four highest scoring words above a low
threshold. That is suitable as soft first-pass pressure but is too broad for an
editorial replacement command. In the three reviewed records its leading keys
were `working`, `raced`, `court-appointed`, `divorce`, `entered`, `arranged`
and `candidacy`. These largely reflect the shared source sequence or previous
rewrites of it. A copy editor told to replace those would risk damaging the
narrative structure while missing lower-ranked `marmalade`, `teapot` or
`milk-float`.

A safe hot list should therefore be computed from the existing per-pet events,
not copied verbatim from the current top-four guidance. A candidate should:

1. occur in the current first-pass extract;
2. be absent from the current source using existing source-exemption rules;
3. appear in at least two recent first/final events, with final use weighted
   most heavily;
4. be a high-confidence content noun or compact identity, rather than a
   narrative verb or grammar word;
5. be capped at three exact targets, sorted by score and recency.

The existing lexical data can satisfy conditions 1–3. Condition 4 needs a
conservative noun filter or known-vocabulary intersection. The repository's
source preprocessor already uses linguistic analysis, but its suitability and
runtime cost for this small second-pass filter should be tested before reuse.
A static blacklist of favourite words is not recommended.

### Semantic motifs

`TopicMemory` has explainable regexes for seven subject families—gravy,
pudding/dessert, tea equipment, allotments, milk floats, queueing and municipal
authority—and six constructions including powered machinery, tribunals and
illegal raffles. These are high-confidence but intentionally incomplete. It can
reliably label those exact families, not general semantic similarity.

`FinalJokeMemory` is narrower still: numbered-group gags and queue-containment.
Generated concepts carry semantic themes and premise keys, but current history
does not establish that every offered premise appeared in the article.
Phase 4P memory records selected seeds/constructions, not final uptake.

The existing topic and final-joke records are global rather than Phase 4M's
per-pet scope. They should not be silently presented as a per-pet hot list. A
minimal experiment can derive the supported regex motifs directly from the
same pet's retained Phase 4M first/final text keys only where exact evidence is
available, or initially restrict itself to lexical targets. Broader claims such
as “animals with occupations” require a new explainable detector and should be
labelled rule-based, never semantic measurement.

## Three recent manual outputs

All three records are in ignored `local_audits/comedy_audit.jsonl`. They use the
same Devin Battley source and enable Phases 4M, 4N, 4P and 4R. The source
contains none of the reviewed comedy vocabulary. All three selected Phase 4P
sparks reached an adjacent prompt block; none appeared exactly in pass one or
the final. The audit cannot rule out diffuse thematic influence, but it provides
no positive exact evidence of it.

### Professor Godfrey Gravygascoigne

Confirmed slate origins include the name `Professor Godfrey Gravygascoigne`,
`marmalade-launching salad spinner`, `hand-cranked-powered food processor`,
three powered-device offers, licensed objects, a provisional warrant, a cow as
divorce mediator and a budgerigar commanding a fire brigade. Gravy is embedded
in the offered name; marmalade, salad spinner, food processor, licensing,
warrant and powered machinery are direct concept offers. They are not
independent model inventions.

The first pass used these motifs. The copy editor removed the redundant
`-powered` from `hand-cranked-powered food processor`, preserved the
black-hole-powered doorbell and other motifs, and promoted the marmalade salad
spinner into the final headline. Thus it improved grammar but did not reduce
the salient repetition. Available unused sparks were archaeological-layering
inquiry with annealing, a bronze-cast pony using suspicious curves and contact
with a scribe during magnetic storms. The selected domains also offered glass,
aurora, epidemiology and manuscript material.

### Colin “Giddy” Sausagemouth

The drain-surveying stoat, freelance queue-consulting dormouse,
government-issue cork stepladder, constitutionally protected heron,
neighbour-alarming pressure washer, statutory lampshade application and two
powered-machine concepts all came from the recorded slate. The copy editor
again removed `-powered` from a hand-cranked shredder while retaining the
geothermal-powered soup dispenser. It introduced none of the reviewed motifs.

Unused sparks were an encrypted field colander using hand-painted film, an
otter in ecological succession with a control system, and static charge with
stability. Domains covered animal navigation, experimental cinema,
electromagnetism and control theory. A targeted editor could reasonably replace
one powered construction or the queue-consultant motif while preserving the
stoat, pressure-washer race and source sequence.

### Norman “Pickle” Nibbleshire

Every highlighted recurring motif has a confirmed concept origin:
`marmalade-powered ticket machine`, national crumpet crisis, milk-float
intelligence subcommittee, unlicensed-teapot inquiry, industrial wicker cream
horn, royal scandal, licensed royal footman, four powered-machine offers and
the vigorously plunging sponge bag. The first pass selected many of them. The
copy editor retained them, repaired the sponge-bag grammar and rearranged the
crumpet/inquiry sentence. It did not introduce these repetitions.

Unused sparks were a dose-dependent jelly mould using navigation dynamics, an
annealing-ovens-adapted soap dish and bubbles performed with an antenna.
Domains covered glassmaking, neuroscience, Viking navigation and entomology.
This is the strongest case for a bounded intervention: one article contains
several independently tracked familiar motifs, while three fresh current-slate
alternatives went unused.

Across the three pass-one bodies, `hand-cranked-powered` appeared in all three.
The copy edit reduced it in the first two but retained it twice in the third.
The editor therefore already performs incidental lexical cleanup, but not
history-aware replacement. Cross-article repetition in these records primarily
originates in the selected generated concepts and name slate. The model chose
which offers to foreground and supplied connective transformations, while the
copy editor preserved nearly all selected motifs.

## Replacement ingredients

The current generation already supplies the smallest useful alternative pool:
the three Phase 4P ingredients selected under the current domains and lexical
penalties. In these records all nine were unused exactly. Passing at most two
unused current sparks to the editor requires no new selection, ranking,
catalogue read, memory write or provider call. Their provenance and grammatical
roles already exist.

Phase 4N inspirations are broader and useful as background, but they are not
grammar-ready substitutions. A fresh underrepresented-domain pool would broaden
choice but introduce another selection path and make a first experiment harder
to interpret. It should be considered only if current unused sparks repeatedly
prove unusable. Used ingredients should not be suggested as replacements, and
suggestions containing a hot target should be excluded to avoid replacement-
induced repetition.

The editor should be free to distort a suggestion rather than perform a literal
swap. Exact grammar-role compatibility can guide which suggestions are shown,
but the model should retain freedom to change inflection and syntax.

## Options

### A — Extend the existing copy-edit pass

This is feasible with a deliberate, narrow exception to the current “fix only”
contract. Add a compact block containing no more than three hot targets actually
present in pass one and no more than two unused Phase 4P suggestions. Permit at
most two substitutions. Explicitly preserve narrative sequence, every comic
event, profanity, innuendo, density and irrationality; forbid simplification,
sanitisation and forced use.

Advantages are zero extra provider calls, existing fallback behavior, access to
the complete sentence context and a single-variable default-off experiment.
Risks are instruction conflict, unnecessary rewriting, grammar damage, reduced
joke density or mechanical insertion. These are manageable only if the base
prompt is rewritten coherently rather than appending contradictory prose.

Exact verification is straightforward for target counts before/after and exact
suggestion uptake. Paraphrases and semantic replacements require manual review.
A representative bounded block is roughly 450–650 characters, approximately
110–160 input tokens by the repository's character/4 estimate.

### B — Add a separate inexpensive replacement pass

The repository's rewrite path currently supports only `gpt-6-sol`; it does not
have a configurable cheaper text-edit model. The README mentions
`gpt-4.1-mini`, and that model supports the Responses API and structured output,
but adopting it here would be new runtime integration rather than reuse.
Official pricing currently lists GPT-4.1 mini at $0.40 per million input tokens
and $1.60 per million output tokens in the
[OpenAI model documentation](https://developers.openai.com/api/docs/models/gpt-4.1-mini).

At a deliberately generous 1,000 input and 750 output tokens, one extra pass
would cost about $0.0016 before regional or future pricing adjustments. The
monetary cost is small; latency, another failure mode, third-pass drift and an
extra opportunity to flatten the comedy are more material. It could trigger
only above a verified hot-list threshold and safely fall back to the existing
final article. Evidence does not justify that complexity before Option A is
tested.

### C — Local deterministic replacement

Simple string substitution is unsafe. Number, articles, possessives,
hyphenation, compounds, adjective placement, repeated references and comic
callbacks all depend on context. Replacing `milk float` with an arbitrary seed
can break later pronouns and the deliberately escalating joke. Local code is
appropriate for detection, ranking and exact verification, but not for editing
the prose. A tiny hand-authored substitution dictionary would merely create a
new set of favourites and conflicts with the no-permanent-ban objective.

## Recommended minimal experiment

Implement a separate default-off flag, tentatively
`NEWSMUNCHER_TARGETED_COPY_VARIETY=evaluation`, that changes only the existing
copy-edit request:

1. After pass one, calculate a per-pet hot list from the already-loaded Phase
   4M events. Select at most three high-confidence, source-exempt targets that
   occur in pass one. Require repeated recent article exposure and reject
   structural verbs/common grammar.
2. Select at most two current Phase 4P ingredients that do not occur exactly in
   pass one and do not contain a hot target. Prefer role-compatible suggestions;
   do not generate a fresh pool initially.
3. Add one compact instruction permitting replacement of at most two targets.
   Reaffirm that the source sequence, events, joke density, profanity,
   innuendo, bizarre relationships and surreal intensity must remain.
4. If no reliable target or alternative exists, call the unchanged copy-edit
   prompt. Never force a replacement.
5. Retain the current `None` fallback to pass one and make no third call.
6. Audit exact target counts before and after, exact suggestion use, targets
   retained, and configuration. Label semantic/manual judgments separately.

For the first experiment, exact lexical targets should be the primary control.
Add only the already supported high-confidence topic/construction detectors
whose scope and memory ownership are explicit. Do not claim general motif
understanding.

## Provider-free validation plan

Offline tests should cover:

- recency/frequency ordering and decay of hot lexical targets;
- minimum repeated-event threshold, bounded three-item output and non-banning;
- per-pet isolation, persistence, restart, duplicate writes and bounded memory;
- exclusion of current-source terms, grammar words and narrative verbs;
- exact words versus compact identities versus explicitly rule-based motifs;
- no unsupported semantic-family claims;
- selection of unused, target-free, role-compatible Phase 4P suggestions;
- no new selection/database work and no suggestion when none is suitable;
- deterministic prompt assembly and measured character/token overhead;
- byte-for-byte default-off copy-edit prompt equivalence;
- unchanged two-call count and existing pass-one fallback;
- compatibility with Phase 4M–4R independently enabled or disabled;
- exact before/after audit measurements and secret-safe schemas;
- adversarial grammar fixtures covering plurals, possessives, compounds,
  articles and repeated references without performing local substitution.

Mocked model responses can prove request shape, validation and fallback. They
cannot prove that humour, density and narrative structure survive or that the
model avoids mechanical insertion. Those questions require a small separately
approved paired live test using identical pass-one extracts.

## Risks, limitations and unresolved evidence

- The three reviewed articles share one source. Repeated narrative verbs are
  partly an ordering/source effect and should not become replacement targets.
- The lexical ledger does not retain within-article counts or final noun
  phrases, so it cannot yet rank phrase repetition comprehensively.
- Topic detectors are useful but incomplete; broader motifs such as animals in
  occupations need explicit reviewed rules or remain manual observations.
- All nine Phase 4P sparks were unused exactly. Their utility as second-pass
  alternatives is plausible, not demonstrated.
- The existing editor may preserve humour under a two-substitution allowance,
  but offline tests cannot establish that.
- Exact verification will undercount creative paraphrases. Automated semantic
  scoring would introduce the same uncertainty this investigation avoids.
- `gpt-6-sol` billing is not exposed locally, and the provider wrapper retains
  no usage. Option A adds only input tokens; Option B pricing estimates use the
  public GPT-4.1 mini rate and are not evidence of project access or quality.

The recommended next step is review of this design, followed by a provider-free
prototype of Option A only. No implementation should begin until reviewed.
