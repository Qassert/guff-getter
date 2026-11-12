# Gallery ENHANCE compatibility — 2026-11-12

## Separate confirmed causes

1. Dickens/Gainsbourg EDIT: nomination `ebaba1a0daa768613e7f4010`, rewrite
   `259c422f-9760-40ee-bd58-a3bd9154a46e` had valid saved Mongo text but lacked
   local rewrite state in this worktree. The previous c8a290f fix restores it at
   read time; those regressions remain passing. Not an age/schema or policy error.
2. Exact vicar story beginning "owing to the right-wing manboob alumni": nomination
   `a9c2877b50a20710efe906fd`, rewrite `5017c24f-e0e6-4f24-acd1-ca1910f954e0`.
   Its full database title/body are in tests/fixtures/fax_vicar_nomination.json.
   Its main image completed. Its referenced video end image definitively failed
   with OpenAI HTTP 400 / moderation_blocked / sexual category. The saved video
   error stage is end_image. The video submission was therefore not reached.
   This is not the Dickens missing-state problem, an invalid payload/ID, a BUILD
   validation failure or an age-specific format failure.

The retained image/end-image prompt predates a body edit ("because ... banned
postmen" versus the currently saved "owing to ..."). Story edits deliberately
preserve existing media. This is not evidence of another nomination being used.
The exact trigger term cannot be established from the coarse provider rejection.

## Changes

ENHANCE follows Gallery complete(): prepare selected nomination, read current
stored item, generate only missing image/video/jingle, then refresh that item.
Preparation previously duplicated older loading logic and could fill missing text
back into Mongo. It now reuses CREATE's owner/nomination-checked restore helper and
read-time JSON/optional-field normalisation. Known text can come from matching
local/legacy state; original source text is never invented as rewritten text.
Subsequent item reads apply the same title/body compatibility interpretation.

Preparation is local-only and no longer writes Mongo story or identity metadata.
For genuinely old records missing required media identity/owner/nomination flags,
the app asks the user to confirm a compatibility update before generating media.
A separate confirmed endpoint validates owner and a saved-text revision hash,
then conditionally commits only rewrite_id, image_owner and nominated. Concurrent
text/ownership changes abort the commit. Story/source/media fields remain intact;
cancelling does not change the saved record. Existing local recovered text is
retained across the explicitly committed identity. Invalid non-empty identities
require review rather than being silently replaced. Modern records need no
confirmation or metadata update.

An initial proposed edit retaining implicit metadata writes was rejected by
automatic approval review before execution. The implemented read-only preparation
and separately confirmed commit replace that design. No live commit endpoint was
called during investigation; its write tests use fake Mongo only.

The ENHANCE controller captures nomination ID, prepared rewrite ID, saved title/
body and operation token. Checks before/after asynchronous stored/provider calls
prevent old selection work from submitting new generation or applying responses
to another nomination. An old finally handler cannot clear a newer operation's
busy state. A changed saved story stops safely rather than continuing with stale
text. Provider payloads retain the selected rewrite ID.

Video status exposes failure_kind=content_policy and failure_stage=end_image for
definitive moderation blocks. Gallery reports that policy failure instead of an
uncertain/pending outcome. Main-image terminal moderation failures also have a
structured media_content_rejected code, distinct from data-loading/validation
errors. Existing safety controls, automatic image recovery bounds and paid-video
retry restrictions remain in place. No moderation settings were relaxed.

## Known-case outcome and limitations

Dickens EDIT remains fixed. Vicar ENHANCE preparation was checked with the real
Mongo entry, a read-only collection adapter and a temporary copy of its state:
HTTP 200; exact saved body matched; can_enhance=true; Mongo unchanged. Its saved
status now reports content_policy/end_image and forbids automatic generation.
This does NOT establish successful live image/video completion. The blocked
historical attempt is preserved. A new safe visual attempt must be explicitly
chosen (EDIT → REDO IMAGE); provider acceptance cannot be guaranteed. No old
image, video, nomination or failed attempt was deleted/replaced in this work.

Legacy preparation and successful ENHANCE flows are covered with mocked media;
missing genuinely unrecoverable text gives a data error, not a policy error.
No actual browser or paid-provider test was performed. No app-server commands,
push, merge or deployment were run. The prior uncommitted helper offset remains
untouched.

## Validation

116 Python tests plus 6 subtests pass: new exact-case ENHANCE tests, historical
EDIT, saved text, video, Gallery, image lifecycle and bounded recovery. Six existing
dependency/datetime warnings remain. 47 JS tests pass: ENHANCE, historical restore,
Gallery navigation, nomination races and image flow. Syntax/diff checks pass.

Coverage includes full stored vicar text, Dickens regression, legacy JSON/null
fields, cache-only body/title, new nominations, correct generation payloads,
changed saved text, rapid selection, unexpected IDs, policy-vs-data failures,
read-only preparation, declined/stale/confirmed metadata commitment and unchanged
original story/media. All write/provider tests use temporary stores/fakes.

Changed files: api/promotion_gallery.py, api/previews.py, services/video.py,
static/js/gallery/promotion-gallery.js, tests/frontend/gallery_enhance.test.js,
tests/python/test_gallery_enhance_compatibility.py, tests/python/test_media_recovery.py,
tests/fixtures/fax_vicar_nomination.json, CURRENT_WORK.md and this report.
