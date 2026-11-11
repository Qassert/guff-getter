# Mad Helper shared colour-changing glow

Small visual refinement in the previously clean NewsMuncher-Build develop worktree.
No original checkout changes, media regeneration, backend edits, paid generation,
push, merge or deployment.

The helper's PNG, animated WebP and video now use the existing --glow-rest-filter and
--glow-hover-filter tokens from shared/styles.css, rather than a private fixed palette.
These are the same filters used by navigation, udder objects, buttons and Gallery controls.
They combine a soft dark drop shadow with coloured soft glow layers derived from the
shared --glow-r/--glow-g/--glow-b variables. Transitions use the existing 700ms ease timing.
Reduced-motion disables that transition, and a plain dark drop shadow is the fallback
if the shared tokens are unavailable. Only the media pixels are filtered, not the bubble.

The existing shared GlowTheme changes colour on load and decorated-control clicks;
it is not an autonomous hue-spin timer. Mad Helper buttons join that existing selector,
so their clicks select the next non-repeating shared palette colour, and other controls
also change the helper glow in sync. No new timer, palette, per-frame JS or geometry change.
The helper's alpha masks, asset files, size, left edge, bubble, sound and playback code
are unchanged. Shared script and helper CSS cache versions are refreshed across all modes.

Validation was kept focused:
- node --test tests/frontend/glow_theme.test.js tests/frontend/mad_helper.test.js: 20 pass.
- node --check shared/glow-theme.js and git diff --check pass.
- One isolated Chrome full-CREATE fixture with disposable source/result text: helper clicks
  and a decorated control change the shared colour; PNG and active-video computed filters
  match after the transition; helper rectangles remain identical before/after; reduced-motion
  gives zero-duration transitions; invalid shared tokens use the fallback shadow.
- Light parchment and dark-background screenshots inspected; the glow follows the cutout
  without an opaque rectangle or change to artwork. No live MUNGE or database operation.
- No Python/broad suites repeated for this CSS/selector-only change. Temporary served HTML,
  isolated Chrome and static server are removed/stopped at completion. No app-server startup.

Files: shared/glow-theme.js, creation/mad-helper.css, base.html and CREATE/BUILD/GALLERY CSS
cache versions, tests/frontend/glow_theme.test.js, CURRENT_WORK.md and this handover.
