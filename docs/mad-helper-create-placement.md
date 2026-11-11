# CREATE helper placement from the screenshot

CREATE-only placement refinement in NewsMuncher-Build. Existing uncommitted work for this
task was retained and continued. No unrelated checkout work, media regeneration, generation
API calls, database edits, push, merge or deployment.

## Reference and clarification

The upper red guide ends near the top-left of the source parchment, above the source text.
The lower guide ends below the story near the results parchment's right margin. Andy
explicitly confirmed moving the lower helper to that lower-right endpoint; this overrides
the earlier written instruction that both helpers remain on the left.

The upper helper now anchors at paper top + 0.36 times its current size, rather than half
of the source paragraph height. A document-space minimum keeps its hair on-screen without
making it sticky during scrolling. Mobile uses the first 15% of the text instead and avoids
source teats/navigation, so the higher placement cannot block source controls.

The lower helper occupies a real layout slot below the rendered story. Its right edge is
24px inside the results parchment edge, placing its centre about 133px inside that edge at
the unchanged desktop size, closely matching the guide. Its top stays at least 12px below
visible story text. The STUFF/SWEAR tools share the row on the left, with a reserved bubble
column; on mobile the helper slot follows both tools and aligns right. This reserves space
rather than overlaying content. Toggle-off hides the slot and restores the original block
layout and field padding. Per-text anchors/docks are opt-in; BUILD/GALLERY defaults remain.

## Flip and speech bubble

Only CREATE's result text opts into a flipped helper. CSS scaleX(-1) applies to its PNG,
video and WebP fallback only, leaving the button hit area, SQUIRT lettering and shared glow
untouched. The shared video element derives its flip from its current parent: moving back
to the upper helper restores the normal orientation automatically.

The lower bubble sits left of the flipped face, in reserved space below the paragraph,
with a short curved pointer towards the mirrored mouth. Other bubble timing and click,
audio, random-idle, masking, size and toggle behavior are unchanged.

## Focused verification

- node --test tests/frontend/mad_helper.test.js tests/frontend/glow_theme.test.js: 26 pass.
- Targeted shared_helper_settings Python render check: one pass, 19 deselected; two existing
  dependency warnings. JS syntax and git diff --check pass.
- One isolated full CREATE Chrome fixture used disposable text matching the screenshot.
  At 1960px: upper centre is higher than source text and aligned to the left edge; lower
  right inset is exactly 24px and frame starts below story. At 390px: helper remains inside
  viewport, lower slot follows tools, and no helper/button intersections were found.
- Clicked lower helper: PNG/video both mirrored, dimensions identical, SQUIRT unmirrored
  and left of the face. Clicking the upper helper afterwards restores the shared video's
  unflipped appearance. Toggle-off removes the dock/grid and both helpers. Screenshots
  inspected. No live MUNGE/nomination/media or database operation; no broad suites rerun.
- Temporary fixture, isolated Chrome and static server removed/stopped at completion.
  Screenshots/logs are ignored under tmp/. Native Safari was not retested.

Files: shared mad-helper.js/CSS, CREATE template, BUILD/GALLERY helper asset cache versions,
focused helper/glow/template tests, CURRENT_WORK.md and this handover. No artwork changed.
