# Global word shuffle and second‑pass copy‑editing

Branch: feature/global-word-shuffle. Review required; not committed or pushed.

## Changes made

1. **Removed visible contender‑word display**  
   - Deleted `<aside id="contenderWords">` from `pet_profile.html`.  
   - Removed all contender‑word CSS from `static/styles.css`.  
   - Removed all three `contenderWords.show()` calls from `static/script.js`.  
   - The `contenders` field **remains in the backend payload**, so the word‑selection logic is unchanged; only the frontend visualisation is gone.  
   - `contenders.js` file is kept (untracked) but no longer loaded.

2. **Permanent one‑time global word claims** (replaces the previous cycle‑based rollover)  
   - `services/word_shuffle.py` completely rewritten.  
   - A word is claimed globally only once, via an atomic MongoDB `find_one_and_update` with a `$gte` condition that ensures enough remaining words exist.  
   - When a bank is exhausted, `BankExhaustedError` is raised immediately. **Words are never recycled.**  
   - CSV files remain read‑only; a changed CSV resets the bank (the only way to “refill”).  
   - All five shared banks (adverbs, animals, nouns, places, slang) use this mechanism; names continue to be sampled locally.  
   - Concurrent claims are disjoint; no read‑then‑write race is possible.  
   - Tests updated to verify exhaustion, independence, concurrency, persistence and CSV‑change reset.

3. **Second AI copy‑editing pass**  
   - Added `copy_edit_pass()` to `utils/clean_data.py` (replacing the unused `correct_grammar`).  
   - Receives **only** the pass‑1 output (`crazyReplacement1Title` + `crazyReplacement1Extract`). Never sees the original source text.  
   - System prompt: “A highly competent copy editor who accepts that every insane thing in this article is completely true.”  
   - Fixes grammar, sentence structure, agreement, flow and readability while **preserving all absurdity, bizarre events, rude/slang words, strange names, surreal imagery, invented relationships and overall ridiculousness.**  
   - Must **NOT** make the story sensible, sanitise it, revert toward normal journalism, remove weird details or explain jokes.  
   - If the pass fails (network error, incomplete response, invalid JSON), the function returns `None` and the caller falls back to the successful pass‑1 result.  
   - Integrated in `api/previews.py`: after `format_shizzalise_result` succeeds, call `copy_edit_pass`; if it returns a polished dict, use it, otherwise keep the pass‑1 result.  
   - Tests verify that only pass‑1 output is sent, the absurdity‑preserving prompt is used, successful polishing returns sanitised text, and failures fall back safely.

## Storage and atomic claims

MongoDB collection: `funny_json_db.word_shuffle_bags`, same `MONGO_URI` and TLS CA configuration, majority write concern. No additional credentials/dependencies. MongoDB 4.2+ required for update pipelines. One document per bank:

```json
{
  "_id": "animals",
  "cursor": 10,
  "size": 2000,
  "words": ["… one‑time shuffled unique bank …"],
  "source_sha256": "…"
}
```

Keys: adverbs, animals, nouns, places, slang. The master CSVs are read‑only. Exact duplicate entries are collapsed after trimming boundary whitespace; spelling, capitalisation and compound formatting are otherwise unchanged. Names intentionally retain the existing random sampling because they are not one of the five requested shared banks. Independence is per bank, not cross‑bank vocabulary deduplication.

### Claim semantics

- `ShuffleBags.draw(bank, words, count)` atomically reserves `count` positions via a single `find_one_and_update` pipeline that checks `size - cursor >= count`.  
- If insufficient words remain, `BankExhaustedError` is raised. Words are **never** returned to the pool.  
- Concurrent workers reserve disjoint slices; the cursor advances exactly by `count` in the same operation that reads the slice boundaries.  
- On first use the bank is initialised with a one‑time shuffle; subsequent calls from a fresh process re‑use the same shuffled order already stored in MongoDB.  
- CSV changes are detected by comparing a SHA‑256 digest of the vocabulary; a mismatch triggers an atomic reset of the bank (new shuffle, cursor back to 0). This is the **only** path by which previously claimed words can become available again.  

