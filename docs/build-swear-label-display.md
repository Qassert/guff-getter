# BUILD SWEAR label display — 2026-11-08

STATUS: REVIEW
OWNER: CODEX

## Root cause and fix

BUILD reads complete insult components from `static/data/build-swear.csv`. The
`bijv_nw`, `gilles`, `zelfs_nw` and `handelend` categories are functional bank keys
used in six insult structures. The shared `BuildWorkshop.slotMarkup()` renderer
prints every component category in a `small` element beneath its clickable text;
underscores become spaces and CSS uppercases the labels. These internal keys are
therefore exposed as BIJV NW, GILLES, ZELFS NW and HANDELEND.

Added a CSS rule scoped to `.ingredient-group[data-category="swear"]` that sets
only `.ingredient-word small` to `display: none`. The insult components, underlying
metadata, six structures, random selection, word buttons and action buttons remain
unchanged. Other ingredient labels remain visible. Existing typography, colours,
parchment styling, padding, gaps and card minimum-height declarations are untouched.
No JavaScript or template edit is required. A hard refresh may be needed to reload
the stylesheet; the template's cache key was left untouched to preserve unrelated work.

## Validation

- `node --test tests/build_swear_display.test.js tests/build_modifiers.test.js tests/build_animals.test.js tests/build_workshop.test.js tests/build_generation.test.js`: 33 passed.
- Four focused tests check the SWEAR-only hiding rule and template scope, retained
  labels elsewhere, all six insult structures and metadata, component/action markup,
  SPIN, individual word spin, USE, recipe removal, slot removal/minimum, + SLOT,
  editable prompt inclusion and mocked MUNGE 30/60/90 requests.
- `/Users/andrewwhite/GIT/NewsMuncher/.venv/bin/python -m pytest tests/test_build_page.py tests/test_build_generation.py -q -p no:cacheprovider`: 25 passed, six existing dependency deprecation warnings.
- `git diff --check`: passed.
- Browser visual verification was not performed. Display validation checks the CSS
  selector and rendered markup; generation requests are mocked. No paid/external
  generation or database writes were performed.

## Isolation

Andy authorized proceeding alongside the nine existing modified files only with
safe isolation. Their SHA-256 hashes remain unchanged. The CSS file was clean
before this task; only the CSS, new focused tests and this note belong to the fix.
`CURRENT_WORK.md` remains untouched to preserve its existing changes. No push,
merge or deployment was performed.
