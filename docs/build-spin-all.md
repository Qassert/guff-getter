# BUILD SPIN ALL — 2026-11-09

STATUS: REVIEW
OWNER: CODEX

SPIN ALL is immediately before + SLOT in STUFF's heading. It uses the existing
mini-action class and a wrapping flex button group for smaller screens.

The controller dispatches every current category/slot through `randomiseSlot()`
concurrently, preserving slot IDs and counts. Existing animation, random structure
selection, bank sampling, active-word exclusions and busy-row protection are reused.
Already-spinning rows finish their existing spin; they are not started a second time.
Repeated SPIN ALL clicks are ignored while its operation is running, and the button
is restored in a finally block. No network calls or reloads are introduced.

For SPIN ALL only, identical full-phrase candidates receive up to five further
attempts using the existing candidate method. Tiny pools still terminate. Individual
SPIN keeps its previous single-attempt behaviour. Recipe entries, edited prompts,
generated/edited stories and nomination headline state are not altered.

Changed files:
- `newsmuncher/templates/build.html`: button placement and group wrapper.
- `newsmuncher/static/build-page.js`: delegation, concurrent dispatcher and optional repeat avoidance.
- `newsmuncher/static/build-page.css`: responsive action group only.
- `tests/build_spin_all.test.js`: six focused tests.
- This handover note.

Validation:
- `node --test tests/build_spin_all.test.js tests/build_swear_display.test.js tests/build_modifiers.test.js tests/build_animals.test.js tests/build_workshop.test.js tests/build_generation.test.js`: 39 passed.
- New tests cover placement, all-category updates, changed row suggestions, slot IDs
  and counts, frozen recipe preservation, edited prompt/story and headline state,
  concurrent delegation, repeated clicks, bounded repeat avoidance, individual SPIN
  behaviour, busy-row guards, failure cleanup and delegated click wiring.
- `/Users/andrewwhite/GIT/NewsMuncher/.venv/bin/python -m pytest tests/test_build_page.py tests/test_build_generation.py -q -p no:cacheprovider`: 25 passed, six existing dependency deprecation warnings.
- `node --check newsmuncher/static/build-page.js` and `git diff --check`: passed.
- Browser visual verification was not performed. Existing cache keys are preserved;
  hard-refresh BUILD when reviewing updated frontend assets.

Andy expressly authorized isolated edits in the already-modified template and
controller. Removing only the SPIN ALL additions reproduces both original working
files exactly. The seven other pre-existing modified files remain byte-for-byte
unchanged. CURRENT_WORK.md was left untouched; this note is the separate handover.
All work remains unstaged and uncommitted for review. No push, merge, deployment,
paid generation, provider calls or production database writes occurred.
