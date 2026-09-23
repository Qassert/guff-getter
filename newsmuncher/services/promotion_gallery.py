"""Nominated-content retrieval and review only. No generation-service imports."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
from contextlib import closing
import json
import random
import sqlite3
from uuid import UUID, uuid4

from bson import ObjectId
from fastapi import HTTPException
from pymongo import ReturnDocument
from pymongo.read_concern import ReadConcern
from pymongo.write_concern import WriteConcern

from newsmuncher.config import (GENERATED_IMAGES_DIR, GENERATED_AUDIO_DIR,
                               GENERATED_NARRATION_DIR, JINGLE_STATE_FILE)

# Same conservative legacy interpretation as nomination_state; explicit false wins.
NOMINATED = {'$or': [{'nominated': True},
    {'nominated': {'$exists': False}, 'crazyReplacement1done': True}]}


def seen(entry):
    count = entry.get('promotion_gallery_seen_count', 0)
    return count if type(count) is int and count >= 0 else 0


class PromotionGallery:
    def __init__(self, entries, receipts, images=GENERATED_IMAGES_DIR,
                 narration=GENERATED_NARRATION_DIR, audio=GENERATED_AUDIO_DIR,
                 jingles=JINGLE_STATE_FILE, choose=random.choice):
        self.entries, self.receipts = entries, receipts
        self.images, self.narration, self.audio = map(Path, (images, narration, audio))
        self.jingles, self.choose = Path(jingles), choose

    def entry(self, key, session=None):
        if not ObjectId.is_valid(key):
            raise HTTPException(404, 'Nomination not found.')
        entry = self.entries.find_one({'_id': ObjectId(key), **NOMINATED}, session=session)
        if not entry:
            raise HTTPException(404, 'Nomination not found.')
        return entry

    @staticmethod
    def exists(path):
        try:
            return not path.is_symlink() and path.is_file() and path.stat().st_size > 0
        except OSError:
            return False

    def media_path(self, entry, kind):
        key = str(entry['_id'])
        if kind == 'image':
            url = entry.get('image_url')
            if not isinstance(url, str):
                return None
            try:
                image_id = UUID(url.removeprefix('/generated-images/').removesuffix('.png'))
            except ValueError:
                return None
            if url != f'/generated-images/{image_id}.png':
                return None
            path = self.images / f'{image_id}.png'
        elif kind == 'narration':
            state = entry.get('narration')
            if not isinstance(state, dict) or state.get('entry_id') != key:
                return None
            path = self.narration / f'{key}.mp3'
        elif kind == 'jingle':
            path = self.audio / f'{key}.mp3'
            if not self.exists(path):
                return None
            # Recover an existing, unsynced jingle from its read-only local sidecar.
            if entry.get('jingle_url') != f'/generated-audio/{key}.mp3':
                if not self.jingles.is_file():
                    return None
                try:
                    with closing(sqlite3.connect(self.jingles.resolve().as_uri() + '?mode=ro', uri=True)) as db:
                        row = db.execute('SELECT state FROM jingles WHERE id=?', (key,)).fetchone()
                    state = json.loads(row[0]) if row else {}
                    if state.get('status') == 'retired' or not state.get('brief'):
                        return None
                except (sqlite3.Error, ValueError, TypeError):
                    return None
        else:
            return None
        return path if self.exists(path) else None

    def serialize(self, entry):
        key = str(entry['_id'])
        return {'id': key, 'title': entry.get('crazyReplacement1Title') or '',
            'body': entry.get('crazyReplacement1Extract') or '',
            'promoted': entry.get('promoted') is True,
            'seen_count': seen(entry),
            **{kind + '_url': f'/promotion-gallery/items/{key}/media/{kind}'
               if self.media_path(entry, kind) else None for kind in ('image', 'narration', 'jingle')}}

    def select(self, viewer):
        # Only IDs/counts are scanned; content/assets are loaded for one item.
        candidates = list(self.entries.find(NOMINATED, {'promotion_gallery_seen_count': 1}))
        if not candidates:
            return {'item': None}
        minimum = min(map(seen, candidates))
        selected = self.choose([e for e in candidates if seen(e) == minimum])
        entry = self.entry(str(selected['_id']))
        token = str(uuid4())
        self.receipts.create_index('expires_at', expireAfterSeconds=0)
        self.receipts.insert_one({'_id': token, 'viewer': viewer, 'entry_id': entry['_id'],
            'displayed': False, 'expires_at': datetime.now(timezone.utc) + timedelta(minutes=10)})
        return {'item': self.serialize(entry), 'view_token': token}

    def displayed(self, viewer, token):
        # Receipt + count commit together; a retried ACK cannot increment twice.
        def apply(session):
            query = {'_id': token, 'viewer': viewer,
                     'expires_at': {'$gt': datetime.now(timezone.utc)}}
            receipt = self.receipts.find_one(query, session=session)
            if not receipt:
                raise HTTPException(409, 'View expired. Turn to another creation.')
            if receipt['displayed']:
                return {'recorded': True}
            self.entry(str(receipt['entry_id']), session)
            self.receipts.update_one({**query, 'displayed': False},
                                     {'$set': {'displayed': True}}, session=session)
            # Legacy missing/null/invalid counters begin at zero, without a migration.
            entry = self.entry(str(receipt['entry_id']), session)
            self.entries.update_one({'_id': entry['_id'], **NOMINATED},
                {'$set': {'promotion_gallery_seen_count': seen(entry) + 1}}, session=session)
            return {'recorded': True}
        with self.entries.database.client.start_session() as session:
            return session.with_transaction(apply, read_concern=ReadConcern('snapshot'),
                                            write_concern=WriteConcern('majority'))

    def promote(self, key):
        entry = self.entry(key)
        result = self.entries.find_one_and_update(
            {'_id': entry['_id'], **NOMINATED, 'promoted': {'$ne': True}},
            {'$set': {'promoted': True, 'promoted_at': datetime.now(timezone.utc)}},
            return_document=ReturnDocument.AFTER)
        if not result:
            result = self.entry(key)
        return {'id': key, 'promoted': result.get('promoted') is True,
                'promoted_at': result['promoted_at'].isoformat() if isinstance(result.get('promoted_at'), datetime) else None}
