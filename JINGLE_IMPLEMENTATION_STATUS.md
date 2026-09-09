# Jingle checkpoint — 2026-09-09

Branch: feature/jingle-generation. Started clean. Main untouched.

## Completed
- Traced previews.py SQLite draft state and entries.py Mongo nomination persistence.
  Stable entry identity derives from owner + rewrite UUID. Updates mutate nominated
  text in place. Image API persists markers before paid calls; UI guards stale loads.
- Reviewed official ACE-Step, Modal APIs/pricing and OpenAI structured output docs.
- Upstream source reviewed in /tmp/newsmuncher-acestep-review, pinned revision
  ca1e85fe9430179831e6bc6be790c332190a3866.
- Isolated .venv-modal (Modal 1.5.5). Application .venv unchanged.
- Bounded shared wire schema and one-call nominated-rewrite-only OpenAI brief
  (gpt-4.1-mini, 400 output tokens, no tools or retries).
- Prepared private Modal proof: Python 3.11/T4/turbo/8 steps/no LM, CPU offload,
  max one container/input, min zero, two-second idle tail, durable markers/results,
  MP3 output with load/generation/measured-duration headers.
- One-shot dummy benchmark; dry-run default, local marker before POST, no OpenAI.
- Git exclusions, .env.example, README setup and cost caveats.
- No live OpenAI, MongoDB, Modal deployment or GPU generation.

## Authorization blocker
No ~/.modal.toml exists; no configured CLI login. User must run from repo:

    .venv-modal/bin/modal token new

Approve existing workspace in browser. Do not add a payment method.
Confirm remaining free allowance before deployment. Proxy credentials belong only
in root .env; do not print them.

## Exact next steps
1. After login, verify free allowance; deploy jingle_service/modal_app.py.
   Image imports locally but has NOT been built or tested on Modal.
2. Fix build/inference issues conservatively. Test T4 first; use L4 only if justified.
3. Configure private proxy token and endpoint in root .env without logging secrets.
4. Run ONE dummy benchmark (--generate), listen to MP3, inspect reported duration,
   collect Modal billing/load/inference/wall timings. No cost target proven yet.
5. ONLY AFTER proof succeeds integrate backend and UI:
   - Verify Mongo nominated==true + ownership; snapshot nominated rewritten text.
   - SQLite BEGIN IMMEDIATE ledger: global UTC daily new-claim quota (default20)
     and stable nomination idempotency, concurrent request protection.
   - Reserve before APIs; distinguish definite pre-generation failures from
     uncertain outcomes; reconcile same remote ID, never blindly regenerate.
   - Atomic local MP3 + durable Mongo metadata sync/recovery; generated-audio mount.
   - Status/restoration and MAKE/GENERATING/PLAY/STOP, stable rewrite stale guards.
   - PLAY reads stored file; nomination updates retain jingle and text snapshot.
6. Mock tests for drafts/ownership/success/metadata/restore/concurrency/quota/
   failures/uncertain outcomes/updates/UI. Run full suite and template/JS checks.
7. Complete docs, final feature commit and push branch; never merge main.

## Known limitations
- No app jingle routes/UI/daily quota yet, intentionally awaiting proof.
- Private proof endpoint trusts authenticated caller; does not query Mongo.
- Do not run parallel deployments against single-writer result volume.
- Uncertain attempts require operator inspection, no automatic retry.
- Weights fetched at remote build, not local/Git; model weight revision not yet pinned.
- Cold-start HTTP timeout possible; attempt marker retained.
- Actual cost, GPU speed and audio quality unknown.

## Validation
Full offline suite: 61 tests passed (57 existing + four new).
Modal app import and dummy benchmark dry-run pass locally.
No changes to application routes/templates/frontend in this checkpoint.

## Live proof update — 2026-09-09, evening
- Modal login qassert completed. Explicit user approval: deploy and exactly ONE
  25-second T4 generation, no payment method, no additional GPU runs without asking.
- Deployment succeeded. Serving FastAPI must be installed before setting PYTHONPATH.
- First HTTP request got proxy 401 (no GPU). Created proxy token privately, stored
  pair in ignored root .env. Same request ID resumed after confirmed auth rejection.
- ONE authenticated T4 request reached inference and failed with NaN float16 latents.
  Diffusion 2.3731787s; logged request duration63.3s, execution11.8s; no audio.
  Exact client wall time was not retained by failure path; reporting improved offline.
- Workspace metered$0.02, credits-$0.02, billed$0.00. Not a cost per successful song.
- Stopped newsmuncher-jingles deployment, no containers running.
- Offline fixes: cache upstream-required bundled LM files during CPU build; expose
  optional L4 configuration for a future separately approved bfloat16 test; record
  failed HTTP timing/status and test refusal to rerun a failed request.
- T4 float32 suggestion in upstream error is not actually wired as ACESTEP_DTYPE
  in pinned initializer; do not blindly set that env var as a purported fix.
- Backend/UI still awaits successful proof per requested phase order.
- Next authorization required: ONE additional L4 test (or explicit T4 precision
  workaround test). Do NOT run without approval. Do not reuse the failed attempt
  ID or delete markers merely to get past safeguards; retain audit and use a
  separately approved benchmark attempt mechanism.
