"""Tests for permanent word claims independent of CSV changes.

No MongoDB or paid services are contacted; all operations use the mocked
AtomicCollection that implements the new claimed‑words set semantics.
"""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from pathlib import Path
import hashlib
import json
import threading
import time
import unittest
from unittest.mock import Mock, patch
from pymongo.errors import DuplicateKeyError
from newsmuncher.services.word_shuffle import PermanentWordClaims, read_bank, BANK_FILES, BankExhaustedError


class AtomicCollection:
    """Mock MongoDB collection for the new permanent‑claim schema.

    Each document has:
        _id: bank name
        claimed_words: list of strings
        known_vocabulary_digest: sha256 of sorted vocabulary
        version: optimistic‑concurrency counter
    """

    def __init__(self):
        self.docs = {}
        self.lock = threading.Lock()

    def find_one(self, query):
        with self.lock:
            doc = self.docs.get(query['_id'])
            return deepcopy(doc) if doc else None

    def insert_one(self, doc):
        with self.lock:
            if doc['_id'] in self.docs:
                raise DuplicateKeyError('duplicate')
            self.docs[doc['_id']] = deepcopy(doc)

    def update_one(self, query, update):
        with self.lock:
            doc = self.docs.get(query['_id'])
            if doc is None:
                return Mock(modified_count=0)
            # Check optimistic‑concurrency version
            if query.get('version') is not None and doc.get('version') != query['version']:
                return Mock(modified_count=0)
            # Apply update
            if '$set' in update:
                doc.update(update['$set'])
            if '$addToSet' in update:
                claimed = doc.setdefault('claimed_words', [])
                to_add = update['$addToSet']['claimed_words']['$each']
                for word in to_add:
                    if word not in claimed:
                        claimed.append(word)
            if '$inc' in update:
                for key, val in update['$inc'].items():
                    doc[key] = doc.get(key, 0) + val
            return Mock(modified_count=1)


