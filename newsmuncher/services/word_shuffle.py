"""Permanent per-bank claims selected atomically by MongoDB; never reset on CSV edits."""
import csv
from functools import lru_cache
import hashlib
import json
import os
import random

import certifi
from pymongo import MongoClient, ReturnDocument
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
    """One permanent claimed_words ledger per bank; CSV edits never clear it."""

    def __init__(self, collection, shuffle=None):
        self.collection = collection
        self.shuffle = shuffle or random.SystemRandom().shuffle

    def draw(self, bank, current_words, count, max_attempts=10):
        if count < 0 or not current_words:
            raise ValueError('Nonempty bank and nonnegative count required')
        if count == 0:
            return []
        vocabulary = list(dict.fromkeys(current_words))
        self.shuffle(vocabulary)  # Shuffle the master vocabulary, not an unused snapshot.
        digest = hashlib.sha256(json.dumps(sorted(vocabulary), ensure_ascii=False).encode()).hexdigest()
        try:
            self.collection.insert_one({'_id': bank, 'claimed_words': [], 'version': 1})
        except DuplicateKeyError:
            pass
        for _ in range(max_attempts):
            # Both eligibility and selection are evaluated against the current ledger
            # by MongoDB in the same atomic operation. Literal protects '$'-prefixed words.
            available = {'$filter': {'input': {'$literal': vocabulary}, 'as': 'word',
                'cond': {'$not': [{'$in': ['$$word', '$claimed_words']}]}}}
            result = self.collection.find_one_and_update(
                {'_id': bank, 'claimed_words': {'$type': 'array'},
                 '$expr': {'$gte': [{'$size': available}, count]}},
                [{'$set': {'last_claim': {'$slice': [available, count]}}},
                 {'$set': {'claimed_words': {'$setUnion': ['$claimed_words', '$last_claim']},
                           'known_vocabulary_digest': digest,
                           'version': {'$add': [{'$ifNull': ['$version', 0]}, 1]}}}],
                return_document=ReturnDocument.AFTER)
            if result is not None:
                return result['last_claim']
            state = self.collection.find_one({'_id': bank})
            if state is None:
                raise RuntimeError('Word ledger disappeared; refusing to recreate claim history')
            if 'claimed_words' in state:
                raise BankExhaustedError(f"Bank '{bank}' has insufficient unclaimed words for {count}; never recycled.")
            # Old cursor/reset records cannot prove the full historical used set.
            # Fail closed rather than make an erased claim available again.
            raise RuntimeError('Legacy word ledger requires historical claim recovery before use')



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
