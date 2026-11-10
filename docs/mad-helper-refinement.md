# Mad Helper visual refinement

Scoped refinement in the clean NewsMuncher-Build develop worktree. No original checkout
edits, new dependencies, paid generation, backend behavior changes, push, merge or deployment.

## Appearance and layout

The shared helper defaults to 217.6px desktop / 129.2px mobile, exactly 1.7 times the previous
128px / 76px. PNG, WebM and fallback WebP still occupy the same fixed square box. Desktop
gutter is calculated from the viewport; mobile trades inner text clearance for a 57px outer
gutter so the helper still straddles the left paper edge. CREATE's mobile engine group fits
within its container. Dynamic text clearance and existing Gallery control avoidance remain.

The SQUIRT bubble sits completely outside the artwork frame, at its upper-left corner.
A curved ink pointer runs beside the silhouette towards the mouth, leaving the face and
hair visible. Near the viewport top it flips below the artwork. Gallery collision checks
include the extra bubble footprint, so arrows remain clear. Its footprint stays in the
left clearance area rather than over readable text.

All media states get two alpha-aware CSS filters: a soft warm shadow (4px down, 4px blur,
45% opacity) and a very fine 1px dark edge (50% opacity). There is no opaque image container,
white outline or added artwork. The static/animated alignment and behavior are unchanged.

## Matte refinement

The previous outer-edge flood fill could not reach the enclosed bright patch between the
legs (488 bright pixels in the inspected base PNG). The offline pipeline now adds selective
seeds for narrow, tall, bright neutral cavities in the lower leg-gap region, then propagates
through a restricted neutral lower-body corridor to remove the grey matte boundary too.
Small enclosed near-white hair pockets in the upper hair band receive equivalent handling.
The eyes, teeth and torso are excluded from these extra seed regions. A two-pixel boundary
band with white-unmatting reduces residual edge contamination without globally keying out
light details. This is deliberately tailored to the supplied character, not general-purpose
white-clothing segmentation; different artwork needs a new mask review.

The PNG and all sixteen WebM/WebP derivative pairs were regenerated, retaining the original
320px/20fps canvas and silent video settings. A manifest revision adds cache-busting URLs.
All seventeen supplied original assets remain byte-for-byte unchanged in their original
location. The existing alpha capability probe is unchanged. Very fine pale hair highlights
can still remain because the flattened originals do not contain a true studio alpha matte;
the obvious leg patch is transparent in both the checked PNG and decoded video frame.

## Minimal verification, as requested

- Only tests/frontend/mad_helper.test.js: 15 pass.
- Only the targeted template render and PNG/video matte checks in tests/test_mad_helper.py:
  3 pass, 17 deselected, two existing dependency warnings. Pixel checks confirm transparent
  leg gap and opaque eye/teeth/clothing samples in the PNG and a decoded animation frame.
- JS syntax, Python AST and git diff checks pass. No broad application suite was rerun.
- One isolated Chrome visual pass at 1200px and 390px covered shared CREATE source/results,
  BUILD prompt/results and Gallery placement, exact sizes, readable text clearance, bubble
  boxes outside the artwork and viewport bounds, shadow filters, click playback and matching
  PNG/video dimensions. The final mobile gutter was inspected, with Gallery checked after
  its page-turn animation settled. Screenshots of PNG, animation and mobile were viewed.
- Local fixtures only: manual disposable text / mocked Gallery responses; no generation or
  database requests. Native Safari was not retested. Temporary served fixtures and browser/
  static server are stopped/removed at completion; diagnostic screenshots remain ignored
  under tmp/.

Changed files: shared mad-helper.js/CSS; prepare_mad_helper.py; PNG and sixteen WebM/WebP
pairs plus manifest; CREATE/BUILD/GALLERY template asset versions; the two focused helper
test files; CURRENT_WORK.md and this handover. Existing audio and other workflows unchanged.
