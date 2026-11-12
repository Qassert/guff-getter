STATUS: REVIEW
OWNER: CODEX
BRANCH: develop
LAST_COMPLETED_FEATURE: BUILD DIRECTIONS INPUT BORDER AND PADDING
LAST_COMPLETED_COMMIT: See latest BUILD directions refinement commit in Git history
LAST_OWNER: CODEX
HANDOVER: README.md

## Status Values

- **READY**: repository is available for a new task
- **ACTIVE**: one named agent currently owns the task
- **BLOCKED**: work is incomplete and must not be overwritten
- **REVIEW**: implementation is complete but awaiting Andy's review/approval

CURRENT_TASK: Match Further Instructions text padding and border to the custom ingredient input; preserve helper edit.
APPROVAL: BUILD-only layered panels, bounded custom ingredients and 100-character directions; retain advanced editing, core prompts and existing work. No paid generation, push/merge/deploy.
NEXT_STEP: Review the small BUILD directions refinement. Prior uncommitted helper offset is preserved.
VALIDATION: Scoped CSS values match the existing ingredient input; BUILD page checks and diff checks pass. No generation changes.


## Early adoption access — 2026-11-09

- Shared server checks protect CREATE, BUILD and GALLERY navigation and late MUNGE requests.
- Reused active_pet, adopted records and existing validated login sessions; Gallery authorization remains intact.
- Existing adoption/login forms carry safe return destinations, including validation failures.
- Per-tab drafts preserve CREATE text/source metadata and BUILD ingredients, recipe, prompts and story.
- Missing adoption is checked before destructive UI changes; storage failure blocks automatic redirection.
- Local develop commit only; unrelated work in the other worktree is untouched.

## BUILD consolidation — 2026-11-09

- Consolidated Maximum Mungery, separate generated headlines with safe edited-story fallback, and all-category SPIN ALL.
- Retained animal OBJECTS, two-word MODIFIERS and hidden SWEAR metadata labels.
- Advanced BUILD frontend cache versions and verified recipe/prompt/story preservation.
- develop did not exist locally or remotely; integration starts from origin/main, preserving main unchanged.
- Other worktree prompt edits and untracked media remain excluded and untouched.
- Detailed review, validation and integration handover: docs/build-consolidation.md.

## Maximum Mungery prompt — 2026-11-08

- Replaced the BUILD creative instructions in the frontend and backend defaults with Maximum Mungery.
- Preserved dynamic non-empty ingredient insertion and the editable complete-prompt workflow.
- Kept 30/60/90 as dynamic ranges; MUNGE 60 produces the requested 54–66 wording without imposing that range on the other buttons.
- The existing endpoint, `gpt-6-sol` model, Responses API request, validation, timeout, response cap and editable story display are unchanged.

## BUILD prompt arrow — 2026-11-07

- Replaced the plain prompt-editor title with a broad downward-pointing `EDIT PROMPT` label aimed at the nested parchment.
- The label uses a muted ochre gradient, heavy NewsMuncher display type, raised dark shadow and embossed text highlights while retaining its accessible textarea association.
- Advanced the BUILD stylesheet cache key so the arrow loads on refresh.

## BUILD nested prompt parchment — 2026-11-07

- The complete editable prompt and RESET PROMPT control now sit on a second torn parchment layer inside the recipe parchment.
- The textarea itself is transparent and borderless so the nested parchment is the visible editing surface.
- The BUILD stylesheet cache key was advanced to ensure the new presentation loads on refresh.

## BUILD cache mismatch repair — 2026-11-07

- Bumped the BUILD JavaScript cache key after removing Theme / Scene so browsers no longer combine the new template with the old theme-loading controller.
- Bumped the BUILD stylesheet cache key at the same time so the recent result spacing and rejected-image parchment styles load consistently.

## BUILD prompt category cleanup — 2026-11-07

- Removed the Theme / Scene selector and its runtime vocabulary request from BUILD while retaining the underlying data and backend field for compatibility.
- Frontend and backend canonical prompt builders now omit unselected categories entirely instead of sending `None selected` statements to the model.
- Existing prompt-edit preservation, RESET PROMPT, ingredient selection and 30/60/90 length handling remain unchanged.

## BUILD rejected-image guidance — 2026-11-07

- A 422 from the initial nominated-image request now replaces the stopped flicker layer with user guidance instead of exposing an empty panel.
- BUILD alone renders that guidance centred on the established parchment texture; CREATE and successful-image presentation remain unchanged.
- REDO IMAGE remains available, successful retry removes the rejection presentation, and a new story resets it.

## BUILD nomination flicker parity — 2026-11-07

- BUILD now invokes nomination through the explicit shared `creationActions.nominate()` API instead of an optional incidental window global.
- The shared action delegates unchanged to CREATE's `bankThisBeauty()` lifecycle, so BUILD uses the same embellishment controller, image shuffle, timing, cleanup and failure handling.
- Missing shared nomination controls now produce a visible retryable error instead of silently stopping after draft preparation.

## CREATE-to-BUILD integration — 2026-11-07

- Merged `feature/video-animation` at `956394c` into the isolated BUILD branch with
  both histories preserved and pre-merge backup refs for each branch tip.
- Retained BUILD's DOM guards for shared CREATE controllers while adding CREATE's
  asynchronous source-load error handling, OpenAlex/NASA/Hacker News adapters,
  attribution metadata, glow theme and full-volume MUNGE soundtrack.
- Automatic merges preserved CREATE | BUILD | GALLERY navigation, BUILD's prompt/story
  editing and persistence boundary, Gallery media fallback, and the shared responsive
  layouts. The imported research report's trailing blank line was removed so diff checks pass.

## Build prompt editor cleanup — 2026-11-06

- Removed the second, read-only assembled prompt block. BUILD now shows only the full
  editable creative instructions and expands that textarea to its measured content height.
- Ingredients and the selected 30/60/90 length contract remain separate and are combined
  with the edited instructions only when the generation request is assembled.
- The editable story and CREATE-compatible action lifecycle are unchanged.

## Build editing and CREATE action reuse — 2026-11-06

- BUILD exposes the established absurdist creative instructions in an editable prompt
  field. The selected 30/60/90 target remains server-controlled and is appended to the
  edited instructions with the matching 33/66/99 hard cap.
- Generated stories use CREATE's editable response textarea. COPY, nomination updates,
  image recovery, deletion, re-embellishment, jingle and video controllers now use the
  latest edited story through CREATE's existing action lifecycle and button order.
- Generating a BUILD story remains persistence-free. The server creates a bounded local
  draft only after an explicit NOMINATE click, then the existing nomination pipeline owns
  any database or media work invoked by that action.
- Chrome was unavailable for native visual inspection. A local GET rendered `/build`
  successfully with all three length controls, both editors and the shared action row.

## Build MUNGE generation — 2026-11-06

- Build now submits its structured committed recipe asynchronously to a dedicated
  `/build/generate` endpoint. The server reconstructs the existing preview prompt,
  validates bounded ingredient lists and text lengths, and calls the established
  OpenAI Responses API using `gpt-6-sol` with the repository's server-side credentials.
- Provider output is capped to 80 whitespace-delimited words before returning. The
  browser keeps all recipe selections, prevents duplicate requests, applies a 35-second
  client timeout and displays safe timeout/failure messages without persistence.
- The former MUNCH prototype control is now a centred primary MUNGE action with a
  separated result panel. Build overrides only its footer block, removing the white
  strip without changing Create or Gallery. The prior responsive heading clearance
  beneath the unchanged udder remains in place.
- Focused validation uses a mocked Responses client and route provider. No provider,
  database, image, audio or Gallery operation ran during tests.

## Build Create-visual reuse — 2026-11-06

- Build now reuses Create's five-teat source udder assets, shared responsive CSS,
  physical canvas animation and sound controller. Build teat markup intentionally omits
  `data-source`, inline retrieval handlers and Create's action script, so interaction is
  cosmetic and auditory only.
- Both workshop panels use the same `profile-container` nine-slice parchment surface as
  Create. The retired Build-only parchment pseudo-element was removed while Build's
  controls, recipe and prompt layout remain intact.
- Build includes Create's exact initial/generated background layers, stored-background
  loader and colour wash. It performs the same read-only `/profile-background` selection
  on page load and retains the existing missing-image fallback and crossfade code.
- Native browser inspection was attempted, but neither Chrome nor the in-app browser was
  available. Rendered HTML, route, controller and responsive behavior remain covered by
  focused offline checks.
- Screenshot follow-up renamed the heading to `BUILD A MUNGE` and reserves a responsive
  70–150px intro offset beneath the udder's visual overhang. Six focused Python tests,
  eight Build frontend tests and `git diff --check` pass.

## Build worktree media repair — 2026-11-06

- Confirmed Create/Gallery code and environment credentials matched the original checkout;
  the regression was caused by checkout-relative generated-media paths pointing at the
  Build worktree's empty media scaffolds.
- Added an ignored per-worktree media-root pointer. Existing generated images, audio,
  narration and video are read through a local-first, read-only fallback; all generation
  writes remain in the Build worktree.
- Create background selection and Gallery media lookup now inspect both roots. Shared
  videos cannot trigger derivative writes in the original checkout.
- Added a guarded setup utility which refuses to configure over nonempty worktree media.
  No original media, databases, environment files or uncommitted source changes were
  modified.

## External source teat replacement — 2026-11-03

- Preserved the historical teat action identifiers and all visual/audio interaction
  geometry while replacing DATING with OpenAlex, POEM with NASA Images, and PEOPLE
  with Hacker News.
- Added shared local HTML cleanup and sentence-order reduction targeting 80 words,
  bounded at roughly 100 words, plus one bounded `Retry-After`-aware HTTP 429 retry.
- Source selection now locks every teat immediately, aborts after 35 seconds, rejects
  stale responses, and always unlocks after success, failure, or timeout. The former
  fixed post-request delay was removed.
- Source title, URL, provider, author, and licence notes are carried into drafts without
  entering the comedy prompt; existing sources retain their previous prompt shape.
- Live read-only checks returned 95 NASA words, 86 Hacker News words, and 100 OpenAlex
  words. Hacker News API access does not establish publication or derivative-use rights,
  so its attribution explicitly records that reuse rights remain unconfirmed.

## Free content API evaluation — 2026-11-02

- Evaluated OpenAlex, arXiv, Hacker News, UK PlanIt, NASA Image and Video
  Library, and the Guardian Open Platform using official documentation and live
  unauthenticated requests.
- Stored bounded representative samples and a failed Guardian HTTP 401 record
  under `research/content-api-evaluation/`; no full papers or Guardian articles
  were downloaded.
- Recommended OpenAlex first, NASA second, and arXiv only behind a compatible
  per-work licence filter. PlanIt is better suited to short British premise
  ingredients, while Hacker News and Guardian present material reuse concerns.

## MUNGE soundtrack/effect level parity — 2026-11-02

- Teat effects use native `Audio` playback at the default `1.0` volume. The soundtrack
  previously compounded a `0.22` voice gain with a `0.82` master gain (about `0.18`).
- Set both soundtrack gains to `1.0`, removing the deliberate attenuation while retaining
  all existing clip crossfades, master fade-out, mute routing and cleanup behavior.

## Parchment and grouped udder visibility — 2026-10-22

- Added a deep outline-following shadow plus three strong golden-orange and amber
  `drop-shadow()` layers to both parchment artwork surfaces, the complete source udder,
  and each complete MUNGE assembly.
- Body and teat image layers no longer carry individual shadows. Each udder is composited
  first and shadowed once at its outer wrapper, preventing internal shadows between the
  body and teats.
- Hover and keyboard focus intensify the glow and visually scale the complete
  idle udder assembly by 7% over 250ms without touching rotor transforms, geometry or
  processing animations. Reduced-motion mode keeps the glow but suppresses scaling.
- Create/Gallery navigation, parchment action controls, Gallery arrows and furry controls,
  master mute, and the Gallery parchment now use the same shared silhouette glow.
- A seven-colour non-orange palette selects once on page load and advances to a different
  random colour after each decorated control activation. Matching filter stacks transition
  over 700ms; reduced-motion mode changes colour without the transition.
- Reduced every shared shadow radius and opacity twice by approximately one third after
  visual review, retaining the same layered treatment and stronger hover/focus state.

## NOMINATE repeated image failure and REDO recovery — 2026-10-21

- The latest durable record proved media-safe-v2 was running, but clause filtering kept
  suggestive compounds and malformed duplicated quoted fragments from the source. OpenAI
  returned `moderation_blocked` with `safety_violations=[sexual]` again.
- Media-safe-v3 preserves clean articles verbatim, but any locally detected unsafe source
  now receives the existing standalone harmless visual scene. No source fragments or
  descriptions of omitted categories enter either the main or endpoint image prompt.
- Restored REDO IMAGE to the shared action row. A definitive main or replacement failure
  exposes the action even after nomination; the request declares nomination replacement,
  rebuilds stale descriptions, and makes exactly one user-triggered provider attempt.
- Definitive failed redo claims are archived and may be explicitly retried. Started or
  uncertain claims remain blocked and confirmation-gated, and successful images remain
  hidden from REDO so RE-EMBELLISH retains ownership of deliberate replacement.

## NOMINATE image HTTP 422 correction — 2026-10-21

- The durable attempt record proved the browser payload passed FastAPI validation and
  OpenAI returned `moderation_blocked` with a sexual classification. The v1 sanitizer
  removed the source clause but reintroduced the labels "adult or graphic material"
  into the provider prompt.
- Media-safe v2 retains the same clause removal and harmless replacement strategy but
  refers only to "anything omitted". The version bump rebuilds persisted v1 descriptions
  on an explicit retry without bypassing the existing paid-attempt safeguard.
- Regression coverage exercises the real FastAPI payload shape with a mocked provider,
  preserves the original nomination text, verifies one provider call, rejects an invalid
  payload, and confirms prior v1 descriptions are rebuilt.

## NOMINATE media reliability — 2026-10-21

- Added a deterministic nomination-only media description that preserves clean visual
  material, removes unsafe clauses, and falls back to a harmless surreal British
  editorial scene without changing saved or displayed comedy.
- Main and endpoint images share the durable description and one retained visual style.
  Each new video claim stores one of five coordinated transformation directions used by
  both the endpoint-image prompt and WaveSpeed transition prompt.
- Exact byte-identical endpoint images are detected by SHA-256, diagnosed, removed, and
  left for the existing explicit retry flow; no automatic paid retry was added.
- Endpoint OpenAI failures now retain bounded structured diagnostics using the same
  request-ID-stripping helper as main images. Existing WaveSpeed records showed that all
  four upload-ticket HTTP 400s were insufficient-credit responses, so request construction
  was left unchanged. The existing polling timeout remains an uncertain non-retry state.
- Validation used mocked providers only: 157 focused Python tests and 153 frontend tests
  pass, compilation and diff checks pass, and MUNGE isolation is explicitly covered.

## MUNGE body shadow strength — 2026-10-20

- Changed the single shared `.profile-page .munge-body` drop shadow from
  `drop-shadow(0 8px 7px #35151c55)` to `drop-shadow(0 16px 14px #35151caa)`.
  The original colour is retained while offset, softness and alpha are doubled.
  Existing overflow remains visible, so the larger filter footprint is not clipped.

## Standalone Create swear-word generator — 2026-10-20

- Mechanically extracted all 756 runtime strings from the authoritative RTF source into
  a UTF-8 CSV: 440 `bijv_nw`, 141 `gilles`, 70 `zelfs_nw`, and 105 `handelend`.
  The six original phrase structures are unchanged. No StatCounter or other analytics
  source was copied.
- Added an independent Create-page panel below the existing workshop. It does not read
  or mutate MUNGE, nomination, Gallery, parchment, audio, database or provider state.
- Generation retains five 100ms flicks and starts the next slot after the third flick.
  Completed slots become native buttons; replacing one retains its category and every
  other slot. Reduced motion resolves immediately, and superseded timer chains settle
  safely.
- Completed phrase keys are retained in bounded session storage. Small spaces are
  checked exactly without materialising their combinations; large spaces use 64 bounded
  random attempts before clearing the 2,000-key history and selecting safely.
- Restyled the visible control as one compact transparent flex row: parchment-style
  `SWEAR` button followed immediately by the wrapping dark-red serif phrase. Removed the
  heading, panel backgrounds, dotted word rules, instruction and visible phrase history;
  sessionStorage duplicate tracking remains unchanged. Loading/replacement state remains
  available to assistive technology without adding another visible element.
- Moved that row into `#outputContainer` between the unchanged response editor and image
  panel, with a 4px top margin. Added a matching `COPY` button beside `SWEAR`; it copies
  `generator.phrase()` as plain text through the Clipboard API or a temporary-textarea
  fallback, shows `COPIED` for 1.2 seconds only after success, and is disabled before a
  complete phrase and throughout whole-phrase or individual-slot animation.

## Experimental controlling-premise trial — 2026-10-19

- Added default-off `NEWSMUNCHER_RADICAL_CONTROLLING_PREMISE=evaluation` for
  Experimental only. It loads the existing 118-entry Codex editorial premise batch.
  The controlling-premise view excludes 30 short entries from
  `everyday_post_modifiers` and `cheeky_post_modifiers`, leaving 88 narrative-capable
  entries across eight families; the source catalogues remain unchanged. It selects
  a family uniformly, then one premise within it using a rewrite-ID-seeded RNG.
  Current and Classic never enter this path. An unexpectedly empty eligible view
  safely produces the unchanged baseline RADICAL prompt rather than failing.
- When enabled, the selected relationship becomes the first pass's primary direction:
  it must be adapted rather than quoted, transform the generic subject/function and
  develop through at least two existing narrative beats. The existing six sparks
  remain unchanged and secondary. With the flag absent/off, no text is appended to
  the checkpointed RADICAL prompt.
- Local audits now record the enabled state, stable premise identifier, mechanism
  family and at most six bounded spark strings under `radical_experiment`. No prompt,
  provider metadata, history, reservation, editor, model or database behavior changed.
- Validation: 40 focused Python tests and all 107 frontend tests pass; compilation and
  `git diff --check` pass. Fifteen source-preprocessing tests pass separately. Broader
  legacy route suites still exhibit their pre-existing module-stub isolation failure
  when `source_preprocessing` is replaced without the RADICAL exports; no product-code
  failure was found. No provider call or Mongo write occurred.
MILESTONE_COMMITS: M1/M2 02b36ed; M3 b5e2baf; M4 cd1e7e0; M5 a0d0ab7; M6 7f947fc.
LIMITATIONS: ELEVENLABS_API_KEY is not configured, so no real jingle was generated. Historical narration and Modal/ACE-Step artifacts remain preserved but inactive.

## Create MUNGE control position — 2026-10-20

- Changed only `.profile-page .munge-generation-controls` from
  `translate(-50%, 50%)` to `translate(-50%, calc(50% + 12px))`.
- This is a visual offset on the existing absolute group. Its anchor, flow, dimensions,
  horizontal position, internal spacing, parchment geometry and text regions are unchanged.

## Source-udder milk-puddle feathering — 2026-10-20

- Feathered only the irregular canvas contour used by the `cream` puddles emitted by
  source teat indices 0 and 2. Fourteen shape-following alpha bands preserve the
  enlarged outer contour and opaque radial-gradient centre; the existing 2x canvas
  effect scale makes the transition approximately 28 rendered pixels at full puddle
  size. The old puddle-edge shadow was removed because it retained a perceptible hard
  contour. The complete puddle footprint, highlight and edge droplets are now twice as
  wide around the same impact point, while every vertical measurement remains unchanged.
- Stream rendering, teat origins, trajectories, puddle centre and height,
  animation/fade timing, and every non-cream teat effect remain unchanged.
- The puddle interior uses an 88% opacity base, matching the feather's innermost band,
  plus seven broad deterministic radial alpha fields clipped inside the unchanged
  boundary. Each field fades completely before its rectangular paint extent, so no
  individual ellipse or hard geometric boundary is rendered. The former long highlight
  ellipse was removed because it produced the visible horizontal cream band.
- The seven small satellite splash marks retain their existing centres and dimensions,
  but now fade organically to transparent instead of ending as solid pale ovals.
- Validation: source-udder and MUNGE-control focused tests pass (10/10); all 127
  frontend tests pass; JavaScript syntax and `git diff --check` pass.

## Source-udder bubble-puddle width — 2026-10-20

- Expanded only the settled `foam` phase used by source teat indices 1 and 4. It reads
  the source parchment's live rendered bounds each frame and distributes 25–72 bubbles
  irregularly across that width, retaining the existing bubble renderer and four-row
  vertical range. Seven overlapping base patches replace the former localised patch.
- Initial emission coordinates, falling trajectories, bubble sizes/colours/alpha,
  build/fade timing, milk effects and all layout geometry remain unchanged.

## Combined source-udder liquid effects — 2026-10-20

- Every one of the five source teats now creates one `liquid` effect record whose shared
  renderer invokes the existing milk puddle, full-width foam, milk stream and milk
  droplets together. The layer order keeps the stream visible above both puddles.
- Each effect retains the clicked teat's existing start/impact calculation and a 5700ms
  lifetime, matching the longest existing foam effect. Individual milk and foam phase
  timings, geometry and fades are unchanged; active-effect cleanup remains unified.

## Engine-specific MUNGE rotor motion — 2026-10-20

- Doubled full-turn duration from 1120ms to 2240ms. Classic now rotates anticlockwise;
  Experimental retains clockwise rotation. Both remain constant-speed linear loops.
- Current enters from upright to -90 degrees in 560ms, then alternates linearly between
  -90 and +90 degrees in 1120ms per half-turn. Its one-time entry controller hands off
  to the alternating animation without a repeated 0-degree boundary or extra listeners.
- Existing rotor origin, group position, 12px visual offset, control dimensions, hover
  interactions, processing lifecycle and cleanup are unchanged.

## Hybrid Gallery nomination ordering — 2026-10-20

- New Mongo nomination documents receive `nominated_at` as a BSON date alongside
  `creationDate`; the idempotent rewrite upsert places it under `$setOnInsert`, and
  edit/media/promotion paths do not update it.
- A fresh Gallery shows the three newest nominations first. Recency uses valid
  `nominated_at`, falls back to valid legacy `creationDate`, puts undated records last,
  and resolves equal dates by descending `_id`.
- From the fourth selection onward, the original minimum
  `promotion_gallery_seen_count` floor and random tie-breaking are active again. Page-local
  visited state avoids repeats until the available cycle is exhausted; persisted counters
  continue to increment only after successful display acknowledgement.
- BACK stores the page just left in an in-memory forward stack. NEXT after BACK restores
  that same page without a new random selection or duplicate view-count acknowledgement.
- Focused hybrid ordering/persistence tests and Gallery frontend tests pass. No MongoDB
  or provider call was made. The combined legacy run still has its pre-existing 960px CSS
  assertion and source-preprocessing module-stub isolation failures.