## Verification

- **Word‑shuffle tests** (9 new/updated): basic claim/exhaustion, bank independence, concurrent disjoint claims, CSV‑change reset, argument validation, persistence across processes, CSV read‑only property, database‑error propagation.  
- **Contender‑frontend tests** (3): confirm the `contenders.js` script is absent from the template, CSS rules for `.contender‑words`/.`.contender‑side` are removed, and the `contenders` field is still present in integration payloads.  
- **Copy‑edit‑pass tests** (7): receives only pass‑1 output, preserves absurdity in system prompt, successful polishing returns sanitised result, incomplete responses raise `ValueError` and return `None`, network/exceptions return `None`, empty title/extract returns `None` early.  
- **Full test suite** (110 tests) passes with all mocks; no live MongoDB, OpenAI, Modal, ACE‑Step, image or audio generation.

## Remaining risks

1. **Exhaustion behaviour** – once a bank is exhausted, the application will raise `BankExhaustedError` and prompt preparation will fail. The caller must handle this explicitly (e.g., by rotating to a different source, showing a user‑friendly error, or manually resetting the CSV). This is intentional: words are **never** recycled.  
2. **Concurrent CSV changes** – if two workers simultaneously detect a CSV change, both may attempt to reset the bank; the CAS on `source_sha256` ensures only one wins, but the loser’s `draw()` call will retry and see the fresh bank. No data corruption occurs.  
3. **Copy‑edit pass cost** – every successful rewrite now incurs **two** OpenAI API calls (pass‑1 + pass‑2). Pass‑2 uses `gpt‑5.6‑luna` with `max_output_tokens=750`. Failed pass‑2 attempts still consume quota.  
4. **Copy‑edit prompt fidelity** – the system prompt attempts to preserve absurdity, but there is no guarantee the model won’t subtly “sanitise” the text. The fallback to pass‑1 mitigates total failure but cannot detect unwanted normalisation.  
5. **Backward compatibility** – the `contenders` field is still present in the rewrite response, so existing code that reads it (e.g., future analytics) continues to work. The removal of the frontend display is transparent to the backend.

## Modified files

- `CURRENT_WORK.md` – updated to `ACTIVE / KIRO`, then `REVIEW / KIRO`.  
- `newsmuncher/api/previews.py` – added import and call to `copy_edit_pass`.  
- `newsmuncher/services/word_shuffle.py` – completely rewritten (new permanent‑one‑time logic, `BankExhaustedError`).  
- `newsmuncher/static/script.js` – removed three `contenderWords.show()` calls.  
- `newsmuncher/static/styles.css` – deleted the whole contender‑word CSS block.  
- `newsmuncher/templates/pet_profile.html` – removed `<aside id="contenderWords">` and the `contenders.js` script tag.  
- `newsmuncher/utils/clean_data.py` – replaced `correct_grammar` with `copy_edit_pass`.  
- `tests/test_image_generation.py` – added `copy_edit_pass` to the mocked module and set its return value to `None` in one test.  
- `tests/test_source_preprocessing.py` – already updated by Codex (unrelated).  
- `tests/test_contender_frontend.py` – updated to verify UI removal.  
- `tests/test_copy_edit_pass.py` – new test suite for the second pass.  
- `tests/test_word_shuffle.py` – updated for permanent‑one‑time claims.  

**Untracked files** (from Codex): `WORD_SHUFFLE_STATUS.md`, `newsmuncher/services/word_shuffle.py` (now overwritten), `newsmuncher/static/contenders.js`, `tests/test_contender_frontend.py` (updated), `tests/test_copy_edit_pass.py` (new), `tests/test_word_shuffle.py` (updated).

## Next steps

Review the diff, confirm the changes match the requirements, and decide whether to commit/push or request adjustments.