# BUILD approximate word targets — 2026-11-10

STATUS: REVIEW
OWNER: CODEX
BRANCH: develop

## Behaviour

MUNGE 30/60/90 now aim for approximately the selected number of words. The canonical
length line explicitly permits slight overruns for coherence, comic timing or a
better punchline, favours a complete funny story and suggests fewer ingredients when
crowded. The existing per-length pacing guidance remains. The shared editable
creative instructions and ingredient assembly are otherwise unchanged.

Frontend buildPrompt/applyStoryLength share one length-instruction helper; backend
build_story_prompt/apply_story_length do likewise. Switching lengths replaces only
the reserved Story length line, preserving other manual edits. RESET restores the
updated flexible wording and current recipe. The BUILD JS cache version is advanced.

The provider's higher-priority instruction also follows the approximate user target
rather than imposing a strict maximum. Safety ceilings are 45/90/135 words (150% of
30/60/90), separate from the creative target and not advertised as desired lengths.
The existing 750-token cap, model, single-call/no-retry policy, request validation,
provider error handling, headline bounds and media/nomination flows are unchanged.

No story is sliced at a word or sentence boundary. A complete response within the
safety ceiling is returned whole, including its final punchline. An excessively long
response is rejected through the existing safe response-error path with a retry
message; the current recipe, edited instructions and previous story remain intact.
This chooses the allowed safe-handling alternative over dropping later sentences
and potentially losing the payoff. No automatic paid retry is introduced.

CREATE does not import BUILD's limiter or prompt helpers and its code is untouched.
The original worktree's uncommitted radical prompt/test edits and media remain
untouched and excluded from this commit.

## Validation

- `node --test tests/*.test.js tests/frontend/*.test.js`: 217 passed.
- `MONGO_URI=mongodb://127.0.0.1:27017 python -m pytest tests/test_build_generation.py tests/test_build_page.py tests/test_adoption_access.py tests/python/test_gallery_text_edit.py tests/python/test_promotion_gallery.py tests/python/test_image_generation.py tests/python/test_draft_lifecycle.py tests/python/test_first_pass_prompt.py tests/python/test_munge_engines.py tests/python/test_jingles.py tests/python/test_video.py -q -p no:cacheprovider`: 230 passed plus six subtests; 15 existing deprecation warnings.
- Regression cases cover intact 34/68/102-word stories above the old thresholds;
  exact 45/90/135-word ceilings; rejection of excessive output without partial prose;
  preserved final sentences, previous story and recipe; frontend/backend instruction
  parity; manual edits during length switching; RESET at all targets; and existing
  CREATE, Gallery, nomination, image, video and jingle behaviour.
- JavaScript/Python syntax and git diff checks pass.
- Provider/database operations in tests are mocked; no live/paid generation or
  production database writes were performed. Real-browser/live-generation QA was
  not performed for this wording refinement.

Only BUILD prompt/length handling, its template cache version, affected tests and
handover notes changed. Local commit only; no push, merge or deployment.
