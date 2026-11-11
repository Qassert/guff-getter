# Historical Gallery → CREATE restoration — 2026-11-11

## Confirmed root cause

The supplied Dickens/Gainsbourg story is nomination `ebaba1a0daa768613e7f4010`,
rewrite `259c422f-9760-40ee-bd58-a3bd9154a46e`. Its Mongo record has valid flat
story strings, nominated and legacy-done flags, a valid rewrite ID, owner and
media metadata. The original checkout's SQLite sidecar contains its source and
rewrite state; NewsMuncher-Build's local sidecar does not.

Gallery serialises Mongo text and links to CREATE with rewrite_id. CREATE then
requested `/temp/image_result/{rewrite_id}`, which only read the local sidecar.
That returned 404 despite the persisted nomination being recoverable. The browser
silently returned on non-OK responses. No schema migration is needed. Age is not
the fundamental boundary: newer nominations with missing sidecar state can also
fail, while old nominations with complete local state can succeed.

## Compatibility and data protection

- Shared `creation_restore.py` normalises flat historical fields, JSON-encoded
  result wrappers and missing/null optional fields. It never uses original source
  extract as a replacement for the nominated story.
- Missing or incomplete saved sidecar state can be reconstructed from an exact,
  owner-matched Mongo nomination. Optional source/state recovery reads the already
  configured shared legacy SQLite sidecar using mode=ro, and requires the same
  owner and nomination ID. No provider is called.
- Reconstruction populates only the current worktree's local runtime cache. It
  performs no Mongo updates, historical migration or media-file changes. A
  refreshed restored editor reads canonical saved Mongo text, so another browser's
  saved edits do not leave the editor stuck on its cached version.
- Gallery EDIT retains modern rewrite_id URLs. Entries without one carry their
  nomination_id instead. A deterministic editor-only UUID maps these to the same
  original nomination; explicit text saves update that nomination by its original
  ObjectId and owner. No new nomination or persisted rewrite ID is invented.
- Existing modern local-state handling remains in place. Explicit text saves use
  text-only updates, retaining image/audio/video/source metadata. Ownership and
  identity checks remain enforced, including nullable historical owner metadata.
- Explicit EDIT navigation no longer loads unrelated temporary source material
  or a different session's result. Recoverable source fields populate the existing
  source controls; missing source text stays empty.
- Failed loads show an error while leaving current editor text intact. Request
  tokens prevent late A responses overwriting B. Obsolete media controls clear
  only after a new nomination has successfully loaded. Diagnostics contain IDs,
  not story text or credentials. Merely opening/cancelling does not save edits.

## Verification

The actual known Mongo record was read through a read-only adapter and the updated
endpoint using a temporary SQLite cache. First load and reload returned HTTP 200
and exact saved story equality; original source was recovered, the image URL
matched, and Mongo record equality before/after was true. This was an in-process
API check, not a real-browser test or a write to historical data. No app restart.

70 Python tests plus 6 subtests pass: historical restoration, Gallery text-save,
image lifecycle and Gallery routes. 45 JS tests pass: historical EDIT navigation,
editable text restoration, failures, out-of-order results, saved Gallery edits,
Gallery controls, image flow and nomination races. Syntax and diff-whitespace
checks pass. Existing dependency/datetime deprecation warnings remain.

Regression fixtures use the supplied exact Dickens story and the observed flat
historical record shape; write tests use only fake Mongo and temporary SQLite.
Coverage includes missing IDs, JSON wrappers with null optional fields, CREATE
and BUILD origins, refreshed canonical text, incomplete local state, owner errors,
text saves/media preservation, cancellation and consecutive selections.

No historical story/media was modified, deleted or regenerated; no paid calls.
The pre-existing uncommitted Mad Helper 65px offset is preserved. Local commit
only: no push, merge or deployment.

## Changed files

- newsmuncher/services/creation_restore.py
- newsmuncher/api/previews.py
- newsmuncher/static/js/creation/script.js
- newsmuncher/static/js/gallery/promotion-gallery.js
- tests/python/test_historical_creation_restore.py
- tests/frontend/historical_creation_restore.test.js
- CURRENT_WORK.md and this report
