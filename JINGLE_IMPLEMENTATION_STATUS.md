# Jingle implementation — 2026-09-10

First version implemented on feature/jingle-generation. Main was not modified.
User word-bank edits are preserved and excluded from all jingle commits.

## Completed
- Private Modal ACE-Step1.5 service; pinned source revision
  ca1e85fe9430179831e6bc6be790c332190a3866; separate Python3.11 ML image.
- Successful L4 25-second benchmark after one separately approved failed T4 test.
- Bounded nominated-rewrite-only OpenAI structured brief, gpt-4.1-mini default,
  max400 output tokens, no tools, no automatic retries.
- GET/POST /jingles/{rewrite_id}: server verifies permanent nominated entry and
  active-pet ownership; frontend flags/text cannot authorize generation.
- SQLite atomic nomination claim + global UTC daily cap (default20).
  Every new claim counts, including failed attempts; status/playback do not.
- Local MP3 storage, atomic file writes, persistent Mongo jingle metadata,
  durable recovery after file-write/metadata-sync gaps.
- One jingle per nomination. Uncertain provider outcomes cannot regenerate
  automatically. Explicit brief-only retry allowed because music was not submitted.
- MAKE/MAKING/PLAY/STOP parchment UI after nomination, saved-jingle restoration,
  stale callback protection, browser playback without provider calls.
- Nomination edits retain existing jingle and original nominated-text snapshot.
- Only .mp3 served from generated-audio mount; markers/reports are not public.
- README, .env.example, ignored audio/credentials/cache directories.

## Live test results
Exactly TWO separately authorized inference attempts total:
1. T4: failed float16 NaN latents, no audio. Modal total63.3s, execution11.8s,
   diffusion2.373s. Workspace rounded meter$0.02, billed$0.00 after credits.
2. L4: succeeded. Wall53.869s, model-load8.216s, generation+encoding13.137s.
   MP3 duration25.032s, file400941bytes, stereo48kHz/128kbps.
   data/generated_audio/l4-approved/309c2077-c511-4a36-8729-2e29d327425e.mp3
   Local afinfo independently confirmed format/duration.
   Workspace rounded meter$0.06, billed$0.00 after credits.
   Deployed meter increment approximately$0.02793 for the successful cold proof;
   total incremental$0.04 includes builds/setup. Not a guaranteed future unit price.
No live OpenAI brief call was made: benchmark brief was fixed, OpenAI cost$0.
No further GPU/API generations were used for integration or tests.
No payment method added; no paid billing enabled.

## Deployment/configuration
Private URL is in ignored root .env with proxy token pair; never print credentials.
L4 service is deployed, min0/max1 container, one input at a time, two-second
scale-down. There is no permanently warm GPU. The runtime GPU env value is L4.
Local default changed to L4 after successful proof; no further deploy needed for
that default-only change because deployed configuration already explicitly uses L4.
To disable new app generations: NEWSMUNCHER_JINGLE_ENABLED=false.
Every future MAKE JINGLE click is a real usage-consuming action; PLAY is not.

## Validation
79 offline Python tests passed, including Node frontend regression suites.
New route/ownership/concurrency/quota/provider/brief/UI/template tests are mocked.
New Python syntax and JS syntax/template rendering checks passed.
No live MongoDB writes or live browser-generated jingle during implementation.

## Files in this feature
- .gitignore, .env.example, README.md, JINGLE_IMPLEMENTATION_STATUS.md
- data/generated_audio/.gitkeep
- jingle_service/__init__.py, contract.py, modal_app.py, requirements-dev.txt
- scripts/benchmark_jingle.py
- newsmuncher/config.py, main.py
- newsmuncher/api/jingles.py
- newsmuncher/services/jingle_brief.py, jingles.py
- newsmuncher/static/jingles.js, script.js, styles.css
- newsmuncher/templates/pet_profile.html
- tests/test_jingle_brief.py, test_jingles.py, test_jingle_frontend.py, jingles.test.js

## Limits / future hosting
- Browser UI tested with mocks/template checks; no live MAKE click after proof.
- Audio quality needs listening review; only format/duration are automatically verified.
- All workers must share local SQLite/audio directory. Multi-host hosting needs
  shared transactional claims/quota and object storage.
