"""Nominated-content retrieval and review only. No generation-service imports."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
from contextlib import closing
import json
import random
import re
import sqlite3
from uuid import UUID, uuid4

from bson import ObjectId
from fastapi import HTTPException
from pymongo import ReturnDocument
from pymongo.read_concern import ReadConcern
from pymongo.write_concern import WriteConcern

from newsmuncher.config import (GENERATED_IMAGES_READ_DIRS, GENERATED_AUDIO_READ_DIRS,
                               GENERATED_NARRATION_READ_DIRS, GENERATED_VIDEO_READ_DIRS,
                               JINGLE_STATE_FILE)
from newsmuncher.services.video_pingpong import service as pingpong

# Same conservative legacy interpretation as nomination_state; explicit false wins.
NOMINATED = {'$or': [{'nominated': True},
    {'nominated': {'$exists': False}, 'crazyReplacement1done': True}]}


def seen(entry):
    count = entry.get('promotion_gallery_seen_count', 0)
    return count if isinstance(count, int) and not isinstance(count, bool) and count >= 0 else 0


def minimum_seen_count(entries, exclude=None):
    """Return the current Gallery floor without changing any existing entry."""
    query = dict(NOMINATED)
    if exclude is not None:
        query['_id'] = {'$ne': exclude}
    candidates = entries.find(query, {'promotion_gallery_seen_count': 1})
    return min((seen(entry) for entry in candidates), default=0)


def nomination_time(entry):
    """Return one comparable naive-UTC BSON date, or None for undated legacy rows."""
    value = entry.get('nominated_at')
    if not isinstance(value, datetime):
        value = entry.get('creationDate')
    if not isinstance(value, datetime):
        return None
    if value.tzinfo is not None:
        value = value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def chronological_key(entry):
    value = nomination_time(entry)
    return (value is not None, value or datetime.min, str(entry['_id']))


class PromotionGallery:
    def __init__(self, entries, receipts, images=GENERATED_IMAGES_READ_DIRS,
                 narration=GENERATED_NARRATION_READ_DIRS, audio=GENERATED_AUDIO_READ_DIRS,
                 jingles=JINGLE_STATE_FILE, choose=random.choice,
                 videos=GENERATED_VIDEO_READ_DIRS):
        self.entries, self.receipts = entries, receipts
        self.image_roots = self._directories(images)
        self.narration_roots = self._directories(narration)
        self.audio_roots = self._directories(audio)
        self.images, self.narration, self.audio = (
            self.image_roots[0], self.narration_roots[0], self.audio_roots[0])
        self.jingles, self.choose = Path(jingles), choose
        self.video_roots = self._directories(videos)
        self.videos = self.video_roots[0]

    @staticmethod
    def _directories(value):
        return ((Path(value),) if isinstance(value, (str, Path))
                else tuple(map(Path, value)))

    def first_existing(self, directories, name):
        return next((path for root in directories
                     if self.exists(path := root / name)), None)

    @staticmethod
    def with_primary(primary, directories):
        primary = Path(primary)
        return (primary,) + tuple(root for root in directories if root != primary)

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
            path = self.first_existing(
                self.with_primary(self.images, self.image_roots), f'{image_id}.png')
        elif kind == 'video':
            path = self.original_video_path(entry)
            if not path:
                return None
            path = pingpong.preferred(path)
        elif kind == 'narration':
            state = entry.get('narration')
            if not isinstance(state, dict) or state.get('entry_id') != key:
                return None
            path = self.first_existing(
                self.with_primary(self.narration, self.narration_roots), f'{key}.mp3')
        elif kind == 'jingle':
            url = entry.get('jingle_url')
            name = url.removeprefix('/generated-audio/') if isinstance(url, str) else ''
            if re.fullmatch(rf'{key}(?:\.[a-z0-9_-]+)?\.mp3', name):
                path = self.first_existing(
                    self.with_primary(self.audio, self.audio_roots), name)
            else:
                path = self._sidecar_jingle(key)
                if not path:
                    return None
        else:
            return None
        return path if path and self.exists(path) else None

    def original_video_path(self, entry):
        state = entry.get('video')
        if not isinstance(state, dict) or state.get('status') != 'complete':
            return None
        try:
            rewrite_id = str(UUID(entry.get('rewrite_id', '')))
        except (ValueError, TypeError, AttributeError):
            return None
        if state.get('rewrite_id') != rewrite_id or state.get('storage_key') != f'{rewrite_id}.mp4':
            return None
        return self.first_existing(
            self.with_primary(self.videos, self.video_roots), f'{rewrite_id}.mp4')

    def owns_video(self, path):
        """Only locally written videos may receive generated derivatives."""
        try:
            return Path(path).parent.resolve() == self.videos.resolve()
        except OSError:
            return False

    def _sidecar_jingle(self, key):
        """Recover existing legacy/versioned audio without generating or mutating."""
        if not self.jingles.is_file():
            return None
        try:
            with closing(sqlite3.connect(self.jingles.resolve().as_uri() + '?mode=ro', uri=True)) as db:
                rows = db.execute(
                    'SELECT id,state FROM jingles WHERE id=? OR id LIKE ? ORDER BY rowid DESC',
                    (key, key + ':%')).fetchall()
            for state_id, encoded in rows:
                state = json.loads(encoded)
                if not isinstance(state, dict) or state.get('status') == 'retired' or not state.get('brief'):
                    continue
                version = state_id.partition(':')[2]
                if version and not re.fullmatch(r'[a-z0-9_-]+', version):
                    continue
                name = f'{key}.{version}.mp3' if version else f'{key}.mp3'
                roots = self.with_primary(self.audio, self.audio_roots)
                if candidate := self.first_existing(roots, name):
                    return candidate
        except (sqlite3.Error, ValueError, TypeError, OSError):
            return None
        return None

    def serialize(self, entry):
        key = str(entry['_id'])
        return {'id': key, 'title': entry.get('crazyReplacement1Title') or '',
            'body': entry.get('crazyReplacement1Extract') or '',
            'rewrite_id': entry.get('rewrite_id'),
            'promoted': entry.get('promoted') is True,
            'seen_count': seen(entry),
            'image_style': entry.get('image_style'),
            'video_derivative_status': self.video_derivative_status(entry),
            **{kind + '_url': self.media_url(entry, kind) for kind in ('image', 'jingle', 'video')}}

    def video_derivative_status(self, entry):
        original = self.original_video_path(entry)
        if not original:
            return 'unavailable'
        if pingpong.available(original):
            return 'ready'
        if pingpong.failure_reason(original):
            return 'failed'
        return 'pending' if pingpong.can_attempt(original) else 'unavailable'

    def media_url(self, entry, kind):
        path = self.media_path(entry, kind)
        if not path:
            return None
        url = f"/promotion-gallery/items/{entry['_id']}/media/{kind}"
        if kind != 'video':
            return url
        try:
            stat = path.stat()
            variant = 'pingpong' if path.name.endswith('-pingpong.mp4') else 'original'
            return f'{url}?v={variant}-{stat.st_mtime_ns}-{stat.st_size}'
        except OSError:
            return url

    def select(self, viewer, previous=None, shown=(), chronological_index=0):
        # Only ordering metadata is scanned; content/assets are loaded for one item.
        candidates = list(self.entries.find(NOMINATED, {
            'nominated_at': 1, 'creationDate': 1, 'promotion_gallery_seen_count': 1
        }))
        if not candidates:
            return {'item': None}
        candidates.sort(key=chronological_key, reverse=True)
        shown = set(shown)
        unseen = [entry for entry in candidates if str(entry['_id']) not in shown]
        chronological = chronological_index < 3 and bool(unseen)
        if chronological:
            selected = unseen[0]
        else:
            # Once the three newest entries have been shown, retain the original
            # fairness floor and random tie-breaking. Prefer unvisited entries for
            # this page's browsing cycle, then resume normal fairness selection.
            pool = unseen or [entry for entry in candidates if str(entry['_id']) != previous]
            pool = pool or candidates
            floor = min(seen(entry) for entry in pool)
            selected = self.choose([entry for entry in pool if seen(entry) == floor])
        entry = self.entry(str(selected['_id']))
        token = str(uuid4())
        self.receipts.create_index('expires_at', expireAfterSeconds=0)
        self.receipts.insert_one({'_id': token, 'viewer': viewer, 'entry_id': entry['_id'],
            'displayed': False, 'expires_at': datetime.now(timezone.utc) + timedelta(minutes=10)})
        return {'item': self.serialize(entry), 'view_token': token,
                'chronological': chronological,
                'chronological_complete': chronological and (
                    chronological_index >= 2 or len(unseen) == 1),
                'cycle_complete': len(unseen) == 1}

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
