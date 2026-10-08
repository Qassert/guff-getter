# NewsMuncher

A Python FastAPI application that fetches content, rewrites it into humorous
versions using OpenAI, and saves entries in MongoDB. Pet avatars provide the
application's adoption and login interface.

## Current status

Repository storage was audited and cleaned on 2026-09-29 on
`feature/video-animation`. Persistent media, user data and SQLite state were preserved.
See `CURRENT_WORK.md` for validation and current handover status. No live providers,
database services or deployment were used for this cleanup.

## Project structure

- `newsmuncher/main.py`: FastAPI entry point and static mounts.
- `newsmuncher/config.py`: filesystem paths anchored to the project location.
- `newsmuncher/api/`: entries, pets, previews, and the reusable content API.
- `newsmuncher/jobs/`: source fetchers and batch processing.
- `newsmuncher/utils/`: prompt preparation, rewriting, and file utilities.
- `newsmuncher/endpoints.py`: API URL definitions.
- `newsmuncher/templates/`: HTML templates.
- `newsmuncher/static/js/`: active Creation, Gallery and shared browser modules.
- `newsmuncher/static/css/`: shared/base and Gallery stylesheets.
- `newsmuncher/static/images/`: button artwork, source/MUNGE udder assemblies and backgrounds.
- `newsmuncher/static/audio/`: spoken control voices and interaction effects grouped by purpose.
- `newsmuncher/resources/prompts/rewrite.txt`: rewrite prompt.
- `newsmuncher/resources/words/`: CSV word banks.
- `data/seeds/`: historical funnies and lonely-hearts JSON source data.
- `data/avatars/`: existing and uploaded pet images, served at `/avatars`.
- `data/previews/`: live preview JSON and durable rewrite/jingle SQLite state, excluded from Git.
- `docs/status/`: feature handovers and implementation history.
- `docs/diagnostics/`: operator guidance for standalone diagnostic tools.
- `scripts/`: administrative, diagnostic and explicitly opt-in comparison tools.

## Repository storage and cleanup boundaries

| Area | Purpose and retention |
| --- | --- |
| `newsmuncher/` | Production Python, APIs, provider integrations, templates and static JS/CSS/artwork. |
| `newsmuncher/resources/`, `data/seeds/` | Tracked prompts, word banks and reusable source JSON. These are source data, not generated artifacts. |
| `jingle_service/` | Shared persisted jingle wire contracts; legacy Modal experiment source remains inactive for historical reference. |
| `data/avatars/` | Real pet/user images. Preserve, including existing tracked images. |
| `data/previews/` | Live preview JSON **and persistent SQLite claims/associations** (`image_rewrites.sqlite3`, `jingles.sqlite3`, including journals/WAL/SHM). Preserve and back up; never clear as a cache. |
| `data/generated_images/`, `data/generated_audio/`, `data/generated_narration/`, `data/generated_video/` | Reusable application media. Preserve these paths and files, including empty directory scaffolds. Ignoring them only prevents accidental commits. |
| `tmp/` | Local throwaway experiments, including `video-smoke-test/`. Media/comparison pages may be removed after review; retained `results.json` records are paid-attempt diagnostics, not new-run authorization. |
| `data/tts-comparison/` | Standalone TTS comparison samples, recreated by the tool as needed; old samples removed. Not used by production. |
| `data/jingle-reference-comparison/` | A/B recovery audio, manifests, locks and submitted-state markers. Retained together: removing them can erase evidence of paid work or defeat duplicate-spend guards. |
| `scripts/` | Keep password/claim reset, database checks, word-bank maintenance, benchmark, TTS/reference comparison and video diagnostics. Tools are documented and/or tested; do not run live/reset commands as cleanup. |
| `tests/` | Python and Node regression tests; fixtures are inline or generated in temporary directories. They do not depend on old comparison output. |
| `.venv/`, `.venv-modal/` | Installed development environments, retained. Project `__pycache__`, `.pytest_cache` and `.DS_Store` are disposable. |

2026-09-29 audit: removed four smoke-test input copies, four comparison HTML pages,
one smoke-test Wan MP4, four TTS samples, project caches/OS metadata, empty legacy
`code/` and root `words/`, and the unused `examples/index.html` calling obsolete
`/main/get_all`. No application code or useful scripts were deleted. No separate
image-comparison output or additional provider/model-cache folders were found.

Deliberately retained ambiguous/historical evidence: four smoke-test `results.json`
files (three failed/uncertain attempts), all narration-reference A/B files, and jingle
benchmark markers/diagnostics plus the documented `data/generated_audio/l4-approved/`
proof. Do not infer that old-looking media is orphaned without checking its runtime
association. This audit did not contact MongoDB or inspect remote Modal storage.