## Site-wide master mute — 2026-10-19

- Added a shared controller loaded by the base template, with a fixed native button and
  the persistent `newsmuncher.masterMuted` localStorage preference. The default remains
  unmuted. The accessible label, pressed state and temporary speaker icon update together.
- The controller intercepts `HTMLMediaElement.play()` once, so existing and dynamically
  created Audio/video players inherit mute before playback. It remembers and restores
  each player's prior individual muted state rather than changing its volume.
- MUNGE Web Audio now routes its unchanged `.82` creative master through a separate
  registered mute gain. This leaves clip crossfades and the 1.5-second completion fade
  intact while allowing immediate site-wide silence and clean gain deregistration.
- Explicit Create and Gallery Play Jingle actions synchronously clear and persist master
  mute before playback. Automatic MUNGE, media, narration and effect paths never unmute.
- Validation: 76 focused audio/media tests and all 126 frontend tests pass; JavaScript
  syntax checks and `git diff --check` pass.

## MUNGE loading-jingle crossfade — 2026-10-19

- Consecutive decoded excerpts now start 500ms before the outgoing excerpt ends.
  Very short excerpts cap the overlap at half their actual duration.
- Per-voice Web Audio gain nodes linearly fade the outgoing voice from the existing
  `.22` level to zero while the incoming voice rises from zero to `.22`. The existing
  `.82` master level, five-jingle choice, shuffled order, progressive loading, final
  1.5-second soundtrack fade and immediate restart cleanup are unchanged.
- Transition scheduling now uses each excerpt's decoded duration rather than rounding
  its end to a beat interval. Failed buffers remain skipped and the first available
  decoded buffer can still begin without waiting for all five.
- Validation: 11 soundtrack tests, 17 focused soundtrack/engine tests and all 120
  frontend tests pass; JavaScript syntax and `git diff --check` pass.

## Create and Gallery parchment enlargement — 2026-10-19

- Increased both effective desktop parchment shells from 960px to 1200px, while
  retaining viewport gutters and the existing 24px mobile gutter.