- Uncertain remote outcomes require operator inspection of Modal volume/markers.
  Automated remote reconciliation is not implemented. Never clear an uncertain
  claim or choose a new request ID to bypass duplicate-cost protection.
- Remote Volume writer assumes one deployment; don't deploy parallel services
  against that volume. Model-weight repository not independently revision-pinned.
- Warm-song price unmeasured. Cold proof did not establish a one-penny total price.
- Uses existing active-pet cookie ownership model; no unrelated auth refactor.
- No gallery, video, R2, external account, model changes to Shizzalise, or changes
  to source masking, image generation, backgrounds or nomination persistence logic.

## Git
Checkpoints c149da7 (proof) and 7cc582d (T4 results/fixes), followed by final
implementation commit. Push feature branch only; never merge main.

## Lifecycle hardening — approved, 2026-09-10

Completed CODEX work; Andy approved commit/push as "Harden jingle persistence and lifecycle".

- GET /jingles/ discovers the active pet's saved nomination jingles from MongoDB,
  reusing the existing nominated/owner checks. Profile startup fetches this list
  independently of sessionStorage. A small saved-jingle selector provides stored
  PLAY/STOP without replacing the current draft, editor, or nomination controls.
- Stable Mongo entry-ID filenames and provider request IDs are unchanged.
- Discovery and GET /jingles/{rewrite_id} are the reconciliation path: a valid
  local MP3 plus SQLite brief/snapshot restores Mongo metadata without generation.
  Mongo write failures preserve recoverable audio/state and metadata_pending.
- Metadata sync now checks matched_count. A vanished nomination is not reported
  as successfully attached. Missing entries detected after provider completion
  trigger proven-owned cleanup rather than leaving a silently successful result.
- All existing entry-delete routes capture candidate IDs, delete matching entries,
  then verify absence before retiring their jingles. Ownership requires either
  the matching deterministic SQLite request ID or exact local URL + modal provider
  metadata. No directory sweep; ambiguous files and symlinks remain untouched.
- Retired SQLite rows retain only status and request ID; daily quota claims remain.
  These tombstones prevent late preparation/generation from resurrecting audio or
  allowing a duplicate paid request. Audio writes and retirement share the SQLite
  transaction lock. The existing provider call itself cannot be cancelled/refunded.
- Nomination edits keep the MP3 and original text snapshot. Mismatch warnings now
  also work from Mongo metadata if the local SQLite row is absent.

Validation: 32 targeted jingle tests and all 89 offline tests passed. Includes
Node frontend tests, JavaScript syntax, template rendering/unique IDs, fresh-session
playback, ownership, sync repair, deletion routes/races, ambiguous audio preservation,
and Mongo-only text mismatch. Python syntax and git diff --check passed.
Existing datetime/Starlette dependency deprecation warnings remain. The benchmark
failure printed by tests is a mocked failure-path fixture, not a live generation.
No OpenAI/Modal/ACE-Step/Mongo services were contacted, and no audio was generated.

Operational limits: audio and SQLite still require persistent shared disk and backups.
Deletion is not an atomic cross-database transaction. If the process crashes after
Mongo deletion but before retirement, an operator can retry
service.retire_deleted(collection, {"_id": ObjectId(entry_id)}) for a known deleted
entry; its ownership/absence checks remain mandatory. File-removal failures log a
cleanup warning and keep the retirement tombstone. Out-of-band Mongo deletions are
not automatically swept, and ambiguous legacy files require manual review.

## Final review fixes — approved
- Discovery explicitly sorts creationDate descending, then _id descending.
- entry_status uses the exact discovered Mongo entry and preserves owner checks;
  duplicate legacy rewrite IDs cannot pair another entry's audio with its title.
- Confirmed zero-match sync remains 404 even when retirement fails; failures log
  a retry warning rather than becoming successful metadata_pending responses.
- Nomination saves and completed jingle responses refresh saved playback choices.
  Refresh preserves selection/playback by entry_id and URL, updating title/warnings
  independently of the displayed rewrite.
- Validation: 34 targeted tests and full 91-test suite passed, including JS/template
  checks. Full 91-test suite reconfirmed before commit. No live services called.
  Existing deprecation warnings remain.
