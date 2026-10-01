STATUS: REVIEW
OWNER: CODEX
BRANCH: feature/video-animation
LAST_COMPLETED_FEATURE: Safe image recovery, six-word titles and explicit Creator audio sequencing
LAST_COMPLETED_COMMIT: :/^Refine creation recovery titles and audio intent
LAST_OWNER: CODEX
HANDOVER: README.md

## Status Values

- **READY**: repository is available for a new task
- **ACTIVE**: one named agent currently owns the task
- **BLOCKED**: work is incomplete and must not be overwritten
- **REVIEW**: implementation is complete but awaiting Andy's review/approval

CURRENT_TASK: Independent start/end-frame video experiment implemented; awaiting review.
APPROVAL: Reuse durable generation paths, mock providers in tests, preserve styling and unrelated behavior. No live provider calls or main changes.
NEXT_STEP: Review the two-frame visual result with one explicitly authorized generation; no deployment performed.
VALIDATION: Two-frame image/video tests 77 passed (6 subtests); frontend 72/72; Python full suite 291 passed with one pre-existing brittle CSS-string assertion failure. Compile validation passed. All HTTP/providers mocked; no live provider calls.
MILESTONE_COMMITS: M1/M2 02b36ed; M3 b5e2baf; M4 cd1e7e0; M5 a0d0ab7; M6 7f947fc.
LIMITATIONS: Browser visual review remains unavailable: local startup requires Mongo DNS and no browser surface is exposed. Asset, template, syntax and interaction tests passed. No deployment or live provider/Mongo calls.

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
VALIDATION: 18 image-generation tests passed offline, including frontend checks.
No real images or external calls. Changes intentionally uncommitted/unpushed for review.


## Temporary TTS comparison harness — 2026-09-15

Standalone scripts/compare_tts.py only; no app integration. Curated editable voice
pools, one random voice/sample per selected provider, identical fixed sample text.
OpenAI SDK plus existing requests HTTP for ElevenLabs/Cartesia; no new dependencies.
Environment/root .env keys: OPENAI_API_KEY, ELEVENLABS_API_KEY, CARTESIA_API_KEY.
Missing keys skip safely; --dry-run writes nothing and calls no provider. No retries.
Unique MP3 files go to ignored data/tts-comparison/. No generated audio committed.
Run from root using .venv/bin/python -m scripts.compare_tts --provider all --dry-run.
For one live sample, replace all with openai/elevenlabs/cartesia and omit --dry-run.
Each provider requires an API-enabled account, usable quota/credit and access to the
configured voice IDs. Account/voice availability has not been tested live.
VALIDATION: 7 targeted mocked tests passed; no synthesis/provider API calls made.
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

scripts/compare_jingle_reference.py defaults to dry-run; --run explicitly opts into
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
./.venv/bin/python -m scripts.compare_jingle_reference --entry-id ENTRY_ID --seed 1729 --dry-run
./.venv/bin/python -m scripts.compare_jingle_reference --entry-id ENTRY_ID --seed 1729 --run
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
./.venv/bin/python -m scripts.compare_jingle_reference --resume data/jingle-reference-comparison/d625b73f0949f58c5f9d9435a560b3b1e9a11a37224f3fe679c12bae4b6c163a

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
NEWSMUNCHER_ENV=development ./.venv/bin/python -m scripts.reset_word_claims --confirm RESET-WORD-CLAIMS
The script hard-codes funny_json_db.word_shuffle_bags and calls delete_many only on
that collection. It refuses to connect unless both the environment guard and exact
confirmation are supplied. It does not touch nominations, pets, users or media state.

Files: newsmuncher/services/word_shuffle.py, newsmuncher/utils/clean_data.py,
newsmuncher/api/previews.py, newsmuncher/services/image_generation.py,
scripts/reset_word_claims.py, tests/test_permanent_word_claims.py,
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
branch untouched. scripts/video_smoke_test.py is standalone and uses existing requests.
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
