# Gallery remembered sorting — 2026-11-12

## Behaviour and placement

The Gallery now has RANDOM and LATEST FIRST parchment buttons immediately below
main navigation and above the nomination content, following the written placement
requirement. This is a remembered preference, not a physically sticky toolbar.
The existing funky-button texture, typography and glow are reused. Selected
buttons have a darker parchment, a 2px depressed position, inset shadow and
underline, with aria-pressed state. Native button keyboard behaviour, focus rings,
small-screen padding and reduced-motion support are retained.

The selected mode uses localStorage key newsmuncher.gallery.sort. Missing/invalid
preferences default to RANDOM. Storage access failures fall back to a working
in-memory choice. Returning/reloading restores the selected button before the
first nomination is displayed. No account/database preference field is created.

## Full-collection retrieval

The existing one-item /promotion-gallery/next API accepts sort=random|latest and
an optional bounded seed. It defaults to random; the old three-newest preamble is
not used by the Gallery's explicit sorting modes. Existing internal callers that
omit a mode retain their original selector behaviour for compatibility.

Both modes examine only the existing projection of nomination ordering metadata,
then load one selected record. There is no database $rand/full-content random sort
or media/provider request introduced by sorting.

RANDOM uses a fresh per-controller cycle seed and deterministic SHA-256 ranking
of seed plus nomination ID. Selecting the lowest unvisited rank yields a stable
permutation for a fixed collection without sorting the whole candidate set.
Shown IDs are excluded throughout the current cycle, and a new seed starts after
the full cycle. Immediate repetition at a cycle boundary is avoided when more
than one nomination exists. Back/forward history preserves already viewed items.
A collection containing just one item necessarily repeats when browsing again.

LATEST FIRST selects the maximum chronological key among all remaining entries,
not just three entries or those cached in the browser. It uses nominated_at first,
then the existing legacy creationDate fallback, with descending nomination ID as
a deterministic tie-break. Invalid/missing dates follow dated entries. Media and
last-edited timestamps are ignored. It wraps after the entire collection is seen.

Mode switching immediately saves the preference, clears history/forward/shown
cursors, renews the random seed, cancels pending selection/enhancement work and
loads the new order. Existing sequence/abort guards discard stale responses.
Pending animated arrow, EDIT and PROMOTE actions are cancelled on mode changes,
so delayed callbacks cannot skip or act on the newly sorted nomination.

The new row spans the desktop grid. Existing image measurements now also supply
arrow vertical alignment, keeping arrows alongside the image after the toolbar
adds height. Mobile options wrap if needed. No helper positioning code changed.

Sorting only reads nomination data. Existing display receipts/view-count
acknowledgements continue as before when a nomination is displayed; no sort field,
story, nomination/media identity or media metadata is modified by selection.

## Validation

84 Python tests pass: new full-collection/random-seed/date/tie/API-validation tests
and existing Gallery, ENHANCE, historical EDIT, saved-text and video regressions.
Four existing dependency/datetime warnings remain. 68 JS tests pass: sort defaults,
persistence, blocked storage, cursor reset, seed stability, stale responses,
correct nomination identity, delayed-action cancellation, selected styling and
existing Gallery/EDIT/ENHANCE/video/nomination flows. Syntax/diff checks pass.

Desktop/mobile layout is covered by markup/CSS regressions, not live visual
browser inspection: there is no connected browser surface available. No paid
requests, real nomination writes, app-server commands, push, merge or deployment
were performed. The existing uncommitted 65px helper offset remains untouched.

Changed files:
- newsmuncher/services/promotion_gallery.py
- newsmuncher/api/promotion_gallery.py
- newsmuncher/static/js/gallery/promotion-gallery.js
- newsmuncher/static/css/gallery/promotion-gallery.css
- newsmuncher/templates/promotion_gallery.html
- tests/python/test_gallery_sorting.py
- tests/frontend/gallery_sorting.test.js
- CURRENT_WORK.md and this report

## Placement follow-up

Andy’s subsequent screenshot moves the toggle below the story on the lower-right
side of the parchment. The toggle is now inside the copy column, after the fitted
story region, aligned right in normal flex flow. Space is reserved so it cannot
cover story text; desktop overflow permits the existing button glow. The original
pressed state and preference/selection logic are unchanged.