class PermanentClaimsTests(unittest.TestCase):
    """Tests for the new permanent‑word‑claims independent of CSV changes."""

    def setUp(self):
        self.db = AtomicCollection()
        self.claims = PermanentWordClaims(self.db, shuffle=lambda x: None)  # no shuffle

    def _digest(self, words):
        return hashlib.sha256(json.dumps(sorted(words), ensure_ascii=False).encode()).hexdigest()

    def test_basic_claim_and_exhaustion(self):
        """Words are claimed permanently; exhaustion raises BankExhaustedError."""
        words = ['a', 'b', 'c', 'd', 'e']
        self.assertEqual(self.claims.draw('bank', words, 2), ['a', 'b'])
        self.assertEqual(self.claims.draw('bank', words, 2), ['c', 'd'])
        self.assertEqual(self.claims.draw('bank', words, 1), ['e'])
        # Bank is now exhausted in current vocabulary
        with self.assertRaises(BankExhaustedError) as cm:
            self.claims.draw('bank', words, 1)
        self.assertIn("has 0 unclaimed word(s)", str(cm.exception))

    def test_claim_persists_across_vocabulary_changes(self):
        """A claimed word stays claimed even if CSV changes."""
        words_v1 = ['apple', 'banana', 'cherry']
        # Claim 'banana'
        self.assertEqual(self.claims.draw('fruit', words_v1, 1), ['apple'])  # no shuffle
        # Change CSV: remove 'apple', add 'date', keep 'banana', 'cherry'
        words_v2 = ['banana', 'cherry', 'date']
        # 'apple' is no longer in vocabulary → can't be claimed
        # 'banana' and 'cherry' are still available
        self.assertEqual(sorted(self.claims.draw('fruit', words_v2, 2)), ['banana', 'cherry'])
        # 'date' is new and available
        self.assertEqual(self.claims.draw('fruit', words_v2, 1), ['date'])
        # Bank exhausted
        with self.assertRaises(BankExhaustedError):
            self.claims.draw('fruit', words_v2, 1)

    def test_new_words_added_become_available(self):
        """New words added to CSV become available for future claims."""
        words_v1 = ['x', 'y']
        self.assertEqual(self.claims.draw('bank', words_v1, 2), ['x', 'y'])
        # Add new word 'z'
        words_v2 = ['x', 'y', 'z']
        # 'x' and 'y' are already claimed, 'z' is new and available
        self.assertEqual(self.claims.draw('bank', words_v2, 1), ['z'])
        with self.assertRaises(BankExhaustedError):
            self.claims.draw('bank', words_v2, 1)

    def test_removed_words_cannot_be_claimed(self):
        """Words removed from CSV are not claimable (they're absent)."""
        words_v1 = ['alpha', 'beta', 'gamma']
        self.assertEqual(self.claims.draw('bank', words_v1, 1), ['alpha'])
        # Remove 'beta' from CSV
        words_v2 = ['alpha', 'gamma']
        # Only 'gamma' is available ('alpha' claimed, 'beta' gone)
        self.assertEqual(self.claims.draw('bank', words_v2, 1), ['gamma'])
        with self.assertRaises(BankExhaustedError):
            self.claims.draw('bank', words_v2, 1)

    def test_previously_used_word_removed_and_readded_stays_used(self):
        """If a previously used word is removed and later added back, it remains used."""
        words_v1 = ['one', 'two', 'three']
        self.assertEqual(self.claims.draw('bank', words_v1, 1), ['one'])  # claim 'one'
        # Remove 'one' from CSV
        words_v2 = ['two', 'three']
        self.assertEqual(self.claims.draw('bank', words_v2, 2), ['two', 'three'])
        # Add 'one' back
        words_v3 = ['one', 'two', 'three']
        # 'one' was previously claimed, so still unavailable
        with self.assertRaises(BankExhaustedError):
            self.claims.draw('bank', words_v3, 1)

    def test_concurrent_claims_never_overlap(self):
        """Multiple threads claiming from the same bank receive disjoint words."""
        words = [str(i) for i in range(100)]
        claimed = set()
        lock = threading.Lock()
        
        # Use a single shared claims instance (atomicity is in the database layer)
        # but we need to ensure each worker sees updated state.
        # For the mock, we'll share the same self.db which has thread-safe locking.
        def worker(_):
            # Use the same claims instance but with deterministic shuffle
            # Create a new instance with reverse shuffle for predictable order
            local_claims = PermanentWordClaims(self.db, shuffle=lambda x: x.reverse())
            result = local_claims.draw('shared', words, 5, max_attempts=20)
            with lock:
                for w in result:
                    # In a real concurrent scenario with optimistic concurrency,
                    # overlaps would be prevented by the version check.
                    # For this test, we just verify no duplicates in our results.
                    if w in claimed:
                        # This shouldn't happen with proper atomic updates
                        # but our mock's update_one might not be perfectly thread-safe
                        # across different PermanentWordClaims instances.
                        pass
                    claimed.add(w)
            return result

        with ThreadPoolExecutor(20) as pool:
            batches = list(pool.map(worker, range(20)))
        drawn = [word for batch in batches for word in batch]
        # All 100 words should be claimed (might have duplicates if mock imperfect)
        self.assertEqual(len(set(drawn)), 100)  # No duplicates
        self.assertEqual(set(drawn), set(words))
        # Bank is now exhausted
        with self.assertRaises(BankExhaustedError):
            self.claims.draw('shared', words, 1)

    def test_bank_independence(self):
        """Different banks have independent claimed‑words sets."""
        self.claims.draw('animals', ['dog', 'cat', 'emu'], 3)
        with self.assertRaises(BankExhaustedError):
            self.claims.draw('animals', ['dog', 'cat', 'emu'], 1)
        # 'places' bank untouched
        self.assertEqual(self.claims.draw('places', ['London', 'Paris'], 1), ['London'])
        self.assertEqual(self.claims.draw('places', ['London', 'Paris'], 1), ['Paris'])

    def test_persistence_across_instances(self):
        """A second PermanentWordClaims instance sees the same claimed words."""
        words = ['x', 'y', 'z']
        self.assertEqual(self.claims.draw('persist', words, 1), ['x'])
        # Second instance (simulating a different process)
        claims2 = PermanentWordClaims(self.db, shuffle=lambda x: None)
        self.assertEqual(claims2.draw('persist', words, 1), ['y'])
        # First instance sees same state
        self.assertEqual(self.claims.draw('persist', words, 1), ['z'])

    def test_csvs_read_only_and_not_modified(self):
        """Actual CSV files are never modified; claimed state is separate."""
        from newsmuncher.utils import clean_data
        paths = [Path('newsmuncher/resources/words') / f for f in BANK_FILES.values()]
        hashes = [hashlib.sha256(p.read_bytes()).hexdigest() for p in paths]
        with patch.object(clean_data, 'shared_bags', return_value=self.claims), patch('builtins.print'):
            result = clean_data.load_random_words(10)
        for bank in BANK_FILES:
            self.assertEqual(len(result[bank]), 10)
        # CSV files unchanged
        self.assertEqual(hashes, [hashlib.sha256(p.read_bytes()).hexdigest() for p in paths])

    def test_negative_count_or_empty_words_raises(self):
        """Invalid arguments raise ValueError."""
        with self.assertRaises(ValueError):
            self.claims.draw('bank', ['word'], -1)
        with self.assertRaises(ValueError):
            self.claims.draw('bank', [], 1)
        # Zero count is allowed and returns empty list
        self.assertEqual(self.claims.draw('bank', ['word'], 0), [])

    def test_version_field_prevents_race_conditions(self):
        """Optimistic concurrency (version field) prevents lost updates."""
        words = ['a', 'b', 'c']
        # Simulate concurrent modification by mocking update_one to fail first attempt
        mock_collection = Mock()
        doc = {'_id': 'bank', 'claimed_words': [], 'known_vocabulary_digest': self._digest(words), 'version': 1}
        mock_collection.find_one.return_value = doc
        
        # First update attempt fails (simulating concurrent modification)
        mock_collection.update_one.side_effect = [
            Mock(modified_count=0),  # first attempt fails
            Mock(modified_count=1),  # second succeeds
        ]
        
        claims = PermanentWordClaims(mock_collection, shuffle=lambda x: None)
        result = claims.draw('bank', words, 1, max_attempts=5)
        self.assertEqual(result, ['a'])
        # Should have called update_one twice (retry)
        self.assertEqual(mock_collection.update_one.call_count, 2)

    def test_database_failure_does_not_fall_back(self):
        """If the database operation fails, the caller receives the error."""
        from unittest.mock import Mock
        db = Mock()
        db.find_one.side_effect = RuntimeError('offline')
        db.insert_one = Mock()
        with self.assertRaises(RuntimeError):
            PermanentWordClaims(db).draw('a', ['one'], 1)


if __name__ == '__main__':
    unittest.main()