- Added a 388px desktop minimum height (from Gallery's previous 310px baseline),
  proportionally enlarged Gallery's image-layout height/gap/arrow position, and let
  the three Create MUNGE controls use the wider panel without changing hitboxes.
- The parchment nine-slice artwork, full-screen backgrounds, templates and application
  behavior are unchanged. Focused Create/Gallery tests and all 109 frontend tests pass;
  `git diff --check` passes. Live rendering was not started because application startup
  attempts to resolve the configured MongoDB host; no database connection was made.

## Create forward/reverse nominated-video playback — 2026-10-19

- Create now consumes the same local FFmpeg ping-pong derivative already used by
  Gallery. Its authenticated status/media route prefers the derivative, serves the
  original immediately while a missing derivative is prepared, and exposes a bounded
  readiness state without invoking a paid media provider.
- Create continues read-only status polling at two-second intervals only while that
  derivative is pending. A versioned URL change runs through the existing video
  replacement lifecycle, which pauses, unloads and removes the old player before the
  muted native loop starts automatically. Page exit, rewrite replacement, media errors
  and reduced-motion cleanup retain their existing behavior.
- Validation: 23 video-service Python tests, 16 focused Create video tests and all 110
  frontend tests pass. Python compilation and `git diff --check` pass. No provider call
  or database write occurred.

## Dynamic Create and Gallery article sizing — 2026-10-19

- Added one shared `ArticleTextFitter` with an 8px (6pt) floor, generous 60px ceiling,
  1.35 line height and bounded binary search over measured `scrollHeight` /
  `scrollWidth` versus a separate allocated content region. Content is never altered.
- Create's editable response and Gallery's article column now expose the full responsive
  region to the fitter, with 26px top/bottom breathing room (22px on narrow Gallery
  layouts). The fitted block is vertically centred. Unfittable text remains contained
  and vertically scrollable at the minimum rather than clipping or overlapping controls.
- Fitting is coalesced through `requestAnimationFrame` after edits, entry changes,
  image layout changes, ResizeObserver notifications, viewport resizing and font load.
  Page exit disconnects observers and listeners.
- The correction removes the previous 26px cap and no longer measures against the
  text node's collapsing natural box, which had left short Gallery articles small and
  pinned to the top. Eight focused fitter tests and all 118 frontend tests pass;
  JavaScript syntax checks and `git diff --check` pass.

## RADICAL noun-replacement prompt correction — 2026-10-18

- Replaced the recovered prompt's conflicting requirements to preserve principal
  generic subjects and maintain sentence-by-sentence correspondence. The source
  is now explicitly the event/relationship skeleton rather than the vocabulary
  or generic subject matter of the finished article.
- The first pass must replace most significant unprotected nouns, generic subjects,
  objects, occupations, institutions and descriptions, including transforming the
  central generic subject. Protected placeholders remain exact and restorable.
- Local prompt assembly confirmed ordinary noun phrases remain visible, factual
  aliases remain masked, the new requirements are sent to the provider, and the
  obsolete preservation clauses are absent. The shared system instruction adds
  only strict JSON/absurd-transformation framing and does not conflict.
- No preprocessing, editor, model, sparks, catalogue, memory, route, CURRENT or
  CLASSIC behavior changed. Prompt backup:
  `/private/tmp/newsmuncher-radical-prompt-before-20261018T221927Z`.

## RADICAL factual-anchor preprocessing trial — 2026-10-18

- The verified pre-blacklist prompt, editor instructions, 50% target, six sparks,
  model path and premise memory are unchanged. Only Experimental preprocessing
  now differs from that baseline.
- Experimental masks named people, places and organisations plus dates, times,
  quantities, money, percentages, cardinals and ordinals. Repeated identities and
  unambiguous surname references share stable placeholders across source fields.
- Ordinary nouns, generic subjects and objects, adjectives, adverbs, descriptions
  and verbs remain visible to the writer and therefore can be transformed. The
  existing restoration and unresolved-placeholder guard now also cover FACT IDs.
- CURRENT still calls the original `preprocess_source()`; CLASSIC remains on its
  separate CSV path. No prompt, editor, catalogue or memory file was changed.
- Pre-experiment backup:
  `/private/tmp/newsmuncher-radical-preprocessing-experiment-20261018T220204Z`.

## RADICAL pre-blacklist restoration — 2026-10-18

- Restored the dedicated RADICAL prompt, service and focused tests exactly from
  the hash-verified 2026-10-18 16:47 snapshot. The shared route now again uses
  the ordinary 50% comedy-editor target and no longer invokes blacklist metrics.
- RADICAL once again uses the shared `preprocess_source()` placeholder pathway.
  The later anchor-only/FACT masking function and FACT placeholder recognition
  were removed, restoring the original placeholder creation and restoration.
- Restored the earlier short RADICAL editor suffix. Removed the fixed negative
  prompt and all associated diagnostics so they cannot affect or fail the route.
- The pre-restoration files are backed up at
  `/private/tmp/newsmuncher-radical-pre-restore-20261018T214845Z`.
- The following two historical sections describe superseded experiments and are
  retained as history only; their behaviours are no longer active.

## RADICAL transformation-strength correction — 2026-10-18

- Experimental now uses a separate anchor-only source preprocessor. It masks and
  safely restores named people, organisations, places, dates and quantities while
  leaving ordinary nouns, adjectives, adverbs and descriptions visible for comic
  transformation. CURRENT still uses its existing full replacement preprocessing.
- The RADICAL prompt now requires one silent controlling premise that develops
  across multiple factual beats. Fidelity is defined at event level rather than
  sentence level, while genuine identities, chronology, milestones and outcomes
  remain protected.
- The Experimental editor targets 72% of the first pass, normally 62–82%, and is
  explicitly told to preserve the premise, transformed vocabulary, escalation and
  payoff. CURRENT retains its existing 50% target and editor instructions.
- The fixed negative trial additionally covers trousers, trouser pockets and close
  possessive/hyphenated compounds. Its list remains static and Experimental-only.
- Focused validation: 106 tests passed. Live comedy quality remains to be assessed
  through separately authorised MUNGEs; no provider request was made here.

## Experimental fixed negative-prompt trial — 2026-10-18

- Added one clearly delimited, fixed RADICAL V1 negative-prompt section covering
  the requested ingredients, common variants and eight overused construction
  families. Genuine source facts are explicitly exempt; the list does not learn
  or grow between rewrites.
- Experimental final output is inspected locally after editing and placeholder
  restoration. Numeric diagnostics distinguish exact copied source clauses,
  uncertain source overlap and material absent from the source. Construction
  recognition is deliberately labelled heuristic because local matching cannot
  prove every paraphrase or factual exception.
- Diagnostics use the existing completion timing record and, when enabled, the
  existing local comedy audit JSONL. They do not add a model call, database state
  or enforcement pass. Classic and Current do not invoke the experiment.
- Focused validation: 55 tests passed. No catalogue, selector, cooldown,
  reservation, exclusion or persistent-memory behaviour changed.

## Codex catalogue expansion and exclusion release — 2026-10-18

- Authored 360 vocabulary proposals and 132 premise components directly in the
  conversation, with no external model requests. Accepted 299 vocabulary entries
  across 18 domains and 118 premises across 11 editorial mechanism families;
  rejected 61 and 14 respectively. Per-entry decisions, edits, fiction labels
  and provenance are in `docs/candidates/codex-catalogue-expansion-2026-10-18.json`.
  These are Codex editorial decisions, not human-review claims.
- Added approved entries to the existing vocabulary catalogue and premise
  banks. Existing template patterns/weights and Radical inspiration banks are
  unchanged. Reviewed food now reaches the existing cheeky-object bank. All 299
  nouns pass reviewed eligibility; all 118 premises pass real template generation
  and rejection checks with two-word bases. Phrase counts are not independent
  noun-anchor capacity: compounds continue sharing the existing hard identities.
- Reduced active hard history to the newest 1,500 distinct entries. Retain up to
  5,000 history entries in the same field for inspection/rollback. Atomic checks
  and diagnostics use the active tail even on old documents; reusing a released
  historical entry puts it at the FIFO end, while active repeats do not refresh
  their position. No live data was read or modified for this implementation.
- Atomic reservation, in-memory exclusions and diagnostics now ignore leases
  expiring at or before the operation time. Missing/invalid lease dates remain
  blocking. Boundary, true-conflict, concurrent acquisition, failure-release and
  history-preservation tests pass. Three sequential offline CURRENT selections
  retain 14 nouns/6 animals internally, 14/4 in the prompt, and leave no leases.
- Classic, Current prompts, Radical writing/editor logic and UI are untouched.
  Comedy quality has not been evaluated through paid/live generation.

## Create-page teat sounds and spacing — 2026-10-17

- Selecting any MUNGE engine now assigns its six teats six distinct effects from
  the shared 38-sound pool. The mapping remains fixed throughout that MUNGE and
  refreshes when an engine is selected again.
- Three layout-only reservations were reduced by 30px: source-udder clearance,
  the source parchment's transparent lower border and the response parchment's
  transparent upper border. Udder artwork and hitbox geometry are unchanged.

## MUNGE EXPERIMENTAL RADICAL MODE — 2026-10-17

- Experimental now bypasses the ranked concept, descriptor and invented-name
  selectors. Its concise source-led prompt asks the existing writer to invent
  premises and relationships, with six seeded vocabulary sparks as optional
  inspiration rather than mandatory constructions.
- A per-pet, 12-article soft premise memory stores relationship-plus-target
  identities only after successful draft persistence. It shares the existing
  noun-history Mongo collection without changing Current's records, has bounded
  five-item guidance, and treats the same mechanism with a different target as
  a fresh joke.
- The existing first-pass and editor calls are reused. Radical-specific editor
  guidance preserves novel ideas while Current calls retain their exact prior
  arguments and prompts. Classic remains on its stateless CSV route.
- Structural source aliases are now restored deterministically before editing,
  with repeated aliases resolved to one canonical source reference. A second
  check after editing and an authoritative pre-save guard reject any unknown or
  newly introduced structural placeholder instead of completing the draft.
- The Radical prompt now requires every surreal idea to perform the narrative
  work of an existing source sentence, rather than appending detached oddities.
- Focused validation: 148 tests pass. No provider call or database write occurred.

## Phase 4X noun-identity correction — 2026-10-13

- Noun anchors now come from explicit concept base/topic slots, reviewed noun
  catalogues, thematic entities and legacy noun-bank heads. Template modifiers,
  actions and grammar no longer become hard noun exclusions.
- New entries use `noun_identity:`. Ambiguous historical `noun:` entries remain
  active only when an accepted phrase supports them at a compound boundary;
  phrase and premise history is retained unchanged.
- On the current 694-entry ledger, the same 1,500-candidate production pool rose
  from 113 eligible candidates under the immediately preceding classifier to
  351. Ten sequential selections completed while exclusions accumulated from
  694 to 826 entries. Gravy compounds and the ceremonial-dignity premise stayed
  blocked.

## Phase 4X persistent live 409 diagnosis — 2026-10-13

- Failed requests are absent from the success-only audit, and the route formerly
  collapsed four typed selection failures into `selection_exhausted`; the exact
  selector for the latest request therefore cannot be proved retrospectively.
- The last success shows concept selection closest to exhaustion: 1,455 hard
  candidate rejections from 1,500 generated candidates and category slack 2.
  Descriptor selection completed without relaxation. Current noun, concept,
  descriptor and name collections contain no active reservations.
- Added evaluation-only structured failure output identifying the exception,
  selector metrics, per-batch eligibility, hard rejection kinds, cooldown
  losses, category counts, required quotas and reservation count. It contains
  no prompt or source content and does not alter selection.
- Current extraction still labels many modifiers and verbs as nouns. At 694
  ledger entries the finite preconstructed concept space is already nearly
  depleted, so this architecture cannot realistically reach 5,000 hard entries.
- The local audit contains one completed Winifred article. A separate record
  merely offered a different Winifred name that was not used; no final article
  hash is duplicated.

## Phase 4X recurring candidate exhaustion correction — 2026-10-13

- Reproduced the live 409 from temporary copies of the 391-entry noun ledger
  and 4,591 concept records. The first batch looked quota-complete before the
  availability read, but exact phrase cooldown then left the two-slot animal
  cheeky-object category with one candidate. Later sequential failures also
  exposed template grammar such as `powered`, `with` and `insisting` being
  persisted as nouns.
- Phase 4X now builds all five bounded deterministic candidate batches before
  availability filtering, excludes template grammar from noun anchors, and
  progressively relaxes only category allocation after a demonstrated
  exclusion shortage. Total 10+10 counts, phrase cooldowns, leases, unique
  bases/premises and every genuine noun/phrase/premise exclusion stay hard.
- A ten-selection production-path replay used temporary copies only, simulated
  seven exact concept uses per completed article, grew the ledger from 391 to
  812 entries, committed and cleared every reservation, and selected zero
  blocked ingredients. Category slack was 0 for runs 1–7, then 1, 1 and 2.
- Focused validation: 39 tests pass; full suites intentionally not run.

## Phase 4X candidate exhaustion correction — 2026-10-13

- The 5,000-entry FIFO was only 328 entries and had no live reservations. The
  first 30-item category batch was the bottleneck: hard filtering sometimes
  left only one or two of the three required noun/bureaucratic candidates.
- Concept selection now adds up to four deterministic refill batches only when
  the filtered candidates cannot meet existing quotas, stopping as soon as the
  slate is feasible. Noun exclusions, premise exclusions and quotas remain hard.
- The first post-fix ceremonial-dignity reuse was permitted because its older
  occurrence predated premise recording. That successful article added the
  premise key; neither of the following two articles offered it.
- Focused tests: 37 passed. A current-ledger replay selected 20 concepts in two
  batches with no excluded phrase admitted.

## Phase 4X targeted exclusion correction — 2026-10-13

- Filters and reserves complete rendered phrases as well as their bases and
  subjects; all four audited gravy constructions now expose `noun:gravy`.
- Hyphens are component boundaries for filtering and final-output auditing.
- Offered construction matching ignores inserted `a`, `an` and `the`, and
  accepted premise keys enter the same bounded FIFO so cross-base repeats are
  excluded even when ordinary premise cooldowns relax.
- Audit output separates selected/offered exclusion violations from independent
  model introductions. Focused validation passes: 79 tests.

## Universal Comedy Vocabulary Phase 4X — 2026-10-13

- Added default-off `NEWSMUNCHER_NOUN_EXCLUSION=evaluation` with a persistent,
  per-pet 5,000-entry FIFO and atomic short-lived generation reservations.
- Filters singular/plural and compound anchors from generated, legacy, raw and
  thematic ingredient candidates, refilling from existing bounded pools. A real
  shortage returns a controlled 409 rather than bypassing exclusions.
- Commits exact provenance-backed final uses only after successful persistence;
  failed generations release reservations. Source words, names, locations and
  generic compound heads remain protected.
- Optional local audit records separately report prevented candidates,
  independently model-introduced violations and newly extracted entries. No
  provider call was added and final-output enforcement is not claimed.
- Focused tests and compilation pass; full suites were intentionally not run.

## Universal Comedy Vocabulary Phase 4W — 2026-10-13

- Added an isolated provider-free diagnostic for exact provenance-backed comic
  noun and phrase extraction, per-pet FIFO exclusion, candidate refill and
  concurrent temporary reservations.
- A 28-article local sample produced 559 entries, about 20 per article, implying
  roughly 250 articles before a 5,000-entry FIFO releases its oldest entries.
- Exact local scanning detects an already-excluded noun reintroduced by the
  model, but conservative extraction will miss some wholly new model inventions.
- Focused validation passes: 8 tests. Full suites were intentionally not run.
- Findings and the smallest recommended persistent design are in
  `docs/comedy-vocabulary-phase4w-report.md`. Production behavior is unchanged.

## Universal Comedy Vocabulary Phase 4V — 2026-10-13

- Traced the complete source, selection, quota, ranking, prompt, first-pass,
  copy-edit, persistence and memory pipeline without changing runtime behavior.
- Confirmed the main remaining constraint is architectural: Phase 4P supplies
  only three of thirty prompt ingredients, leaving about 90% governed by the
  existing fixed quotas and preconstructed mechanisms.
- Reconciled the Phase 4U `butter paddle` exposure of 98. It is a decaying,
  stage-weighted key score rather than an appearance count; alternative scores
  add component and identity penalties while target scores take their maximum,
  so the displayed values are not directly comparable. Role compatibility is
  ranked before freshness and no maximum alternative score is enforced.
- Consolidated evidence that exact phrase/base/premise controls work, Phase 4M
  lowers short-window word repetition, and recurring food, machinery,
  bureaucracy, official-animal and aristocratic motifs persist through fixed
  quotas, overlapping resource routes and independent model invention.
- Compared strengthening, simplifying and replacing the selection strategy.
  Recommended one bounded premise-to-spark experiment with explicit objective
  thresholds and a stopping rule; no recommendation was implemented.
- Full evidence, architecture diagram, quantitative tables, ranked bottlenecks,
  trade-offs and experiment design are in
  `docs/comedy-vocabulary-phase4v-investigation.md`.
- No paid call, production write, runtime change, commit or push occurred.

## Universal Comedy Vocabulary Phase 4U — 2026-10-13

- Added separate default-off `NEWSMUNCHER_PHRASE_REPLACEMENT=evaluation`.
  Phase 4T must also be enabled; with Phase 4U off, Phase 4T behavior is
  unchanged.
- Phase 4U treats provenance-backed concept bases, descriptor subjects and raw
  identities as atomic phrases. Component exposure can qualify the complete
  identity, while nested words are suppressed and logged as overlap exclusions.
- Offers short current Phase 4P bases/subjects instead of requiring the editor
  to insert complete cross-domain constructions. Exact role/bank compatibility
  and lower recent exposure rank first; full construction and domain provenance
  remain available in the audit.
- If current Phase 4P material exists but no insertable compatible alternative
  remains, the existing editor receives one explicit auditable fallback to
  invent an equally absurd local replacement using current domain cues.
- Strengthened the two-substitution instruction while preserving surrounding
  sentences, source sequence, events, relationships, British absurdity,
  profanity, innuendo, density and timing. No name or protected source detail
  may change, and no provider call was added.
- Provider-free replay changed the three manual target sets from nine component
  opportunities to six non-overlapping identities: `rescue wheelbarrow`,
  `sandwich press`, `jelly mould`, `licensing authority`, `trouser press` and
  `gravy boat`. It removed every observed nested component target and offered a
  zero-exposure first alternative for each article.
- Full design, replay table, audit fields, startup command and limitations are
  in `docs/comedy-vocabulary-phase4u-report.md`.
- Focused validation passes: 50 tests. Full Python passes with 523 tests and
  105 subtests; JavaScript passes with 84 tests. Python compilation, production
  JavaScript syntax and `git diff --check` pass. No paid call, production write,
  commit or push occurred.

## Universal Comedy Vocabulary Phase 4T — 2026-10-13

- Added default-off `NEWSMUNCHER_REPETITION_REPLACEMENT=evaluation`. It reuses
  the existing second-pass `gpt-6-sol` call and never adds a third provider call.
- Selects at most three exact first-pass targets from confirmed ingredient
  bases/subjects using bounded per-pet Phase 4M exposure. Source words, known
  names/places, narrative/reporting verbs, absent terms and weak exposure are
  rejected. Multiword targets require their own identity evidence.
- Offers at most two unused current Phase 4P ingredients, with broad role
  compatibility and lower exposure preferred. Without reliable targets and
  alternatives, the existing copy-edit call remains unchanged.
- The appended instruction permits at most two optional substitutions and
  explicitly preserves sequence, events, relationships, density, profanity,
  innuendo, surreal intensity, humour and timing. Existing model, timeout,
  schema, token cap and pass-one fallback remain unchanged.
- Phase 4T can read/update the Phase 4M ledger without activating Phase 4M's
  ingredient ranking or first-pass guidance. Phase 4P is the practical source
  of controlled alternatives; Phase 4N and 4R remain compatible.
- Extended optional local audit output with eligible/rejected evidence,
  exposure signals, exact before/after counts, exact additions/removals, new
  already-exposed terms and fallback state. It makes no semantic-success claim.
- Implementation, exact startup command, manual review method and limitations
  are in `docs/comedy-vocabulary-phase4t-report.md`.
- Focused validation passes: 44 tests. Full Python passes with 517 tests and
  105 subtests; JavaScript passes with 84 tests. Python compilation, production
  JavaScript syntax and `git diff --check` pass. No paid call, production write,
  commit or push occurred.

## Universal Comedy Vocabulary Phase 4S — 2026-10-13

- Confirmed the `gpt-6-sol` copy editor receives only the first-pass extract. It
  receives no source, ingredient slate, lexical history or thematic alternatives
  and is explicitly limited to grammar, structure, agreement, flow and
  readability while preserving every strange detail.
- Phase 4M supplies bounded, persistent, per-pet exact-word evidence, but its
  current top-word guidance is unsafe as a replacement list: the reviewed
  records were led by narrative terms such as `working`, `raced`, `entered`,
  `arranged` and `candidacy`. Final-text noun phrases and within-article counts
  are not currently retained.
- High-confidence topic regexes can identify a small fixed set of subjects and
  constructions. Broader semantic motifs cannot be inferred reliably from the
  existing ledger, and the current topic/final-joke stores do not share Phase
  4M's per-pet scope.
- In the three recent same-source articles, the prominent gravy-name,
  marmalade, crumpet, milk-float, teapot, bureaucratic, occupation and powered
  motifs overwhelmingly had confirmed slate origins. They were already in pass
  one. The copy editor mostly repaired grammar, removed two redundant
  `hand-cranked-powered` forms and otherwise preserved or headlined them.
- All nine Phase 4P sparks were unused exactly. The smallest alternative pool
  is therefore at most two unused current-slate sparks, with no new selection
  path. Their usefulness for replacement still requires live evidence.
- Recommended for review: a default-off Option A prototype that gives the
  existing copy-edit call at most three source-exempt, repeated, pass-one-present
  noun/identity targets and at most two unused compatible Phase 4P suggestions,
  permits no more than two substitutions and explicitly preserves narrative
  sequence, joke density, profanity, innuendo and surreal intensity.
- Rejected local string replacement as grammatically and comedically unsafe.
  A third inexpensive model pass is technically possible but adds latency,
  drift and failure surface without evidence that the existing call is
  insufficient.
- Full provenance, architecture, option analysis, risks and provider-free test
  plan are in `docs/comedy-vocabulary-phase4s-investigation.md`. No runtime
  implementation, paid call, production write, commit or push occurred.

## Universal Comedy Vocabulary Phase 4R — 2026-10-13

- Added independent, default-off `NEWSMUNCHER_THEME_SPARKS=evaluation`. With
  Phase 4P enabled, it moves the same two thematic concepts and one thematic
  descriptor from anonymous ingredient banks into one compact optional block
  immediately before the source. It does not select, add, remove or rerank any
  ingredient and has no effect when Phase 4P is off.
- Preserved descriptor role tags, the 20/10 totals, core comedy instructions,
  source handling, Phase 4M/4N compatibility, memory behavior and the existing
  two-call rewrite/copy-edit path. Each spark occurs once in the prompt.
- Extended optional local audit records with spark state, prompt placement and
  separate conservative exact-match evidence for first pass and final text.
- Across 500 provider-free equivalent-slate pairs, all 500 combined ingredient
  sets were identical and every enabled prompt contained three sparks. The net
  presentation overhead averaged 138 characters, about 34.5 estimated input
  tokens. Offline checks cannot establish uptake or humour.
- Corrected Phase 4P documentation: code provides nine possible construction
  IDs (three concept plus six descriptor-role patterns); the earlier seven was
  the number of additional identities observed in that sample.
- Proposed the smallest useful live check: three fixed neutral sources, one
  paired off/on output each, six finished articles and twelve existing two-pass
  calls. Recent actual workload implies roughly 23,000–28,000 input and
  2,500–5,000 output tokens; exact billing is unavailable, so the suggested
  separate approval cap is USD $0.50.
- Full implementation, configuration, audit fields, validation, experiment
  design and limitations are in `docs/comedy-vocabulary-phase4r-report.md`.
  No paid call, production write, commit or push occurred.

## Universal Comedy Vocabulary Phase 4Q — 2026-10-13

- Matched Hattie Hobbleham, Nora Squeezemouth and Doctor Philomena Fustianholme to exact rewrite UUIDs using their unique Phase 4M lexical signatures, Phase 4N/4P memory events and local preview records. Phase 4I JSONL logging was not enabled for these runs; A/B previews are deliberate tombstones and C retains complete source/final text.
- Reconstructed the nine exact prompt-visible Phase 4P ingredients from persisted seeds/constructions, recorded offered vocabulary and checked-in generic formulas. All nine reached the prompt: two of twenty concepts and one of ten descriptors in each article.
- Only three of nine Phase 4P ingredients were recognisable in first-pass output, one per article. The same three survived the copy edit. Six losses therefore occurred before first-pass output, and there is no evidence of copy-edit removal.
- Confirmed low representation and anonymous prompt dilution as the strongest structural explanations. Model preference is supported but cannot be separated cleanly from dilution. Existing quality ranking did not suppress the selected winners because Phase 4P replaces slate positions after ordinary ranking.
- Found five Phase 4P construction IDs across the three articles. `process_adapted_base` appeared three times and supplied two recognisable finals; the sample is too small to call it a new cliché. Also identified a documentation discrepancy: code defines nine possible generic IDs, while Phase 4P prose described seven observed patterns.
- Recommended a single-variable next experiment: keep the same three Phase 4P items and all selection behaviour, but present them once in a compact adjacent optional theme-spark block instead of anonymous bank positions. Measure first/final uptake with Phase 4I enabled before changing counts or constructions.
- Full per-article provenance, stage table, evidence ranking, limitations and recommendation are in `docs/comedy-vocabulary-phase4q-investigation.md`. No runtime code, prompt, production default, provider call, database write, commit or push occurred.

## Universal Comedy Vocabulary Phase 4P — 2026-10-12

- Added a versioned 1,600-seed companion catalogue covering entities, processes, properties and relationships across all 100 Phase 4N domains, with grammar, provenance, licence, review and safety metadata plus a reproducible builder.
- Added independent, default-off `NEWSMUNCHER_THEME_INGREDIENTS=evaluation`. It replaces at most one noun concept, one animal-bank concept and one role-preserving descriptor using nine possible generic construction IDs: three concept patterns and six role-preserving descriptor patterns. The 20/10 counts, existing objects and creatures, registries and provider-call count remain unchanged.
- Phase 4P reuses Phase 4N's selected domains when both are enabled. Alone, it uses the same selector under an isolated per-pet scope. Phase 4M lexical penalties can influence seed choice; all three feature flags remain independently configurable.
- Added bounded per-pet seed/construction memory with decaying weighted penalties and a 12% exploration floor. It persists across restart, isolates pets, handles duplicate/concurrent writes and updates only after successful persistence. Failures remain advisory.
- Expanded the Phase 4I local audit with selected seed/domain/construction provenance, active penalties and candidate-stage metrics. No audit data is exposed to website users.
- Across 500 equivalent-seed generations per configuration, Phase 4P raised unique ingredient phrases from 10,420 to 11,110 and meaningful vocabulary from 2,323 to 3,480, covered all 100 domains, and lowered rolling-five/ten phrase reuse from 0.300/0.624 to 0.238/0.498. Familiar-word share fell from 1.908% to 1.741%.
- Rolling-five construction overlap rose from 15.540 to 16.250. The first experiment observed seven additional construction identities from nine available generic IDs; offline metrics cannot establish finished-article humour or uptake.
- Full architecture, configuration, measurements, examples and limitations are in `docs/comedy-vocabulary-phase4p-report.md`; machine-readable measurements are in `docs/comedy-vocabulary-phase4p-results.json`. No live provider experiment, production write, commit or push occurred.
- Full validation: Python 502 passed, 0 failed, 105 subtests; Node 84 passed, 0 failed; focused Phase 4P/audit tests 19 passed; compilation and `git diff --check` pass.

## Universal Comedy Vocabulary Phase 4O — 2026-10-12

- Confirmed Phase 4N domains currently affect only optional first-pass guidance. They do not influence concepts, descriptors, names, raw ingredients, component sampling, quality scores, quotas or ranking. Existing local Phase 4I/4K/4M audits contain no Phase 4N records, so real theme uptake has not yet been measured.
- Traced the complete source, ingredient, ranking, prompt, first-pass, copy-edit and persistence path. Large base banks are narrowed by hard category/role quotas, compactness bonuses, explicit proven-mechanism bonuses and small curated modifier banks. Literal familiar anchors also occur independently in concept, descriptor and name resources.
- In 100 provider-free slates, the leading concept templates were strong compact creatures (344/2,000), self-acting devices (209), cheeky modifier objects (201), powered devices (169), official documents (153) and official bodies (147). Production-shaped descriptor assembly was broader, but still ranged from 93 class/etiquette selections to one mistaken-relationship selection across 1,000 outputs.
- Compared tagged catalogues, domain-specific seeds, hybrid selection and prompt-only guidance. Recommended a default-off hybrid: typed domain entities/processes/properties/relationships combined by generic cross-domain recipes with a small bounded share of the existing slate. Current ingredients remain reachable and no theme becomes a mandatory final-text quota.
- Designed a four-way, equivalent-seed, 500-generation provider-free evaluation with candidate-stage loss accounting, domain influence before/after ranking, construction concentration, cross-domain coverage, hard-quota parity, Phase 4M compatibility and prompt/runtime costs. Proposed a later 12-article blind check only after separate spend approval.
- Full evidence, code locations, safeguards, trade-offs and implementation sequence are in `docs/comedy-vocabulary-phase4o-investigation.md`. No generator, selector, prompt, production default or runtime behaviour changed.

## Universal Comedy Vocabulary Phase 4N — 2026-10-12

- Confirmed that the core prompt contains no fixed examples of the recurring food, household or institutional vocabulary. The large CSV/catalogue pools are narrowed by generated-concept category quotas, descriptor category/role quotas, quality ranking and small joke-bearing modifier banks; the first-pass model also independently supplies familiar British-surreal material.
- Added a curated catalogue of exactly 100 domains across 11 natural, scientific, historical, cultural, built, medical, technological, artistic, craft and field-practice families.
- Added independent, default-off `NEWSMUNCHER_THEMATIC_DIVERSITY=evaluation`. It selects four optional domains by recency- and family-aware weighted sampling, retains a 12% exploration floor and appends concise creative springboards to the existing first-pass guidance without changing the core prompt or provider-call count.
- The anonymized per-pet memory persists in a separate bounded Mongo-shaped record, appends only after successful draft persistence, handles concurrent first writes, rejects duplicate rewrite UUIDs and cannot block a successful rewrite if unavailable.
- Phase 4I audit records can now distinguish domains offered to the model, selection penalties and conservative source-exempt keyword evidence in final text. Phase 4M remains independently configurable and compatible.
- In 500 provider-free generations, all 100 domains appeared. The largest domain share was 1.65%, largest family share 9.95%, and a four-domain slate averaged 3.504 families. Rolling-five domain overlap fell from 0.782 under equivalent uniform sampling to 0.710; rolling-ten fell from 1.398 to 1.296. Memory stayed bounded at 20 events.
- Findings and limitations are in `docs/comedy-vocabulary-phase4n-investigation.md`; implementation, configuration and measurements are in `docs/comedy-vocabulary-phase4n-results.md`. No paid experiment, production write, commit or push occurred.
- Full validation: Python 493 passed, 0 failed, 105 subtests; Node 84 passed, 0 failed; Python compilation, production JavaScript syntax and `git diff --check` pass.

## Universal Comedy Vocabulary Phase 4M — 2026-10-12

- Completed the approved six-source × three-repetition × off/on live experiment: 36 finished articles and 72 existing two-pass `gpt-6-sol` calls. All outputs succeeded without retries or substitutions; group memories remained isolated and accumulated sequentially.
- Blind articles, the separate answer key, complete JSONL and machine-readable measurements are under ignored `local_audits/phase4m_live_experiment/20261012T_phase4m_live_ab_network/`. The main report does not map individual versions to configurations.
- Final unique meaningful words per 1,000 rose 641.86→654.45; rolling-five repeated words fell 16.28→13.50, rolling-ten 28.78→25.11 and top-15 share 6.34%→5.41%. Offered-word breadth improved more strongly, confirming partial rather than complete transmission into final copy.
- Gravy and custard article counts were unchanged; marmalade fell while cucumber slicer, crumpet and milk float rose. Copy editing introduced none of these terms. Model-side first-pass invention remained material, so Phase 4M is suitable for broader opt-in review but not default promotion from this sample.
- Full design, provenance, aggregate results and limitations are in `docs/comedy-vocabulary-phase4m-live-results.md`.
- Full post-run validation: Python 484 passed, 0 failed, 105 subtests; Node 84 passed, 0 failed; Python compilation, JavaScript syntax and `git diff --check` pass.

- Added default-off `NEWSMUNCHER_LEXICAL_DIVERSITY=evaluation`. A bounded Mongo event stream is isolated by an anonymized active-pet scope, shared across workers, persistent across restart and appended atomically only after successful draft persistence.
- Meaningful words and compact identities from offers, first-pass text and final text receive frequency/recency exposure weights. Source-required vocabulary is exempt. Final use weighs more than an unused offer; events decay out after ten articles by default.
- Concept components, descriptor components, Phase 4K generated downsampling and raw CSV/catalogue identities use nonzero weighted sampling. Existing safety, grammar, quality, quota, lease, cooldown, semantic/topic memory and default paths remain intact.
- Added bounded soft prompt guidance for recently prominent model-invented words without substitutions, bans or another provider call. Local audit records can now distinguish first-pass/final text and record active lexical penalties and affected selected ingredients.
- Live preflight exposed deterministic candidate-pool collapse after accumulated penalties. Added an 8% exploration floor; this keeps recently exposed words less likely while preventing finite-pool exhaustion.
- Across the corrected 250 provider-free rewrites, meaningful word breadth rose 1,431→1,466; rolling-five repetition fell 83.70→57.95 and rolling-ten 276.33→188.37. Category counts were identical, quality changed 7.311→7.304, and no selection exhausted. Complete-phrase breadth rose 4,367→4,374.
- Configuration, architecture, metrics, test commands and limitations are in `docs/comedy-vocabulary-phase4m-results.md`. No Phase 4K variant was promoted. Changes remain uncommitted and unpushed.
- Full safe validation: Python 481 passed, 0 failed, 105 subtests; Node 84 passed, 0 failed; compilation, JavaScript syntax and `git diff --check` pass.

## Universal Comedy Vocabulary Phase 4L — 2026-10-12

- Traced gravy, custard, marmalade, cucumber slicer, crumpet and milk float through all 28 Phase 4K records. None came from the seven sources. Cucumber slicer, crumpet and milk float were fully explained by same-article offers; four gravy articles and four marmalade articles had no same-article recorded offer, confirming a material model-side contribution. The audit did not retain pass one, so first-pass versus copy-edit attribution remains unknown.
- Confirmed that exact diversity is working: A offered 140 unique concept phrases and 138 bases; all variants had unique generated concept phrases; 279/280 descriptors were unique. Reader-visible repetition persists because there is no general word/head memory and the same editorial anchors occur across concept, descriptor, name and catalogue resources.
- The large raw pools contain 2,331 unique noun texts and 2,575 unique historical-animal-bank texts, but hard quotas and compact quality scoring narrow effective generated diversity. In A, institutional control, impossible technology, innuendo and unexpected behaviour formed 101/140 concept offers.
- Length-normalized cross-article recurring-word excess was 75.0/50.3/42.9/40.3 per 1,000 final tokens for A/B/C/D. This supports a premise-density effect but does not rank humour or justify promoting a variant.
- Recommended for review: a soft, decaying, source-exempt lexical-exposure ledger across offers/finals plus exposure-aware component sampling. Every word retains nonzero future probability. Prompt changes, bans, coherence filters and implementation were explicitly excluded.
- Full evidence, limitations, control audit and ranked remedies are in `docs/comedy-vocabulary-phase4l-investigation.md`. Changes remain uncommitted and unpushed.

## Universal Comedy Vocabulary Phase 4K — 2026-10-12

- Completed the explicitly approved automated real-provider comparison: seven fixed neutral sources × four variants, using the authentic two-pass `gpt-6-sol` rewrite/copy-edit path. All 28 outputs succeeded; there were no retries, substitutions or error records. Each variant used fresh isolated memory while its seven articles shared that variant's sequential memory.
- The ignored run directory is `local_audits/phase4k_experiment/20261012T_phase4k_abcd/`. Read `blind_comparison.md` and fill `scorecard.md` before opening `answer_key.csv`; complete JSONL records and objective metrics remain in the same directory.
- Objective observations only: A/B/C/D averaged 164.57/140/138/132 article words; offered 140/70/70/42 generated premises; offered 0/70/0/70 raw identities; and recorded 19/9/9/7 repeated detected-topic occurrences. These figures cannot determine funniness, coherence or preference.
- Added the reproducible experiment runner, fixed source fixture, source-grouped blind exporter and focused regression coverage. Hybrid raw offers and exact-final matches retain separate provenance. Default live behavior remains variant A.
- Full post-run validation: Python 472 passed, 0 failed, 105 subtests; Node 84 passed, 0 failed; Python compilation and JavaScript syntax pass. No production database or media operation occurred. Changes and local results remain uncommitted and unpushed.

- Analysed the ignored twelve-MUNGE audit. Powered constructions appeared in 8/12 articles, parliament in 7/12, and royal/crumpet wording in 5/12. The offered slate concentrated 99/240 concepts in institutional-control or impossible-technology themes despite exact phrase uniqueness.
- Confirmed that historical `animals` is a prompt bank containing animals and objects, while machine taxonomy also creates false species such as hood, game and survivor. Hybrid metadata calls the CSV source `legacy_mixed_identity`, invents no species, and admits only reviewed catalogue identities.
- Added default-preserving `NEWSMUNCHER_COMEDY_VARIANT=A|B|C|D`: A is exact Phase 4J; B is 10 generated + 10 raw; C is 10 generated; D is 6 generated + 10 raw. Provider count, default path, registries, two-pass rewrite and permanent memories remain intact.
- Audit records now distinguish hybrid raw offers from exact final matches and retain provenance plus comparison labels. Added an offline blind Markdown exporter with a separate key file.
- Across 250 provider-free prompts, hybrids roughly doubled unique word breadth and added eight raw domains; C and D cut concept text by about half. Exact ingredient reuse did not uniformly improve, and offline proxies cannot decide humour, coherence or source relevance.
- Full evidence, measurements, commands, limitations and human-review procedure are in `docs/comedy-vocabulary-phase4k-report.txt`. Changes remain uncommitted and unpushed.
- Full safe validation: Python 469 passed, 0 failed, 105 subtests; Node 84 passed, 0 failed; focused Phase 4K tests 56 passed; compilation, JavaScript syntax, ignore checks and `git diff --check` pass.

## Universal Comedy Vocabulary Phase 4J — 2026-10-12

- Analysed the ignored twenty-MUNGE Phase 4I audit locally. Confirmed that unused offers are correctly released but never influence accepted memory, allowing quality-ranked descriptors and bounded concept modifiers to recur. Only 2/200 descriptors were exact-final matches, so Phase 4G had almost no accepted descriptor signal.
- Added independent `NEWSMUNCHER_COMEDY_TOPIC_MEMORY=evaluation` mode with one bounded history read and one atomic post-persistence event update. Completed offers remain separate from accepted use and final detections.
- Recent completed concept phrases/premises/bases, descriptor phrases/premises and name families receive soft ordering penalties. Hard leases, exact accepted cooldowns, retry identity, grammar/category/intensity quotas, quality floors and exhaustion behavior are unchanged.
- Added evidence-led source-exempt detection for gravy, desserts, tea equipment, allotments, milk floats, queueing, municipal authority, powered constructions, tribunal self-representation, illegal raffles, neighbour-started-it, unauthorised swelling and floorboards-framed-it. Audit records include the exact matched evidence.
- Prompt guidance appears only after a family occurs twice in five articles, contains at most four labels and adds no provider call. In the 250-MUNGE fixture, rolling-ten exact-offer repetition fell 260.27→40.00, final-subject repetition 11.42→0.99 and final-construction repetition 9.00→1.36. Quality moved 8.271→8.161 within the 0.15 gate; average prompt overhead was 2.94 estimated tokens; no exhaustion occurred.
- Full findings, source-concentration caveat, metrics, quality risks and command are in `docs/comedy-vocabulary-phase4j-report.txt`. Changes remain uncommitted and unpushed.
- Full safe validation: Python 464 passed, 0 failed, 105 subtests; Node 84 passed, 0 failed; focused Phase 4J tests 95 passed; compilation, JavaScript syntax and `git diff --check` pass.

## Universal Comedy Vocabulary Phase 4I — 2026-10-12

- Added default-off `NEWSMUNCHER_COMEDY_AUDIT_LOG=on` diagnostics after successful rewrite persistence. Generation prompts, selection, semantic memory and final-joke memory are unchanged.
- Each fixed-schema JSONL record preserves complete source/final text, offered generated and legacy ingredients, exact final-text matches, premise and canonical joke-family metadata, allowlisted feature modes and existing numeric timing data. Unknown or unavailable metadata is not invented.
- The local writer uses owner-only creation modes, an exclusive file lock, an in-lock rewrite UUID check, UTF-8 append, flush and `fsync`. Failed or abandoned rewrites add nothing; logging failures only emit a concise exception-class warning.
- Added Markdown and CSV export preserving full article text and provenance. Both the default `local_audits/comedy_audit.jsonl` and exported reports are covered by the ignored `local_audits/` directory and are never uploaded automatically.
- Full commands, schema, sharing warning, file list and limitations are in `docs/comedy-vocabulary-phase4i-report.txt`. Changes remain uncommitted and unpushed.
- Full safe validation: Python 455 passed, 0 failed, 105 subtests; Node 84 passed, 0 failed; focused Phase 4I tests 27 passed; compilation, JavaScript syntax, `git diff --check` and ignore checks pass.

## Universal Comedy Vocabulary Phase 4H — 2026-10-12

- Traced "seventeen accountants" and "queue containment" to generated concept components and recorded Phase 2C prompt offers. Neither is a hardcoded rewrite example. Existing accepted matching can miss the memorable fragment when the provider shortens or paraphrases the complete offered phrase.
- Added independent `NEWSMUNCHER_FINAL_JOKE_MEMORY=evaluation` mode. It recognizes narrow accepted-output constructions, exempts source facts and supplies at most four recent avoid labels without banning broad subjects or adding a provider call.
- History updates occur only after successful draft persistence. Atomic article sequencing provides a ten-article cooldown; failed rewrites add nothing, concurrent updates remain safe, and read/write failures cannot block a rewrite.
- In the 250-rewrite equivalent fixture, repeated exact final jokes fell from 244 to 65 and repeated canonical constructions from 248 to 40. Rolling-five canonical repeats fell from 3.00 to zero; ingredient/premise diversity remained identical and neither path exhausted.
- Average prompt overhead was 237.58 characters (estimated 59.39 tokens), with 542 local memory operations across 250 rewrites. The report clearly identifies the synthetic-provider-compliance limitation.
- Full findings, metrics, trade-offs and manual commands are in `docs/comedy-vocabulary-phase4h-report.txt`. Changes remain uncommitted and unpushed.
- Full safe validation: Python 445 passed, 0 failed, 105 subtests; Node 84 passed, 0 failed; focused Phase 4H tests 25 passed; compilation, JavaScript syntax and `git diff --check` pass.

## Universal Comedy Vocabulary Phase 4G — 2026-10-12

- Confirmed that exact phrase cooldowns were functioning while descriptor mechanisms, close subject paraphrases and name sound families remained repetitive. Existing concept base/premise/animal memory was already stronger.
- Added independent `NEWSMUNCHER_COMEDY_SEMANTIC_MEMORY=evaluation` mode. It records only accepted semantic families and applies bounded soft ranking penalties; defaults and Phase 4D/4F modes are unchanged.
- Close descriptor wording such as competitive/professional queueing now shares an explicit theme-plus-anchor family. Source-story mentions are exempt. No embeddings, fuzzy service or model call was added.
- Rejected concept mechanism ranking after it worsened prompt premise/object diversity. Reordered descriptor penalties behind grammar, quotas, within-slate mechanism balance and short-form preference after an early family-first version reduced quality and lengthened phrases.
- In the 250-rewrite fixture, Phase 4G improved rolling-ten accepted ingredient repetition from 4.78 to 3.90, accepted premise repetition from 5.49 to 4.57 and structure repetition from 41.17 to 38.09 versus Phase 4F. Exact descriptor offers were less diverse, which is documented rather than hidden.
- Full findings, fair metrics, quality trade-offs, commands and rollout recommendation are in `docs/comedy-vocabulary-phase4g-report.txt`. Changes remain uncommitted and unpushed.
- Full safe validation: Python 434 passed, 0 failed, 105 subtests; Node 84 passed, 0 failed; focused Phase 4G/rewrite tests 76 passed; 250-MUNGE audit completed without exhaustion.

## MUNGE rewrite credit-exhaustion correction — 2026-10-11

- The running terminal showed the rewrite provider returning HTTP 429 with `insufficient_quota` / `credit_balance_exhausted`; concept, name and descriptor selection had all succeeded. The generic 500 came from `send_prompt()` collapsing every provider exception to `None`.
- Credit exhaustion is now preserved as a typed failure and returned as an actionable HTTP 503. Existing frontend handling displays the detail, hides the loader and restores MUNGE controls. No automatic provider retry was added.
- Failure cleanup still releases all temporary name, concept and descriptor leases. A successful rewrite still requires OpenAI API credits; code cannot bypass account billing.
- Corrected the Phase 4F live descriptor registry to apply diversified assembly in evaluation mode during both viability and final selection.
- Full safe validation: Python 427 passed, 0 failed, 105 subtests; Node 84 passed, 0 failed; focused tests 32 passed; compilation, JavaScript syntax and `git diff --check` pass.

## Universal Comedy Vocabulary Phase 4F — 2026-10-11

- Corrected the Phase 4E comparison to use identical seeds, quotas and mocked uptake for live, Phase 4E and Phase 4F configurations. Confirmed that descriptor ranking, small fixed expression spaces and equal template selection caused the disappointing results.
- Descriptor evaluation now samples across the complete quality-filtered compatible stratum. Unique offers improved from 888 live / 817 Phase 4E to 1,178 Phase 4F; rolling-ten repeats fell to 8.39 from 13.00 live, with 202 premises, 24 mechanisms and no exhaustion.
- Retained the Phase 4E name algorithm after a recipe-balancing experiment reduced diversity. Equivalent-seed results show modest exact/root improvement but no phonetic-pattern improvement, so names remain evaluation-only.
- Added structurally distinct offline slang and place constructions with bounded capacity-aware selection. Slang remains inferior to live. Places exceed live lifetime uniqueness but retain worse short-window repetition. Both remain offline.
- Full measurements, performance, acceptance decisions, trade-offs and 200 labelled examples are in `docs/comedy-vocabulary-phase4f-report.txt`.
- Full safe validation: Python 424 passed, 0 failed, 105 subtests; Node 84 passed, 0 failed; focused Phase 4F 63 passed; compilation, JavaScript syntax and `git diff --check` pass.

## Universal Comedy Vocabulary Phase 4E — 2026-10-11

- Added independently gated, machine-checked descriptor and invented-name expansions. `NEWSMUNCHER_EXPANDED_DESCRIPTORS` and `NEWSMUNCHER_EXPANDED_NAMES` default to `off`; `reviewed` also preserves current behaviour because no Phase 4E item has been promoted by a human.
- Added 12 descriptor mechanisms across all six grammatical roles and expanded the existing cheeky/absurd component families without changing live quotas, registry semantics, accepted-use cooldowns, retry identity or provider calls.
- Added deterministic typed slang and fictional-place generators for offline evaluation only. Their 250-MUNGE results repeat substantially more than the live CSV baselines, so neither is wired into the rewrite path.
- The 250-MUNGE audit found broader descriptor mechanism coverage (12 to 17 observed) and modest name lifetime diversity improvement (2,243 to 2,254 unique offers), but descriptor exact diversity and rolling-window name repetition did not improve. Both expansions remain local evaluation material.
- Full metrics, licensing/editorial state, weak examples, manual commands and 200 labelled outputs are in `docs/comedy-vocabulary-phase4e-report.txt`.
- Full safe validation: Python 422 passed, 0 failed, 105 subtests; Node 84 passed, 0 failed; compilation, production JavaScript syntax, resource rebuilding and `git diff --check` pass.

## Universal Comedy Vocabulary Phase 4D — 2026-10-10

- Added an explicit `NEWSMUNCHER_EXPANDED_VOCABULARY` switch: `off` remains the default, `reviewed` admits only prior human-reviewed animal/object entries, and `evaluation` deliberately exposes compatible machine-checked entries for local editorial testing without relabelling them.
- Integrated catalogue bases into the existing concept generator only. Existing templates, quotas, prompt size, leases, cooldowns, accepted-use memory, provider count and historical behaviour remain intact. Cheeky, emergency and ceremonial identity banks stay curated rather than inferring comic purpose from taxonomy.
- Added a cached validation/eligibility gate for grammar, familiarity, classification, safety flags and sensitive definitions. The review path admits 560 total animal and 928 total object identities while excluding 979 and 2,981 machine entries respectively; all machine entries remain unapproved.
- The 250-rewrite comparison increased unique offered bases from 276 to 1,223. Average local generation changed from 9.94 ms to 14.66 ms, while average concept-prompt characters changed from 761.58 to 739.42 and the number of prompt concepts stayed at twenty.
- Added expanded-mode determinism, concurrency, failure cleanup, accepted-animal memory and offer/prompt/mock-final accounting coverage. Full findings, weak combinations, licensing, descriptor/name investigation and manual instructions are in `docs/comedy-vocabulary-phase4d-report.txt`.

## Universal Comedy Vocabulary Phase 4C — 2026-10-10

- Expanded the offline typed catalogue from 1,932 to 9,980 entries: animals 1,539; objects 3,909; descriptors 2,948; names 915; slang 128; fictional-place ingredients 541.
- Added a reproducible Open English WordNet 2025 CC BY 4.0 importer retaining synset IDs, definitions, release URL and attribution. The raw archive remains under `/tmp` and is not part of the repository. All 7,046 OEWN-derived entries remain machine-checked/needs-review.
- Added original safe, role-labelled slang and fictional construction components. Unsafe legacy slang and factual place/name banks were not bulk-imported. Names and slang remain below their aspirational lower targets rather than being padded with weak or unsafe variants.
- Expanded validation/safety filtering and optimized near-duplicate detection from quadratic scanning to indexed lookup. The 9,980-entry catalogue has zero validation errors, two near-duplicate warnings and five honest semantic-concentration warnings.
- The 250-MUNGE audit distinguishes offers from simulated accepted use. Unique offered identities rose from 133→518 animals, 506→1,462 objects, 30→128 slang and 58→467 places. Descriptor diversity remained flat because lexical adjectives do not supply genuinely new comic situations; name-root improvement was modest.
- Full source/licensing inventory, editorial status, measurements, 100 examples, weak/rejected material, gaps and staged integration plan are in `docs/comedy-vocabulary-phase4c-report.txt`. Live MUNGE behavior and all existing registries remain unchanged. No production write, paid provider call, commit or push.

## Universal Comedy Vocabulary Phase 4B — 2026-10-10

- Added a versioned typed JSON catalogue and schema covering animals, objects, descriptors, names, slang and fictional-place ingredients. Stable identities, grammar, semantics, mechanisms, familiarity, provenance/licensing, editorial flags and approval status are explicit.
- The reproducible local build contains 1,932 ingredients: 1,438 previously reviewed and 494 machine-checked/needs-review. All source records honestly remain `INTERNAL-UNVERIFIED`; no external dataset was copied or scraped.
- Added build-time validation for duplicate/near-duplicate identities, malformed content, grammatical roles, provenance/licences, discriminatory and identity risks, unsupported obscurity and semantic concentration. The snapshot has zero errors and three retained concentration/classification warnings.
- Added a deterministic offline selector with recent-ID avoidance, semantic/familiarity balance and role/mechanism compatibility. It is not imported by the live rewrite pipeline and does not replace any lease, cooldown or claim registry.
- The 250-MUNGE comparison uses production suggestion volumes and includes 100 labelled examples. It shows zero rolling-ten reuse in the four broad reviewed families while honestly exposing that the 30-item slang and 58-item place samples are far too small for integration.
- Full architecture, licensing inventory, counts, measurements, gaps, risks, examples and staged integration plan are in `docs/comedy-vocabulary-phase4b-report.txt`. No live behavior, database, provider, commit or push.

## Universal Comedy Vocabulary Phase 4A — 2026-10-10

- Audited all six legacy CSVs and the structured concept, descriptor and invented-name resources. Raw string capacity is high, but meaningful humour remains bounded by small base, mechanism and modifier banks.
- Identified suitable source families: Wikidata CC0, Open English WordNet CC BY 4.0 plus Princeton notice, licence-filtered GBIF datasets, OS Open Names/OGL, GeoNames CC BY 4.0 and ONS/OGL. Wiktionary requires a separate CC BY-SA/GFDL decision.
- Added an offline-only deterministic catalogue prototype. It is not imported by live code and changes no existing resource. Its 100-rewrite comparison demonstrates lower short-window identity reuse while exposing unsafe, malformed and grammatically incompatible legacy candidates rather than hiding them.
- Recommended versioned typed catalogues, build-time normalization, one batched history read, final atomic leases, identity/premise cooldown keys and explicit compatibility/quality review.
- Full inventory, 50 examples, measurements, licensing notes, risks and staged implementation are in `docs/comedy-vocabulary-phase4a-report.txt`. No live integration, provider call, production write, commit or push.
- Full safe validation: Python 407 passed, 0 failed, 105 subtests; Node 84 passed, 0 failed; compilation and diff checks pass.

## Comedy Selection Reliability Phase 3G — 2026-10-10

- Confirmed invented-name failure was artificial candidate-pool exhaustion: new rewrites reused `active_pet:draft_session`, repeatedly searching the same 100 candidates per style while accepted names accumulated exact cooldowns.
- Names now use the fresh rewrite UUID, generate 300 deterministic candidates per style, perform one batched availability read, and atomically lease only the final 7 cheeky / 3 absurd slate. Exact-name cooldown and active leases never relax.
- Added typed `NameSelectionExhausted`; partial leases are released and the route returns an actionable HTTP 409 before either provider pass. Existing Creator error handling displays it and restores MUNGE after wind-down.
- Audited concepts and descriptors: both already follow the bounded/batched/typed reliability pattern, with only documented soft ingredient diversity relaxation. Phase 3F memory and timing behavior remains intact.
- A combined in-memory audit completed 10, 25, 50, 100 and 250 consecutive production-quota selections. At 250: 2,368 unique names among 2,500 offers, zero failure, average local selection 600.20 ms, maximum 868.71 ms.
- Full findings and operation counts are in `docs/comedy-selection-reliability-phase3g-report.txt`. Changes remain uncommitted and unpushed.
- Full safe validation: Python 406 passed, 0 failed, 105 subtests; Node 84 passed, 0 failed; compilation, JavaScript syntax and diff checks pass.

## Comedy Ingredient Memory Phase 3F — 2026-10-09

- Confirmed that animals embedded in power sources, repelling behaviors, bureaucracy and emergencies bypassed creature-base cooldown. Full-phrase-only accepted matching also missed paraphrased species and animals independently introduced by the rewrite.
- Added conservative 60-species accepted-text detection with singular/plural and multiword handling, source-fact exemption, persistent animal records, object-base memory and descriptor subject/premise memory. Only successfully persisted accepted output updates history.
- Selection now uses one batched availability read and an in-memory quota viability check before atomically leasing the final slate. A reconstructed 100-rewrite Phase 3E path made 24,161 atomic writes and 7,050 cleanup writes; Phase 3F made 6,409 and 301 respectively, despite adding animal leases.
- Added safe structured `[munge-timing]` diagnostics for local selection stages, database operation counts, prompt construction, each provider pass, persistence, accepted matching/cooldowns and total duration. No source text, prompt, response or credential is logged.
- The 100-rewrite audit improved average unique species per rolling ten from 7.77 to 10.00 and reduced simulated hamster use from seven to two. Accepted object identity improved from 52 to 100 unique; descriptor subjects from 63 to 100; combined premise keys from 107 to 162 of 200.
- Full findings and manual timing instructions are in `docs/comedy-ingredient-memory-phase3f-report.txt`. Changes remain uncommitted and unpushed.
- Full safe validation: Python 400 passed, 0 failed, 105 subtests; Node 84 passed, 0 failed; focused post-validation 48 passed; compilation, JavaScript syntax and diff checks pass.

## Comedy Diversity Phase 3E — 2026-10-09

- Confirmed that phrase uniqueness concealed repeated structures and premises: concept/descriptor quality ranking repeatedly favored a limited set of mechanisms, while old cooldown keys represented bases or subjects rather than the underlying joke.
- Added deterministic `semantic_theme` and `premise_key` metadata. Concepts now lease and cool exact phrase, base and premise records; descriptors assemble from an availability-filtered broad pool and protect exact phrases plus subjects.
- Exact phrase cooldown and active concurrency leases remain hard. Base/premise or subject cooldown alone can relax after demonstrated saturation, preserving completion without disabling cooldowns or falling back to CSV banks.
- Added seven concept and eight descriptor comic mechanisms, bringing both resources to 24 templates. Cross-generator assembly softly deprioritizes descriptor themes already dominant in the 20-concept slate without changing prompt length or provider count.
- A production-shaped 100-rewrite simulation completed all rewrites; the old descriptor path exhausted after only 4–6. The final 2,000 concept offers contained 1,828 unique phrases and 19 mechanisms; 1,000 descriptor offers contained 796 unique phrases and 20 mechanisms.
- Full findings, measurements, 30 examples, trade-offs and manual steps are in `docs/comedy-diversity-phase3e-report.txt`. Changes remain uncommitted and unpushed for review.
- Full safe validation: Python 393 passed, 0 failed, 105 subtests; Node 84 passed, 0 failed; Python compilation, production JavaScript syntax and `git diff --check` pass.
- Manual testing exposed PyMongo's default naive-UTC BSON decoding in the new descriptor availability prefilter. Persisted `last_used_at` and `offer_until` values are now normalized to aware UTC before Python comparisons, eliminating the pre-provider 500 without changing cooldown semantics. Regression coverage uses naive Mongo-shaped timestamps; final validation is Python 394 passed and Node 84 passed.

## Comedy Descriptors Phase 3D — 2026-10-09

- New rewrites default to ten generated descriptors and zero `adverbs.csv` candidates. `NEWSMUNCHER_DESCRIPTOR_MODE=legacy` restores the original CSV and permanent-claim behavior without changing historical creations.
- Production slates preserve exact 7/3 cheeky/absurd and 3/5/2 intensity allocations, all six grammatical roles, unique phrases and unique joke subjects. Compact role tags plus one shared rule block ask for roughly two to four natural uses.
- Generated descriptors are excluded from permanent CSV claims and direct DESCRIPTION-placeholder assignment. The existing two-pass rewrite/copy-edit provider architecture is unchanged.
- Added a dedicated `generated_descriptor_usage` registry with phrase and subject records, rewrite-UUID attempt identities, stable deterministic retries, atomic leases, partial-acquisition rollback, expiry, conservative exact-use cooldowns and unused/failure release.
- Bounded selection exhaustion is now a controlled HTTP 409 before any rewrite request. Existing Creator error handling displays the detail and completes its normal loading wind-down.
- The integrated example adds 1,017 characters versus a representative legacy slate, approximately 254 input tokens using the repository's documented character/4 estimate. It adds no provider request. Ten local slate builds averaged 172 ms.
- Full safe validation: Python 390 passed, 0 failed, 105 subtests; Node 84 passed, 0 failed; compilation, JavaScript syntax and diff checks pass. No provider call, production database write, commit or push.

## Comedy Descriptors Phase 3C — 2026-10-09

- Traced the live descriptor path: ten unclaimed `adverbs.csv` values are source-filtered, split across three flat prompt placeholders, treated as interchangeable adjective/adverb ingredients and permanently claimed only for exact accepted final uses after copy-editing.
- Added an offline-only shadow module comparing ten generated descriptors, seven generated plus three legacy, and six generated plus four legacy while preserving the existing ten prompt slots.
- Full-replacement slates use exact 7/3 categories and 3/5/2 intensities, prioritize all six grammatical roles, unique mechanisms and short forms, and prevent repeated joke subjects. Ten reviewed Strategy A slates each covered all six roles with no repeated subject.
- Added role-labelled mock prompt previews and concise guidance to use roughly two to four descriptors naturally rather than forcing predicate/clause forms into adjective positions.
- Modelled a future separate descriptor lease/cooldown lifecycle using rewrite-attempt identities, expanded deterministic pools, stable retries, concurrent phrase/subject exclusion, failure release, expiry and exact accepted-use matching. Eight saturated rounds followed by a ninth fresh selection successfully.
- Strategy A is recommended for Phase 3D behind generated/legacy configuration. Average estimated prompt increase was 430 tokens, with no extra provider request; legacy `adverbs.csv` remains the fallback.
- Full safe validation: Python 377 passed, 0 failed, 105 subtests; focused descriptor/shadow tests 21 passed. Live prompts, CSVs, permanent claims and runtime behavior are unchanged. No provider call, production write, commit or push.

## Comedy Descriptors Phase 3B — 2026-10-09

- Raised the humour floor by replacing generic competence adjectives with concise comic contradictions, removing ordinary grievance subjects and giving inappropriate-confidence descriptions an explicit absurd basis.
- Added deterministic insertion rules and usage examples to every generated descriptor. The six roles now explicitly distinguish attributive pre-noun phrases, linking-verb predicates, post-noun modifiers, action adverbials, ongoing behaviours and complete/partial short clauses.
- Reworked longer templates so their second clause supplies a causal payoff or limitation instead of unrelated padding. Short forms remain common; length earns no automatic score advantage and outputs over ten words are flagged.
- Corrected audit accounting: proposed candidates now reconcile exactly into explicit rejections and eligible candidates, while eligible candidates reconcile into emitted results and valid alternatives not selected from ranking pools.
- Seeded audit: 5,000 unique, zero duplicates, exact 3,500/1,500 category and 1,500/2,250/1,250 intensity allocations, all roles/templates/mechanisms represented, 100,481 proposals, 60,481 rejections, 40,000 eligible candidates and no exhaustion. Proposal volume fell 67% versus Phase 3A.
- Full safe validation: Python 368 passed, 0 failed, 105 subtests; focused descriptor tests 12 passed. The generator remains offline. No provider call, production database write, commit or push.

## Comedy Descriptors Phase 3A — 2026-10-09

- Audited the three remaining live CSV banks. Adverbs has 1,954 cells / 1,683 unique values and is predominantly an adjective/participle descriptor bank; slang has 2,277 / 2,142 and mixes several incompatible grammatical/safety roles; places has 1,005 / 997 and mixes real geography with fictional locations and institutions.
- Confirmed all three still use ten unclaimed legacy candidates, exact accepted-use detection and permanent transactional claims. There is no cooldown or recycling. Phase 2 generated concepts and invented names do not change these paths.
- Added a standalone deterministic comedy-descriptor generator with 70/30 cheeky/absurd categories, three intensities, six grammatical roles, sixteen compatible templates, thirteen comic mechanisms, diversity caps, safety/grammar filters, bounded generation, quality scores and editorial warnings.
- The seeded 5,000 audit produced 5,000 unique outputs, zero duplicates, exact 3,500/1,500 category and 1,500/2,250/1,250 intensity allocations, all roles/templates represented, 304,575 proposals and 224,575 explicit rejections without exhaustion.
- Added an offline diagnostic command and a 150-item categorized editorial sample plus weakest-30 audit at `docs/comedy-descriptors-phase3a-review.txt`. The report also proposes role-aware future slang generation and source-geography-preserving place generation.
- Full safe validation: Python 365 passed, 0 failed, 105 subtests; focused descriptor tests 9 passed; compilation and diff checks passed. Live prompts, CSVs, claims, names, concepts and media behavior remain unchanged. No provider call, production write, commit or push.

## Phase 2E repeated-MUNGE fix — 2026-10-09

- Confirmed the browser's durable draft-session identifier was also being used as the deterministic concept seed. Consecutive MUNGEs therefore revisited the same 60-item mixed pool; accepted base objects entered cooldown until a category quota became impossible, even though unused leases were correctly released.
- Each newly allocated rewrite UUID now provides the concept-attempt identity. Separate rewrites from the same source receive fresh deterministic pools; retrying the same registry attempt key remains stable.
- Replaced the mixed 60-item candidate pool with bounded category-and-target-specific pools of 30 candidates. This gives scarce categories independent collision/cooldown headroom while retaining the exact 10+10 semantic quotas, base uniqueness and atomic Mongo leases.
- Genuine bounded exhaustion now becomes a controlled HTTP 409 before either rewrite provider call. Creator displays the server detail, stops loading and restores MUNGE availability instead of failing silently.
- Existing records require no migration: unused leases were already released, active leases expire after 15 minutes, and accepted cooldowns naturally expire under their configured period.
- Full safe validation: Python 356 passed, 0 failed, 105 subtests; Node 84 passed, 0 failed; Python compilation, JavaScript syntax and `git diff --check` passed. No provider call, production write, commit or push.

## Comedy Concepts Generator Phase 2E — 2026-10-09

- Generated mode now supplies ten generated noun concepts and ten generated animal/object concepts. It does not draw from `nouns.csv` or `animalsAndObjects.csv`, and generated concepts never enter permanent CSV claims.
- The semantically constrained slate uses this combined category allocation: three everyday British, four cheeky objects, four absurd inventions, four ridiculous creatures, three bureaucratic concepts, one emergency item and one ceremonial object. Creatures remain confined to the animal/object bank; bureaucracy remains confined to nouns.
- The existing concise guidance continues to make concepts optional and asks for roughly two to four natural uses. Provider count and the two-pass rewrite/title flow are unchanged.
- Twenty concepts use base-keyed atomic leases with deterministic retries, concurrent-session exclusion, exact accepted-use cooldowns, expired-offer recovery and bulk release for unused or failed offers. Legacy mode restores the original ten CSV nouns plus ten CSV animals/objects and their permanent-claim behavior.
- Full safe validation: Python 351 passed, 0 failed, 105 subtests; Node 83 passed, 0 failed; Python compilation, JavaScript syntax and `git diff --check` passed. No provider call, production database write, commit or push.

## Comedy Concepts Generator Phase 2D — 2026-10-09

- Strategy C is now the default for new Creation rewrites: seven ordinary plus three generated noun candidates, and seven ordinary plus three generated animal/object candidates. Legacy mode restores the original ten-plus-ten CSV behavior.
- Added a separate `generated_concept_usage` Mongo collection with base-keyed atomic temporary leases, exact accepted-phrase cooldown tracking, deterministic retries, expiry, failure release, generator metadata and no permanent exhaustion.
- Generated concepts are removed from permanent claim contenders; only the seven ordinary values in each modified bank remain eligible for the existing transactional word claims.
- Added concise optional-ingredient guidance without another provider call or any change to the two-pass rewrite/title architecture. Tracking failures after a successful paid rewrite are logged safely and cannot discard the saved rewrite.
- Full safe validation: Python 350 passed, 0 failed, 105 subtests; Node 83 passed, 0 failed. Focused concept/name/shadow selection: 38 passed. No provider call or production database write.

## Comedy Concepts Generator Phase 2C — 2026-10-09

- Added a standalone offline shadow-selection and prompt-preview module; neither `previews.py` nor `clean_data.py` imports it, so normal Creation behavior cannot change.
- Confirmed the live pipeline draws ten candidates from each of nouns, animals/objects, descriptors, slang and places, plus ten invented names. It splits each bank across the three existing placeholders and permanently claims only exact accepted uses from the five legacy claim banks.
- Compared three strategies across ten deterministic mock slates: A replaces ten nouns, B replaces all twenty noun/animal slots, and C retains fourteen ordinary anchors while adding three concepts to each bank.
- Candidate-only estimated token increase averaged 37 for A, 95 for B and 27 for C. The proposed optional-use guidance adds an estimated 84 tokens in all previews. Estimates use UTF-8 length divided by four because the project has no local tokenizer dependency.
- Added an in-memory lease/cooldown simulation covering stable retries, concurrent phrase and base exclusion, failed-rewrite release, exact accepted-use tracking, version metadata and reuse after cooldown. It never accesses MongoDB.
- Recommendation for Phase 2D: Strategy C behind a disabled-by-default switch, with six concepts treated as optional ingredients and tracked separately from permanent CSV claims.
- Full safe validation: 344 passed, 0 failed, 105 subtests passed, including 23 focused concept/shadow tests. No provider call, production write, prompt activation, commit or push.

## Comedy Concepts Generator Phase 2B.1 — 2026-10-09

- Recast creature, emergency, ceremonial and bureaucratic templates around their recognisable head noun: animals now act, possess histories or work in roles; equipment and ceremonial objects state their purpose; commissions and documents regulate a clear absurd responsibility.
- Added an editorially controlled compact-creature template and a 10% batch cap. Strong short premises such as `filibustering mackerel` remain possible without dominating developed animal-first stories.
- Added regressions for the reviewed awkward constructions and retained the Phase 2B metadata, warnings, mechanism labels and deterministic category/intensity allocation.
- Seeded audit: 5,000 unique phrases, zero duplicates, all 17 templates represented, 86,611 candidates attempted, 16,611 rejected and no exhaustion. This is 618 additional attempts/rejections versus Phase 2B, reflecting the deliberate compact-creature cap rather than reduced construction capacity.
- Full safe validation: 338 passed, 0 failed, 105 subtests passed, including 17 focused concept tests. No provider call, production write, integration change, commit or push.

## Comedy Concepts Generator Phase 2B — 2026-10-09

- Corrected modifier placement using separate pre-noun and post-noun templates. Post-noun histories and capabilities no longer produce constructions such as `trained in close combat stepladder`; repeated emergency terms are structurally excluded.
- Ridiculous creatures now normally receive a developed occupation, scandal, impossible ability or institutional responsibility. Strong compact jokes remain supported through an explicit two-word exception list rather than a general short-form template.
- Ceremonial objects now receive a ridiculous ceremonial purpose or inappropriate symbolic importance. Emergency equipment now combines a recognisable device with a grammatical absurd emergency purpose.
- Template metadata now identifies the comic mechanism. Results additionally record editorial warnings and word count; the CLI prints all review metadata and reports short-form rates, grammatical validation and the weakest 30 accepted concepts.
- Seeded audit: 5,000 unique phrases, zero emitted duplicates, exact category/intensity allocations, all 15 templates represented, 85,993 candidates considered, 15,993 rejected and no category exhausted. Ridiculous creatures and ceremonial objects produced zero two-word outputs in this seed; explicit tests prove strong two-word creature exceptions remain available.
- Compared with Phase 2A, rejection volume fell from 35,657 to 15,993 because templates now form compatible grammatical premises more reliably. The stronger structures retain sufficient variety and did not exhaust any category.
- Full safe Python validation: 338 passed, 0 failed, 105 subtests passed, including 17 focused concept tests. No provider call, production write, live integration, source-bank modification, commit or push.

## Comedy Concepts Generator Phase 2A — 2026-10-09

- Added a standalone deterministic offline generator for seven configurable concept categories and three configurable comedy-intensity levels. It uses structured component banks, compatible templates, bounded candidate ranking and explicit rejection reasons.
- Every accepted concept records phrase, category, visible base subject, template, intensity, visual suitability, number/countability, article, generator version and quality score.
- Added `python -m scripts.diagnostics.generate_comedy_concepts` for the approved 135-item editorial sample and a seeded 5,000-item audit. It has no database, network, provider or live-application dependency.
- Seeded audit: 5,000 unique phrases, zero emitted duplicates, exact 15/20/20/20/15/5/5 category allocation, exact 30/45/25 intensity allocation, 105,622 candidates considered, 35,657 rejected, and no category exhausted. Monitored biscuit/sausage/custard/trouser/council themes each remained below 1%.
- Full safe Python validation: 335 passed, 0 failed, 105 subtests passed, including 14 focused concept-generator tests. No provider call, production database write, live prompt change, word-claim change or source-bank modification.
- Work remains uncommitted and unpushed for editorial review.

## Invented Comedy Names Phase 2 — 2026-10-09

- New Creation rewrites now default to an exact ten-name invented slate: seven approved cheeky names and three approved absurd names. The phonetic category is excluded from live selection.
- `NEWSMUNCHER_NAME_MODE=legacy` restores the original `names.csv` prompt behavior; the legacy bank and implementation remain present and historical creations require no migration.
- Added Mongo-backed temporary name leases keyed by active pet/draft session. Deterministic slates make retries consistent, `_id`-guarded atomic leases keep concurrent sessions disjoint, and failed rewrites release their offers.
- Only supplied names found literally in the accepted final title/body receive a configurable recent-use timestamp. Unused prompt candidates are released, cooldowns expire, and invented names are never added to permanent word claims.
- Added concise invented-name rewrite guidance to favor supplied identities, retain character-name consistency, avoid real celebrity replacements and avoid forcing all ten names into a story. The existing two-pass provider flow is unchanged.
- Added environment configuration for mode, weights, slate size, cooldown days and offer duration. Default behavior remains 70/30 with ten names.
- Cost impact: no additional provider calls. Prompt input grows by roughly 70–130 tokens from the name-specific rules and potentially longer invented names. A new rewrite normally performs ten atomic lease writes, up to ten accepted-use updates and one unused-offer release against the dedicated Mongo collection.
- Full safe validation: Python 321/321 plus 105 subtests; Node 83/83; syntax and diff checks clean. No external provider call or production database write. Work remains uncommitted and unpushed for manual review.

## Comedy Name Generator Phase 1C — 2026-10-09

- Replaced the shuffled fixed phonetic-name list with 16 deterministic editorial joke families that combine compatible name-like openings and spoken punchline components.
- Every phonetic result now records its intended spoken reading, construction technique and component family. Family-balanced selection prevents a single productive pattern from dominating a review batch.
- Added 32 explicit familiar internet joke-name exclusions, including the reviewed Ben Dover / Phil McCracken / Drew Peacock class. No output is labelled a spoonerism because the current approved construction families do not perform a genuine sound exchange.
- The present editorial construction space contains 102 candidates. The fixed-seed review evaluated all 102 and selected 50 distinct meanings; no candidate from the curated component space failed the general safety/pronunciation filter. The bounded space is deliberately honest and fails on exhaustion rather than padding output.
- Cheeky and absurd component banks, templates, weights and construction methods remain unchanged from approved Phase 1B.
- Full offline validation: Python 312/312 plus 105 subtests, including 14 focused generator tests. No provider call, production database write, live rewrite change, reservation/cooldown or permanent claim change. Work remains uncommitted for editorial review.

## Comedy Name Generator Phase 1B — 2026-10-09

- Expanded the isolated component banks and construction grammar across six cheeky and seven absurd templates, plus a larger hand-curated phonetic set and explicit source-phrase spoonerisms.
- Candidate generation now chooses among multiple candidates within the selected weighted template, scores spoken shape and structural interest, rejects weak/safety failures, and applies first-name and surname-family diversity caps. The configured 70/30 style mixture remains unchanged.
- Seeded 5,000-name audit: 5,000 unique; zero exact duplicates; 3,500 cheeky / 1,500 absurd; 12 templates; 65,004 candidates considered; 7,160 duplicate candidates rejected; five quality/safety candidates rejected; no category exhausted. The most reused first component appeared 53 times and the most reused surname component 17 times.
- Review CLI now defaults to 100 cheeky, 50 absurd and 50 phonetic/spoonerism names and prints the construction recipe plus detailed audit diagnostics.
- Full offline validation: Python 310/310 plus 105 subtests, including 12 focused generator tests. No provider call, production database write, live rewrite change, reservation/cooldown or permanent claim change. Work remains uncommitted for editorial review.

## Comedy Name Generator Phase 1 — 2026-10-09

- Added an isolated deterministic generator with reusable cheeky/absurd component banks, curated phonetic jokes, configurable seeds, exact default 70/30 invented-style batching and reserved future real-name category weights.
- Filtering rejects normalized duplicates, legacy-bank collisions, blocked terms/pairs, overlong names and basic unpronounceable consonant/vowel forms. Gender-compatible honorific and ceremonial-epithet banks prevent accidental mismatches.
- Added `python -m scripts.diagnostics.generate_comedy_names` for local review samples. It has no database, network, provider or live application dependency.
- The live `names.csv`, rewrite prompt, name sampling, word claims and all downstream media behavior remain byte-for-byte untouched.
- Full offline validation: Python 308/308 plus 105 subtests; syntax and diff checks clean. Changes remain uncommitted for review and have not been pushed.

## Final Gallery check-in — 2026-10-09

- Restored functional client-side BACK history while preserving NEXT selection, progressive media playback and navigation cleanup.
- Made BACK/NEXT a matched cowhide pair, removed parchment seams, reduced and aligned shared CREATE/GALLERY navigation, and advanced static cache tokens.
- New nominated entries start at the current Gallery display-count floor; NEXT excludes the current creation whenever another eligible creation exists.
- Added the original local `cartoon-double-boing-pop.wav` click effect for BACK/NEXT with one shared non-overlapping player; existing hover effects remain unchanged.
- Full offline validation: Node 83/83; Python 298/298 plus 105 subtests; Python/JavaScript syntax and diff checks clean. No paid provider call, production database write, merge or deployment.

EXPERIMENT: Rewrite quality comparison: `gpt-5.6-luna` → `gpt-5.6-terra` → `gpt-6-luna` → `gpt-6-sol`. Prompts and all other rewrite settings remain unchanged.

## Repository reorganisation Batch D — 2026-10-08

- Moved the isolated WaveSpeed HTTP transport from `services/wavespeed.py` to `integrations/wavespeed.py`; API/service orchestration and provider behavior are unchanged.
- Added a compatibility import at the former module path and updated production, smoke-test, test and documentation imports to the canonical integration path.
- Focused video validation: 48 passed / 3 known failures. Full Python validation: 280 passed / 11 known failures / 105 subtests, exactly matching Batch C.
- No provider call, database access, generated-media mutation, push or merge.

## Repository reorganisation Batch E — 2026-10-08

- Moved 16 Node tests to `tests/frontend/` and 26 Python tests to `tests/python/`.
- Updated only structural module paths, repository-root calculations, cross-runner commands and documentation references.
- Full Node validation: 63 passed / 19 known failures. Full Python validation: 280 passed / 11 known failures / 105 subtests. Results exactly match Batch D.
- No provider call, database access, generated-media mutation, push or merge.

## Repository reorganisation Batch F — 2026-10-08

- Moved four administrative tools to `scripts/maintenance/` and four opt-in provider/media diagnostics to `scripts/diagnostics/`.
- Updated package imports, mocks, repository-root calculations and documented CLI commands. Added subpackage markers so module invocation remains available.
- Historical recovery and comparison tools remain present; paid diagnostic paths retain their explicit opt-in safeguards.
- Focused script validation: 92 passed plus 99 subtests. No provider call, database access, generated-media mutation, push or merge.

## Baseline test repair — 2026-10-08

- Updated stale tests for the current `gpt-6-sol` rewrite experiment, five source controls, Creator confirmation UI, MUNGE geometry, canvas teat effects, two-play Gallery jingles, Gallery progress/backdrop behavior, current furry navigation, local ping-pong media versions and independent end-frame styles.
- Browser mocks now implement only the DOM methods used by the approved current code. Provider and socket guards remain active; no assertion was weakened to permit external calls.
- Full Node validation: 82 passed / 0 failed. Full Python validation: 291 passed / 0 failed / 105 subtests.
- No application behavior, provider request, database state or generated media changed.

## Low-risk cleanup — 2026-10-08

- Removed nine unused imports and three unreferenced utility functions. Active prompts, word banks, generated media, persistence paths and historical recovery/compatibility code remain untouched.
- Retained all audit-classified obsolete artwork/code pending explicit deletion approval.
- Static reference audit reports only the previously documented missing Gallery BACK image and the expected runtime-composed MUNGE teat path false positive.
- Full offline validation remains green: Node 82/82; Python 291/291 plus 105 subtests. No provider call, production database access, generated-media mutation, push or merge.

## Final asset housekeeping — 2026-10-08

- Confirmed `gallery-back.png` never existed in Git. BACK now uses the supplied NEXT cowhide-arrow PNG with a BACK-only horizontal mirror; routes, sounds, animation and navigation logic are unchanged.
- Deleted ten unreferenced, superseded raster assets (9,520,715 bytes) plus three conclusively inactive OBSOLETE code candidates (2,759 bytes).
- Retained the MUNGE source sheet, complete udder reference, master udder and original udder source because they remain the only rebuild/reference masters for current raster artwork.
- Full validation passed: Node 82/82; Python 291/291 plus 105 subtests; Python/JavaScript syntax and diff checks clean. Creation/Gallery route coverage passes, and the static audit has no missing literal asset.

## Repository reorganisation Batch C — 2026-10-08

- Moved 13 active JavaScript files and two active stylesheets with `git mv`: Creation scripts now live under `static/js/creation/`, Gallery code under `static/js/gallery/`, shared navigation under `static/js/shared/`, shared CSS under `static/css/shared/` and Gallery CSS under `static/css/gallery/`.
- Preserved the Creation script loading order and existing global/DOMContentLoaded architecture. Updated Jinja, JavaScript/Python test fixtures, README and status documentation to the new paths; moved static references use the `frontend-c1` cache token.
- Updated the two moved stylesheets' parchment URL from a root-relative-file assumption to `../../images/backgrounds/parchment.png`. No other CSS, JavaScript behavior or asset contents changed.
- Retained `static/narration.js` at its compatibility-sensitive historical path and retained the obsolete-but-unapproved `static/profile-editing.js` in place.
- JavaScript syntax checks passed for every production script. Static reference checking found only the pre-existing missing `images/buttons/gallery-back.png`; its other reported item is the expected runtime-composed `munge-teat-${index}.png` path.
- Local HTTP verification returned 200 for both moved stylesheets, representative shared/Creation/Gallery JavaScript, and the Gallery page. The rendered Gallery shell references the new shared and Gallery CSS and shared navigation URL.
- Full Node validation: 63 passed / 19 failed, exactly matching Batch B. Full Python validation: 280 passed / 11 failed / 105 subtests, exactly matching Batch B. No new failures.
- No provider call, production database access, generated-media mutation, deletion, push or merge. Batch C remains uncommitted for review.

## Repository reorganisation Batch B — 2026-10-08

- Moved 14 active images without changing bytes: parchment background, six source-udder files and seven MUNGE assembly files.
- Moved all 31 packaged static audio files without changing bytes: seven voices and 24 UI/MUNGE/source-udder effects. There are no packaged application music assets, so no empty `music/` folder was added.
- Updated Jinja, JavaScript, CSS and directly affected path assertions. Cache tokens for changed CSS/JavaScript references now use `static-assets-b1`.
- Preserved `/static/image-stub.svg` because the URL is stored in rewrite state. Gallery buttons already live in `images/buttons/` and remain there.
- Left all obsolete/reference artwork in its original location. The known missing `images/buttons/gallery-back.png` remains unresolved by design; no replacement was generated.
- Static reference audit checked 61 literal/dynamic references. The only missing reference is the pre-existing Gallery BACK asset.
- Local NewsMuncher HTTP verification returned 200 for parchment, source udder, MUNGE, voice, UI effect, both effect pools and the preserved image-stub URL.
- Focused Node selection: 20 passed / 17 failed, exactly matching `50d0e45`. Focused Python selection: 39 passed / 7 failed / 6 subtests, exactly matching `50d0e45`. Failures are the documented stale baseline assertions; no new failures.
- JavaScript syntax checks and `git diff --check` passed. No provider call, production database access, generated-media mutation, deletion, commit, push or merge.

## Repository reorganisation Batch A — 2026-10-07

- Complete 224-file old-path → proposed-path map saved in `docs/repository-reorganisation-plan.md` with MOVE, KEEP, REVIEW and OBSOLETE classifications.
- Proposed structure keeps runtime/generated data paths fixed, retains active `jingle_service` contracts at top level and defers public static URL, Python import and test-tree changes to separately reviewed batches.
- Documentation moved with `git mv`:
  - `JINGLE_IMPLEMENTATION_STATUS.md` → `docs/status/jingle-implementation.md`
  - `PROMOTION_GALLERY_STATUS.md` → `docs/status/promotion-gallery.md`
  - `VIDEO_ANIMATION_STATUS.md` → `docs/status/video-animation.md`
  - `WORD_SHUFFLE_STATUS.md` → `docs/status/word-shuffle.md`
  - `scripts/video_smoke_test.md` → `docs/diagnostics/video-smoke-test.md`
- Updated only documentation references, the smoke-test module docstring and README structure listing. Script module paths and behavior are unchanged.
- Maintenance/diagnostic script moves were deliberately deferred because their module paths are referenced by tests, documentation and operational commands.
- Targeted offline validation: `tests/test_video_smoke_test.py` 29/29 passed; `scripts/diagnostics/video_smoke_test.py` compiles; no stale old documentation references remain outside the historical mapping/audit record.
- No new failure, provider call, production database access, generated-media mutation, deletion, commit, push or merge.

## Pre-cleanup audit — 2026-10-07

### Checkpoint and inventory

- Created local-only checkpoint `309aa54` (`checkpoint pre-cleanup application state`) on `feature/video-animation`: 39 files changed, 2,047 insertions and 129 deletions. It has not been pushed or merged; `main` was untouched.
- Credential-like values, `.env`, generated creation media, caches, virtual environments and ignored runtime artifacts were excluded.
- Inventory: 224 tracked files (~52.1 MiB); 78 Python files repository-wide (35 under `newsmuncher/`), 31 JavaScript files (15 production static scripts), 2 CSS files, 6 templates and 41 tests.
- Static media: 34 tracked files under `newsmuncher/static/images/` and 31 under `newsmuncher/static/audio/`.
- Ignored local environments/caches include `.venv` (~263 MiB), `.venv-modal` (~60 MiB), `.pytest_cache`, bytecode caches and temporary data.

### A — definitely unused / low-risk candidates

- Fourteen unreferenced raster source/reference assets (~18.43 MiB):
  - `newsmuncher/static/images/Furry Cow-Spot Button Sprite Sheet.png`
  - `newsmuncher/static/images/Whimsical Fur-Button Gallery Interface.png`
  - `newsmuncher/static/images/buttons/Furry Cow-Print Button States Spec.png`
  - `newsmuncher/static/images/munge button/Furry Cow Udder Button Asset Sheet.png`
  - `newsmuncher/static/images/udder/cow-body.png`, `full-udder.png`, `master_udder.png`, `udder-body.png`, `udder-source.png`
  - `newsmuncher/static/images/udder/teat-1.png` through `teat-5.png`
- `newsmuncher/static/profile-editing.js`: no template loads it; tests explicitly assert the retired controller is absent from Creation.
- Unused imports: `Response` in `api/pets.py`; `Body` in `api/previews.py`; `clean_data` in `jobs/fetch_people.py`; `os` in `jobs/fetch_poem.py` and `jobs/fetch_wikipedia.py`; `json` in `jobs/process_data.py`; `Path` in `scripts/diagnostics/benchmark_jingle.py`; `math` and `Path` in `scripts/maintenance/clean_word_banks.py`.

### B — probably unused or superseded; verify before removal

- `newsmuncher/endpoints.py`: unreferenced endpoint constants, apparently superseded by current route construction.
- `utils/file_handler.py`: `load_json()` and `save_json()` have no call sites; active `load_prompt()` must remain.
- `utils/clean_data.py:process_batch()` has no call sites.
- `services/video_prompt.py:build_motion_prompt()` is test-only; production uses `build_transition_prompt()`.
- Hidden `#loader.page-loader` remains in `pet_profile.html` but is forced to `display:none`; current loading feedback is MUNGE. The separate active image-loader and shared `.loader`/`l9` CSS must remain.
- Likely retired `base.css` selectors include `#titleDescBox`, `.info-textarea`, `.result-heading`, `#crazyExtractBox`, `.confirmation-message` and possibly `.vibrate`; verify each at runtime. `.speech-bubble` and `@keyframes l9` are active.
- `modal==1.5.5` is outside the active app path and could move from main requirements to the existing `jingle_service` development requirements after verification.
- MUNGE and udder `suspense.wav` files are byte-identical but both URL roots are active; consolidation requires deliberate reference changes, so neither is directly deletable.

### C — historical compatibility / recovery material

- Narration API/service and `static/narration.js`: generation is retired, but backend read/status/resolve/audio paths preserve historical media and mutation endpoints deliberately return `410`.
- `jingle_service/`, Modal/ACE-Step comparison/recovery scripts and `.venv-modal`: inactive in the ElevenLabs production path but documented historical/diagnostic tooling.
- Persisted creations and all ignored generated images, end images, videos, ping-pong derivatives, jingles and narration.
- Tracked seed data, avatars, word-bank CSVs and claim/accounting data.

### D — active runtime paths/assets

- Creation, Gallery, deletion, Enhance/completion, image/end-image, WaveSpeed video, ping-pong derivation and ElevenLabs jingle code.
- Source udder: `udder-master-body.png` plus dynamically selected `udder-teat-1.png` through `udder-teat-5.png`.
- MUNGE: `munge-body.png` plus dynamically selected `munge-teat-1.png` through `munge-teat-6.png`.
- Current furry navigation/Gallery button images, all 31 tracked audio files, loading-image shuffle audio and hover/click sound pools.
- Active dependencies: FastAPI, Uvicorn, Pydantic, Jinja2, python-multipart, requests, python-dotenv, certifi, PyMongo, Motor, Passlib/bcrypt, OpenAI and spaCy.

### E — uncertain / owner decision or correction needed

- `pet_profile.html` references `static/images/buttons/gallery-back.png`, but the file is not tracked. BACK appears only with history, making this a latent missing-asset defect rather than unused code.
- Static cache tokens are ad hoc across templates; consolidation can affect browser caching and should be separate.
- `.venv-modal` is ignored but ~60 MiB; retention for recovery/diagnostics is an owner decision.

### Offline baseline

- Python: 280 passed, 11 failed, 105 subtests passed, 12 warnings in 4.75 seconds.
- Frontend Node: 63 passed, 19 failed, 0 skipped (82 total).
- Provider keys were blank and MongoDB targeted an unavailable local port. No OpenAI, WaveSpeed, ElevenLabs, Modal or other provider calls occurred.
- Failures were not changed. Most are stale expectations after approved behavior changes: old rewrite model, new teat DOM/canvas, image-only Gallery navigation, two-play jingles, Gallery Enhance imports, versioned video URLs, ping-pong sidecars and current completion/end-image states. Some frontend mocks lack newly used browser/DOM state. Warnings cover Starlette/httpx and `datetime.utcnow()` deprecations.

### Proposed order — requires approval

1. Update stale offline tests and repair/resolve the missing Gallery BACK asset reference so current approved behavior has a trustworthy baseline.
2. Remove only A-class dead imports, retired controller and confirmed unreferenced artwork in coherent, separately validated batches.
3. Verify and remove B-class functions/selectors subsystem by subsystem, preserving shared active CSS/helpers.
4. Separate legacy Modal tooling dependencies from active application dependencies without deleting recovery tooling.
5. Review narration and legacy jingle compatibility boundaries with Andy before structural removal.
6. Handle cache-token and duplicate-asset consolidation as separate behavior-aware changes.

## Creator headline and versioned-jingle checkpoint — 2026-10-05

New rewrites retain the AI-written headline instead of replacing it with the first six
description words. Both existing rewrite passes request a grammatical, singable 12–18
word headline and local validation applies only the hard 18-word cap; it never derives
a fallback from the body.

ElevenLabs Music uses only that persisted title under the `[Jingle]` composition section.
Current claims and MP3 filenames carry `elevenlabs-music_v2_5-title-v2`, so legacy or
earlier-version audio cannot suppress one current generation while duplicate current
requests remain idempotent. Historical files and claims remain intact. Read-only loading
image and Gallery lookup accepts legacy, earlier fingerprinted and current saved audio;
missing audio is silent and cannot block Gallery content.

Video end frames now select a random style independently of the start image while
preserving scene/character/action continuity. Focused validation: frontend 47/47;
Python 142 passed plus 6 subtests. No provider calls or generated media.

## ElevenLabs response-title input verification — 2026-10-05

The deterministic jingle plan reads only persisted `crazyReplacement1Title` and passes it unchanged as `brief.lyrics`, which becomes the ElevenLabs composition chunk text. `crazyReplacement1Extract` (the response description/body) is excluded. A focused regression fixture now contains a distinctive body marker and proves it cannot enter the serialized music plan. Focused mocked tests: 51 passed. No provider call.

## Creator audio handoff and frame continuity — 2026-10-05

Explicit EMBELLISH playback now waits until the generated image has actually loaded and the image-shuffle/loading audio has been stopped. A ready or slightly-late ElevenLabs jingle then starts from 0:00. The Creation video reports its first genuine `playing` event once per player; during the same explicit EMBELLISH session that event stops, resets and restarts the already-saved jingle. Restore remains silent because it never arms EMBELLISH playback, and autoplay failures retain the manual PLAY JINGLE control. No additional jingle request is made.

Animation claims now require the start image's persisted `image_style`, copy that exact value to `shared_visual_style` and `end_frame.image_style`, and build both prompts with it. Historical images without style metadata fail before a paid claim. The referenced end-frame prompt now advances action while preserving characters, objects, setting, camera, palette, lighting and artistic treatment instead of replacing the scene. Redo's existing fresh-style choice is unchanged and its newly persisted style feeds the subsequent pair.

Full validation: Node 82/82; Python 289 passed plus 105 subtests. No provider calls or generated media.

## ElevenLabs Music migration — 2026-10-05

New jingles now use one server-side ElevenLabs Music `music_v2_5` composition-plan request. The saved hidden title is passed unchanged as the lyric; deterministic positive/negative styles combine the existing random genre with immediate intelligible vocals and a clean ten-second comedy-jingle shape. The durable pre-submission claim, daily cap, duplicate protection and ambiguous-outcome no-retry rule remain in place.

New titles target 12–18 words and are locally hard-capped at 18. Creator/EMBELLISH/Viewing now use the WaveSpeed video plus jingle only. New narration POST/replace routes return 410, while historical narration data/files and authenticated playback remain intact. Gallery omits historical narration from its payload and audio sequence. WaveSpeed code was not changed. Legacy Modal/ACE-Step tools remain as inactive historical/diagnostic source; the production path and `.env.example` now require only `ELEVENLABS_API_KEY` for jingles.

Full validation: Node 81/81; Python 288 passed plus 105 subtests. `ELEVENLABS_API_KEY` was absent. No OpenAI, ElevenLabs, WaveSpeed, Modal, Mongo or other provider call occurred.

## MUNGE edge placement tuning — 2026-10-02

Pulled every teat toward its socket using only the existing centralized coordinates:
upper-left 29.5/20 to 32/23; upper-right 70.5/20 to 68/23; left 23/42 to
26/42; right 77/42 to 74/42; lower-left 35/63 to 37/60; lower-right 65/63
to 63/60. Artwork, roots, rotations, axes, hit areas, animation and sound are unchanged.

The large blank parchment area came from the full MUNGE control participating in
normal flow. Its wrapper is now absolutely anchored to the parchment artwork's actual
bottom edge (`bottom: -paper-edge`) and translated vertically by 50%, placing its
centreline on that edge without clipping. A positive responsive `profile-container`
bottom margin reserves 145–172px for the protruding half; width is unchanged and no
negative margin is used. Focused frontend 20/20 and full frontend 87/87 passed. No
provider calls, deployment, main changes, or functionality changes.

## Six-teat furry MUNGE control — 2026-10-02

Replaced the rectangular MUNGE IT button with the supplied raster body and six
transparent teat crops. The stationary branded body and six native buttons are
assembled as separate layers. Each teat's socket position, size, attachment
translation, radial movement axis, root pivot and base rotation live together in the
template configuration for straightforward visual tuning. Furry collars render above
the body and overlap its sockets; the original artwork is not redrawn or distorted.

`MungeControl` applies the proven pointer-track, spring, wobble and squeeze approach
independently along each teat's configured radial axis. Touch does not synthesize
hover and reduced motion disables deformation without disabling native clicks. Every
teat is bound directly to `confirmData`, so all six invoke the existing text-only
MUNGE workflow exactly once. Sound binding loads first, preserving one suspense cue
before the shared action without duplicating its business logic.

The existing `UdderSounds` helper now owns two independent sets: five top-udder teats
and six MUNGE teats. Both draw unique assignments from the same Mixkit pool, create a
fresh Audio object on each non-touch pointer entry, allow overlap and clean finished,
errored or rejected instances. A MUNGE teat click plays suspense once and reshuffles
only its six-sound set; initial load is silent. The five-teat artwork, physics, liquid,
actions and sound behavior are unchanged.

Files include the supplied source sheet plus extracted `munge-body.png` and
`munge-teat-1.png` through `munge-teat-6.png`, template/CSS, `munge-control.js`, shared
sound initialization and focused tests. Full frontend: 87/87. Relevant Python:
21 passed. No external/provider calls, deployment, or main changes.

## Hide generated titles from presentation — 2026-10-02

Creator retains `responseTitleDraft` as a hidden value populated on generation and
restore, so nomination updates, narration and jingles still receive the generated
title. Its body now occupies the freed response space with a responsive 10–16px top
inset. Viewing removes the generated-title heading and renders the body as its primary
copy while the gallery API continues returning `title`. The audit found no other
active generated-title presentation; internal audio, video and persistence consumers
remain unchanged. Udder visuals, physics, liquid and sound code were untouched.

## Hide source titles from presentation — 2026-10-02

The remaining Creator heading was `sourceTitleDraft`, populated by `populateTempData`
from the reusable/source response's `title` and `description`. The previous change hid
only `responseTitleDraft`, so source headings such as “DEAD FUNNY - 1994 AMERICAN
FILM” remained visible. `sourceTitleDraft` is now a hidden input, retaining the exact
value used by MUNGE IT while only `sourceBodyDraft` is presented. Responsive top
spacing derives from the existing desktop/mobile udder height clamps and clears the
lower teat footprint without retaining the former headline-sized gap.

Viewing remains body-only: no gallery title element or title DOM assignment exists,
while its API still returns title metadata. Generated and source titles remain in
requests, persistence and restore paths; the generated six-word title continues to
seed jingles. Regression coverage runs the real source loader with the distinctive
source heading and confirms it enters hidden metadata while the body remains visible.
Full offline suites pass: frontend 83/83; Python 295 plus 105 subtests. No providers,
deployment, main changes, or udder behavior changes.

## Polyphonic udder sounds — 2026-10-02

The Creator now assigns five unique transient Mixkit sounds from one centralized
browser pool. Desktop pointer entry creates a fresh independent `Audio` instance;
finished, errored and rejected instances release their references. Teat clicks play
`suspense.wav` and reshuffle all assignments without affecting the existing action,
physics or liquid handlers. MUNGE IT also plays suspense. Touch receives no synthetic
hover, initial load is silent, and these effects do not interact with application
narration, jingles, loading audio, gallery audio or video.

## Composition-preserving end frame — 2026-10-02

The installed OpenAI SDK supports `gpt-image-1.5` reference editing. New video claims
persist a deterministic five-region transformation map. Their worker generates the
end frame sequentially with the saved start PNG through `images.edit` and
`input_fidelity=high`, asking the model to preserve camera geometry and spatial masses
while replacing their reality. Providers without reference editing retain a prompt-only
fallback containing matching spatial instructions. WaveSpeed start/end assignment,
durable claims, failure handling and legacy video claims remain unchanged.

## Shared visual style for two-frame video — 2026-10-02

Video claims now reuse the start image's one persisted `image_style` as
`shared_visual_style`; no second style draw occurs. The independent end-frame prompt
receives that exact value, while retaining its instruction to change subjects,
objects, setting, camera and composition. The transition prompt names the shared
visual world and asks WaveSpeed to preserve its medium, light, colour, era and
texture throughout a physical surreal morph. Legacy images without style metadata
remain supported without regeneration or invented metadata.

## Outer teat coordinate fine-tuning — 2026-10-02

Teat 1 now has a -12px Y resting offset. Teat 5 has -12px X and -12px Y
resting offsets. These offsets adjust the absolute button coordinates, including hit
areas and liquid-tip measurements, while leaving the animated child transform intact.

## Independent video end-frame experiment — 2026-10-01

New animation claims keep the existing generated still as the first frame and durably
claim a second OpenAI `gpt-image-1.5` image with an independent scene prompt and image
identity. The worker retains that end-frame metadata under the video claim, uploads
both PNGs, and submits them to WaveSpeed Wan 2.2 I2V 480p Ultra Fast as `image` and
`last_image`. Its motion prompt asks for a continuous surreal transformation rather
than a cut. End-image failure preserves the first image and prevents video submission;
legacy claims without end-frame metadata retain the single-image provider path.

## Progressive Creator follow-up — 2026-10-01

Removed the retired EDIT-tab parchment pseudo-elements and renamed MUNGE to MUNGE IT.
Every source choice now immediately invalidates the old rewrite callbacks, stops its
media/loading controllers, clears the stored rewrite selector and hides/empties the
complete lower result. A successful MUNGE IT reveals only the new editable result.
NOMINATE remains hidden permanently after its successful action.

RE-EMBELLISH first persists the current title/body through the existing in-place
nomination update. Narration status compares its durable generation snapshot with that
persisted Mongo entry. Unchanged text reuses narration; changed text explicitly
archives the old narration claim and file and creates one new guarded claim. Image,
video and jingle replacement behavior and nomination identity remain unchanged.

The flipping loader now ends as soon as the generated still has preloaded and the
still is revealed. Video generation continues from that image and replaces it through
the existing in-place player when ready. Narration and jingle expose their own status
and controls independently. Whichever audio becomes ready first may autoplay; one
shared arbitration flag prevents the later asset overlapping it. Manual PLAY/STOP
remains unchanged. Full offline suites pass; no provider calls or deployment.

## Simplified Creator flow — 2026-10-01

Source and munged text are directly editable without EDIT/SAVE/CANCEL. MUNGE is
text-only. NOMINATE persists the current edited result, starts image, narration and
jingle generation, then starts animation only after the image succeeds. The shared
loading presentation remains until video, narration and jingle are saved or terminal;
the completed image/video is then revealed and narration precedes jingle playback.
Manual animation, image-mode, REDO IMAGE and persistent NOMINATED controls are removed.

RE-EMBELLISH keeps the nomination/rewrite identity and narration. It creates a
durably claimed replacement image first, then retires the old video and jingle and
creates fresh claims for their replacements. Existing image/video/jingle evidence is
kept in state history where applicable, ambiguous attempts cannot auto-retry, and
legacy jingle request identities remain compatible. REVIEW/CODEX.

## Safe image recovery, six-word titles and explicit audio intent — 2026-09-30

Initial images may make one automatic recovery submission only after the provider
positively returns without a usable image. The first failed attempt and second claim
are durable before retry. The retry uses a new image UUID and retains the chosen style,
prompt and rewrite association. Timeouts, network/provider ambiguity, invalid local
files and write/metadata failures never auto-retry. A second definite failure stops;
REDO IMAGE is then available, including after restore and when no image was published.
Its press is the user's explicit paid decision. The existing loading/photo shuffle
spans the server-side retry and never exposes an empty panel while the request runs.

The copy-edit prompt and local grounded validation now enforce at most six title words.
Extractive fallback also stops at six; historical stored titles and the two-call text
flow are untouched, and no model call was added.

Creator jingle discovery, restore and generation completion are silent. EMBELLISH is
the explicit intent that generates/reuses media, waits for readiness, plays narration
first, then starts the jingle only after narration ends naturally. Missing narration
falls through to jingle; missing jingle leaves narration intact. Revision guards and
timer cancellation prevent old completion callbacks starting audio after a rewrite.
Manual PLAY controls remain and still enforce exclusive audio. Gallery sequencing is
unchanged. The shell/backdrop/EDIT/top-spacing work from ec9ebcd remains intact.

Full mocked/offline suites pass. No live provider/API call, deployment, main change,
historical migration or generation-cost/prompt-setting change beyond the requested
six-word title instruction and one strictly classified image recovery was made.

## Gallery entry backdrops and exact edit return — 2026-09-30

Creator and Viewing now share a centered 960px shell and normal top page inset; the
old viewport-height Creator lead-in was removed at its parent rather than offsetting
individual controls. Existing animation rendering already hid ANIMATE IMAGE for both
newly ready and restored videos; that paid/idempotent state remains unchanged and is
covered explicitly.

Viewing receives the selected nomination's persisted rewrite ID. EDIT combines that
ID with the existing session-derived Creator URL; Creator reads the query selector
and restores through the existing owner-checked GET endpoint, with session restore as
fallback. This performs no generation or media mutation.

GalleryBackdrop is independent from foreground video/audio. Each entry first installs
its still as a full-viewport cover image, then mounts at most one existing saved video
as muted/inline/looping atmosphere. It reveals only after playback starts. Page turns,
exit and replacement pause, unload and remove the prior player; generation guards
reject stale callbacks. Autoplay/load failure and reduced motion retain the still.
Parchment content remains above a light paper wash. Gallery selection, counts,
promotion, foreground media sequencing and providers are unchanged. REVIEW/CODEX.

## Unified Creator and Viewing presentation — 2026-09-29

Creator now leads with a centred, wrapping CREATOR / VIEWING mode control above the
centred source row; its navigation action says VIEW GALLERY. The artwork lead-in was
halved on desktop and narrow/short screens without changing the parchment/image cards.

Viewing uses the same compact mode control and the existing session-derived Creator
URL, preserving the active pet. Removed the separate masthead/footer, back button,
collection label, large Promotion Gallery heading, tagline and their whitespace.
The nominated creation now follows the mode control directly in a 960px parchment
layout with Creator typography and parchment buttons, without lime styling.

All gallery IDs, selection/promotion controls, page-turn logic and media JS are
unchanged. Focused tests cover labels, active modes, URLs, obsolete chrome removal,
centering/wrapping and gallery behavior; full frontend suite passes. No live calls,
deployment, backend logic or completed video work changed. REVIEW/CODEX.

## Creation Page consolidated media UI — 2026-09-29

Completed the intentional inherited WIP after commit 750d36e; provider/backend video
generation and its completed 8-second action work were not changed. creation-meta.js
loads before video/narration/jingle controllers and owns the single dynamic line under
the image: IMAGE STYLE, MUSIC GENRE and VOICE. Missing values and separators disappear;
rewrite changes reset all three. Hidden duplicate style/genre elements were removed.

REDO IMAGE, NOMINATE/NOMINATED, EMBELLISH/EMBELLISHED, jingle, narration and animation
actions now live in one centred flex-wrap row. Direct-button visibility mirrors the
existing nomination/media controller state even though legacy lifecycle wrappers are
empty and hidden. Hidden actions consume no space. A scoped CSS override removes the
old absolute NOMINATE placement inside this row while retaining its existing state,
event and parchment styling.

Normal completed-state prose is suppressed: no ANIMATION READY, aggregate media-ready
list, duplicated STYLE/GENRE/VOICE, or saved-media status copy. Operational progress,
text-change warnings and genuine errors remain. EMBELLISH reports component failures
only; its button conveys working/completed state. Focused layout/controller tests cover
dynamic metadata/separators, script ordering, row membership, centring/wrapping, hidden
gaps, nomination gating, restore and media state. No live calls or deployment.

## Loading-shuffle audio collage — 2026-09-29

loading_images now returns image_url plus optional jingle_url for each sampled image.
Owner-scoped rewrite state supplies the nomination entry_id; Jingles.saved_url reads
that ID in the existing jingle SQLite DB using mode=ro and validates the saved MP3.
Missing, incomplete, retired or unavailable jingles produce null. No Mongo sync,
provider call, generation, new metadata store or mutation during retrieval.

Independent LoadingAudio owns ephemeral Audio instances; it never alters normal
jingle, narration, EMBELLISH or gallery player state. Each musical selection seeks
LOADING_JINGLE_OFFSET_SECONDS=2 after metadata/canplay; duration <=2 starts at zero.
A failed early seek can wait for canplay, with one play attempt per selection. Four
25ms volume steps give a 100ms fade-out/fade-in; retired players unload promptly.
Musicless selections retain already-playing music but cancel pending old starts.
Repeated same-track selections restart at offset without duplicate event playback.
Revision guards reject stale events/promises, and stop clears every ramp/player.

Both full stop and frozen-visual completion immediately stop audio. Existing initial
image/Redo success/failure, rewrite changes and pagehide paths reuse that cleanup.
Any play rejection silences the remainder of the session; another explicit loading
session resets this flag. Reduced motion disables temporary audio, including when
the preference changes during loading. Visual loading never depends on playback.

Tests cover saved nomination association, ownership, null/retired media and read-only
lookup; seek/short tracks, no-music continuation, switching/repeats, fades, stale
loads/promises, cleanup, blocked autoplay and reduced motion. Full offline suites pass.
README updated. No live APIs/providers, media generation, deployment or main changes.

## Embellish and loading UX — 2026-09-29

EMBELLISH appears only for persisted nominations and runs only on explicit press.
New coordinator calls existing controllers' ensure adapters with allSettled isolation;
adapters await restore then reuse ready media, attach to in-progress state or invoke
the existing guarded action. Rapid duplicate presses are ignored; individual controls
remain. Component statuses are independent, aggregate state polls read-only controller
snapshots and cancels on rewrite/page changes. No new generation API or paid claims.
Nomination success alert removed; normal state/controls update remains.

Narration has PLAY NARRATION on the existing styled button, voice label and hidden
audio without controls/timeline. Playback never generates and narration never autoplays.
Playing either narration or jingle pauses the other; jingle ready autoplay/fallback
remains. Redo Image is centered below the image with style nearby.

Audited generic spinners: only pet_profile.html's page spinner/styles.css spinner
existed. Replaced it with shared loader class/l9 CSS and reused that indicator in the
image pane. Informational status text and legitimate media controls remain intact.

ImageShuffle uses GET /temp/loading_images: up to five unique valid local UUID PNGs
from current, non-discarded rewrite records owned by active_pet. No Mongo/provider
calls, arbitrary paths, symlinks, metadata writes or cross-owner images. Empty history
uses loader alone. 500ms Fisher-Yates bags loop without consecutive repeats; clipped
absolute card transitions knock/swivel images without changing pane size. Reduced
motion shows one static image and stops animated loader CSS. Timers stop as soon as
the generation response arrives; frozen loading visuals bridge real-image preload,
then are removed on load. Failure/rewrite/pagehide removes visuals and cancels timers.
Initial image generation and Redo share this path; temporary URLs never enter saved
metadata. Existing paid idempotency, ambiguous-attempt protection and model settings
unchanged. README updated; no live calls, deployment or main changes.

## Creation media UX and guarded Redo Image — 2026-09-29

Titles now allow 20 words / 140 characters, with body-vocabulary validation and
extractive fallback; existing second-call flow unchanged. Genre label reads saved
jingle_prompt.genre_profile.label (SQLite brief or Mongo fallback); missing legacy
profiles remain unknown/hidden. Active jingle load/request attempts playback once
when ready; rejected autoplay leaves PLAY available, with no generation retry/loop.

Removed Creation/Gallery STOP ANIMATION buttons and their bindings/CSS; automatic
pause/unload/reduced-motion cleanup remains. Narration and video controls are hidden
before persisted nomination, restored from saved state, and revealed on successful
nomination only. Nominating never generates audio/video. Existing saved animation
can play without exposing pre-nomination controls. CSS explicitly honors hidden.

REDO IMAGE posts rewrite ID plus expected current image URL. Under the existing
SQLite transaction, enforce un-nominated/current image/no unresolved attempt, choose
a different random style and persist a unique image UUID + prompt/settings before
one provider call. Same body/title/identity/word claims remain. On success, atomically
publish new image metadata. Old PNGs and historical attempt evidence are retained.
The UI keeps the old still while loading, updates style on load and rejects stale
rewrite/image callbacks. Duplicate clicks/replayed URLs cannot resubmit payment.

Nomination cannot race a pending replacement; nomination_pending blocks replacement
in the opposite direction. An ambiguous failure retains old metadata and its claim;
GET restore recovers only an already-published PNG. Otherwise nomination/redo stay
blocked for operator review, never automatic paid retry. A late worker cannot
supersede a newer replacement recovered by GET. Gallery receives nominated final URL.
Video source lookup accepts the saved UUID image URL; historical video is detached
when an image changes, retaining its original paid claim/file and suppressing sync
and playback. No new animation is scheduled or paid claim reopened.

Tests cover limits, genre restore/legacy, playback rejection, nomination visibility,
internal stop lifecycle, double-click/concurrent paid claims, pending nomination,
metadata/file recovery, stale worker completion, video detachment and frontend swap.
Full offline suites pass with existing warnings only. README documents behavior.
No provider/API calls, deployment, media deletion or main changes.

## Canonical body and media seeds — 2026-09-29

Existing two calls retained: rewrite body, then copy-edit body and derive a summary
from that exact final body (extract precedes title in strict schema). Copy-edit input
excludes the preliminary title. Local final_title enforces 60 characters, at most
8 words and body vocabulary; invalid summaries or failed pass 2 use an ordered
excerpt of the accepted body. Short bodies may yield fewer than 3 words. Vocabulary
validation cannot prove semantic entailment; summarisation follows the prompt.
No additional text call. Claims run only after final title selection, unchanged
transaction/conflict semantics and no duplicate title/body counting.

Image prompt removes Scene title entirely, retaining body (existing 1200-character
bound), persisted style, palette and composition. Model/quality/size/claims unchanged.
Jingle brief now receives only saved title (200-character legacy bound); existing
lyric/genre/profile constraints and disabled narration reference remain. Narration
still speaks only body. No saved record migration or retroactive generation; gallery
and restoration continue to display saved content unchanged.

Tests cover accepted and fallback title flows, bounds/unrelated vocabulary rejection,
claims on actual final content, body-only styled images, title-only jingle payload,
existing genre/reference/narration/cache/restoration behavior. README updated.
No live API/provider calls, deployment or main changes.

## Persisted random image styles — 2026-09-29

IMAGE_STYLES in services/image_generation.py contains the exact 20-style pool.
Choose once inside the existing SQLite image claim transaction; save style and
prompt before the provider call. Successful image metadata carries image_style into
the rewrite, Mongo nomination and gallery payload. Recovery uses the saved attempt;
failed/uncertain attempts never reroll or retry. Existing images remain unchanged;
legacy missing styles are null, with no inferred style or regeneration.

Prompt remains scene-led with recognisable subjects, coherent composition and a
4–6 colour palette, followed by "Visual style: Cyberpunk." (example). Removed hard
photorealism-only restrictions that contradicted the requested styles. No additional
model request; generation settings and cost unchanged. Creation Page shows a subtle
style label after image load and on restore, clearing it when the rewrite changes.
Word claims, video prompts/generation, audio and gallery playback remain unchanged.

Mocked tests cover single selection, prompt, persistence/reopen, repeated viewing,
legacy metadata preservation, failed attempt retention, file recovery, nomination
storage, gallery serialization and frontend labels. Full offline Python and Node
suites passed; only existing deprecation warnings. README documents persistence.
No live API/provider calls, generated content, deployment or main changes.

## Repository hygiene — 2026-09-29

Audited source/config, Python/JS/template references, all tests/scripts, ignore rules
and image/narration/jingle/video handovers before deleting. Initial tree was clean on
feature/video-animation at 9f379f9. No app architecture or production path changes.

Removed 109 local files / 12,622,251 bytes: four smoke-test input PNG copies, four
comparison HTML pages, one experimental Wan MP4, four standalone TTS comparison MP3s,
85 project bytecode files, five pytest-cache files, five .DS_Store files, and the
unused tracked examples/index.html (obsolete /main/get_all; no app/test consumers).
Removed empty code/api, code/utils, code, root words, examples, data/tts-comparison,
nine project __pycache__ directories and the .pytest_cache tree. Ignored artifact
removals are local disk cleanup; the Git commit records the example deletion/docs/rules.

Retained production source incl. shared WaveSpeed client and Modal ACE-Step service;
resources, seeds, static assets, tests/inline fixtures, avatars, generated images,
jingles, narration and video; preview JSON and both durable SQLite databases; all
runtime directories/scaffolds and installed .venv/.venv-modal environments.
SHA-256 checks before/after cleanup and validation confirm 180 protected files unchanged.
No local model-weight/provider-cache/image-comparison directories were found.

Ambiguous/protective leftovers deliberately retained: all four video smoke-test
results.json records (three failed/uncertain); entire jingle-reference-comparison
A/B folder incl. MP3s/manifests/state/lock; benchmark attempt/auth diagnostics and
documented l4-approved proof. These preserve evidence/recovery and duplicate-spend
protection. All useful admin/reset/maintenance/diagnostic scripts remain; none run.

.gitignore consolidated by purpose; now ignores new avatar uploads, preview SQLite
files plus journals/WAL/SHM, and all root tmp output. Existing tracked avatar images,
seed JSON, source word banks and directory scaffolds remain tracked. README documents
production/runtime/test/experiment/cache/legacy classifications and retention rules.

Full tests use mocked providers and blocked socket/DNS/Node network entry points;
.env loading disabled. No-cache/no-bytecode flags prevent recreating removed caches.
Startup validation imports the real FastAPI app with Mongo constructors mocked and
builds OpenAPI without serving requests; admin scripts are parsed only, never imported.
Only existing dependency/datetime warnings. REVIEW/CODEX; commit/push authorized.

## Creation Page in-place animation — 2026-09-29

Removed separate native player. Existing still sets layout while an absolute overlay
preloads at opacity zero; canplay attempts muted/inline/loop playback, and playing
starts the 600ms opacity fade. No extra Play click. Existing image-load callback
notifies the controller so restored video cannot mount before the still is ready.
Gallery-style generation guards stop/unload media and reject stale readiness/play
callbacks. Reduced motion, blocked autoplay and decode errors retain the still;
STOP ANIMATION returns to the still without regeneration. Generation/status logic,
backend, gallery, audio and nomination logic unchanged. Frontend-only tests run.

## AnimationUI native timer fix — 2026-09-29

Creation Page video.js uses wrapper defaults for both setTimeout and clearTimeout.
Browser-style receiver mocks cover show/stop, repeated status-poll scheduling and
cancellation of stale polling after stop. Only video.js, its targeted tests and this
status file changed; eligibility, backend, providers, storage, gallery, styling and
narration/jingle behavior are unchanged. REVIEW/CODEX; commit/push authorized.

## GalleryVideo native timer fix

Both timer defaults now use wrappers, preserving the browser receiver for scheduling
and cancellation. Only gallery JS, targeted frontend regression tests and this status
file changed. Browser-style mocks independently reproduce both original failures.
No backend, generation, selection, promotion, audio-sequence or styling changes.

## Video animation milestones — 2026-09-28

Branch deliberately starts at experiment/video-smoke-test 7fbb648, reusing its proven
client; main and experiment branch remain unchanged. No unrelated dirty files.
- [x] M1 inspect + design
- [x] M2 shared WaveSpeed service, deterministic prompt, mocked tests
- [x] M3 rewrite state, explicit authenticated API, background task, duplicate guard
- [x] M4 compact Creation Page controls and status polling
- [x] M5 gallery still-to-video playback, cleanup and reduced motion
- [x] M6 regression, review and final handover

Design: existing RewriteStore SQLite transaction serializes one permanent video claim
per rewrite (including drafts). Store metadata on that row; mirror to the existing
Mongo nomination on completion/banking/status, never create a duplicate nomination.
Draft tombstones retain the claim. A durable worker_started flag permits one execution only;
no expiration authorizes re-generation. BackgroundTasks runs synchronous provider work
after the response; crash/timeout stays uncertain, with no worker or user retry.
Generation requires a validated existing login session and same-origin custom header.
Read-only status/playback never schedules work. Key read from environment only.
Source is the existing UUID PNG, no copied image. Output: ignored data/generated_video/
<rewrite UUID>.mp4; authenticated routes only. Persist prompt, seed, model, duration,
source hash, timestamps, job ID and sanitized stages; normal users see safe status only.
Prompt: fixed preservation constraints plus at most two deterministic actions matched
from rewritten text, no extra paid text call. Reuse ticket -> PUT -> submit -> poll ->
download from the experiment via a shared module, keeping CLI safeguards/tests.
Creation Page enables ANIMATE IMAGE for available images, never on view/restore.
Gallery starts from the still, delays muted inline looping video, fades only once it
plays, and cancels old timers/media on NEXT/pagehide. Reduced motion keeps the still.
Existing gallery audio sequence remains independent and unchanged.
Durability limitation: SQLite/media must remain on shared durable storage across app
workers; interrupted background jobs need operator review, not automatic resubmission.

## Promotion Gallery milestone plan — 2026-09-22

OWNER: CODEX. Branch feature/promotion-gallery, based on 903f5d1.
- [x] M1 Discovery and design (planning checkpoint)
- [x] M2 Data/backend, private access, targeted tests
- [x] M3 Gallery page/navigation/text/images/promotion
- [x] M4 Media lifecycle and race tests
- [x] M5 Responsive flip-book polish and fallbacks
- [x] M6 Regression, complete diff review, REVIEW checkpoint

Discovery: pet_profile.html is served by api/pets.py. api/previews.py banks drafts
via /create/ into funny_json_db.entries. Mongo _id is permanent nomination identity;
rewritten fields are crazyReplacement1Title/Extract. Explicit nominated=False must
stay excluded; legacy missing nominated uses crazyReplacement1done as in moderation.py.
Existing gallery_status pending/approved/rejected is a separate unused moderation
concept, preserved. Add promoted/promoted_at and promotion_gallery_seen_count to the
same entries lazily, no backfill and no duplicate creation model. All pets' nominations
participate, including promoted items. Gallery is review/retrieval only.

Rotation: random among minimum valid seen counts. Selection does not increment;
after DOM display, acknowledge a short-lived view receipt. A Mongo transaction marks
the receipt consumed and increments the entry once, making retries idempotent.
Transient promotion_gallery_views receipts expire (TTL index); no source usage changes.
Frontend serializes display acknowledgements before selecting again and rejects stale
selection/media callbacks. Multi-viewer in-flight selections may coincide; committed
counts guide subsequent selections. Newly nominated items start at zero.

Private access: existing active_pet cookie is unsigned. Issue an opaque, hashed,
24-hour server session on successful login/adoption; validate it plus the adopted pet
for gallery APIs/page/media. Existing users sign in once again. Session records expire;
no global auth redesign. POSTs require a same-origin browser header check.

Assets: existing image_url points to local UUID PNG; narration uses nomination-ID
MP3 plus narration metadata; jingle uses nomination-ID MP3 and Mongo metadata or
SQLite sidecar. Resolve local files read-only without importing generation services.
Authenticated gallery media routes reuse the same files (no copies), allowing all
nominated items to play while existing owner-specific narration routes stay unchanged.
Missing/legacy/unsafe assets degrade to text. No generation endpoints in gallery JS.

UI: separate template/CSS/JS, one creation, NEXT/PROMOTE and return navigation.
DOM textContent for stored text. A modest page-turn animation, reduced-motion override,
responsive parchment presentation. Jingle plays before narration; page turn
immediately pauses/unloads both and invalidates pending starts. Explicit PLAY AUDIO
fallback when autoplay is blocked. No public gallery/social/editor/generation controls.

Tests: fake Mongo transactions/files/HTTP, JS deferred promises and fake media; run
existing nomination/image/narration/jingle/source/profile regression tests at M6.
Antigravity optional; skip unless a safe read-only invocation is readily available.

## Image style wording refinement

Ultra-photorealistic editorial surrealism replaces the flat/cartoon direction in the
image prompt only: believable figures/materials, cinematic lighting, connected scenes,
absurd humour and 4–6 dominant colours. Flat style retained as PREVIOUS_IMAGE_STYLE;
original graffiti/zine wording retained as ORIGINAL_IMAGE_STYLE, both reference-only.
Image settings, rewritten scene inputs and lifecycle unchanged.
VALIDATION: Scoped CSS values match the existing ingredient input; BUILD page checks and diff checks pass. No generation changes.
No real images or external calls. Changes intentionally uncommitted/unpushed for review.


## Temporary TTS comparison harness — 2026-09-15

Standalone scripts/diagnostics/compare_tts.py only; no app integration. Curated editable voice
pools, one random voice/sample per selected provider, identical fixed sample text.
OpenAI SDK plus existing requests HTTP for ElevenLabs/Cartesia; no new dependencies.
Environment/root .env keys: OPENAI_API_KEY, ELEVENLABS_API_KEY, CARTESIA_API_KEY.
Missing keys skip safely; --dry-run writes nothing and calls no provider. No retries.
Unique MP3 files go to ignored data/tts-comparison/. No generated audio committed.
Run from root using .venv/bin/python -m scripts.diagnostics.compare_tts --provider all --dry-run.
For one live sample, replace all with openai/elevenlabs/cartesia and omit --dry-run.
Each provider requires an API-enabled account, usable quota/credit and access to the
configured voice IDs. Account/voice availability has not been tested live.
VALIDATION: Scoped CSS values match the existing ingredient input; BUILD page checks and diff checks pass. No generation changes.
STATUS: REVIEW / CODEX; user authorized committing and pushing this harness.
Earlier image-style changes are already committed; older uncommitted wording above
is historical. No unrelated files changed in this harness task.


## On-demand saved-item narration — 2026-09-15

Shared provider: newsmuncher/services/openai_tts.py (gpt-4o-mini-tts, Cedar/Marin/Coral,
random.choice, MP3, 60-second timeout, zero SDK retries). Comparison CLI still uses it.
Only the READ ALOUD click sends POST /narrations/{entry_id}. JSON contains current
visible response title/body, including open edit drafts, never original source text.
Title punctuation/newline separation only; no additional text-model call.
Nominate first; draft READ ALOUD stays disabled. After success PLAY and audio controls
reuse backend audio. Saved narrations selector discovers existing audio with no
sessionStorage requirement and never replaces the displayed rewrite. Late responses
are guarded by UI revision. Generation never blocks SHIZZALISE/images/jingles.

Mongo entries gain an optional narration object on the first explicit request:
entry_id, status, voice, voice_name, model, provider, snapshot (title/body), storage_key,
url, requested_at, generated_at on completion/recovery. No migration/backfill or live
DB operations performed during development. Exact Mongo _id is the stable identity;
rewrite lookup rejects legacy duplicate matches. Existing pet ownership checks apply.
Atomic update conditional on absent narration, acknowledged with majority write concern,
claims once across workers. A failure/uncertain response leaves the durable claim and
never retries synthesis. Missing keys/invalid text fail before claiming. Claims are
not expiring locks. Operators must investigate failed/interrupted claims; there is
intentionally no regenerate/reset UI or automatic retry.

Files: data/generated_narration/<entry_id>.mp3, ignored; temporary .part files atomically
published. GET status repairs completion metadata from owned files without synthesis.
Authenticated GET /narrations/{entry_id}/audio uses FileResponse (200/206/416 tested).
Mongo metadata and files both need durable backups; multiple hosts must share this
filesystem. Lost files remain unavailable rather than causing another paid call.
Deletion during generation is checked before file publication/metadata completion.
Existing files after later entry deletion are inaccessible through the authenticated
endpoint but may remain on disk for operator cleanup; no unrelated deletion refactor.
Narration snapshot is immutable; later nomination edits report text_changed and do not
regenerate. UI can narrate unsaved response edits without altering the nomination.
Input limited to 3500 combined title/body characters; longer text is rejected, not cut.

Manual test (requires OPENAI_API_KEY in environment/root .env):
1. Start: .venv/bin/python -m uvicorn newsmuncher.main:app --reload --host 127.0.0.1 --port 8000
2. Log in/select your pet; use a rewrite and NOMINATE it. Optional response edits can
   be made before READ ALOUD. Generating a new rewrite separately invokes paid text APIs.
3. Click READ ALOUD once, wait for PLAY narration and Voice label; play via button/audio.
4. Reload: PLAY remains available. In a fresh browser session select the same pet and
   use Saved narrations; no speech call occurs. Repeated POSTs also reuse existing state.

Validation command:
./.venv/bin/python -m pytest tests/test_narration.py tests/test_compare_tts.py tests/test_image_generation.py tests/test_jingle_frontend.py tests/test_jingles.py -q
68 passed, 9 subtests passed; existing dependency deprecation warnings only.
Includes mocked OpenAI/Mongo, JS syntax/behavior and Jinja rendering checks. No live
OpenAI, MongoDB, image, jingle, Modal or ACE-Step calls; no real audio generated.
No dependencies added. Main untouched. REVIEW / CODEX; commit/push authorized.


## Isolated narration-reference jingle A/B — 2026-09-15

scripts/diagnostics/compare_jingle_reference.py defaults to dry-run; --run explicitly opts into
at most two single-attempt Modal POSTs. No OpenAI/TTS imports or calls. Reads existing
narration at data/generated_narration/<entry_id>.mp3 and brief from read-only SQLite
(data/previews/jingles.sqlite3, jingles.state.brief for same entry ID). If unavailable,
--brief-json PATH accepts an existing exported MusicBrief JSON containing music_prompt,
lyrics, duration_seconds. No brief generation, genre redraw, Mongo access or production
writes. Narration may reflect earlier/unsaved edits: operator must choose matching inputs.

Both variants retain caption/genre, lyrics, duration, turbo model, 8 steps, English,
LM disabled, output settings and fixed seed (default 1729). Only B adds reference.
GenerationConfig uses use_random_seed=False,seeds=[seed]; Python random is seeded for
reference segment sampling. src_audio and audio_cover_strength are never set.

Contract optional experimental namespace/seed/base64/SHA256 fields are validated;
reference requires strict base64, <=2 MB decoded MP3 and matching SHA256. Modal stages
reference inside TemporaryDirectory, checks codec and 0<duration<=120 via ffprobe,
then passes reference_audio to text2music. Cleanup occurs on success/failure. No
fallback generation without reference if validation fails. Full decoder/silence
validation still belongs to ACE-Step; that validation can fail after A succeeds.

Production marker shape/default inference settings remain unchanged. Experimental
files/markers use /results/experiments/narration-reference-v1/<request_uuid>.*. IDs
are deterministic and derived from entry ID, brief, seed, reference hash and A/B label;
not production IDs. Markers record checksum instead of base64. Existing complete
requests return cached audio; changed-input or uncertain attempts fail closed.
Untracked audio is never overwritten. Local outputs/attempt manifest are ignored at
data/jingle-reference-comparison/<input-hash>/{A.mp3,B.mp3,attempt.json}. Exclusive
pair-directory creation before requests prevents repeated/concurrent CLI runs from
spending again; interrupted runs require inspection, not deletion/retry guessing.

Commands from repository root (replace ENTRY_ID with the same nominated item's ID):
./.venv/bin/python -m scripts.diagnostics.compare_jingle_reference --entry-id ENTRY_ID --seed 1729 --dry-run
./.venv/bin/python -m scripts.diagnostics.compare_jingle_reference --entry-id ENTRY_ID --seed 1729 --run
The second command is for a future explicitly authorized A/B run only. It expects
MODAL_JINGLE_ENDPOINT, MODAL_JINGLE_KEY, MODAL_JINGLE_SECRET in environment/root .env.
Updated jingle_service/modal_app.py must be deployed first; no deployment performed.
Existing deployment will reject new experiment fields. No UI or production lifecycle
integration. Comparison output must not be promoted/attached to production entries.

Targeted command: ./.venv/bin/python -m pytest tests/test_jingle_reference.py tests/test_jingles.py -q
47 passed; two existing dependency deprecation warnings. Endpoint tests execute its
actual body with mocked Modal/ACE-Step/subprocess boundaries, verify cache compatibility,
fixed A/B inputs, production isolation and temporary cleanup. No live provider or
GPU calls. No actual audio generated. Main untouched. REVIEW / CODEX.


## Temporary deployed-schema diagnostic — 2026-09-16

jingle_service/modal_app.py adds diagnostic_schema, a separate @app.function with
explicit gpu=None, min_containers=0, retries=0, no volume, same image as JingleGenerator.
It never instantiates the class, loads ACE-Step or invokes generation. Returns build
identifier reference-ab-schema-diagnostic-v1, contract/module file paths and SHA-256
hashes, sorted GenerationRequest fields. The identifier is a label, not a Git hash;
compare returned hashes against checkout files to prove exact content.

Package inclusion now uses add_local_python_source("jingle_service", copy=True).
Both class and diagnostic disable implicit source inclusion; module-mode deploy is
required. Model/settings/production endpoint/proxy auth/volume unchanged. Image build
will bake current source rather than overlay competing runtime source mounts.

From repository root, using the existing Modal workspace/profile/environment:
NEWSMUNCHER_JINGLE_GPU=L4 ./.venv-modal/bin/python -m modal deploy -m jingle_service.modal_app --tag reference-ab-schema-diagnostic-v1
./.venv-modal/bin/python -c 'import json, modal; print(json.dumps(modal.Function.from_name("newsmuncher-jingles", "diagnostic_schema").remote(), indent=2))'
shasum -a 256 jingle_service/contract.py jingle_service/modal_app.py

Expect /root/jingle_service/contract.py and /root/jingle_service/modal_app.py,
matching hashes, and fields: duration_seconds, experiment, lyrics, music_prompt,
reference_audio_b64, reference_sha256, request_id, seed. Missing function means wrong
or older deployment/environment. Wrong hashes/paths indicate stale/mismatched source.
A matching diagnostic verifies same-image source without a GPU invocation; it does
not prove a separately configured HTTP URL points to that deployment. Do not retry
A/B until schema and endpoint identity are confirmed. Existing attempt directories
were not inspected, changed or deleted. Actual CPU invocation can incur a small CPU
charge; no paid or remote calls were made in this task. No deployment performed.

Tests: ./.venv/bin/python -m pytest tests/test_modal_schema_diagnostic.py tests/test_jingle_reference.py -q
21 passed. Mocked decorators prove CPU configuration, common image, deterministic
package inclusion and absence of class instantiation. A/B regression tests retained.
REVIEW / CODEX; commit/push authorized, main untouched.


## A/B recovery and B-only resume — 2026-09-16

--resume DIRECTORY uses the frozen attempt.json brief/seed plus the existing narration
checksum, verifies the deterministic directory identity, and requires valid A.mp3/A.json.
A marker must be complete and match the exact canonical request; MP3 signature/size
and marker byte count must agree. A files/manifest remain untouched. A gets zero POSTs.
Same checks permit recovery of B without any generation after an ambiguous outcome.
The existing local A was validated read-only; no actual variant state was written.

Per-variant *.state.json records UUID, canonical request (no base64), volume/path,
stage, HTTP status, allowlisted content type, byte count and safe error category.
Submitted state is atomically persisted/fsynced before POST. Local flock prevents
concurrent resume processes. Submitted/ambiguous/failed states never retry; only
pending or previously unattempted B may POST. Response errors remain ambiguous,
including non-200 responses. No redirect following, no generation retries.
Audio is atomically published; missing/incomplete marker pairs fail closed for
operator recovery. Existing telemetry survives artifact recovery. Legacy attempt
manifests lack B progress: this resume assumes the operator-confirmed A-only attempt;
it cannot prove an unrecorded historical B request never occurred. Keep attempt files.
fcntl locking targets existing macOS/Linux environments. No production changes.

Command from repository root (explicitly generates B; NOT executed by Codex):
./.venv/bin/python -m scripts.diagnostics.compare_jingle_reference --resume data/jingle-reference-comparison/d625b73f0949f58c5f9d9435a560b3b1e9a11a37224f3fe679c12bae4b6c163a

Tests: ./.venv/bin/python -m pytest tests/test_jingle_reference.py tests/test_modal_schema_diagnostic.py -q
31 passed, all provider interactions mocked. No deployment, live service calls or
new audio. Recovered A.mp3/A.json and attempt.json not modified or committed.
REVIEW / CODEX. Commit/push authorized; main unchanged.


## Structured genre conditioning — 2026-09-16

jingle_service/genres.py defines all 35 existing genres in the same order. Random
choice occurs once in create_jingle_brief. Immutable GenreProfile snapshots persist
label, bpm, timesignature, cues and optional avoid text in MusicBrief and request
markers. Modal forwards snapshot bpm and timesignature directly to GenerationParams;
no inference-time genre redraw. New captions are deterministic, below 512 characters,
without story prose or potentially conflicting model-generated instrumentation.
The same single OpenAI request/schema returns short production caption and existing
20–40-word absurd lyrics; its lyrics are preserved, caption is enforced from profile.
No narration, new call, duration, GPU, generation, retry or storage lifecycle changes.

Acid House: bpm=125, timesignature="4" (4/4); dominant TB-303, TR-909 four-on-floor,
open hats/clap, repetitive groove, sparse vocal chants. Avoid pop/rock/orchestral is
caption guidance only. No lm_negative_prompt passed: LM is disabled, turbo does not
support ordinary CFG, so a true negative-conditioning guarantee would be misleading.
Pinned source ca1e85fe9430179831e6bc6be790c332190a3866/acestep/inference.py defines
bpm Optional[int], timesignature str, and forwards both to DiT generation metadata.
https://github.com/ace-step/ACE-Step-1.5/blob/ca1e85fe9430179831e6bc6be790c332190a3866/acestep/inference.py

All BPM values are editable arrangement targets, not authoritative genre definitions.
Opera/Jazz/Gospel/Ambient/Flamenco/Heavy Metal/Hardcore especially approximate. All
presets use simple 4/4; Flamenco deliberately chooses tangos, not 12-beat compas.
Audio adherence remains probabilistic and has not been evaluated with live generation.
Legacy briefs omit absent genre_profile in serialization, preserving old markers,
caches and A/B identities. No backfill/regeneration of existing jingles. Deploy new
Modal contract BEFORE sending new-profile briefs (old deployment rejects extra field).
Diagnostic field list now additionally contains genre_profile; compare current hashes.

Read-only profile verification (no keys/services):
./.venv/bin/python -c 'from jingle_service.genres import GENRE_PROFILES; p=GENRE_PROFILES["Acid House"]; print(p.model_dump()); print(p.caption())'

Targeted tests:
./.venv/bin/python -m pytest tests/test_jingle_brief.py tests/test_jingle_genre.py tests/test_jingle_genre_truncate.py tests/test_jingle_reference.py tests/test_modal_schema_diagnostic.py tests/test_jingles.py tests/test_jingle_frontend.py -q
71 passed; two existing dependency deprecation warnings. Tests cover one brief call,
profile persistence through the actual mocked endpoint, BPM/meter, no reference,
cache reuse, legacy schema shape, and A/B recovery. No deployment or real generation.
Manual: after separately deploying updated Modal service, start local uvicorn, log
in/select pet, nominate a rewrite without an existing jingle, click MAKE JINGLE once.
Random genre remains random; inspect stored profile/Modal metadata for selected tempo.
Play and refresh: existing audio must be reused. This manual click incurs normal paid
brief/GPU calls; it was not performed. Existing saved jingles are not regenerated.


## Compact jingle lyrics — 2026-09-16

Only the existing brief prompt changed: target 16–28 words total, preferably four
newline-separated lines, roughly 3–7 words per line. Simple rhythmic phrases, light
rhyme/repetition, absurd rewritten imagery; avoid dense clauses, punctuation-heavy
lines, tongue twisters, stage directions and section labels. Not four isolated words.
Lyrics remain separate from the unchanged deterministic genre caption. Random pool,
profile, BPM/meter, duration, provider settings and production reference behavior unchanged.

These are prompt targets, not a hard word-count guarantee. Existing 500-character
MusicBrief validation remains; no truncation existed and none was added. No padding,
fallback rewrite, second call or retry. Tests verify instruction delivery and intact
compact mocked lyrics, not real model compliance or audible vocal density.
Genre profiles with sparse vocals intentionally remain sparse; four easier lines may
improve usable delivery but cannot force ACE-Step to sing every word in 25 seconds.

Files: newsmuncher/services/jingle_brief.py, tests/test_jingle_brief.py, CURRENT_WORK.md.
Tests: ./.venv/bin/python -m pytest tests/test_jingle_brief.py tests/test_jingle_genre.py tests/test_jingle_genre_truncate.py tests/test_jingle_reference.py tests/test_modal_schema_diagnostic.py tests/test_jingles.py tests/test_jingle_frontend.py -q
72 passed, two existing dependency warnings. All generation mocked; no live calls.
Manual: restart local uvicorn; use deployed genre-profile service from 89a93ec (this
prompt-only change requires no new Modal deploy). Log in/select pet, nominate an item
without an existing jingle, press MAKE JINGLE once, listen and inspect stored lyrics.
Refresh/replay should reuse audio. Manual generation costs money; Codex did not run it.
REVIEW / CODEX; commit/push authorized. Existing jingles/briefs are not regenerated.


## Body-only audio inputs — 2026-09-16

Narrations.generate sends text_snapshot['body'].strip() only to TTS, preserving
internal punctuation/newlines. Body must be nonempty and <=3500 characters; title
no longer consumes speech budget. Title stays in UI/request/snapshot metadata and
existing mismatch reporting is unchanged. Existing audio returns before input
validation or synthesis, including older recordings that spoke the title.

create_jingle_brief now validates only rewritten body as story content and sends
JSON {"body": body[:1800]} to the same single OpenAI call. Existing body input cap,
16–28-word/four-line lyric guidance, random genre, profile caption, BPM/meter and
25-second duration unchanged. No title-derived caption text. Existing briefs,
media, snapshots and cache identities are not rewritten or regenerated.
No image/UI/routes/shared TTS helper/Modal changes; no Modal redeploy required
assuming the prior genre-profile service is already deployed.

Files: newsmuncher/services/narration.py, newsmuncher/services/jingle_brief.py,
tests/test_narration.py, tests/test_jingle_brief.py, CURRENT_WORK.md.
Validation: ./.venv/bin/python -m pytest tests/test_narration.py tests/test_compare_tts.py tests/test_jingle_brief.py tests/test_jingle_genre.py tests/test_jingle_genre_truncate.py tests/test_jingle_reference.py tests/test_modal_schema_diagnostic.py tests/test_jingles.py tests/test_jingle_frontend.py -q
95 passed, 3 subtests passed; two existing dependency warnings. Mocked providers;
legacy narration replay explicitly tested without synthesis. No live services called.
REVIEW / CODEX. Commit/push authorized; main unchanged.


## Lyric-friendly production pool — 2026-09-16

GENRES now explicitly lists Country, Folk, Heavy Metal, Punk Rock, Pop Rock,
Indie Rock, Glam Rock, Blues, Soul, Funk, Gospel, Ska, Reggae, Rockabilly,
Bluegrass, Musical Theatre, Opera, Power Ballad, Disco, Electro-pop.
Reused Heavy Metal/Gospel/Reggae/Opera tempos and strengthened clear lead-vocal cues;
16 others newly added. All 35 historical profiles remain available (51 total).
Old persisted snapshots/audio remain unchanged; removed genres cannot be randomly
selected in production but remain usable by direct profile reference.
Representative editable tempos, all 4/4; neither defines every arrangement in a genre.

Only genre profile data/pool, tests and this handover changed. One OpenAI call,
body-only input, 16–28-word/four-line lyrics, BPM/meter plumbing, 25 seconds,
idempotency and production no-reference behavior unchanged. No schema changes.
Modal consumes the supplied snapshot, not its local genre pool: no redeploy needed
assuming the prior structured-profile service is deployed. Restart local app.

Validation: ./.venv/bin/python -m pytest tests/test_jingle_brief.py tests/test_jingle_genre.py tests/test_jingle_genre_truncate.py tests/test_jingle_reference.py tests/test_modal_schema_diagnostic.py tests/test_jingles.py tests/test_jingle_frontend.py -q
93 passed, two existing dependency warnings. Tests exercise every active genre,
explicit vocal cues, single-call brief, historical Acid House BPM/meter and cache reuse.
No live services, deployment or audio generation. REVIEW / CODEX; push authorized.


## Profile narration UI cleanup — 2026-09-22

The narration commit had appended narrationControls as a generic container sibling
after outputContainer. Shared container styling created the large white card and its
normal document flow pushed the rest of the page/footer downward. The original lower
response parchment was never removed; outputContainer remained immediately above it.

Narration controls now live inside outputContainer. Before audio exists, the single
visible control is READ ALOUD. The existing per-rewrite lookup still resolves saved
audio without a provider call; when audio exists, READ ALOUD is hidden and the native
audio control plus a small voice/status line are shown. The manual Saved narrations
select, its separate play button, and their list-fetching JS were removed. Narration
and jingle APIs, generation, persistence and media are unchanged. Jingle controls,
nomination, SHIZZALISE, image mode and both parchment surfaces remain intact.

base.html now exposes its existing footer as an overridable block; pet_profile.html
renders that block empty, removing the profile-page footer without changing other
pages. Responsive audio width is bounded to the parchment.

Files: newsmuncher/templates/base.html, newsmuncher/templates/pet_profile.html,
newsmuncher/static/narration.js, newsmuncher/static/script.js,
newsmuncher/static/styles.css, tests/narration.test.js, tests/test_narration.py,
CURRENT_WORK.md.
Validation: ./.venv/bin/python -m pytest tests/test_narration.py tests/test_jingle_frontend.py -q
18 passed; two existing dependency warnings. Provider interactions remain mocked;
no live calls, generation, deployment or media changes. REVIEW / CODEX.


## Final-output word claims — 2026-09-22

Root cause: load_random_words called PermanentWordClaims.draw during prepare_prompt;
draw used find_one_and_update to append every selected candidate to claimed_words
before pass 1 started. Consequently unused prompt words and failed requests consumed
the full draw permanently.

Draw now reads the ledger and selects unclaimed candidates without mutating claims.
After pass 2 succeeds, or validated pass 1 becomes the fallback, exact whole-candidate
matches in the accepted final title/body are calculated case-insensitively. Only those
matches are committed. The commit runs across all affected bank documents in one Mongo
transaction; each update requires that none of its words was already claimed. A
concurrent conflict aborts every bank update and returns HTTP 409 before the local draft
is completed or returned. Unused candidates and failed pass-1 generation claim nothing.
CSV master vocabularies remain read-only; pass-2 prompts/behaviour are unchanged.

Guarded development reset (not run):
NEWSMUNCHER_ENV=development ./.venv/bin/python -m scripts.maintenance.reset_word_claims --confirm RESET-WORD-CLAIMS
The script hard-codes funny_json_db.word_shuffle_bags and calls delete_many only on
that collection. It refuses to connect unless both the environment guard and exact
confirmation are supplied. It does not touch nominations, pets, users or media state.

Files: newsmuncher/services/word_shuffle.py, newsmuncher/utils/clean_data.py,
newsmuncher/api/previews.py, newsmuncher/services/image_generation.py,
scripts/maintenance/reset_word_claims.py, tests/test_permanent_word_claims.py,
tests/test_copy_edit_pass.py, tests/test_image_generation.py,
WORD_SHUFFLE_STATUS.md, CURRENT_WORK.md.
Validation: ./.venv/bin/python -m pytest tests/test_permanent_word_claims.py tests/test_copy_edit_pass.py tests/test_source_preprocessing.py tests/test_image_generation.py -q
52 passed, 6 subtests passed; existing dependency/cache warnings only. All providers
mocked; no live OpenAI/Mongo calls, reset, deployment or media generation. REVIEW/CODEX.


## Nouns bank expansion — 2026-09-22

REVIEW / CODEX. User authorized including the pre-existing nouns.csv edit.
That edit already appended all 1,000 entries from Downloads/
newsmuncher_1000_new_nouns_comma_separated.txt in source order. Preserved the
authorized CSV byte-for-byte; no second append was needed.
Counts against HEAD: old 710, added 1,000, new 1,710; duplicate additions 0.
Against the working bank, all 1,000 prepared entries were already present and
therefore skipped on re-import. No existing nouns removed or altered.
Validation: strict csv.reader parsing and isolated execution of the application's
read_bank function passed; exact existing prefix and prepared suffix confirmed;
all 1,710 entries case-insensitively unique. No application logic changes,
Mongo access, claims changes, reset, provider calls, deployment or main changes.
Files: nouns.csv and CURRENT_WORK.md. Commit/push authorized.


## DATING reusable source — 2026-09-22

REVIEW / CODEX. pet_profile.html inserts DATING before DRIVEL in the existing
centred, wrapping source group. No CSS or existing button changes. The previews
script mapping invokes the existing historical-funny job with argument dating.
That job uses the existing get_all/increment_usage API with source=dating;
random least-used selection, preview fields and SHIZZALISE workflow are shared.

DRIVEL reads Mongo reusable_entries, not the seed JSON on each click. Its default
API behavior remains unchanged. DATING reads data/seeds/lonelyHearts.json and
idempotently seeds a separate dating_entries collection using content-derived IDs
and $setOnInsert, retaining existing usage counts. Missing numberOftimesUsed is 0;
extract is retained when present, otherwise description supplies the source body.
Counters persist in Mongo, not the seed file. Changed seed content becomes a new
entry; this initialization does not delete previously seeded entries.

Included Andy's authorized manual historicalFunnies.json update unchanged; JSON
parsing checked. No live Mongo/provider calls, claims changes, deployment or main
changes. Rewrite/image/narration/jingle logic untouched.
Validation: ./.venv/bin/python -m pytest tests/test_dating_source.py -q
4 passed (two dependency deprecation warnings), with fake Mongo and HTTP. Covers
real seed reading, fields, missing counts, persisted increments, least-used selection,
DRIVEL isolation/regression, rendered button order and existing centring/wrapping CSS.
node --test tests/profile_editing.test.js: 1 passed. git diff --check passed.


Promotion Gallery M2 checkpoint: backend plus server-validated login sessions implemented.
7 offline tests pass: rotation/display-only counts, retry/concurrency/rollback, legacy
records, idempotent promotion, private routes, CSRF boundary, safe existing media and
read-only unsynced jingle recovery, session cookies/password invalidation. Mongo and
HTTP mocked; temporary files only. No real DB, provider, migration or deployment.
Runtime needs Mongo transactions (already required for final-output word claims).
Sessions use pet_adoption_db.gallery_sessions with hashed opaque tokens and 24-hour
expiry; receipts use funny_json_db.promotion_gallery_views with 10-minute expiry.
Indexes are non-destructive TTL indexes created on first runtime use.

Promotion Gallery M3 checkpoint: separate private page/template/CSS/controller;
creation-page link and return navigation, one-item text/image rendering, promotion
state, empty state and sign-in gate. No generation scripts loaded. Display ACK waits
for a visible painted page; next selection waits for the preceding ACK. Late network
and promotion callbacks cannot replace the active item. 12 Python tests (gallery +
DATING) and 5 Node tests (gallery + existing profile controls) pass offline.

Promotion Gallery M4 checkpoint: per-item audio objects for stored jingle/narration,
both play() calls issued together. NEXT/pagehide stop and unload old tracks before
network waits; generation tokens guard late play promises/events. STOP cancels pending
starts; explicit PLAY AUDIO is the browser-permission fallback. Missing/unsupported
media does not block navigation. No silent-audio or autoplay-policy bypass.
9 Node gallery tests and 8 Python gallery tests pass offline, including late startup,
rapid navigation, blocked autoplay, single/no tracks and deliberate restart.

Promotion Gallery M5 checkpoint: existing parchment artwork, shallow CSS book-turn,
desktop image/text spread and stacked mobile layout; reduced-motion override, native
keyboard controls, loading/empty/sign-in and missing-image fallbacks. Hidden states
explicitly override the desktop grid. Old image errors cannot hide a newer image.
9 Python + 9 Node gallery tests passed offline. Visual screenshot/browser interaction
check was attempted with a loopback fixture only, but no browser connection is available
and native Computer Use permissions are not granted. No production app was opened.
Antigravity: inspected agy --help only; no readily available read-only mode, skipped.

Promotion Gallery M6 final checkpoint — 2026-09-23: REVIEW/CODEX.
125 Python tests + 6 subtests and 15 Node tests passed; only existing dependency and
datetime deprecation warnings. Regression covers DATING/DRIVEL, rewrite/word claims,
nomination, images, narration, jingles and profile controls. New login/adoption tests
prove gallery sessions are issued only after successful credentials/adoption.
Final fixes: expired/deleted receipts no longer strand navigation, BSON int64 counters
remain valid, malformed jingle sidecar state degrades safely, and previous-item
exclusion avoids immediate repeats when equal-minimum alternatives exist.
Complete diff reviewed and git diff --check passed. No paid/external generation,
live Mongo calls, destructive migration, deployment or main changes. New detailed
handover: PROMOTION_GALLERY_STATUS.md. Manual visual/audio QA remains unverified due
to unavailable browser connection/Computer Use permission; no production app opened.

## Promotion Gallery browser follow-up — 2026-09-23

Native Chrome access became available. Local fixture review caught Illegal invocation
from calling the default native fetch as this.fetcher. Wrapped the default fetch call
so it retains correct browser invocation; added a regression test rejecting a gallery
instance as native fetch receiver. Chrome now loads the gallery successfully.
Visually checked desktop image/text and text-only pages, fixture promotion state,
NEXT, and a 390px iframe viewport using the real template/CSS/JS. No real nomination
or provider access. 16 Node tests pass (11 gallery tests plus 5 existing frontend
suites). Prior 125 Python + 6 subtests unchanged; no backend changes.
Real stored-audio playback/authenticated production end-to-end review remains manual.
STATUS: REVIEW / CODEX; follow-up commit/push authorized by continued task.

## Promotion Gallery sequential audio — 2026-09-23

REVIEW/CODEX. Frontend GalleryMedia now plays jingle first and advances to narration
only on the active jingle's natural ended event. Single tracks start immediately;
text-only pages remain silent. Generation guards invalidate ended/playing callbacks
and pending play promises when turning pages or stopping. PLAY AUDIO retries the
current blocked track; STOP/PLAY restarts that track and retains only the remaining
sequence, so stopping narration never replays an already-finished jingle.
Only gallery JS, targeted frontend tests and handover docs changed. Selection,
promotion, backend APIs, stored media, generation and Creation Page are unchanged.
Validation: node --test tests/promotion_gallery.test.js tests/narration.test.js tests/jingles.test.js
20 tests passed; all media/network mocked, no external/provider calls.
No deployment or main changes. Commit/push authorized.

## Standalone image-to-video comparison — 2026-09-23

REVIEW / CODEX. Branch experiment/video-smoke-test from f7a65da; Promotion Gallery
branch untouched. scripts/diagnostics/video_smoke_test.py is standalone and uses existing requests.
Official current Wan/fal schemas, upload mechanisms, queue APIs and prices checked
before implementation; sources and commands in scripts/video_smoke_test.md.
Wan: supported multipart upload, 480p/5s, motion prompt and recorded random seed.
SVD: documented image data URI, no prompt, motion_bucket_id=127, cond_aug=0.02, fps=25,
recorded random seed. Same local image byte snapshot sent to both. No new dependencies.

Default providers none; no confirmation means zero HTTP calls and no output files.
All requested environment-only keys required before uploading/spending. Both
WAVESPEED_API_KEY and FAL_KEY are currently absent from the agent environment; no
.env values inspected. One generation submission per selected provider, no retries,
fal server queue retries disabled, bounded polling/downloads. Failures halt further
providers; attempt metadata persists before submission. No URL/credential logging.
Gitignored tmp/video-smoke-test/ holds source snapshot, successful MP4s, results.json
and local comparison HTML. Each new confirmed invocation is a fresh spend, not resume.

16 mocked tests passed; syntax compile passed; actual local dry-run reported $0.125
maximum estimate and zero calls. Missing-key and missing-image CLI checks returned
clean errors before transport. Ignore rules and git diff --check passed. No paid
API calls, live uploads, Mongo/nomination edits, app/gallery changes, deploy or main
changes. Only script, experiment docs/tests, .gitignore and CURRENT_WORK.md changed.
