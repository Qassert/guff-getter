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

## Jingle feature — isolated proof stage (not yet enabled in the UI)

One real ACE-Step jingle must succeed before backend/UI integration.
Nothing currently auto-generates music on nomination. The application stays Python
3.13; the Modal image uses Python 3.11 and the upstream ACE-Step dependency lockfile.
Do not install ACE-Step into .venv.

Prepared architecture: nominated rewritten text → one bounded OpenAI JSON brief →
private Modal HTTPS endpoint → ACE-Step 1.5 turbo (eight steps, one 25-second output,
no extra ACE language model) → MP3 → local generated-audio storage. The proof uses
a dummy brief, so it spends no OpenAI tokens.

Setup (separate CLI environment):

    python3 -m venv .venv-modal
    .venv-modal/bin/python -m pip install -r jingle_service/requirements-dev.txt
    .venv-modal/bin/modal token new
    .venv-modal/bin/modal deploy jingle_service/modal_app.py

Deployment builds/downloads ML dependencies remotely and consumes Modal resources.
Do not deploy until authenticated and available free allowance is confirmed. No
payment method is required by this implementation.

Create a Modal Proxy Token in the workspace dashboard. Put the deployed endpoint
and its token pair in root .env as MODAL_JINGLE_ENDPOINT, MODAL_JINGLE_KEY,
and MODAL_JINGLE_SECRET. Never put them in browser JavaScript or commit them.
Existing OPENAI_API_KEY is reused for the brief. The default brief model is
NEWSMUNCHER_JINGLE_BRIEF_MODEL=gpt-4.1-mini, with 400 maximum output tokens,
structured output, no tools and no automatic retries.

Offline tests and dry-run:

    .venv/bin/python -B -m unittest discover -s tests -q
    .venv/bin/python -m scripts.benchmark_jingle

After authorization, ONE live proof:

    .venv/bin/python -m scripts.benchmark_jingle --generate

This writes an attempt marker before a single POST. Running again refuses another
attempt. Do not delete the marker or choose a new ID after a timeout; inspect Modal
logs/results first. Remote IDs retain durable markers/completed files and never
automatically regenerate. Concurrent deployments sharing that volume are unsupported.

Audio and benchmark reports live in data/generated_audio/ and are Git-ignored.
MP3 uses 128 kbps. The proof returns model-load, generation and measured duration
headers plus file size. Actual billable startup must be checked in Modal's dashboard.

Pricing reviewed 2026-09-09: T4 $0.000164/GPU-second; L4 $0.000222/GPU-second.
T4 is the lowest listed rate and the first candidate for the small turbo model;
speed/quality are NOT yet benchmarked. At 60 GPU seconds, GPU alone would be
$0.00984, before CPU, RAM, cold starts, build, storage and idle tail.
This is not a claim of one-penny total generation. The service has zero minimum
containers, one maximum container, two-second scale-down and no retries.
Volume storage also costs money. Pricing can change.

NEWSMUNCHER_JINGLE_DAILY_LIMIT=20 is reserved for backend integration: a transactional
global UTC-day claim budget, with playback exempt. It is NOT yet enforced by the
private proof endpoint. Do not expose it to browsers or connect MAKE JINGLE yet.
Planned update policy: keep the brief/text snapshot with the audio; nomination
edits never silently regenerate music.

Official references:
- [ACE-Step inference API](https://ace-step.github.io/ACE-Step-1.5/en/INFERENCE)
- [ACE-Step GPU compatibility](https://ace-step.github.io/ACE-Step-1.5/en/GPU_COMPATIBILITY)
- [Pinned source](https://github.com/ace-step/ACE-Step-1.5/tree/ca1e85fe9430179831e6bc6be790c332190a3866)
- [Modal pricing](https://modal.com/pricing)
- [Modal scaling](https://modal.com/docs/guide/scale)
- [Modal proxy authentication](https://modal.com/docs/guide/webhook-proxy-auth)
- [OpenAI brief model](https://developers.openai.com/api/docs/models/gpt-4.1-mini)

See JINGLE_IMPLEMENTATION_STATUS.md for remaining work.
