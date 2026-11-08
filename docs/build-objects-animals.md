# BUILD OBJECTS animal expansion — 2026-11-08

STATUS: REVIEW
OWNER: CODEX

## Implementation

BUILD loads the static `newsmuncher/static/data/build-stuff.csv` through its existing
`data-stuff-url`. `BuildWorkshop.load()` parses the CSV; `candidate()` chooses an
existing weighted phrase structure and samples its word banks, excluding words in
other active slots. USE commits the formatted phrase to the recipe; `renderRecipe()`
and `resetPrompt()` insert it into the editable prompt. Word spins and phrase spins
continue to use the same banks. No database, external vocabulary API or dependency
is involved.

Appended 683 unique real animal names to the existing `object` bank, preserving every
original CSV byte (1,442 object entries, 857 devices, 73 adjectives and 97 surreal
descriptors). Familiar animals, aquatic life, unusual mammals, birds, reptiles and
invertebrates include every specifically requested animal. Names were curated from
the animal portion of the existing `animalsAndObjects.csv` resource and supplemented
with specific real animals. Concatenated source names were spaced; fantasy creatures,
extinct examples, hybrid placeholders and breed/strain placeholders were excluded
from the additions. The source resource itself is unchanged.

The object slot occurs in 75% of the existing weighted structures. Uniform selection
from 2,125 object-bank entries yields 0.75 × 683 / 2,125 = 24.1% animal-containing
STUFF phrases before active-slot exclusions. This is an expected probability, not a
quota; ordinary random variation and existing duplicate avoidance remain intact.
Animals retain the `object` category, controls, formatting and OBJECTS label.
CREATE's separate vocabulary CSV is unchanged, as are prompt construction and all
MUNGE generation code. No additional requests or dependencies were introduced.

## Validation

- `node --test tests/build_animals.test.js tests/build_workshop.test.js tests/build_generation.test.js`: 24 passed.
- New focused tests verify the original CSV prefix hash, all original bank entries,
  required animals, every added animal's reachability, 30,000 seeded candidate draws
  within the requested 20–25% range, USE-to-editable-prompt flow, preservation of a
  manual prompt edit and mocked MUNGE 30/60/90 requests.
- `/Users/andrewwhite/GIT/NewsMuncher/.venv/bin/python -m pytest tests/test_build_page.py tests/test_build_generation.py -q -p no:cacheprovider`: 25 passed, six dependency deprecation warnings.
- `git diff --check`: passed.
- No live provider, paid generation, database write, push, merge or deployment.
- Browser/live-generation verification was not performed; generation validation is mocked.

## Git isolation

Andy explicitly authorized proceeding alongside nine existing modified files.
All nine were inspected and SHA-256 checked unchanged before staging. They contain
Maximum Mungery, headline generation, template cache and related test/handover work.
`CURRENT_WORK.md` was deliberately left untouched; this separate note provides the
animal enhancement handover. Only the BUILD CSV, new animal test and this note belong
to this task's commit. Existing work remains uncommitted and must be preserved.
