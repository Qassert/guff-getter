# Safe video end-frame recovery and Gallery notices — 2026-11-12

## Actual failed request

Nomination a9c2877b50a20710efe906fd / rewrite
5017c24f-e0e6-4f24-acd1-ca1910f954e0 has a successful main PNG at
/generated-images/5017c24f-e0e6-4f24-acd1-ca1910f954e0.png. Read-only verification
confirmed this file exists and its byte hash matches the saved video source hash.
The currently saved rejected end-image attempt is 3eb4cba2-275f-4e3c-95d4-5cd2f81ae92b.
Its exact prompt remains in video.end_frame.image_prompt in the existing sidecar;
there is no need to duplicate the private full prompt in logs or this report.

Main images use images.generate. Original end frames use a separate images.edit
call with the successful PNG as reference, the same media-safe concept and style,
plus later-action/continuity instructions. The stored end prompt differs from the
main prompt, but contains the same cached concept. OpenAI returned HTTP 400 /
moderation_blocked for that end image before video submission. The diagnostic does
not establish whether the reference pixels, words, output or combination caused
the block. Main-image acceptance does not guarantee reference-edit acceptance.

REDO IMAGE was not necessary. The previous shared status message recommending it
has been replaced; neither the story nor successful main PNG needs regeneration.

## Explicit recovery

Existing ENHANCE now recognises a definitive end-frame policy block and offers its
existing end-image confirmation dialog with a new RETRY VIDEO label. The dialog
states that the story/start image stay unchanged and both end-image and video
requests may incur charges. Declining submits neither request.

POST /videos/{rewrite_id}/retry-safe-end-image requires confirmed=true, the exact
failed attempt UUID, authorised owner and an unused policy-recovery budget. It
verifies the saved start-image hash and refuses to overwrite an existing video.
The revised frame receives a fresh UUID and the old attempt is retained in
end_frame_history. The queue claim is committed before paid work can begin; the
same token cannot be replayed. There is one explicit safe recovery per failed
video claim, with no automatic paid retry.

The description is rebuilt using the existing conservative safe-entity adapter on
a copy of the nomination snapshot. For the known case this retains vicar, fax,
choir, paper, parish ceremony and church setting, and omits explicit anatomical
actions. A new end frame is generated independently: the start PNG is not uploaded
to the image provider again. Safe props, composition, artistic style and lighting
instructions provide semantic/style continuity; exact pixel/character continuity
cannot be guaranteed for an independent image. The successful original remains
the actual video start frame, paired with the revised end frame. Existing motion
instructions, style and seed remain in use. No nominated text is changed.

A saved-story hash check rejects edits made between confirmation and job start.
A second moderation block stops with a clear terminal message; no further safe
retry token is exposed. Uncertain failures retain their existing explicit recovery
rules. Existing-video checks at both claim and worker stages prevent overwrites.
No prompt obfuscation, relaxed moderation or provider bypass was introduced.

## Optional endpoint considered

WaveSpeed's model documentation marks last_image optional:
https://wavespeed.ai/docs/docs-api/wavespeed-ai/wan-2.2-i2v-480p-ultra-fast
The local transport already supports omitting it. A mocked transport regression
confirms omission sends only the start image. It is not used as an automatic
fallback here: the app's existing motion workflow explicitly transitions between
two supplied endpoints. The selected recovery retains that behaviour and a
controlled final comic scene instead of silently changing the video workflow.

## Error presentation

The old completion paragraph was absolutely positioned at bottom:-82px outside
the parchment. Completion errors could also be duplicated into the separate
page-status element, which conflicted with the overlapping parchment layout.

The existing completion status is now a styled normal-flow panel inside the
article, spanning both desktop grid columns and wrapping on small screens.
Responsive bottom padding reserves the upper footprint of the existing action
buttons. Errors for visible creations go into this panel rather than outside the
paper. Live/atomic status semantics, programmatic error focus, focus indication
and a labelled/described native confirmation dialog support screen readers and
keyboard users. Controls retain their native tab order. Styles/script cache keys
are advanced. The source/story/media regions and helper artwork are untouched.

## Verification and limits

122 Python tests plus 6 subtests and 68 JS tests pass; six existing deprecation
warnings remain. Coverage includes full stored vicar text, policy classification,
independent frame generation, unchanged main image bytes/result fields, confirmed
and declined recovery, replay/repeated blocks, changed text, late video creation,
optional transport, historical Gallery/EDIT and existing nomination races.
Syntax and diff-whitespace checks pass. A stale static assertion expecting the
old literal CREATE fetch call was aligned with the already implemented path-based
restoration; no CREATE code changed. The accessibility test now allows a focusable
notification while confirming buttons/links remain in native tab order.

No connected browser surface was available. Responsive rules/markup are tested,
but real desktop/mobile screenshots and visual fit remain unverified. No live
image/video call, app-server command, historical record change or existing media
regeneration/deletion occurred. Provider acceptance and visual quality of a real
safe frame/video remain unverified; additional charges are never assumed free.

The existing uncommitted helper-position offset is preserved. Local commit only;
no push, merge or deploy.

Changed files: api/videos.py, services/video.py, static/js/gallery/promotion-gallery.js,
static/css/gallery/promotion-gallery.css, templates/promotion_gallery.html,
tests/python/test_video.py, tests/python/test_promotion_gallery.py,
tests/frontend/gallery_enhance.test.js, tests/frontend/gallery_notice_layout.test.js,
tests/frontend/video.test.js, CURRENT_WORK.md and this report.

## Follow-up: popup-only presentation

Andy requested removal of the visible status box shown beneath the story/image.
The completion status is now screen-reader-only, with no border or layout space.
The recovery popup, confirmation and cost warning remain unchanged. Removed
automatic focus on the now-invisible status, and advanced Gallery asset versions.
