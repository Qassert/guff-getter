# Final-output global word claims and copy-edit pass

Branch: feature/global-word-shuffle. CODEX review checkpoint; do not push without approval.
Baseline: e2bf84a (Kiro/Codex WIP). No CSVs modified in this pass.

## Current implementation

- No contender DOM, script inclusion, CSS, or animation remains. contenders.js was
  already absent. Structured backend contenders remain available for diagnostics.
- MongoDB funny_json_db.word_shuffle_bags stores one permanent claimed_words ledger
  per bank. It is never cleared on fingerprint changes. Existing ledger documents
  continue working unchanged; version and known_vocabulary_digest are informational.
- Candidate drawing reads the current ledger, excludes claimed words and makes no
  permanent claim. After the accepted pass-2 result (or pass-1 fallback) is known,
  exact case-insensitive candidate occurrences in its title/body are committed.
  Unused candidates and failed generations consume nothing.
- Final claims across banks use one Mongo transaction. Each conditional update rejects
  any word claimed by a concurrent completed rewrite; a conflict aborts the transaction
  and returns HTTP 409 before the rewrite is completed or returned. Majority writes and
  TLS remain.
- CSV additions become eligible if never claimed; unclaimed retained words remain
  eligible; removals are excluded from each request's vocabulary; removal/re-addition
  never clears historical claims. Exact string identity is retained (case changes are
  distinct words); no compound normalization. Banks remain independent. Names retain
  existing local sampling, outside the five shared-bank scope.
- Insufficient words raises BankExhaustedError. Draws and filtered words remain
  unclaimed; only exact occurrences in the final accepted output are permanent.
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

52 targeted tests passed plus 6 subtests. Claims concurrency and transaction rollback
were tested with a lock-backed Mongo mock, not live Atlas. Copy-edit and generation
calls were mocked. No live services or generated media.

## Risks / operations

- MongoDB must support multi-document transactions; one bank's ledger must fit 16 MiB.
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

## Authorized real-data migration — 2026-09-14

Re-read all five legacy banks; exact stored array hashes, fields, cycle=1, cursor=80,
sizes and current CSV fingerprints matched the read-only inspection. Canonical
Extended JSON backup (BSON type-preserving) saved outside Git:
/Users/andrewwhite/NewsMuncher-backups/newsmuncher-migration-20260914T163713Z/legacy-word-banks.ejson
SHA256: 2eb2bfdfd056c98eed4260ef1e95aacbb8ee2379f8b82b1cab065e5b11c79173

One snapshot/majority transaction conditionally added claimed_words=words[:80]
and version=1 to slang, nouns, adverbs, animals and places. All original fields
and arrays unchanged. Read-back verified exactly 80 unique claims per bank (400
bank-specific claims). Read-only claim predicates accept all five banks; no draw
or SHIZZALISE was performed. No database contents committed.
16 targeted tests and full 118-test suite passed offline (full suite once).
Ready for an explicitly authorized browser SHIZZALISE test; that test will consume
new permanent claims and make two text-model calls. No such calls made here.
Historical uncertainty predating the preserved experimental records remains as
documented; this migration preserves every claim provable from those records.
