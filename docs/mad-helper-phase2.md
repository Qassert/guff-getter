# Mad Helper — BUILD and GALLERY extension

Andy explicitly authorized extending the completed CREATE helper to BUILD and GALLERY.
Implementation remains isolated in the previously clean NewsMuncher-Build develop worktree.
No original-checkout changes, media generation, database writes, push, merge or deployment.

## Integration

- BUILD: helper anchors beside the editable complete prompt and generated result. Ingredient
  selection controls are outside the placements. Existing recipe, manual prompt edits,
  RESET PROMPT and MUNGE 30/60/90 behavior are unchanged.
- GALLERY: one helper anchors on the outer LEFT parchment edge next to the currently
  displayed saved story. It supports text-only and image/text layouts, NEXT/BACK, refresh
  updates and empty states. Signed-out Gallery retains its existing login UI, with no
  helper toggle/controller loaded.
- CREATE retains its original source/result placements. All three pages explicitly mark
  helper paper/text regions, which the same component discovers without page-specific
  controller copies. Read-only Gallery text uses textContent; editable fields always use
  value, including empty manual edits. Measuring never changes story/prompt content.
- One shared Jinja settings partial keeps the existing Mad Helper toggle, assets and sound
  configuration identical. The same localStorage preference applies across modes, separately
  from master mute. Both animation paths, SQUIRT interaction and elapsed-time scheduling
  reuse phase 1 assets and code. No binary files or original artwork changed.

## Layout and lifecycle

The shared mirror/geometry implementation positions each helper from the actual rendered
text. Existing parchment gutters are reused; modest desktop Gallery/BUILD gutters supply
space for the outer half. Mobile stays on-screen with necessary text clearance. Disabling
restores original layout. Gallery's shared fitter asset version is advanced so content-box
observations refit read-only text if helper clearance changes.

Gallery's previous/next arrows can share the story midpoint. A small general obstacle
adjustment keeps the helper on the LEFT edge while moving it to the nearest clear vertical
position above/below those controls. The speech bubble stays within the helper's clearance.
Gallery's page-turn transform is tracked only while its animation runs, with a final position
update on completion. Child control animations do not start that tracking. Hidden/disabled
states clear motion tracking. Content mutations are observed on the story element, without
observing unrelated animated udder/video subtrees. Empty Gallery stops hidden helper playback.

## Validation

- 243 JavaScript tests pass, including shared field/placement discovery, read-only updates,
  control collision geometry and the existing helper, audio/mute, draft, BUILD and Gallery tests.
- 249 Python tests plus six subtests pass; 15 existing deprecation warnings. Covers all
  three rendered opt-ins, signed-out Gallery, BUILD generation, Gallery persistence/auth,
  adoption, CREATE, draft and media workflows. External services are mocked.
- Syntax and diff checks pass.
- Full rendered BUILD in isolated Chrome: actual USE and MUNGE 30/60/90 controls exercised
  with mocked adoption/provider responses. The recipe and manually edited prompt remain
  identical, final story punctuation is retained, and prompt/result helpers stay clear at
  1200px and 390px. No paid generation request was sent.
- Full rendered GALLERY with mocked records: NEXT/BACK, text-only/image/text, latest story
  content, empty-state cleanup, SQUIRT, master mute, shared toggle preference, desktop/mobile
  clearance. Browser hit testing confirms the previous arrow remains clickable. Screenshots
  inspected. No real story/media/promotion record was modified.
- Cross-page preference persistence and original CREATE placement discovery verified.
- Native Safari inspection was attempted but computer access timed out; it remains unverified.
  The existing alpha probe/WebP fallback and documented fine-hair matte limitation remain.
- Temporary static fixtures and isolated Chrome are removed/stopped at completion. No app
  server is started or restarted. Diagnostics remain ignored under tmp/.
