# BUILD two-word modifiers — 2026-11-08

STATUS: REVIEW
OWNER: CODEX

## Source and behaviour

BUILD loads `newsmuncher/static/data/build-modifiers.csv` using its existing static
CSV loader. Entries are complete phrases, never dynamically assembled. The existing
controller selects an `adverb` or `adjective` bank at random and samples one entry.
The whole phrase remains one clickable part, with its grammatical label displayed
beneath it. USE stores the phrase and label in the recipe; the phrase is included
in the editable MUNGE prompt. No controller, template or generation changes were needed.

## Vocabulary

- Replaced all 41 single-word entries: 40 adverbs and one adjective.
- Preserved all 39 existing two-word adjective phrases.
- Added 40 further two-word adjective phrases.
- Final pool: 120 unique entries, comprising 40 adverbial phrases and 80 adjective phrases.
- Every entry contains exactly two whitespace-separated words; hyphenated words
  such as `well-endowed` remain one word.
- ADVERB labels describe complete adverbial adjuncts: manner, place, time or
  circumstance (for example `without dignity`, `via trebuchet`, `during autopsies`,
  `suspiciously tenderly`). ADJECTIVE labels describe complete noun-modifying or
  predicative phrases (for example `criminally flamboyant`, `vindictively absorbent`).
- Category-first random selection is unchanged: ADVERB and ADJECTIVE each retain
  a 50% chance, despite the larger adjective vocabulary. Duplicate avoidance and
  phrase capitalisation remain unchanged.

## Validation

- `node --test tests/build_modifiers.test.js tests/build_animals.test.js tests/build_workshop.test.js tests/build_generation.test.js`: 29 passed.
- Five new tests cover exact two-word counts, unique complete phrases, retained
  labels and existing phrases, editorial grammar guards, every entry's reachability,
  3,000 seeded draws, whole-slot SPIN, individual phrase spin, USE, recipe removal,
  slot removal/minimum, + SLOT, prompt insertion and mocked 30/60/90 submissions.
- `/Users/andrewwhite/GIT/NewsMuncher/.venv/bin/python -m pytest tests/test_build_page.py tests/test_build_generation.py -q -p no:cacheprovider`: 25 passed, six existing dependency deprecation warnings.
- `git diff --check`: passed. Animal and other BUILD regression tests pass.
- No live provider calls or browser verification. Generation requests are mocked.

## Isolation and handover

Andy authorized working alongside the nine existing modified files only with
complete isolation. Their SHA-256 hashes remain unchanged. Only the modifier CSV,
new modifier tests and this note are part of this task. `CURRENT_WORK.md` remains
untouched to preserve its existing changes. All other ingredient data, UI code,
story prompts, models, endpoints and word limits are unchanged. No push, merge or
deployment was performed. Reload BUILD to review the vocabulary in the browser.
