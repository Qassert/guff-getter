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
