# CREATE source layout — 2026-11-11

The MUNGE group was absolutely positioned outside normal flow and the source
editor had a negative trailing margin. Source wrapping could therefore enter the
buttons' painted footprint without increasing the parchment's reserved space.

CREATE's source parchment now reserves half the MUNGE control height in normal
flow. A shared responsive width variable drives both the controls' width and the
reserved height, using their existing 1.18 aspect ratio. The lower half continues
to overlap the parchment transition; negative trailing space is derived from
existing border, padding and transition geometry. A 1em text-to-control gap keeps
prose clear. The negative source-editor margin is removed. Selectors require
#sourceEditor, so BUILD/result panels retain their existing geometry.

Source font changes from 1rem to calc(1rem + 2pt): at the default 16px root this is
16px/12pt to 18.6667px/14pt. The formula preserves an exact 2 CSS-point increase
with a different root font size. Existing family, weight and proportional 1.6
line-height remain unchanged. Generated result typography is untouched.

The existing textarea autoResize function now also runs on source width changes,
window resizing and font readiness. The width guard avoids height feedback loops.
The shared result fitter and helper positioning/interaction code are unchanged.

Validation: 42 JS tests pass across the new source layout/resize tests and
existing result fitter, helper, MUNGE engine and nomination race tests. Syntax and
diff-whitespace checks pass. Mocks cover short/medium/long source heights, width
changes, resize events, font readiness and avoiding source font shrinking.

Chrome browser automation returned "Browser is not available: chrome". Actual
visual checks at desktop/mobile sizes, browser zoom 100/125/150%, and helper
enabled/disabled remain unverified. No app was started or restarted, and no user
session or source/story/media data was changed. No paid generation occurred.

The existing uncommitted 65px helper offset remains untouched. Local commit only;
no push, merge or deploy.
