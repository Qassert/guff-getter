# Gallery EDIT text persistence — 2026-11-09

STATUS: REVIEW
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
