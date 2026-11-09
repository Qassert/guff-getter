# Gallery EDIT text persistence — 2026-11-09

STATUS: VERIFIED — real browser
OWNER: CODEX
BRANCH: develop

## Root cause

Gallery serializes Mongo's crazyReplacement1Extract directly as body, not a preview,
summary or truncated field. Its API requests already use no-store. CREATE's editable
response textarea only called responseEdited(), which changed nomination controls;
per-tab adoption draft storage retained the edit. Reopening EDIT could overlay that
local text on the SQLite-backed editor response while Gallery continued reading the
unchanged Mongo record. No ordinary navigation save synchronized those two paths.

The explicit nomination-update path was unsuitable as an automatic text save because
bank_image_rewrite invalidates/unlinks image state after text edits. This fix leaves
that broader media lifecycle intact and provides a separate text-only save.

## Fix

- PATCH /temp/creation/{rewrite_id}/text validates active-pet ownership of the durable
  SQLite rewrite and matching Mongo record. It $sets only crazyReplacement1Title and
  crazyReplacement1Extract, then updates the editor's durable SQLite result. It does
  not change original source title/extract, other records, nomination timestamps,
  promotion flags, image metadata, files, audio, video or media-generation state.
- Existing saved/nominated stories autosave on editing. Saves are serialized; an
  edit made while a save is in flight is saved next. Explicit UPDATE NOMINATION for
  an already-saved creation uses this same text-only path instead of media invalidation.
  New draft nomination is unchanged. Save status is visible beneath the response.
- Normal CREATE/BUILD/GALLERY navigation awaits pending edits. Failure blocks that
  navigation with a visible message; local draft preservation remains available.
  Pagehide also attempts a keepalive text save for browser departures.
- Local drafts record which text was acknowledged by the server. A saved local copy
  cannot replace newer server text on reopen. Unsaved and legacy local edits remain
  recoverable and can be saved, fixing the original reported situation.
- A Gallery restored from BFCache re-reads its current item through the existing
  read-only API. This preserves the displayed identity, does not regenerate media
  or count another view, and is not a page-refresh workaround for failed persistence.
- Related frontend cache versions were advanced. No database migration was needed.

The canonical edited story remains in the existing rewritten-text fields. The model
has separate original source fields, which are preserved; this change does not invent
or delete a separate original-generated-story archive.

## Files

Backend: newsmuncher/api/previews.py.
Frontend: creation/script.js, new creation/story-text-save.js, shared/mode-nav.js,
gallery/promotion-gallery.js. Templates: pet_profile.html, build.html and
promotion_gallery.html for helper loading, save status and cache versions.
Tests: new python/test_gallery_text_edit.py and frontend/gallery_text_edit.test.js;
updated frontend/create_copy.test.js asset version. Handover: this note and CURRENT_WORK.md.

## Validation

- `node --test tests/*.test.js tests/frontend/*.test.js`: 215 passed.
- `MONGO_URI=mongodb://127.0.0.1:27017 python -m pytest tests/python/test_gallery_text_edit.py tests/python/test_promotion_gallery.py tests/python/test_image_generation.py tests/python/test_draft_lifecycle.py tests/test_adoption_access.py tests/test_build_generation.py tests/test_build_page.py -q -p no:cacheprovider`: 149 passed plus six subtests; 15 existing deprecation warnings.
- New real-route tests use temporary SQLite and fake Mongo: edit/save, repeated
  Gallery reads, fresh clients, editor reopen, durable store reopen, owner rejection,
  failed save, unchanged-save idempotence and unchanged other records/media/state.
- Frontend fixtures exercise normal navigation waiting for save, blocked navigation
  on failure/retry, rapid-edit serialization, Gallery resume and protection against
  stale acknowledged local copies overwriting server text.
- JavaScript/Python syntax and git diff checks pass. No production story was edited,
  no paid providers were invoked, and no browser test against real user records was
  performed. Navigation behaviour is tested in Node fixtures.

## Handover

Local develop commit only; no push, merge or deployment. The separate original
NewsMuncher worktree's prompt edits and untracked media remain untouched and excluded.

## Real-browser verification follow-up

Andy subsequently authorized restarting the local server at 0351c5b, verifying with
a disposable story, removing only that test data and pushing develop if all checks pass.
This supersedes the earlier local-commit-only handover restriction.

Verification used native Google Chrome against http://127.0.0.1:8000, the real local
application, its existing adopted-pet session, MongoDB and durable editor store:

- Created exactly one clearly marked disposable nominated story, with a synthetic
  image, copied fixture audio, synthetic one-second video and disposable source fields.
  No generation provider was called. Captured hashes of all other story records.
- Gallery displayed that fixture; EDIT loaded its original text. Changed the text
  and immediately used the Gallery navigation control. The PATCH text save returned
  200 before Gallery's GET, and Gallery displayed the edited text.
- Refreshed Gallery: the edited text remained. Reopened EDIT: it loaded the edit.
- Opened EDIT in a fresh tab without that tab's previous local draft: it loaded the
  latest durable text, demonstrating this was not browser-storage-only preservation.
- Temporarily stopped only the local development server. Changed the fixture again
  and clicked Gallery. Navigation stayed in EDIT; the new text remained visible and
  the explicit failed-save status appeared. Mongo retained the last successful text.
- Restarted the server and retried Gallery navigation. The UI showed saved status,
  PATCH succeeded before navigation and Gallery displayed the recovered edit.
- Compared both durable stores and fixture record fields. Only story body and view
  counter changed. All source/media metadata and all original image/audio/video file
  bytes were unchanged. Every non-fixture story matched its original baseline hash.
- Closed the disposable editor/Gallery tabs. Deleted only the manifest-matched test
  Mongo record, its SQLite rewrite state, six test view receipts and five UUID-named
  media files (including local video derivative files). Verified no fixture jingle
  state remained and all other Mongo records still exactly matched the baseline.
- No production deployment, paid generation, credential or billing changes occurred.
  The local development server remains running with the verified code.

The earlier statement that real-browser verification was pending no longer applies.
Only handover documentation was changed during this verification; implementation
remains 0351c5b. Final automated verification again passed 149 Python tests plus six
subtests and 215 JavaScript tests with mocked dependencies/dummy Mongo configuration.
