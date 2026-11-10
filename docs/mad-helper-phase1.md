# Mad Helper — CREATE phase 1

## Scope and operation

CREATE's source parchment and generated-results parchment opt into the reusable
`js/shared/mad-helper.js` component. BUILD and GALLERY do not load it. Existing
CREATE editors, generation prompts, models, draft saves and media actions are unchanged.
The only controller hook asks the helper to recalculate after `autoResize`.

The toggle is a discreet settings row below the parchment controls; putting it above
CREATE caused the source udder to obscure it on mobile during visual review. It defaults
on and persists `newsmuncher.madHelper.enabled`, independently of master mute. Disabled
means no observers, animation timers, audio or altered text padding/gutter. Storage errors
fall back safely to in-memory behavior. Reduced-motion preference suppresses autonomous
playback; explicit clicks remain interactive.

One controller owns both placements and permits only one animation and one helper sound
at once. Every autonomous cycle chooses a non-repeating clip, then waits a randomized
0.6–1.4 times four times that clip's duration before playing it once. The expected elapsed
time ratio is therefore 80% PNG / 20% animation, rather than an 80/20 selection count.
Clicks interrupt/restart the interaction and naturally change that ratio during active use.
Idle playback is silent. Click sounds reuse the three existing UI boing/squelch effects,
through native Audio and the unchanged master-mute controller. One SQUIRT bubble appears
for 2.5 seconds. Tab hiding/page leaving stops playback, timers, bubble and helper audio.

The component accepts PNG, animations (WebM/WebP URLs and duration), frequency, sounds,
bubble text/duration, enabled default, size/gap, custom positioning function, placements,
random source and storage. Both placements share these controls. Media is loaded on demand,
not all sixteen clips at startup. A playback watchdog and stale-callback token prevent
failed or superseded media from leaving an invisible/stuck helper.

## Positioning and text clearance

The artwork has a fixed square canvas and the PNG/video/fallback occupy the identical
button box. Positions are body-level portals so parchment overflow cannot clip the helper
or speech bubble. A rendered mirror of the textarea's current value, width and font metrics
locates the midpoint of actual displayed text, bounded by its visible scrolling viewport.
Input, programmatic resizing, fonts, viewport resize, scroll, relevant visibility/style
changes and ResizeObserver updates recalculate placement. The observer deliberately excludes
unrelated udder/rotor animation subtrees.

Desktop helper centre aligns with the LEFT parchment edge. At 621–1335px viewport widths,
a 36px outer workshop gutter provides room for the outer half. Wider screens already have
sufficient gutter. On mobile the helper becomes 76px and shifts inward only enough to
remain in the viewport. The entire helper/bubble remains left of readable text. Existing
parchment padding normally provides clearance; only when necessary is a small additional
left padding applied to the editable textarea. Native textareas cannot support a local
float/shape exclusion without replacing the editor, so mobile clearance applies to its
text column. Disabling restores the original gutter and exact inline padding.

## Original assets and transparent derivatives

The user-supplied one PNG and sixteen MP4s were found in the original checkout at
`newsmuncher/static/images/animated helper/`. All 17 files remain there byte-for-byte
unchanged; SHA-256 hashes are recorded in the derivative manifest and verified after work.
They were not moved, deleted or duplicated into this checkout's Git history.

Intentionally included static derivatives live in `images/mad-helper/`: idle PNG, sixteen
alpha WebM clips, sixteen animated WebP fallbacks, a tiny alpha capability probe and a
manifest. Approximately 85MB total; individual media files load only when selected.
The original 624px/24fps MP4s are processed offline to 320px/20fps derivatives, adequate
for the 128px desktop / 76px mobile presentation. No live image/audio/video generation,
external provider, AI background removal or new application dependency is used.

The reproducible offline tool is `scripts/assets/prepare_mad_helper.py`:

```
python scripts/assets/prepare_mad_helper.py SOURCE_DIRECTORY OUTPUT_DIRECTORY
```

It needs ffmpeg with libvpx-vp9/libwebp, NumPy and SciPy in an offline tooling environment
(use mutually supported versions, e.g. NumPy <2.5 for the installed SciPy). These are not
added to the application's dependencies. It removes neutral near-white connected to the
canvas edges, preserving enclosed white eyes/teeth, and unmattes the thin antialiased edge
against white. It strips all video audio, and retains the source SHA-256s and durations.
It does not blindly key out every white pixel or use CSS blending.

Flattened white-backed originals do not contain a recoverable true alpha matte: some pale
fringes/white pockets remain in the finest hair. These were inspected against parchment and
contrasting backgrounds; there is no opaque rectangular background. Perfect hair extraction
requires original transparent masters or artist-supplied mattes. This is a documented visual
limitation, not a claim of studio-quality segmentation.

WebM decoding support alone does not guarantee alpha compositing ([WebKit issue 275908](https://bugs.webkit.org/show_bug.cgi?id=275908)).
The component decodes a tiny fully transparent video and samples its alpha once at startup.
If unsupported, opaque, blocked or failed, it uses preprocessed animated WebP instead; a
WebM playback error also falls back. If the fallback fails, the PNG is restored. There is
no per-frame browser keying/canvas work. Native Safari was unavailable for testing; the
WebP path was explicitly forced and verified in Chrome. Background processing options were
checked against the [FFmpeg filter documentation](https://ffmpeg.org/ffmpeg-filters.html).

## Validation

- 240 JavaScript tests pass, including ten focused helper regressions and existing CREATE,
  BUILD, Gallery, text-fitting, navigation, audio/mute, image, jingle and video tests.
- 249 relevant Python tests and six subtests pass; 15 existing deprecation warnings.
- JS syntax checks, Python AST parsing and git diff --check pass.
- Local static API tests serve the manifest and all derivatives successfully. ffprobe verifies
  every WebM has alpha metadata, a 320px canvas and no audio track.
- Installed headless Chrome: all sixteen video/WebP pairs load; video corner alpha is zero;
  PNG and animation are visibly transparent on contrasting/real parchment backgrounds.
- A disposable fixture and the complete rendered CREATE template with existing controllers
  were inspected at desktop and 390px mobile. Source/result helpers stay LEFT, desktop
  centres match parchment edges, mobile helpers stay on-screen, and text/bubbles do not
  intersect. Text shortening repositions the helper. Original page controls remain present.
- Verified actual silent autonomous playback, video-ended return to PNG, forced WebP return
  to PNG, repeated-click interruption, SQUIRT timeout, master mute, toggle persistence,
  disabled cleanup and hidden-tab cleanup.
- No authenticated app generation, database writes, external paid calls or app-server restart.
  Browser/static-server fixtures were stopped and temporary served HTML removed. Ignored
  diagnostic screenshots/logs remain under tmp/ only. Original checkout's unrelated prompt,
  test and media changes were untouched. Local commit only; no push, merge or deployment.
