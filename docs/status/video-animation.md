# Manual video animation handover

REVIEW / CODEX. Branch `feature/video-animation`, deliberately branched from
`experiment/video-smoke-test` at `7fbb648` to reuse its tested transport.
No deployment, merge, live Mongo operations or live provider calls were performed.
`main` and the experiment branch are unchanged.

## Milestones

- M1/M2 `02b36ed`: design, shared WaveSpeed transport, deterministic motion prompts.
- M3 `b5e2baf`: durable rewrite claims, background execution, authenticated API.
- M4 `cd1e7e0`: compact Creation Page animation controls and saved preview.
- M5 `a0d0ab7`: stored-video gallery transition, lifecycle and accessibility.
- M6 final commit: `git log -1 --format=%H --grep='Complete video animation regression and handover'`.

## Behavior and data

Only an explicit **ANIMATE IMAGE** click sends `POST /videos/{rewrite_id}`. The
existing verified login session plus same-origin header/origin checks apply. An
unsigned `active_pet` cookie alone cannot authorize this new paid action. Drafts
and nominations both work when their existing local generated PNG is available.
The server ignores client prompts/paths/models; it selects these from stored data.

`GET /videos/{rewrite_id}` and `GET /videos/{rewrite_id}/media` never schedule work.
Media is served privately, supports byte ranges, and is not publicly static-mounted.
Existing image generation, nomination fields, source selection, word claims, narration
and jingle generation remain as before. No application model was switched.

One `video` object is attached to the existing RewriteStore row in
`data/previews/image_rewrites.sqlite3`; no new rewrite/nomination collection/table.
Metadata is mirrored onto the existing Mongo nomination's `video` field when banked,
on worker completion, or on a later status read. No migration/backfill/index changes.
Failed metadata synchronization retains the local claim/file and can be repaired by
status/banking without any generation. The gallery reads Mongo metadata only.

Fields: rewrite_id, status, provider, model, duration, resolution, prompt, seed,
source_sha256, requested_at, created_at on completion, storage_key, provider request_id
when known, stages/error. Local-only requested_epoch and worker_started coordinate
execution and stale-state display. Normal UI responses expose only safe status,
availability, and authenticated playback URLs, not provider diagnostics or IDs.

MP4s: `data/generated_video/<rewrite UUID>.mp4`, gitignored. Bounded `.mp4.part`
downloads are fsynced and atomically published after an MP4 header check. The image
is read from its existing location; no source-image copy is saved. Image limit 10 MiB;
video limit 100 MiB. Files/metadata must be backed up together.

## Prompt and paid-call safety

The deterministic prompt uses preservation constraints plus at most two conservative
motion cues matched against the saved rewritten title/body. Examples: penguin reacts,
cupboard door opens, bowling balls roll. It neither forwards the full article nor
calls a text model. Unknown scenes receive restrained reactions/material motion and
camera drift. The final prompt and random seed are stored before provider work.
Unsaved editor changes do not replace this saved scene snapshot. Later edits do not
regenerate animation.

The shared client in `newsmuncher/integrations/wavespeed.py` is extracted from the smoke
test; the CLI now imports it and retains its original spend guard. The app uses:

1. `POST /api/v3/media/uploads`: filename, byte count, content type.
2. PUT original bytes to `data.upload.url`, using supplied upload headers only.
3. POST image=`data.download_url`, prompt, duration=5, seed to
   `https://api.wavespeed.ai/api/v3/wavespeed-ai/wan-2.2/i2v-480p-ultra-fast`.
4. GET `/api/v3/predictions/{id}/result`, every five seconds, up to 15 minutes.
5. Download the output MP4 without provider authorization headers.

SQLite `BEGIN IMMEDIATE` serializes permanent claims across workers sharing the
rewrite store. An existing claim of any shape, existing output, or existing Mongo
video metadata blocks new generation. A second durable `worker_started` guard makes
duplicate background delivery a no-op. Claims are never cleared/expired to permit
another submission; discarded drafts retain tombstones with their claims. A worker
finishing after draft discard cannot expose or attach its output.

FastAPI BackgroundTasks performs synchronous provider work after returning 202. The
browser can leave and reconnect without starting another job. There is no job queue,
automatic recovery submission, normal-user retry, or regeneration button.

Failures retain `failed_or_uncertain` plus safe diagnostics for `auth_upload_ticket`,
`image_upload`, `model_submission`, `prediction_polling`, or `output_download`; local
validation/persistence failures have a separate local stage. HTTP status is null if
there was no response. API keys, authorization headers, signed URLs and credential-like
provider messages are redacted/omitted. Exceptions are never logged raw by this flow.
All HTTP uses no redirects/retries; an ambiguous paid submission is never repeated.
A claimed job interrupted by process shutdown displays as uncertain after 30 minutes;
that display timeout never releases its claim. Operators must inspect provider history
and durable metadata. Do not delete the claim or re-run generation to diagnose it.
A valid atomically published file can be recovered as ready without provider calls.

## Gallery and UI

