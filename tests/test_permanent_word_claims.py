"""Offline tests for candidate selection and final-output word claims."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from pathlib import Path
import hashlib
import threading
import unittest
from unittest.mock import Mock, patch

from pymongo.errors import DuplicateKeyError

from newsmuncher.services.word_shuffle import (
    BANK_FILES, BankExhaustedError, PermanentWordClaims, WordClaimConflict,
)


class AtomicCollection:
    def __init__(self):
        self.docs = {}
        self.lock = threading.RLock()

    def find_one(self, query):
        with self.lock:
            doc = self.docs.get(query['_id'])
            return deepcopy(doc) if doc else None

    def insert_one(self, doc):
        with self.lock:
            if doc['_id'] in self.docs:
                raise DuplicateKeyError('duplicate')
            self.docs[doc['_id']] = deepcopy(doc)

    def update_one(self, query, update, session=None):
        with self.lock:
            doc = self.docs.get(query['_id'])
            claimed = doc.get('claimed_words') if doc else None
            condition = query['claimed_words']
            if not isinstance(claimed, list) or any(word in claimed for word in condition['$nin']):
                return Mock(matched_count=0)
            for word in update['$addToSet']['claimed_words']['$each']:
                if word not in claimed:
                    claimed.append(word)
            doc['last_claim'] = deepcopy(update['$set']['last_claim'])
            doc['version'] = doc.get('version', 0) + update['$inc']['version']
            return Mock(matched_count=1)

    def transaction(self, operation):
        with self.lock:
            snapshot = deepcopy(self.docs)
            try:
                return operation(None)
            except Exception:
                self.docs = snapshot
                raise


class FinalWordClaimsTests(unittest.TestCase):
    def setUp(self):
        self.db = AtomicCollection()
        self.claims = PermanentWordClaims(
            self.db, shuffle=lambda words: None, transaction_runner=self.db.transaction)

    def test_draw_selects_without_claiming(self):
        self.assertEqual(self.claims.draw('nouns', ['teapot', 'moon'], 2), ['teapot', 'moon'])
        self.assertEqual(self.db.docs['nouns']['claimed_words'], [])

    def test_only_candidates_used_in_final_response_are_claimed(self):
        candidates = {'nouns': ['teapot', 'moon'], 'animals': ['cat', 'yak']}
        for bank, words in candidates.items():
            self.claims.draw(bank, words, len(words))
        used = self.claims.claim_used(candidates, 'The TEAPOT returns', 'A yak dances. Catsup stays.')
        self.assertEqual(used, {'nouns': ['teapot'], 'animals': ['yak']})
        self.assertEqual(self.db.docs['nouns']['claimed_words'], ['teapot'])
        self.assertEqual(self.db.docs['animals']['claimed_words'], ['yak'])

    def test_unused_and_failed_generation_claim_nothing(self):
        candidates = {'nouns': ['unused']}
        self.claims.draw('nouns', candidates['nouns'], 1)
        # A failed provider never reaches claim_used.
        self.assertEqual(self.db.docs['nouns']['claimed_words'], [])
        self.assertEqual(self.claims.claim_used(candidates, 'Other title', 'Other body'), {})
        self.assertEqual(self.db.docs['nouns']['claimed_words'], [])
        self.assertEqual(self.claims.draw('nouns', ['unused'], 1), ['unused'])

    def test_concurrent_final_claim_has_one_winner(self):
        candidates = {'nouns': ['moon']}
        self.claims.draw('nouns', ['moon'], 1)
        barrier = threading.Barrier(2)

        def worker():
            barrier.wait()
            try:
                self.claims.claim_used(candidates, 'Moon', 'body')
                return 'claimed'
            except WordClaimConflict:
                return 'conflict'

        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(lambda _: worker(), range(2)))
        self.assertCountEqual(outcomes, ['claimed', 'conflict'])
        self.assertEqual(self.db.docs['nouns']['claimed_words'], ['moon'])

    def test_cross_bank_conflict_rolls_back_entire_claim(self):
        for bank in ('nouns', 'animals'):
            self.claims.draw(bank, ['moon'], 1)
        self.claims.claim_used({'animals': ['moon']}, '', 'moon')
        with self.assertRaises(WordClaimConflict):
            self.claims.claim_used({'nouns': ['moon'], 'animals': ['moon']}, 'moon', '')
        self.assertEqual(self.db.docs['nouns']['claimed_words'], [])
        self.assertEqual(self.db.docs['animals']['claimed_words'], ['moon'])

    def test_claimed_words_are_excluded_and_csvs_stay_read_only(self):
        from newsmuncher.utils import clean_data
        paths = [Path('newsmuncher/resources/words') / name for name in BANK_FILES.values()]
        before = [hashlib.sha256(path.read_bytes()).hexdigest() for path in paths]
        self.claims.draw('nouns', ['used', 'free'], 1)
        self.claims.claim_used({'nouns': ['used']}, 'used', '')
        self.assertEqual(self.claims.draw('nouns', ['used', 'free'], 1), ['free'])
        with patch.object(clean_data, 'shared_bags', return_value=self.claims), patch('builtins.print'):
            result = clean_data.load_random_words(2)
        self.assertTrue(all(len(result[bank]) == 2 for bank in BANK_FILES))
        self.assertEqual(before, [hashlib.sha256(path.read_bytes()).hexdigest() for path in paths])

    def test_legacy_or_exhausted_ledgers_fail_closed(self):
        self.db.docs['legacy'] = {'_id': 'legacy', 'claimed_words': None}
        with self.assertRaisesRegex(RuntimeError, 'historical claim recovery'):
            self.claims.draw('legacy', ['word'], 1)
        self.db.docs['nouns'] = {'_id': 'nouns', 'claimed_words': ['used']}
        with self.assertRaises(BankExhaustedError):
            self.claims.draw('nouns', ['used'], 1)

    def test_invalid_counts(self):
        with self.assertRaises(ValueError):
            self.claims.draw('nouns', ['word'], -1)
        with self.assertRaises(ValueError):
            self.claims.draw('nouns', [], 1)
        self.assertEqual(self.claims.draw('nouns', ['word'], 0), [])


class ResetWordClaimsTests(unittest.TestCase):
    def test_reset_targets_only_supplied_word_claim_collection(self):
        from scripts.reset_word_claims import COLLECTION, DATABASE, reset_word_claims
        collection = Mock()
        collection.delete_many.return_value.deleted_count = 5
        self.assertEqual(reset_word_claims(collection), 5)
        collection.delete_many.assert_called_once_with({})
        self.assertEqual((DATABASE, COLLECTION), ('funny_json_db', 'word_shuffle_bags'))

    def test_command_refuses_non_development_environment_before_connecting(self):
        from scripts.reset_word_claims import main
        with patch.dict('os.environ', {}, clear=True), patch('scripts.reset_word_claims.MongoClient') as client:
            with self.assertRaises(SystemExit):
                main(['--confirm', 'RESET-WORD-CLAIMS'])
        client.assert_not_called()


if __name__ == '__main__':
    unittest.main()
