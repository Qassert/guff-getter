# BUILD quota diagnostics follow-up — 2026-11-09

STATUS: VERIFIED — real-browser generation passed

## Changes

BUILD now classifies provider error.code separately from error.type. A specific
code takes precedence over the broad type. credit_balance_exhausted reports credit
exhaustion; insufficient_quota reports a quota/billing restriction without asserting
an empty balance; organisation/project hard spending limits and the approved
organisation usage limit have distinct messages; rate_limit_exceeded/slow_down and
rate_limit_error identify rate limiting. Unrecognised 429s remain generic failures
rather than being assumed to be rate limiting. Existing credential/model-access
handling and recipe/draft preservation remain intact.

Provider rejection warnings identify endpoint=/build/generate, upstream HTTP status,
separate code and type, and request ID. Only constrained metadata identifiers are
logged; malformed fields and key/token-shaped values are redacted. Exception bodies,
headers, prompts, recipes and generated content are never logged by these diagnostics.

## Exactly one authorised live request

Invoked the actual generate_build_munge handler with a small synthetic input, using
its real generate_build_story service, configured key and existing gpt-6-sol settings.
This was an in-process handler call, not an HTTP/browser request to the running
Uvicorn process; it bypassed navigation/adoption transport but exercised the actual
BUILD payload, prompt-length construction, provider request and response handling.
The SDK client was instrumented only to capture safe metadata. No retries or second
live generation request were made.

- OpenAI HTTP status: 200; response status: completed.
- Handler returned a valid story and headline successfully.
- Request ID: req_d0c0559336e4405e8f0e171d07bedd9f.
- Usage: 226 input tokens and 58 output tokens.
- Model: gpt-6-sol; reasoning effort: none; max_output_tokens: 750; store: false.
- SDK retries: 0. No credentials, actual input text or generated text are recorded here.

## Configuration comparison and conclusion

The running Uvicorn parent/worker use NewsMuncher-Build and the same dotenv source
symlinked to the original checkout. No OpenAI key, organisation, project or base URL
was exported in their inspected startup environment. The diagnostic uses BUILD's
actual service, so its model/schema/request parameters were not a separate probe
configuration. No code-level configuration discrepancy was found. This does not
inspect the running worker's in-memory credentials, prove account/project ownership,
or reproduce a browser request with the user's original recipe.

Current configured-key access to the model is working. The historical account-side
reason for the previous failure cannot be established from the prior generic message
and unavailable terminal history. Billing propagation or a restriction since resolved
remain possibilities, not confirmed causes. The misleading error classification is
confirmed and corrected. No account/limit/credential changes are justified by this
successful request alone. If the browser still fails, capture its new code/type/status
and request ID before deciding which account or project setting needs attention.

## Validation and Git safety

77 Python tests across test_build_generation.py, test_build_page.py and
test_adoption_access.py pass; all 209 JavaScript tests pass. New parameterized tests
cover specific quota/spend/usage/rate codes, type fallback, unknown errors and safe
logging, including keeping credentials, headers, prompt and recipe text out of logs.
Python syntax and diff checks pass.

At the original diagnostic handover, these changes were uncommitted on develop at
96fc6fa. No credential rotation, credit purchase or billing-setting change occurred.
Unrelated work in the original checkout was not touched.

## Completion approval

Andy subsequently authorized committing this reviewed fix, restarting the local
development server and performing a real-browser BUILD MUNGE test. develop may be
pushed only after generation succeeds and the selected recipe is verified intact.
No production deployment is authorized. This supersedes the earlier uncommitted-only
instructions recorded above.

## Completion verification

- Implementation commit: 815d2ce (classification, safe diagnostics and associated tests).
- Restarted the existing local Uvicorn service from NewsMuncher-Build on
  http://127.0.0.1:8000 with the verified develop code and existing dotenv settings.
- Browser: native Google Chrome, fresh BUILD tab, existing adopted pet session.
- Selected three recipe items: one OBJECTS phrase, one MODIFIER and one PERSON.
- Clicked MUNGE 30 exactly once through the normal browser UI. The generated story
  appeared in the editable result field; COPY and NOMINATE appeared. No nomination,
  image, audio or video generation action was invoked.
- Server log confirms GET /pets/adoption-status 200 and POST /build/generate 200.
- Verified all three original recipe items remained present, selected ingredients
  remained in the prompt and all three MUNGE controls were enabled after completion.
- 77 Python tests and 209 JavaScript tests pass. The initial sandboxed Python rerun
  encountered blocked Mongo SRV DNS during module import; rerunning with the dummy
  MONGO_URI=mongodb://127.0.0.1:27017 kept the mocked tests offline and passed.
- Local runtime log: /private/tmp/newsmuncher-build-dev-20261109.log (not committed).
- Browser success satisfies Andy's condition for pushing develop. Production
  deployment remains prohibited; the unrelated original-worktree edits/media are
  preserved and excluded.
