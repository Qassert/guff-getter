STATUS: REVIEW
OWNER: CODEX
BRANCH: feature/global-word-shuffle
LAST_COMPLETED_FEATURE: Fix duplicate jingle controls after refresh
LAST_COMPLETED_COMMIT: :/^Fix duplicate jingle controls after refresh
LAST_OWNER: ANTIGRAVITY
HANDOVER: WORD_SHUFFLE_STATUS.md

## Status Values

- **READY**: repository is available for a new task
- **ACTIVE**: one named agent currently owns the task
- **BLOCKED**: work is incomplete and must not be overwritten
- **REVIEW**: implementation is complete but awaiting Andy's review/approval

CURRENT_TASK: Temporary standalone TTS comparison harness (mocked validation only)

REVIEW_SUMMARY: Authorized five-bank migration completed atomically; 80 proven claims per bank preserved.
  Original fields unchanged; backup outside Git documented in WORD_SHUFFLE_STATUS.md.
VALIDATION: 16 targeted tests; full suite 118 passed (one run); read-only claim predicates accept all banks.
APPROVAL: Migration and local docs checkpoint authorized; no generation or push performed.
NEXT_STEP: Review; ready for separately authorized browser SHIZZALISE test.

## Image style wording refinement

Ultra-photorealistic editorial surrealism replaces the flat/cartoon direction in the
image prompt only: believable figures/materials, cinematic lighting, connected scenes,
absurd humour and 4–6 dominant colours. Flat style retained as PREVIOUS_IMAGE_STYLE;
original graffiti/zine wording retained as ORIGINAL_IMAGE_STYLE, both reference-only.
Image settings, rewritten scene inputs and lifecycle unchanged.
VALIDATION: 18 image-generation tests passed offline, including frontend checks.
No real images or external calls. Changes intentionally uncommitted/unpushed for review.


## Temporary TTS comparison harness — 2026-09-15

Standalone scripts/compare_tts.py only; no app integration. Curated editable voice
pools, one random voice/sample per selected provider, identical fixed sample text.
OpenAI SDK plus existing requests HTTP for ElevenLabs/Cartesia; no new dependencies.
Environment/root .env keys: OPENAI_API_KEY, ELEVENLABS_API_KEY, CARTESIA_API_KEY.
Missing keys skip safely; --dry-run writes nothing and calls no provider. No retries.
Unique MP3 files go to ignored data/tts-comparison/. No generated audio committed.
Run from root using .venv/bin/python -m scripts.compare_tts --provider all --dry-run.
For one live sample, replace all with openai/elevenlabs/cartesia and omit --dry-run.
Each provider requires an API-enabled account, usable quota/credit and access to the
configured voice IDs. Account/voice availability has not been tested live.
VALIDATION: 7 targeted mocked tests passed; no synthesis/provider API calls made.
STATUS: REVIEW / CODEX; user authorized committing and pushing this harness.
Earlier image-style changes are already committed; older uncommitted wording above
is historical. No unrelated files changed in this harness task.
