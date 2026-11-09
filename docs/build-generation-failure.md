# BUILD generation failure follow-up — 2026-11-09

The reported access log was POST /build/generate 502 with the UI detail
"Story generation failed. Your recipe is still here." This is the route's catch-all;
it does not identify an underlying provider rejection or response parsing failure.
The exact original runtime cause remains unconfirmed without a live retry.

Inspection confirmed SDK 2.54.0 supports Responses text.format, the environment file
exists and an API key is configured (no key values were printed). BUILD differed
from the existing CREATE request for the same gpt-6-sol model: CREATE explicitly uses
reasoning effort none, a 750-token output cap and store=False. BUILD now uses those
same settings, retaining its story/headline schema, model, no-retry policy, timeout,
editable prompt and 30/60/90 word limits.

Structured-output responses are checked for refusal and incomplete status before
JSON parsing. Invalid JSON, wrong shapes and empty/non-string stories fail safely;
partial stories are not displayed. Refusal now produces a 422 explaining that the
prompt needs editing. Credit/rate-limit, credentials/model-access, connection and
provider rejection errors produce actionable safe messages rather than the generic
failure. Server warnings log whitelisted error codes/status/request IDs or exception
type, never exception bodies, API keys, prompts or provider-generated text.

Official OpenAI documentation confirms that structured outputs can include refusals
outside the schema and incomplete output must be handled before parsing:
https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses

Validation: 59 Python tests across test_build_generation.py, test_build_page.py and
test_adoption_access.py; all 209 JavaScript tests pass. Added mocked tests cover
request settings at each length, single-call behaviour, refusal, incomplete/invalid
responses and provider billing/auth/model/request failures without sensitive logging.
Syntax and diff checks pass. No paid/live provider call was made.

Local develop commit only. Reload the running server before retrying. If it still
fails, the new safe BUILD warning and user-facing message should identify the failure
category. Unrelated changes in the other worktree remain untouched; no push/merge/deploy.
