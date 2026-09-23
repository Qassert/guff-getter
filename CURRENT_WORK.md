STATUS: ACTIVE
OWNER: CODEX
BRANCH: feature/promotion-gallery
LAST_COMPLETED_FEATURE: Fix duplicate jingle controls after refresh
LAST_COMPLETED_COMMIT: :/^Fix duplicate jingle controls after refresh
LAST_OWNER: ANTIGRAVITY
HANDOVER: WORD_SHUFFLE_STATUS.md

## Status Values

- **READY**: repository is available for a new task
- **ACTIVE**: one named agent currently owns the task
- **BLOCKED**: work is incomplete and must not be overwritten
- **REVIEW**: implementation is complete but awaiting Andy's review/approval

CURRENT_TASK: Promotion Gallery — milestone 3 gallery page complete
APPROVAL: Autonomous milestone commits/pushes authorized. No deployment or live generation.
NEXT_STEP: Implement milestone 4 audio lifecycle and race tests.

## Promotion Gallery milestone plan — 2026-09-22

OWNER: CODEX. Branch feature/promotion-gallery, based on 903f5d1.
- [x] M1 Discovery and design (planning checkpoint)
- [x] M2 Data/backend, private access, targeted tests
- [x] M3 Gallery page/navigation/text/images/promotion
- [ ] M4 Media lifecycle and race tests
- [ ] M5 Responsive flip-book polish and fallbacks
- [ ] M6 Regression, complete diff review, REVIEW checkpoint

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
responsive parchment presentation. Independent audio elements start together; page turn
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