Offline validation runs the full Python suite with socket/DNS connections blocked,
all `tests/frontend/*.test.js` with Node network entry points blocked, and an app import with
Mongo constructors mocked and `.env` loading disabled. Importing admin/reset scripts
is **not** a safe startup check (`check_database.py` contacts Mongo on import).

## Local settings and dependencies

Keep credentials in the root `.env`; application and maintenance commands use
its path from `newsmuncher.config`. Keep credentials out of Git. Existing
process environment values retain precedence where `load_dotenv` is used.
Password recovery reads the root `.env` directly.

Use Python 3.10 or newer. `requirements.txt` lists runtime dependencies identified
from imports and framework features, including template rendering, multipart
forms/uploads, password hashing, and the Uvicorn launcher. It is not a tested
lockfile. The OpenAI constraint preserves the existing pre-1.0 API usage, and
Passlib/bcrypt constraints preserve a conservative legacy pairing. Dependency
installation and runtime verification remain separate work.

`.gitignore` excludes local environment files, virtual environments, Python and
tool caches, logs, build output, runtime SQLite/JSON, uploaded avatars, generated media
and local experiment output. Seed JSON and packaged resources remain eligible for
version control. Existing tracked avatars remain tracked; new uploads stay ignored.
Ignore rules do not untrack existing files or make application data disposable.

## Running locally

From the project root, with the intended Python environment activated:

```sh
python -m uvicorn newsmuncher.main:app --reload --host 127.0.0.1 --port 8000
```

The pet selection page is at <http://127.0.0.1:8000/pets/view_pets> and API
documentation is at <http://127.0.0.1:8000/docs>. No homepage route is defined at `/`.
Resource paths are independent of the working directory. Python still needs to
find the package; when launching elsewhere, provide Uvicorn's `--app-dir` pointing
to this checkout. Job subprocesses run with the project root as their directory.

Application workflows use MongoDB and external content services. Rewriting calls
OpenAI and can incur usage charges.

## Maintenance commands

Run these as modules from the project root, using the intended environment.
Do not invoke them by their file paths; module execution makes the shared package
available without `sys.path` workarounds.

To reset an adopted pet's password, substitute its exact name:

```sh
python -B -m scripts.maintenance.reset_pet_password Andy
```

Enter and repeat the new password in the terminal; input is hidden. This command
contacts MongoDB and updates the matching adopted pet's password hash. It refuses
ambiguous names; use `--avatar FILENAME` to disambiguate. Pet details and posts
are preserved. Existing login cookies are not revoked.

To check database connectivity:

```sh
python -B -m scripts.maintenance.check_database
```

This command contacts MongoDB and sends a ping. Its existing code also executes
when the module is imported, so do not import it for offline verification.
Neither maintenance command was executed during cleanup.

## Remaining known issues

- Runtime startup and dependency compatibility require verification.
- `error.html` is referenced by the pet API but is missing.
- Preview JSON is shared across users; generated `shizz_data.json` is created by
  the rewrite workflow. Keep the `data/previews/` directory available and writable.
- Authentication and unrestricted mutation endpoints need review before public
  hosting. Password resets do not revoke existing login cookies.
- The legacy OpenAI integration is retained; modernization is separate work.

Review files before the first commit, verify the fetch/rewrite/preview/save
workflow, and configure deployment and service secrets before hosting.

## Local source preprocessing

Install the dependency and matching trained English pipeline in the active environment:

```sh
python -m pip install "spacy>=3.8,<4"
python -m spacy download en_core_web_sm
python -m unittest discover -s tests -v
```

The model is loaded locally once per process. No extra OpenAI call is used.
Generation masks detected source names, places, noun phrases and modifiers before
building the prompt; source-to-placeholder records remain local for overlap logs.
A missing model raises an explicit setup error; original text is never silently
sent as a fallback. Detection is heuristic, especially for surreal invented text,
and is not an anonymization guarantee. Actions, quantities and connective language
are intentionally retained. Existing stored text that was lowercased by older
fetchers cannot recover its original capitalization; newly fetched text preserves it.
Overlap logging is diagnostic only and does not reject or regenerate output.

### Canonical rewrite flow

Source → rewritten body → copy-edited final body and short derived title. The
existing second text call finishes the body before summarising it into a singable 12–18-word headline.
A local hard cap keeps newly generated titles to 18 words; existing saved titles remain unchanged. This check is conservative, not a semantic entailment guarantee. No extra
text call is added. Word claims use the accepted final title/body as before.

Images use only the rewritten body plus the persisted visual style and composition
guidance. Jingle lyrics use the saved title unchanged, with the existing random genre profile. Historical narration remains stored and readable, but new narration is retired from the active experience.
Existing saved titles and generated media are not modified or regenerated.

### Creation Page media controls

