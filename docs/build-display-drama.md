# BUILD complete story display and dramatic creative rules

## Display investigation and fix

Generation inserts the complete API story into responseBodyDraft, reveals outputContainer,
then calls CREATE's autoResize, which schedules the shared ArticleTextFitter on an animation
frame. Draft restoration uses the same path. Input edits also schedule fitting. Existing
observers cover the region, result panel and image panel; font readiness and window resize
also schedule fitting. No frontend story truncation was found.

The fitter trusted the parent content dimensions, allowed one pixel of overflow, and hid
overflow without checking the final textarea viewport. It did not observe changes to the
textarea itself. Thus a smaller final viewport or later textarea-only layout change could
leave the last content clipped with no scroll access. The original ordinary fixture cases
fit successfully; Chrome reproduced the one-pixel hidden overflow, rather than a missing
whole sentence. The larger intermittent user case was not reproduced from a supplied story.

The shared fitter now observes its text element as well, rejects any overflow during
measurement, and checks the final actual viewport. Remaining vertical overflow falls back
to 8px with native vertical scrolling. BUILD prevents independent flex shrink of its textarea,
uses border-box sizing and bounds it to its existing fixed parchment region. Existing region
height, padding, typography and styling remain. No story text is modified. Shared CREATE
and Gallery fitting retain their normal behavior and benefit from the safeguard. BUILD
asset cache keys are advanced.

## Exact added creative rule

Make every story outrageously dramatic. Treat trivial events as catastrophic turning points,
exaggerate emotions and consequences to ludicrous extremes, and build towards an explosive,
ridiculous climax. Deliver the chaos with absolute conviction and deadpan seriousness.

This single rule is added to the matching BUILD frontend/backend defaults. All lengths and
RESET PROMPT use it. Existing manually edited prompts are preserved; no migration overwrites
them. Approximate length instructions and CREATE creative prompts are unchanged.

## Validation

- node --test tests/*.test.js tests/frontend/*.test.js: 221 pass.
- Relevant Python BUILD, adoption, Gallery, image, draft, CREATE prompt/MUNGE, jingle and video
  regressions: 231 pass, six subtests pass, 15 existing dependency/datetime warnings.
- JavaScript syntax checks, Python AST parsing and git diff --check pass.
- Isolated installed headless Chrome, using real shared/BUILD CSS and shared fitter with
  displayBuildStory: longer-than-target 30/60/90 samples fit at 17.55/12.47/10.84px respectively.
  Oversized manually edited text stops at 8px and scrolls within the region. A 210px-wide
  layout also scrolls successfully. Screenshot visually confirms the complete final sentence
  and punctuation at the bottom. All text remains intact and textarea stays within its parent.
- This was a local browser fixture, not a live authenticated generation or provider call.
  Temporary diagnostics are ignored under tmp/. No paid service, database, media or user
  content was changed. No push, merge or deployment authorized.
