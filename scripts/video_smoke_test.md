# Standalone video smoke test

Offline first pass only. No NewsMuncher, gallery, nomination or Mongo integration.
Uses the existing `requests` dependency; no SDK/install or dependency changes.
Keys are read only from the process environment: WAVESPEED_API_KEY and FAL_KEY.
The script does not read `.env`. Never put key values in commands or this document.

## Run from the repository root

Dry run (no uploads, requests or output files; keys are not needed):

```sh
./.venv/bin/python scripts/video_smoke_test.py \
  --image /absolute/path/to/image.png \
  --prompt "Preserve the scene. Add restrained movement and gentle camera drift. No new text or objects." \
  --providers wan,svd
```

After supplying both keys securely in the environment, one explicitly paid comparison:

```sh
./.venv/bin/python scripts/video_smoke_test.py \
  --image /absolute/path/to/image.png \
  --prompt "Preserve the scene. Add restrained movement and gentle camera drift. No new text or objects." \
  --providers wan,svd \
  --confirm-spend
```

Without `--providers`, none are selected, even with confirmation. Individual `wan` or
`svd` are supported. Omitting `--prompt` uses the requested conservative motion prompt.
Wan always requests 480p/5 seconds; no prompt enhancer. SVD receives no prompt and uses
motion_bucket_id=127, cond_aug=0.02, fps=25. Each seed is randomly chosen locally and
saved in parameters; fal's returned seed is also retained if supplied.

Estimated cost: Wan $0.05 + SVD $0.075 = **$0.125** total. This is an estimate based
on published rates, not an account-level spending cap. The plan prints before calls.
All requested keys must exist before *any* upload/generation. No flag means zero calls.

PNG/JPEG/WebP inputs up to 10 MiB are accepted by file signature. One byte snapshot
is used for both providers and saved with its SHA-256. WaveSpeed uses its documented
supported multipart upload endpoint. fal explicitly supports image data URIs, so no
SDK or public image hosting is required. The source image is transmitted to each
selected provider only after confirmation. Uploaded content follows provider retention.

## Output and failure behavior

Each confirmed run creates a unique gitignored `tmp/video-smoke-test/<timestamp-id>/`:
source-image.*, results.json, compare.html, and only successfully downloaded wan.mp4
and/or svd.mp4. Open compare.html locally; it uses relative media references, native
controls, loop/mute and responsive columns. Metadata and text are escaped in HTML.
Dry runs and preflight errors write nothing.

One generation submission at most per selected provider per invocation. No HTTP
retries/redirects; fal server queue retries explicitly disabled with X-Fal-No-Retry.
Polls are retrieval-only, five seconds apart, with a 15-minute deadline (plus the final
HTTP timeout). Downloads are bounded to 100 MiB and checked for an MP4 container header.

On failure/timeout/interruption, the harness stops rather than submitting another
provider. Earlier successes remain. Results record the stage and safe job ID if known;
provider exception bodies, keys, authorization headers and upload/output URLs are not
printed or saved. A remote job may still complete after a local timeout. Inspect its
provider dashboard/job history first. **A new invocation is a new paid experiment**;
there is deliberately no automatic resume, retry, regeneration or quality evaluation.
Lost response/download recovery is manual. Do not rerun to recover an uncertain job.

## Official documentation checked 2026-09-23

- [WaveSpeed model schema and pricing](https://wavespeed.ai/docs/docs-api/wavespeed-ai/wan-2.2-i2v-480p-ultra-fast)
- [WaveSpeed supported upload mechanisms](https://wavespeed.ai/docs/upload-files): legacy multipart `/api/v3/media/upload/binary` remains supported; response `data.download_url`. Recommended ticket/PUT upload is also available but unnecessary for this tiny experiment.
- [fal Stable Video Diffusion schema and data-URI input](https://fal.ai/models/fal-ai/stable-video/api)
- [fal model price](https://fal.ai/models/fal-ai/stable-video)
- [fal raw HTTP queue, result retrieval and retry control](https://fal.ai/docs/documentation/model-apis/inference/queue)

No authenticated endpoint or live model availability was tested. Account access, quota,
actual provider responses and video quality remain unverified until an authorized run.

## Offline validation

```sh
./.venv/bin/python -m py_compile scripts/video_smoke_test.py
./.venv/bin/python -m pytest tests/test_video_smoke_test.py -q
```

Tests mock all transport and block real HTTP, covering dry-run/default-off, all-key
preflight, missing/invalid images, one submission per provider, identical source bytes,
SVD parameters/no prompt, output HTML/metadata, secret-free failures, polling timeout
and invalid downloads without automatic retry.