EMBELLISH and animation controls appear only after successful persisted nomination,
including restore. Nomination never starts paid media generation. Video stops and
unloads automatically on creation/page changes; there are no visible Stop Animation
buttons. Existing saved video may still play before nomination.

EMBELLISH is an explicit user action that coordinates the existing video and jingle controls. Saved media is reused; in-progress work is polled; missing media uses the guarded generation APIs once. Nomination has no success popup and never starts these paid requests. The final media experience is the WaveSpeed video plus the sung jingle.

Jingles display `GENRE` from their persisted genre profile (unknown legacy genres
stay hidden). Loading, discovery and generation completion remain silent unless they
belong to the current explicit EMBELLISH sequence. PLAY JINGLE remains available.

REDO IMAGE is an explicit paid action available for an un-nominated image or after a
terminal initial-image failure. It preserves the rewrite ID, body, title and word claims, chooses a different
random style, and stores a new UUID PNG. While waiting, temporary images shuffle in the same pane until the new
one loads. Superseded files are retained for later audited cleanup. Any historical
animation is detached, retaining its paid claim/file without showing it on the new
image; no automatic video generation or new claim is allowed for that old animation.

A durable SQLite attempt keyed to the prior image URL prevents duplicate submissions
and stale clicks. Nomination and replacement are serialized; unresolved replacement
attempts block nomination and further paid retries. Reload can recover a completed
PNG without generating again. If no completed file exists, operator review is needed.
The current image and style are nominated together; the gallery uses that saved URL.

Initial generation automatically retries once only when the provider positively
returns without a usable image. The second paid claim is persisted before submission.
Timeouts, network ambiguity, local write failures and all other uncertain outcomes
never retry automatically. The saved-image shuffle remains active across the single
safe retry. A second definite failure exposes REDO IMAGE and never loops.

During initial image generation and Redo Image, a read-only endpoint samples up to
five distinct current saved images belonging to the active pet from the existing
rewrite store. Temporary images are never attached to the new creation. A shuffled
500ms card animation loops in the clipped image pane under the shared LOADING
indicator. No available images falls back to the loader; reduced motion uses one
static image and a static loader. Completion, failure, rewrite changes and page exit
cancel timers. The former generic page spinner uses the same shared loader CSS.

Loading-image records also carry an optional saved jingle URL, resolved through the
owner's rewrite → nomination ID → existing local jingle record. Only completed,
valid saved MP3s are reused; missing/retired music is normal. An independent temporary
player seeks to 2 seconds (0 for tracks no longer than 2 seconds), with 100ms volume
ramps on switches. Images without music leave the audible previous track running.
Late loads cannot start old selections; completion/failure/teardown unload all audio.
Autoplay rejection silences that loading session. Reduced motion disables temporary
audio entirely. No jingle generation, provider calls or visible-player state changes.

### Random image styles

Each new image gets one uniformly random visual style from the 20-style pool in
`newsmuncher/services/image_generation.py`. The prompt remains scene-led. The style
is recorded before the image request, then stored as `image_style` with the image
metadata and nomination, exposed to the gallery and shown near the Creation Page
image. Restore/reload reuses it without another selection or model call. Older
images keep an unknown/null style; they are never restyled or regenerated.

### Drafts, nomination, and future moderation

Each browser working session has one current draft slot in
`data/previews/image_rewrites.sqlite3`, for text-only and image-enabled rewrites.
A new Shizzalise replaces the un-nominated draft in that slot. Each revision gets a
fresh UUID (a discarded UUID is never reused for a paid image request). Nominate
saves the displayed/edited response to MongoDB with `nominated: true` and
`gallery_status: "pending"`. Subsequent edits can intentionally update the same
nomination; a new Shizzalise always starts a separate draft. Refresh in the same
browser session restores the current result without generating an image again.

Discarding a draft deletes its locally generated PNG and removes its content and
image metadata from SQLite. A tiny UUID/owner tombstone is retained to reject late
workers and repeated paid requests. Late image completions delete their output.
Cleanup also runs opportunistically when another Shizzalise begins: new-style
un-nominated drafts expire 24 hours after creation, and files left against discarded
tombstones are removed. There is no background scheduler. Closing the tab alone
therefore does not immediately delete a draft. Nominated rows/images never expire.

An uncertain nomination HTTP outcome is quarantined with `nomination_pending`:
it may already have committed in MongoDB, so cleanup does not delete its image.
Retrying the same nomination resolves to the same deterministic Mongo `_id`,
preventing duplicate inserts. If the user abandons that operation, reconciliation
is still required before its protected state can be safely removed. Existing
pre-upgrade rows/files without reliable lifecycle ownership are not bulk-deleted.
Legacy JSON previews are adopted into the same stable-ID nomination flow on save.