The Creation Page has a small control next to existing media controls: ANIMATE IMAGE,
ANIMATING…, ANIMATION READY, or ANIMATION FAILED. Ready animations now preload
invisibly over the existing still in the same image panel. `canplay` starts muted,
inline looping playback and `playing` triggers a 600 ms opacity fade. The still
sets dimensions throughout; no separate player or Play click. Autoplay/media errors
and reduced motion preserve the still; STOP ANIMATION returns to it. Gallery-style
lifecycle guards invalidate stale media events/promises and unload on rewrite/page
changes. Status polls use GET only. No source-button layout changes.

Creation Page follow-up validation: 41 targeted Node tests passed (video, image flow,
gallery, narration and jingles). No backend or provider calls, deployment or main
changes. Commit: `git log -1 --format=%H --grep='Animate Creation Page images in place'`.

The gallery serves only an existing completed video associated with the exact rewrite.
It waits for the still image to load, shows it for 1.5 seconds, then plays muted,
inline and looping. The video fades in over 600 ms only after its `playing` event.
Autoplay/decode errors leave the still. NEXT/pagehide cancel timers, invalidate late
callbacks, pause/remove src/load/remove the old element. STOP ANIMATION returns to
the still. Reduced motion skips video, including a preference change during playback.
Image-only/text-only pages retain their existing behavior. Audio still plays jingle
first and narration after its natural end, independently of video.

## Validation and limitations

175 targeted Python tests + 6 subtests, and 34 Node tests pass with mocked providers,
Mongo, HTTP and media. Coverage includes concurrent claims and duplicate worker delivery,
shared transport success and stage failures, stored-output recovery, missing/symlink
files, metadata-sync failures, draft discard, authenticated/range media routes, frontend
races, still/video/text pages, reduced motion, autoplay fallback, and regressions for
nomination/images/narration/jingles/gallery/DATING/DRIVEL/rewrite word claims.
Only existing dependency/datetime deprecation warnings. `git diff --check` passes.

Browser visual review was attempted using a standalone synthetic-media fixture, but
the sandbox blocked its loopback bind and the native browser was actively in use.
No authenticated production page or real nomination was opened. Layout/real-browser
playback and actual provider quality/availability remain manual checks.

Operational limits: one deployment with durable shared SQLite/media; this is not a
multi-host distributed queue. Process termination leaves an intentionally blocked
claim. Repeated metadata-sync failure needs an owner status read once Mongo recovers.
Only rewrites retained in RewriteStore with their local generated image are supported;
there is no legacy-image import. Abandoned/deleted items may leave inaccessible media
for operator cleanup. Prompt cues are intentionally conservative, not semantic parsing.
Input/output checks recognize container signatures, not a full media decode.

## One-item manual live test — requires Andy's explicit approval

Do not run a paid test merely because this handover exists. With the API key already
supplied securely in the server environment (never paste it into logs or commands):

```sh
./.venv/bin/python -m uvicorn newsmuncher.main:app --host 127.0.0.1 --port 8000
```

1. Sign in again to the owning pet, then restore **one existing rewrite with its generated
   image** on the Creation Page. Do not click SHIZZALISE or generate new image/audio.
2. Click **ANIMATE IMAGE exactly once**. Expect ANIMATING…, then ANIMATION READY.
3. Preview it; reload and confirm ready state remains with no new generation button.
4. Nominate it if needed, then view it in the Promotion Gallery: still first, muted
   video after the delay, NEXT stops it. Existing jingle/narration keep their sequence.

Expected video spend: approximately **$0.05** for one 5-second 480p generation,
with **$0 additional text-model cost**. Provider billing applies. An uncertain result
may still be billable; inspect the recorded stage/request ID and provider history,
not a second ANIMATE request or the standalone CLI.

## Changed files

- `.gitignore`, `CURRENT_WORK.md`, `docs/status/video-animation.md`
- `newsmuncher/config.py`, `newsmuncher/main.py`
- `newsmuncher/api/previews.py`, `newsmuncher/api/videos.py`, `newsmuncher/api/promotion_gallery.py`
- `newsmuncher/services/image_generation.py`, `newsmuncher/services/video.py`,
  `newsmuncher/services/video_prompt.py`, `newsmuncher/integrations/wavespeed.py`,
  `newsmuncher/services/promotion_gallery.py`
- `newsmuncher/static/js/creation/video.js`, `newsmuncher/static/js/creation/script.js`, `newsmuncher/static/css/shared/styles.css`,
  `newsmuncher/static/js/gallery/promotion-gallery.js`, `newsmuncher/static/css/gallery/promotion-gallery.css`
- `newsmuncher/templates/pet_profile.html`, `newsmuncher/templates/promotion_gallery.html`
- `scripts/video_smoke_test.py`, `docs/diagnostics/video-smoke-test.md`
- `tests/python/test_video.py`, `tests/python/test_video_prompt.py`, `tests/frontend/video.test.js`,
  `tests/python/test_promotion_gallery.py`, `tests/frontend/promotion_gallery.test.js`
