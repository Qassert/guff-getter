# Automatic safe media recovery — 2026-11-11

## Confirmed evidence

Read-only inspection of the local SQLite sidecar found multiple main-image
attempts rejected externally with HTTP 400, code `moderation_blocked`, and a
stored safety-system message. The latest candidate rewrite is
`76359564-d3e5-460e-a265-430258ce960f`. Its exact submitted prompt is preserved in
`image_attempt.prompt`; the nominated story and media description are separate.
It used Surreal art and a v4 concept which neutralised `manboob` but retained
explicit anatomical actions involving the vicar and fax. The stored provider
message reports sexual/violence categories. This establishes external moderation,
not which individual word caused it. No screenshot/failed-record ID was supplied
to uniquely confirm that this candidate is the reported incident. Earlier failed
records similarly contained anatomy terms the local detector did not recognise.
No need to copy full private prompts into a committed report or application log.

Official API guidance documents the `moderation_blocked` code and optional input/
output moderation details:
https://developers.openai.com/api/docs/guides/image-generation

## Changes

- Shared CREATE/BUILD description v5 expands the existing detection rules to cover
  explicit anatomical terms seen in the failed records. It retains v4's benign
  anatomy neutralisation and safe clause retention. Displayed/stored story text
  and nomination/rewrite identity are never rewritten.
- Main images and manual REDO use one shared recovery helper. Only an HTTP 400
  BadRequestError with exact provider code `moderation_blocked` permits recovery.
  All other errors, including billing/auth/rate limits/network/server errors,
  receive no automatic retry. Empty provider responses also no longer receive
  the former non-content automatic retry.
- Recovery creates a genuinely different non-explicit tableau from known ordinary
  objects, named roles and settings in the captured source. Safe actions include
  unrolling fax paper, a clothed choir singing, marching wooden props, sprouting
  seeds or a harmless water fountain. Rejected anatomical actions and wording
  are not disguised, respelled or passed through. Generic fallback is used when
  no supported safe scene entities remain. This straightforward deterministic
  adaptation has a finite vocabulary; unfamiliar scenes can lose specificity.
- Each rejection is archived and a unique replacement image attempt is atomically
  persisted before submitting the single extra request. Both rejection and
  uncertain outcomes remain durable. Replays cannot restart the budget.
- Captured source hashes and attempt IDs are checked before claiming recovery
  and before attaching completed media; changed story snapshots do not receive
  an older image. The recovered description remains cached under the original
  nominated source hash, so subsequent video end frames use that same concept.
- No new nomination is created. Existing race guards remain unchanged.
- Replaced the frontend's edit-and-restore-the-story guidance. Backend terminal
  errors distinguish exhausted content recovery from other request failures.
  Existing manual REDO remains available where outcomes are definitive.
- Logs identify rewrite/attempt, stage, provider code and retry result without
  story text or prompts. Existing persisted attempt data retains diagnostics.

## Video and costs

Video motion prompts describe continuity between the supplied images; end-frame
images use the same shared description. No automatic video submission or endpoint
retry was added: the existing single-claim/explicit recovery cost controls remain
intact. A blocked end frame still terminates with its structured diagnostic.

At most one extra potentially billable image call is made for a qualifying main
image or manual REDO request. No claim is made that rejected requests are free.
Revision itself uses no API call, dependency or paid language-model generation.
All investigation and tests used mocks/read-only records: no paid calls, existing
media regeneration/deletion, app restart, push, merge or deployment occurred.

## Validation and handover

91 Python tests plus 6 subtests pass (recovery, shared descriptions, main images,
REDO, video), with four existing dependency/datetime deprecation warnings.
34 JS tests pass (nomination races, embellishment, image flow, video and profile
editing). JS syntax and diff-whitespace checks pass. Coverage includes successful
recovery, repeated rejection, non-content failures, replay during the retry,
uncertain retry outcomes, changed snapshots before/during recovery, immutable
story data/IDs, common video concepts and manual REDO. The video suite confirms
end-frame moderation fails without submitting the video.

One stale profile-editing assertion still expected the negative source margin
removed by the preceding CREATE layout commit; it now asserts the committed zero
margin. No source layout code was changed in this task.

The pre-existing uncommitted Mad Helper 65px positioning change is untouched.
Local commit only; enable the updated application code via the user's normal
server lifecycle. No live provider success claim is made from mocked tests.
