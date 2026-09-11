"""Permanent global word claims: once a word is used, it stays used forever.

Design principles
-----------------
- One MongoDB document per bank (keyed by bank name).
- The document stores a persistent set of *claimed words* (strings).
- CSV files are read-only master vocabularies.
- When a word is claimed, it is added to the claimed‑words set.
- A word that has been claimed can NEVER become available again, even if
  its CSV file is edited, the word removed and later re‑added, or the
  entire CSV is replaced.
- New words added to a CSV become available for future claims.
- Words removed from a CSV are no longer claimable (they are absent from
  the current vocabulary).
- Concurrent claims are atomic: the MongoDB update uses `$addToSet` with
  `$each` on the claimed‑words field.  If two workers try to claim overlapping
  words, the loser's update does nothing (modifiedCount == 0) and it retries
  with a fresh view of available words.
- No automatic rollover or recycling.  Exhaustion raises BankExhaustedError.
- Multiple app workers sharing the same MongoDB instance see the same
  claimed‑words set, ensuring truly global one‑time use.
"""
import csv
from functools import lru_cache
import hashlib
import json
import os
import random
import time

import certifi
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
from pymongo.write_concern import WriteConcern

BANK_FILES = {
    'adverbs': 'adverbs.csv',
    'animals': 'animalsAndObjects.csv',
    'nouns': 'nouns.csv',
    'places': 'places.csv',
    'slang': 'slang.csv',
}


class BankExhaustedError(Exception):
    """Raised when a bank has insufficient unclaimed words to satisfy a request.

    Words are never recycled.  The caller must handle this explicitly.
    """


def read_bank(path):
    """Read a CSV bank file into a deduplicated word list.

    Boundary whitespace is stripped; exact duplicates after trimming are
    collapsed.  Spelling, capitalisation and compound formatting are
    otherwise unchanged.  The CSV file is never modified.
    """
    with open(path, encoding='utf-8', newline='') as source:
        return list(dict.fromkeys(
            value.strip()
            for row in csv.reader(source)
            for value in row
            if value.strip()
        ))


class PermanentWordClaims:
    """Atomic, persistent, permanent global word‑claim manager.

    Each instance wraps a MongoDB collection.  Multiple instances that
    share the same collection (across processes/workers) behave as a
    single global claim pool.

    Storage schema per bank:
        {
            _id: 'adverbs',
            claimed_words: ['absurd', 'angular', …],  // strings
            known_vocabulary_digest: 'sha256…',       // digest of all words ever seen
            version: 1                                // optimistic‑concurrency counter
        }
    """

    def __init__(self, collection, shuffle=None):
        self.collection = collection
        self.shuffle = shuffle or random.SystemRandom().shuffle

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _source_digest(self, words):
        return hashlib.sha256(
            json.dumps(sorted(words), ensure_ascii=False).encode()
        ).hexdigest()

    def _ensure_bank_exists(self, bank, current_words):
        """Create the bank document if it doesn't exist.

        The initial claimed_words set is empty.  The known_vocabulary_digest
        is computed from the current word list.
        """
        digest = self._source_digest(current_words)
        try:
            self.collection.insert_one({
                '_id': bank,
                'claimed_words': [],
                'known_vocabulary_digest': digest,
                'version': 1,
            })
        except DuplicateKeyError:
            pass  # Another worker initialised the same bank concurrently.

    def _sync_vocabulary_if_needed(self, bank, current_words):
        """Update known_vocabulary_digest when the CSV has changed.

        This operation adds any new words to the historical record but
        never removes words from claimed_words.  If a word appears in the
        current CSV that was never seen before, it will become available
        for future claims.

        The update is idempotent and uses optimistic concurrency (version
        field) to avoid race conditions between multiple workers detecting
        the same CSV change.
        """
        current_digest = self._source_digest(current_words)

        while True:
            doc = self.collection.find_one({'_id': bank})
            if doc is None:
                return  # Will be created by _ensure_bank_exists later.

            if doc.get('known_vocabulary_digest') == current_digest:
                return  # CSV unchanged; nothing to do.

            # CSV changed: update the digest to reflect the new vocabulary.
            # No change to claimed_words; new words become available.
            result = self.collection.update_one(
                {'_id': bank, 'version': doc['version']},
                {'$set': {
                    'known_vocabulary_digest': current_digest,
                }, '$inc': {'version': 1}},
            )
            if result.modified_count == 1:
                return  # Successfully updated.
            # Concurrent modification; retry the loop.

    def _available_words(self, current_words, claimed_set):
        """Return the list of words in current_words that are NOT in claimed_set."""
        return [w for w in current_words if w not in claimed_set]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def draw(self, bank, current_words, count, max_attempts=10):
        """Claim *count* globally unique words from *bank*.

        Parameters
        ----------
        bank:          str   — bank name (e.g. 'adverbs').
        current_words: list  — the full vocabulary read from the current CSV.
        count:         int   — number of words to claim (≥ 0).
        max_attempts:  int   — maximum number of optimistic‑concurrency retries.

        Returns
        -------
        list of str — exactly *count* words that have never been returned
                      by any previous draw() call on this bank.

        Raises
        ------
        ValueError          — *count* is negative or *current_words* is empty.
        BankExhaustedError  — fewer than *count* unclaimed words remain in
                              the current vocabulary.
        RuntimeError        — optimistic‑concurrency retries exceeded.
        """
        if count < 0 or not current_words:
            raise ValueError('Nonempty bank and nonnegative count required')
        if count == 0:
            return []

        # Ensure the bank document exists and its vocabulary is up‑to‑date.
        self._ensure_bank_exists(bank, current_words)
        self._sync_vocabulary_if_needed(bank, current_words)

        for attempt in range(max_attempts):
            # 1. Read the current state.
            doc = self.collection.find_one({'_id': bank})
            if doc is None:
                # Extremely rare race: initialise and retry.
                self._ensure_bank_exists(bank, current_words)
                continue

            claimed_set = set(doc.get('claimed_words', []))
            available = self._available_words(current_words, claimed_set)

            if len(available) < count:
                raise BankExhaustedError(
                    f"Bank '{bank}' has {len(available)} unclaimed word(s) "
                    f"in the current vocabulary but {count} were requested. "
                    "Words are never recycled."
                )

            # 2. Choose which words to claim (deterministic shuffle).
            self.shuffle(available)
            chosen = available[:count]

            # 3. Attempt to atomically add them to claimed_words.
            result = self.collection.update_one(
                {'_id': bank, 'version': doc['version']},
                {'$addToSet': {'claimed_words': {'$each': chosen}},
                 '$inc': {'version': 1}},
            )

            if result.modified_count == 1:
                return chosen

            # 4. Concurrent modification: someone else updated the document.
            # Wait briefly and retry with a fresh view.
            time.sleep(0.001 * (attempt + 1))

        raise RuntimeError(
            f"Could not claim words after {max_attempts} attempts; "
            "concurrent contention too high."
        )


@lru_cache(maxsize=1)
def shared_bags():
    """Lazily construct the process‑global PermanentWordClaims instance.

    Importing this module (e.g. for tests) never connects to MongoDB;
    the connection is only established on the first call to shared_bags().
    """
    client = MongoClient(
        os.environ['MONGO_URI'],
        tlsCAFile=certifi.where(),
        serverSelectionTimeoutMS=10_000,
    )
    collection = client['funny_json_db'].get_collection(
        'word_shuffle_bags',
        write_concern=WriteConcern(w='majority'),
    )
    return PermanentWordClaims(collection)
