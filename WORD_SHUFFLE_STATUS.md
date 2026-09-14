# Permanent global word claims and copy-edit pass

Branch: feature/global-word-shuffle. CODEX review checkpoint; do not push without approval.
Baseline: e2bf84a (Kiro/Codex WIP). No CSVs modified in this pass.

## Current implementation

- No contender DOM, script inclusion, CSS, or animation remains. contenders.js was
  already absent. Structured backend contenders remain available for diagnostics.
- MongoDB funny_json_db.word_shuffle_bags stores one permanent claimed_words ledger
  per bank. It is never cleared on fingerprint changes. Existing ledger documents
  continue working unchanged; version and known_vocabulary_digest are informational.
- find_one_and_update evaluates eligibility and selects a slice inside MongoDB,
  unions it into claimed_words and returns that operation's last_claim atomically.
  Python shuffles the full deduplicated master vocabulary, not a read of unused words.
  Concurrent workers cannot return overlapping claims. Majority writes and TLS remain.
- CSV additions become eligible if never claimed; unclaimed retained words remain
  eligible; removals are excluded from each request's vocabulary; removal/re-addition
  never clears historical claims. Exact string identity is retained (case changes are
  distinct words); no compound normalization. Banks remain independent. Names retain
  existing local sampling, outside the five shared-bank scope.
- Insufficient words raises BankExhaustedError with no partial claim in that bank.
  Claims in earlier banks, failed rewrites and filtered words remain consumed.
- Legacy cursor-only documents fail closed. The earlier fingerprint-reset design
  could erase history, so a cursor prefix is not sufficient proof of all past usage.
  Recover history from authoritative backups/audits before converting such documents;
  never reset or delete them to bypass exhaustion. No live database inspected/migrated.

## Copy-edit pass (preserved)

Pass 2 receives only generated crazy title/extract as JSON. Existing gpt-5.6-luna,
strict JSON schema, no reasoning, 750-token limit, no retries, no tools. The prompt
requires preserving absurd events, slang, names, imagery and invented relationships,
while correcting grammar/flow rather than normalizing the story. Failure returns None;
the route retains pass 1. Empty or malformed polished output now also uses the same
validated formatter and falls back safely. No original source is included in pass 2.

## Verification

25 targeted tests passed (14 permanent claims, 8 copy-edit, 3 UI-removal).
Full suite: 116 tests passed, run once after targeted checks.
Claims concurrency tested with a lock-backed Mongo operation mock, not live Atlas.
Copy-edit model calls mocked. No live services or generated media.

## Risks / operations

- MongoDB 4.2+ required for pipeline updates; one bank's ledger must fit 16 MiB.
- All instances must deploy the same current CSVs. An old worker with stale CSV
  contents can still claim an unclaimed removed word; coordinate vocabulary rollout.
- Already erased historical claims cannot be reconstructed from a reset document.
  Existing claimed_words ledger integrity and persistent database/backups are required.
- Copy-edit preservation is prompt-based; it cannot guarantee semantic fidelity.
  A successful rewrite incurs two text calls; none were made live during this work.

## Legacy missing-array runtime fix

The second operand of $in was unguarded $claimed_words. MongoDB may evaluate
$expr before its sibling $type predicate, causing findAndModify to fail on legacy
records. $cond/$isArray now supplies a safe array to $in and $setUnion. The type
predicate still rejects invalid ledgers: the empty expression fallback is NOT a
new unused ledger and does not authorize claims. Missing/null/scalar history
produces the explicit history-recovery error without modifying the document.
Valid ledgers missing optional metadata continue working, preserving all claims.
16 targeted tests and full 118-test suite passed offline. No real MongoDB data,
CSVs, or main were modified; no migration or generation performed.
