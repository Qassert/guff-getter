STATUS: REVIEW
OWNER: CODEX
BRANCH: feature/global-word-shuffle
LAST_COMPLETED_FEATURE: Fix duplicate jingle controls after refresh
LAST_COMPLETED_COMMIT: :/^Fix duplicate jingle controls after refresh
LAST_OWNER: ANTIGRAVITY
HANDOVER: WORD_SHUFFLE_STATUS.md

## Status Values

- **READY**: repository is available for a new task
- **ACTIVE**: one named agent currently owns the task
- **BLOCKED**: work is incomplete and must not be overwritten
- **REVIEW**: implementation is complete but awaiting Andy's review/approval

CURRENT_TASK: Isolated narration-reference jingle A/B experiment; no live generation

REVIEW_SUMMARY: Isolated narration-reference A/B harness ready; no live experiment/deploy.
VALIDATION: 47 targeted tests passed; provider/ACE-Step calls mocked.
APPROVAL: Commit/push authorized; real A/B generation not authorized or performed.
NEXT_STEP: Review, then deploy updated Modal code before a separately authorized A/B run.

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
