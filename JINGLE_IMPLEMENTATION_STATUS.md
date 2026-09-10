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
