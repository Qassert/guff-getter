"""Read-only candidate draws and atomic post-rewrite permanent word claims."""
import csv
from functools import lru_cache
import os
import random
import re

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


class WordClaimConflict(Exception):
    """A final rewrite used a candidate claimed by another concurrent rewrite."""


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
    """Select unclaimed candidates, then atomically claim only final-output uses."""

    def __init__(self, collection, shuffle=None, transaction_runner=None):
        self.collection = collection
        self.shuffle = shuffle or random.SystemRandom().shuffle
        self.transaction_runner = transaction_runner or self._mongo_transaction

    def _ensure_ledger(self, bank):
        try:
            self.collection.insert_one({'_id': bank, 'claimed_words': [], 'version': 1})
        except DuplicateKeyError:
            pass
        state = self.collection.find_one({'_id': bank})
        if state is None:
            raise RuntimeError('Word ledger disappeared; refusing to recreate claim history')
        if not isinstance(state.get('claimed_words'), list):
            raise RuntimeError('Legacy word ledger requires historical claim recovery before use')
        return state

    def draw(self, bank, current_words, count, max_attempts=10):
        """Choose candidates without changing the permanent claim ledger.

        Concurrent draws may overlap. ``claim_used`` resolves that race atomically
        after the final accepted rewrite is known. ``max_attempts`` remains accepted
        for compatibility with existing callers.
        """
        if count < 0 or not current_words:
            raise ValueError('Nonempty bank and nonnegative count required')
        if count == 0:
            return []
        vocabulary = list(dict.fromkeys(current_words))
        self.shuffle(vocabulary)
        claimed = set(self._ensure_ledger(bank)['claimed_words'])
        available = [word for word in vocabulary if word not in claimed]
        if len(available) < count:
            raise BankExhaustedError(f"Bank '{bank}' has insufficient unclaimed words for {count}; never recycled.")
        return available[:count]

    @staticmethod
    def words_used(candidates, title, body):
        """Return supplied candidates that occur literally in the accepted output."""
        text = f'{title}\n{body}'
        return {
            bank: list(dict.fromkeys(word for word in words if re.search(
                rf'(?<!\w){re.escape(word)}(?!\w)', text, flags=re.IGNORECASE)))
            for bank, words in candidates.items() if bank in BANK_FILES
        }

    def _mongo_transaction(self, operation):
        client = self.collection.database.client
        with client.start_session() as session:
            return session.with_transaction(operation)

    def claim_used(self, candidates, title, body):
        """Atomically commit only candidates present in the final title/body.

        The multi-document transaction prevents partial cross-bank commits. Each
        update also rejects candidates already claimed by another completed rewrite.
        """
        used = {bank: words for bank, words in self.words_used(candidates, title, body).items() if words}
        if not used:
            return {}

        def commit(session):
            for bank, words in used.items():
                result = self.collection.update_one(
                    {'_id': bank, 'claimed_words': {'$type': 'array', '$nin': words}},
                    {'$addToSet': {'claimed_words': {'$each': words}},
                     '$set': {'last_claim': words}, '$inc': {'version': 1}},
                    session=session,
                )
                if result.matched_count != 1:
                    raise WordClaimConflict(
                        f"A word selected for bank '{bank}' was claimed by another rewrite."
                    )
            return used

        return self.transaction_runner(commit)



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
