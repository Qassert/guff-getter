# Nomination/media association investigation — 2026-11-11

## Evidence and limits

Inspected the existing logged-in Chrome window read-only, initially BUILD and
subsequently Gallery (the agent did not navigate, refresh or click). The exact
nomination the user originally considered incorrect has not been confirmed.
No browser request history from the original incident was available. No paid
calls, regeneration, deletion or modification of persisted media were performed.

- BUILD showed the fax/divorce/Councillor Pritchard story. Sidecar rewrite
  `4ef51dc0-f919-4f10-bbd1-549056c088ae` contains that exact text and nomination
  entry `349bbfda9df8f9c82f85e6dd`. The stored image attempt and video use the
  same rewrite ID. Image generation completed at 19:04:08 UTC.
- Its actual image prompt uses the media-safe-v3 fallback concept:
  "A surreal British editorial scene in an eccentric civic hall, where puzzled
  figures inspect an elaborate household contraption while harmless everyday
  objects behave with solemn ceremonial importance."
  The stored description records `sanitised: true`, category `sexual`; the
  existing detector matches `manboob`. The end-frame prompt uses the same
  generic concept. The video transition prompt morphs between those supplied
  endpoint images. This is deliberate loss of story specificity in the existing
  sanitiser, not evidence of a prior story being substituted. Prompting and
  sanitisation have NOT been changed.
- Gallery showed rewrite `62ac9002-9aee-472f-9b06-5b6ac7722852`: clock,
  Charlotte Brontë's birdhouse, rack, man-of-wars and manatee. Its legacy sidecar
  record in the original checkout was read via SQLite read-only mode. Its stored
  image prompt contains the full matching story and Aurora style (generated
  2026-09-30), and its video rewrite ID matches. Visible image subjects also
  broadly match. This older record is not evidence of the reported rapid sequence.

## Trace

BUILD reads the editable story on NOMINATE and POSTs that captured story and
headline relationship to `/build/draft`, which creates a unique rewrite. Shared
`bankThisBeauty` POSTs editable title/body to `/temp/confirm_data?rewrite_id=...`.
`bank_image_rewrite` persists those fields under the owner-scoped rewrite and
nomination entry, and derives the shared media description from a title/body
source hash. Image generation saves the actual prompt and attempt ID on that
rewrite. Video preparation references the rewrite's start image, description,
end frame and source hash; its saved metadata includes rewrite ID and provider
request ID. A correct association does not ensure the generated image resembles
the story when sanitisation has intentionally replaced the concept.

## Confirmed races and fixes

1. A delayed BUILD draft response previously attached its ID and body without
   checking the current generation. It could replace B with A and then nominate
   under A's ID. BUILD now captures the generation sequence and text before the
   await. A late response banks the original snapshot through an explicit ID/text
   argument, without attaching it to B. Current nominations retain the ordinary
   shared media path. Detached old confirmations do not start media in the newer
   page's controllers; this preserves existing stale-UI cancellation behaviour.
2. An old confirmation's finally handler previously cleared a newer nomination's
   pending flag, and its jingle discovery ran outside the identity guard. Both
   now require the captured rewrite ID and generation sequence to remain current.
3. The embellishment coordinator now rechecks its revision after awaiting video
   status, before starting dependent generation on mutable media controllers.

Already submitted backend jobs retain their original IDs. Generating another
story still cancels obsolete UI follow-on work; this patch does not introduce a
background job queue or guarantee that not-yet-started old video work is launched.
No artificial delay or creative-prompt change was introduced. No evidence links
these reproducible code races to either inspected persisted record.

## Validation

- 40 focused JS tests: BUILD generation, nomination snapshots, stale confirmations,
  out-of-order images, delayed video status, existing image flow and CREATE actions.
- 19 further JS tests: video, jingles, media orchestration and image background.
- 66 Python tests plus 6 subtests: image generation, shared media description and
  video; providers mocked. Four existing dependency/datetime deprecation warnings.
- Syntax checks for all three changed JS modules; `git diff --check` passes.
- No live reproduction involving paid generation, and no restart of the app.
- Pre-existing uncommitted `mad-helper.js` upper-helper 65px offset preserved.
