# NewsMuncher

A Python FastAPI application that fetches content, rewrites it into humorous
versions using OpenAI, and saves entries in MongoDB. Pet avatars provide the
application's adoption and login interface.

## Current status

The recovered project has completed three phases of folder cleanup. A local Git
repository exists. Syntax and static path/import checks have been performed;
application startup, dependency compatibility, and external service connections
have not been verified. No packages were installed or services contacted during
this cleanup.

## Project structure

- `newsmuncher/main.py`: FastAPI entry point and static mounts.
- `newsmuncher/config.py`: filesystem paths anchored to the project location.
- `newsmuncher/api/`: entries, pets, previews, and the reusable content API.
- `newsmuncher/jobs/`: source fetchers and batch processing.
- `newsmuncher/utils/`: prompt preparation, rewriting, and file utilities.
- `newsmuncher/endpoints.py`: API URL definitions.
- `newsmuncher/templates/`: HTML templates.
- `newsmuncher/static/`: JavaScript and CSS, served at `/static`.
- `newsmuncher/resources/prompts/rewrite.txt`: rewrite prompt.
- `newsmuncher/resources/words/`: CSV word banks.
- `data/seeds/`: historical funnies and lonely-hearts JSON source data.
- `data/avatars/`: existing and uploaded pet images, served at `/avatars`.
- `data/previews/`: generated preview JSON, excluded from Git.
- `scripts/`: local password recovery and database connectivity commands.
- `examples/index.html`: standalone example; not an application homepage.

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
tool caches, logs, build output, and preview JSON. Seed JSON and packaged resources
remain eligible for version control. Avatar images remain eligible too; review
uploaded images before staging. Ignore rules do not untrack existing files.

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
python -B -m scripts.reset_pet_password Andy
```

Enter and repeat the new password in the terminal; input is hidden. This command
contacts MongoDB and updates the matching adopted pet's password hash. It refuses
ambiguous names; use `--avatar FILENAME` to disambiguate. Pet details and posts
are preserved. Existing login cookies are not revoked.

To check database connectivity:

```sh
python -B -m scripts.check_database
```

This command contacts MongoDB and sends a ping. Its existing code also executes
when the module is imported, so do not import it for offline verification.
Neither maintenance command was executed during cleanup.

## Remaining known issues

- Runtime startup and dependency compatibility require verification.
- `error.html` is referenced by the pet API but is missing.
- `examples/index.html` still calls the old `/main/get_all` endpoint and is not
  wired into the application.
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

After nominating a rewrite, MAKE JINGLE creates one approximately 25-second song.
PLAY JINGLE and STOP use its stored MP3; they never generate another song.
Nothing auto-generates on nomination. The original source article is never used
for the music brief.

Architecture: nominated Mongo entry → bounded server-side OpenAI structured brief
→ private Modal HTTPS endpoint → ACE-Step 1.5 turbo on L4 → local MP3 + Mongo
metadata. The app remains Python 3.13; Modal runs a separate Python 3.11 ML image.
Do not install ACE-Step into the app's .venv.

### Configuration

Root .env (see .env.example; never commit secrets):

- OPENAI_API_KEY: existing key, reused.
- MODAL_JINGLE_ENDPOINT: deployed private Web Function URL.
- MODAL_JINGLE_KEY / MODAL_JINGLE_SECRET: Modal Proxy Token pair, server-side only.
- NEWSMUNCHER_JINGLE_BRIEF_MODEL: gpt-4.1-mini by default; max400 output tokens,
  structured JSON, no tools, no reasoning configuration and no automatic retries.
- NEWSMUNCHER_JINGLE_ENABLED: true by default, provided credentials are configured;
  set false to disable new generation while preserving playback.
- NEWSMUNCHER_JINGLE_DAILY_LIMIT: default20 new claims globally per UTC day.
- NEWSMUNCHER_JINGLE_GPU: deployment-only, default L4 (the successful benchmark).

Run the existing app normally:

    python -m uvicorn newsmuncher.main:app --reload --host 127.0.0.1 --port 8000

Generate a rewrite, NOMINATE it, then click MAKE JINGLE explicitly. It shows a
disabled loading control until the response arrives. On completion, use PLAY
JINGLE/STOP. Refresh/restoration fetches status only. Switching rewrites discards
stale UI callbacks and stops old playback. No automatic music-generation retries.

### Storage, limits and recovery

MP3 files are stored in data/generated_audio/<Mongo nomination ID>.mp3 and served
at /generated-audio/<ID>.mp3. Only .mp3 files are served; benchmark reports/markers
are not public. Files and benchmark output are ignored by Git. LocalAudio in
newsmuncher/services/jingles.py is the replaceable storage adapter.

Mongo stores jingle URL/status/provider/model/time, brief, OpenAI token usage,
and the nominated text snapshot/hash. It never stores audio bytes/base64.
Updating a nomination retains the existing song and original text snapshot;
the UI indicates when text has changed. No automatic regeneration or version fee.

SQLite data/previews/jingles.sqlite3 reserves one claim per nomination before
either provider call. BEGIN IMMEDIATE makes the claim and UTC daily count atomic
across threads/workers on the same host. Failed claims count too, so retries cannot
bypass the cap. Existing playback/status/duplicate requests do not use quota.
All app workers MUST share this ledger and generated-audio directory. Multiple
independent hosts would need shared transactional storage before deployment.

Only entries with nominated == true and matching active-pet ownership can generate.
GET /jingles/<rewrite_id> restores status; POST to the same path explicitly claims
generation. No frontend-supplied nomination flag or rewritten text is trusted.

A brief failure is safe to retry explicitly (no music was submitted); it consumes
another daily claim. After Modal submission, transport/provider failures are
conservatively marked uncertain and cannot automatically retry. Browser closure
does not cancel the synchronous server worker. A server crash leaves the durable
claim in place. Atomically saved local files are recovered on status requests;
failed Mongo metadata sync is retried without another provider call.

For an uncertain attempt, inspect the private Modal result volume/logs using the
request_id stored in SQLite. Do not delete markers, reset the ledger or submit a
new ID merely because a request timed out. If a completed remote file exists,
operator-assisted retrieval can recover it without inference. Automated remote
reconciliation is not included in this first version.

### Modal deployment

Separate development CLI:

    python3 -m venv .venv-modal
    .venv-modal/bin/python -m pip install -r jingle_service/requirements-dev.txt
    .venv-modal/bin/modal token new
    NEWSMUNCHER_JINGLE_GPU=L4 .venv-modal/bin/modal deploy jingle_service/modal_app.py

Use the existing workspace; do not add payment methods without authorization.
Create a Proxy Token and store its pair only in root .env. Modal CLI curl did NOT
authenticate this .modal.run Web Function in our test; use proxy credentials.

The service is private, max one container/input, zero minimum/buffer containers,
two-second scale-down window, no generation retries. Models load once per warm
container. Source is pinned at ca1e85fe9430179831e6bc6be790c332190a3866.
Remote CPU builds download the full set of files required by upstream's startup
check; the bundled LM is not initialized or used. Eight turbo steps, one batch,
25-second target; WAV is converted to browser-compatible 128kbps MP3.

Remote attempt markers and output files live on a Modal Volume. Do not run multiple
deployments against that single-writer volume. Model weights and volume storage
are not in Git. Model weight revision is not independently pinned yet.

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
    node tests/jingles.test.js
    .venv/bin/python -m scripts.benchmark_jingle

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