Legacy Mongo records with no moderation fields are interpreted at read time:
completed/banked rewrites are nominated and pending; incomplete source entries are
not nominated. Nothing is automatically approved and no destructive migration runs.
`services/moderation.py` defines status validation and the future gallery predicate
(`nominated == true` and `gallery_status == "approved"`), but exposes no route.
The current pet-password login sets an `active_pet` cookie; it is not a signed,
server-validated admin session. Before moderation can be exposed, implement genuine
server-side session validation, an explicit privileged role, ownership/authorization
checks, and an authenticated moderation endpoint. No gallery or video system exists.

## Nominated-entry jingles

After nomination, MAKE JINGLE submits one approximately ten-second song using ElevenLabs Music `music_v2_5`. PLAY JINGLE and STOP reuse the stored MP3; nomination and restore never auto-generate music.

The saved hidden headline is passed unchanged as the composition lyric. The existing random genre profile supplies positive style guidance, alongside immediate intelligible vocals, comedy-ad energy and a clean ending. Negative styles reject instrumental-only output, long intros, indistinct vocals and extended outros. This deterministic plan makes no extra text-model call.

Configure `ELEVENLABS_API_KEY` only in the server-side root `.env`. `NEWSMUNCHER_JINGLE_ENABLED` can disable new generation while preserving playback, and `NEWSMUNCHER_JINGLE_DAILY_LIMIT` defaults to 20 new claims per UTC day.

The durable SQLite claim is committed before the single paid request. Duplicate requests reuse status/audio, and ambiguous submitted outcomes never auto-retry. MP3s remain in `data/generated_audio/<Mongo nomination ID>.mp3`; Mongo retains provider/model, prompt plan, genre and the nominated text snapshot. Historical Modal/ACE-Step records and files remain readable. The old Modal deployment/benchmark utilities are inactive legacy tooling and are not part of the application path.

New narration generation is retired (POST returns 410). Historical narration state and authenticated audio retrieval remain available, while Creator, EMBELLISH and Gallery use jingle audio only. WaveSpeed video generation is unchanged.

### Actual benchmark and cost

2026-09-09: one T4 attempt failed with NaN float16 latents before decoding.
A separately approved L4 attempt succeeded:

- Client wall time: 53.869 seconds (cold request, excludes image build).
- Model-load measurement: 8.216 seconds (excludes Python/container startup).
- Generation + encoding measurement: 13.137 seconds.
- MP3 duration: 25.032 seconds; 400,941 file bytes; stereo 48kHz, 128kbps.
- File: data/generated_audio/l4-approved/309c2077-c511-4a36-8729-2e29d327425e.mp3.
- Benchmark used a fixed dummy brief, so OpenAI usage/cost was ZERO.
- Modal workspace rounded metered usage rose from $0.02 after T4 to $0.06 after
  L4/builds; credits covered $0.06, billed $0.00.
- Deployed-app meter rose from $0.00748483 to $0.03541200: approximately $0.02793
  incremental deployed compute for this cold proof, not a guaranteed unit price.
  The total $0.04 increment includes build/setup. Warm per-jingle cost is unmeasured.

Official L4 rate at review: $0.000222/GPU-second. Applying that rate only to the
13.137-second generation measurement gives about $0.00292 GPU compute, but EXCLUDES
startup, other allocated time, CPU/RAM and storage. The cold test did not establish
a one-penny total cost. Pricing and allowances can change.

No further live OpenAI or GPU calls were used for application integration.
Audio format/duration were locally verified; subjective musical quality is for
listening review, not asserted by automated tests.

### Offline testing

    .venv/bin/python -B -m unittest discover -s tests -q
    node tests/frontend/jingles.test.js
    .venv/bin/python -m scripts.diagnostics.benchmark_jingle

The benchmark defaults to dry-run. --generate is a LIVE cost-incurring request.
Existing attempt markers prevent reruns. Never use another attempt identifier
without explicit authorization. All automated provider tests are mocked.

For cloud hosting, move audio to durable shared storage, replace local quota/claim
SQLite with a shared transactional ledger, retain the existing authenticated-owner
checks, protect/rotate proxy credentials, and add operational reconciliation and
monitoring. No Cloudflare/R2 or other new account is needed locally.

Official references:
- [ACE-Step inference](https://ace-step.github.io/ACE-Step-1.5/en/INFERENCE)
- [ACE-Step GPU compatibility](https://ace-step.github.io/ACE-Step-1.5/en/GPU_COMPATIBILITY)
- [Modal pricing](https://modal.com/pricing)
- [Modal scaling](https://modal.com/docs/guide/scale)
- [Modal proxy authentication](https://modal.com/docs/guide/webhook-proxy-auth)
- [OpenAI brief model](https://developers.openai.com/api/docs/models/gpt-4.1-mini)
