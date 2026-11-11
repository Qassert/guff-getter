# Mad Helper mask and edge-quality refinement

Scoped follow-up in the clean NewsMuncher-Build develop worktree. Original supplied artwork
is retained unchanged. No live/paid generation, database writes, push, merge or deployment.

## Mask and encoding changes

The previous pipeline reduced frames to 320px before creating the matte, used binary
background membership and a fixed brightness divisor for fringe alpha. That made small
hair/jacket/foot boundaries vulnerable to low-resolution stair steps and matte contamination.

The offline tool now:

1. Decodes at the source canvas size (1024px PNG, 624px MP4), preserving detail before masking.
2. Retains protected face/teeth/torso areas and the selective hair-pocket/leg-gap handling;
   area thresholds scale with native resolution and smaller hair cavities are recognized.
3. Estimates white contamination against nearby opaque foreground colours using the white
   compositing equation, rather than a universal alpha divisor. Interior character RGB
   is not blurred or sharpened.
4. Applies a narrow Gaussian to alpha only, approximately 0.47 pixels at the derivative
   resolution; fades tiny alpha residues to zero and restores near-opaque interiors to one.
   Foreground colour extends into the fringe, avoiding white/black bleed when it is resized.
5. Premultiplies RGB by alpha before Lanczos resizing, then unpremultiplies, yielding 448px
   derivatives. WebM CRF 28 / WebP quality 88 retain more detail than the previous 32 / 80.
   All sixteen video/fallback pairs and the PNG were regenerated. The capability probe is
   unchanged, and manifest revision smooth-4 plus template asset versions invalidate caches.

The output files are larger: roughly 220MiB total compared with the previous ~83MiB.
Only the selected animation loads; no new preload-all behavior or runtime matting/canvas
work is introduced. Output remains 20fps, a fixed square canvas and silent video. Original
compression/flattened-white hair limits still apply; this is not a new artist alpha master.

## Visual separation

All still and animated states use the same alpha-aware CSS chain: a faint warm 1px edge
highlight (50%), a soft cool mint 6px outer glow (30%) and a warm dark 5px-offset/5px-blur
shadow (60%). It separates the silhouette from similarly toned paper/backgrounds without
an opaque box, hard sticker border or any blur filter on the character itself.

The component's runtime JavaScript, 217.6px desktop / 129.2px mobile display sizes, gutters,
left-edge/half-overlap positioning, text/control clearance, bubble, random idle scheduling,
click/audio, toggle and cross-page behavior are unchanged.

## Focused verification

- tests/frontend/mad_helper.test.js: 15 pass.
- tests/test_mad_helper.py selected matte/template cases: 3 pass, 17 deselected; two existing
  dependency deprecation warnings. PNG and a decoded WebM retain opaque eye/teeth/clothing
  samples, transparent leg gap and more than 100 intermediate alpha levels.
- Opaque PNG colour comparison against a clean 448px resize of the original: mean absolute
  RGB differences in sampled face/teeth, shirt/tie and jacket regions are respectively
  0.005, 0.000 and 0.037 out of 255. No global softening of those interiors was introduced.
- Before/after PNG comparison at the actual display size on grey and parchment backgrounds,
  plus a full CREATE source/results Chrome review at 1200px and 390px. Screenshots inspected:
  PNG/video align, the checked edges and leg gap are cleaner, glow/shadow remain subtle,
  bubble clears the face, and helper bounds remain left of readable text. Click playback
  works. No live MUNGE or media-generation requests; no broad suite repeated.
- Python AST, diff checks and source hashes verified. Native Safari was not retested.
- Temporary served fixture, isolated Chrome and static server are removed/stopped at
  completion; no app-server startup. Diagnostic comparisons/screenshots remain ignored in tmp/.

Files: prepare_mad_helper.py, shared helper CSS, PNG/sixteen WebM/WebP derivatives and manifest,
CREATE/BUILD/GALLERY template cache versions, the two focused test files, CURRENT_WORK.md
and this handover. No original checkout prompt/test/media work was altered.
