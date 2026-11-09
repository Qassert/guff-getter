# Early adoption access and work preservation — 2026-11-09

STATUS: REVIEW
OWNER: CODEX
BRANCH: develop

## Investigation and access rules

Existing adoption uses the HttpOnly active_pet cookie and pets.adopted in the pet
collection. Gallery additionally uses gallery_session with server-side expiry,
adopted-record and password-version validation. No alternate adoption flag, local
identity tracker or new authentication scheme is introduced.

AdoptionAccessMiddleware checks CREATE profiles and /create, /build and the Gallery
page before rendering, including direct requests and refreshes. /create resolves to
the current adopted pet profile. Missing/stale adoption redirects to the existing
pet chooser with a validated local next destination and a clear explanation.
The existing selection, adoption and password-login experience carries next through
validation errors and successful submission. Profile return URLs resolve to the pet
just adopted/signed into; Gallery's sign-in link now returns to Gallery. Arbitrary
external targets and adoption-page loops are rejected.

A valid existing gallery session can recover active_pet through the existing
session validator. Existing downstream cookie-based handlers receive that recovered
identity. Gallery still applies its own authentication and CSRF/ownership checks.
A valid legacy active_pet pointing at an adopted record keeps its prior CREATE/BUILD
access; this work does not replace that legacy authorization model.

The read-only /pets/adoption-status endpoint uses the same validation. Clients check
it before MUNGE and when a mode page returns from browser back/forward cache. The
server also guards CREATE and BUILD MUNGE/draft POSTs against late expiry before any
provider operation. Missing adoption returns JSON 401 with an adoption URL, rather
than redirecting POST fetches to HTML. Database/status failures leave existing work
in place and report a retryable error. Guarded responses are private/no-store.

## Work preservation

The shared client helper stores work only in per-tab sessionStorage, separately for
CREATE and BUILD. It saves on input/change, pagehide, navigation and before automatic
adoption redirection. Failed storage blocks that automatic redirect and explains
that the current page must remain open. No password or adoption status is stored.

BUILD stores slots, selected recipe, next slot ID, prompt text, automatic/manual
prompt mode, length target, generated/edited story and headline relationship. Restore
clears transient spin locks and makes the retained story usable without generating
again. CREATE stores editable source/response text, attribution fields and its
existing rewrite ID. Existing authorized server draft/media recovery is reused, then
unsaved local edits are reapplied. An explicit Gallery rewrite link takes precedence
over a different stored CREATE draft. No paid media recovery or generation is automatic.

CREATE preflight precedes loader/reset work. Failed generation retains its old image,
source, response and nomination-button state. Image/jingle reset happens only after
a successful result. The MUNGE engine is captured synchronously before awaiting the
adoption check, preserving current/radical selection. BUILD likewise checks before
changing its prompt/length/result state. In-flight double clicks are guarded.

Drafts last for the browser tab session. Source/response text and BUILD recipe state
are restored locally; media/action recovery still requires authorization for the
original server draft. Storage-disabled browsers stay on the working page when an
automatic adoption redirect would otherwise risk losing a draft.

## Validation

- `node --test tests/*.test.js tests/frontend/*.test.js`: 209 passed.
- `python -m pytest tests/test_adoption_access.py tests/test_build_page.py tests/test_build_generation.py tests/python/test_object_generator.py tests/python/test_swear_generator.py tests/python/test_jingles.py tests/python/test_jingle_frontend.py tests/python/test_promotion_gallery.py tests/python/test_image_generation.py tests/python/test_external_content_sources.py -q -p no:cacheprovider`: 163 passed plus six subtests; 12 existing dependency/datetime deprecation warnings.
- New tests cover real-app guard wiring, direct/repeated navigation, missing/stale
  pets, valid existing adoption and login sessions, same-origin return validation,
  adoption/login success and failure, existing Gallery authentication, BFCache checks,
  storage failure, CREATE/BUILD draft restoration, selected MUNGE engine and failed
  generation preservation. Browser lifecycle and client state are tested with Node
  fixtures; real browser visual verification remains pending.
- JavaScript/Python syntax and git diff checks pass. No live database or paid-provider
  calls were performed. Story models, prompts and length contracts are unchanged.

## Git handover

Implemented in the clean develop worktree at NewsMuncher-Build. The separate
NewsMuncher worktree's unrelated prompt edits and untracked media were not edited,
staged or committed. This task is committed locally only; no merge, push or deployment.
