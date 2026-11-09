"""Development-only reset for the isolated global word-claim collection."""
import argparse
import os

import certifi
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.write_concern import WriteConcern

from newsmuncher.config import ENV_FILE


DATABASE = 'funny_json_db'
COLLECTION = 'word_shuffle_bags'
CONFIRMATION = 'RESET-WORD-CLAIMS'


def reset_word_claims(collection):
    """Delete only word-claim ledger documents; never touch another collection."""
    return collection.delete_many({}).deleted_count


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--confirm', required=True)
    args = parser.parse_args(argv)
    if os.getenv('NEWSMUNCHER_ENV') != 'development':
        parser.error('NEWSMUNCHER_ENV must be exactly development')
    if args.confirm != CONFIRMATION:
        parser.error(f'--confirm must be exactly {CONFIRMATION}')

    load_dotenv(ENV_FILE)
    client = MongoClient(os.environ['MONGO_URI'], tlsCAFile=certifi.where(),
                         serverSelectionTimeoutMS=10_000)
    collection = client[DATABASE].get_collection(
        COLLECTION, write_concern=WriteConcern(w='majority'))
    try:
        deleted = reset_word_claims(collection)
        print(f'Deleted {deleted} word-claim ledger document(s) from {DATABASE}.{COLLECTION}.')
    finally:
        client.close()


if __name__ == '__main__':
    main()
