# BUILD interactive ingredient and direction panels — 2026-11-12

## Interface

BUILD now shows two layered parchment sheets inside its existing recipe parchment:
INGREDIENTS and FURTHER INSTRUCTIONS. The first contains the existing categorized
removable chips plus a custom-ingredient form. The second has an optional multiline
100-character field, live counter and CLEAR button. MUNGE 30/60/90 remain beneath
the controls. Paper borders reuse the existing parchment texture; chips and inputs
wrap, panels grow naturally, and narrow layouts stack the custom input/button.

The technical editor remains available in a closed-by-default ADVANCED PROMPT
disclosure, including RESET PROMPT. Its default comedy rules are unchanged.
The recipe helper anchors to the visible INGREDIENTS heading instead of a hidden
technical textarea; helper JavaScript, animation, sounds and saved preference are
unchanged. Styles/script cache versions are advanced.

## One recipe state

The original recipe object remains authoritative. Custom entries live in its
custom array, rather than an independent list or CSV. USE above selects an
ingredient and visibly indicates aria-pressed=true; using the same selected row
again removes it. Chip removal updates that same array, upper USE state and the
canonical prompt section immediately. SPIN, SPIN ALL and slot controls still act
only on their existing suggestion state; custom entries are never randomised.

Custom inputs normalise whitespace, preserve case/punctuation, and reject empty,
duplicate and oversized entries. There are at most 12 custom entries, each at most
160 characters. Frontend chips escape HTML; backend custom-list validation repeats
normalisation/uniqueness checks. Existing aggregate recipe (4000 characters) and
prompt/request limits remain. Nothing updates shared ingredient pools.

## Prompt assembly and snapshots

The existing creative prompt and output/length rules remain. Recipe rendering and
generation rebuild only the canonical selected-ingredients section. Advanced
manual edits outside that section survive; the section itself follows the chips
and is not an independent ingredient editor. Noncanonical old advanced text keeps
its creative prefix while acquiring a fresh canonical ingredient/output section.
Line-anchored section markers prevent punctuation in custom text being mistaken
for a prompt boundary.

Each generation serialises the then-current recipe, target, advanced prompt and
further_instructions. Later edits cannot mutate that JSON request. Backend
validation caps further_instructions at 100 characters, canonicalises selected
recipe lines, applies the existing length instruction, and appends directions as
an additional creative preference within the established task/constraints. The
existing higher-priority developer instructions, provider/model/structured output,
response limits, error handling and story editing remain unchanged. No previous
story is added to the prompt, and no new prompt logging is introduced.

Further directions survive ingredient changes and RESET PROMPT; CLEAR empties
them explicitly. Draft snapshots/restoration include custom recipe entries and
directions. Older drafts gain an empty custom list and empty directions, retaining
existing recipe/prompt/story fields. The new API fields are optional, so callers
without custom entries/directions continue to work. Source, nomination and media
endpoints/workflows are unchanged.

## Validation and limits

87 JS tests pass: BUILD ingredient pools/controls/SPIN ALL, new chips/custom inputs,
USE/remove synchronisation, HTML escaping, instruction limit/counter, all three
request snapshots, manual-rule preservation, malformed marker handling, new/old
draft restore, nomination races, shared helper and text fitter. 67 Python tests
pass: existing BUILD routes/provider mocks plus custom-only generation, exact
length targets, directions reaching the provider and invalid-input rejection
before generation. Six existing dependency/cookie deprecation warnings remain.

A rendered Jinja check verifies both panel headings/order, a closed advanced
editor, the 100-character control, MUNGE placement and the visible helper anchor.
Syntax and diff-whitespace checks pass. Live desktop/tablet/mobile browser visual
inspection was not performed. No paid generation, CSV/database/media changes,
app-server commands, push, merge or deploy occurred. An approval-review timeout
was resolved with a smaller local-only rendering check using the existing venv.

The pre-existing uncommitted helper-position 65px offset remains untouched.

Changed files:
- newsmuncher/templates/build.html
- newsmuncher/static/build-page.js
- newsmuncher/static/build-page.css
- newsmuncher/api/build.py
- tests/build_interactive_prompt.test.js
- tests/test_build_generation.py
- tests/test_build_page.py
- CURRENT_WORK.md and this report
