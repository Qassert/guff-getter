"""Read-time restoration of owner-matched saved nominations; no Mongo writes."""
import json
import logging
import sqlite3
from copy import deepcopy
from uuid import uuid5, NAMESPACE_URL
from fastapi import HTTPException
from newsmuncher.config import SHARED_MEDIA_ROOT


def legacy_editor_id(entry_id):
    return str(uuid5(NAMESPACE_URL, 'newsmuncher:nomination:' + str(entry_id)))


def text_fields(record):
    """Flat historical fields and JSON-encoded result wrappers share one boundary."""
    if isinstance(record, str):
        try: record = json.loads(record)
        except (ValueError, TypeError): record = {}
    if not isinstance(record, dict):
        return {}
    result = record.get('result', {})
    if isinstance(result, str):
        try: result = json.loads(result)
        except (ValueError, TypeError): result = {}
    normal = dict(result) if isinstance(result, dict) else {}
    for key, value in record.items():
        if value is not None and not (key == 'crazyReplacement1Extract' and value == ''):
            normal[key] = value
    return normal


def restore_nomination(entry, owner, store, db, existing=None):
    if not owner or (entry.get('image_owner') or entry.get('creationUser')) != owner:
        raise HTTPException(403, 'This nomination belongs to another pet.')
    if not (entry.get('nominated') or entry.get('crazyReplacement1done')):
        raise HTTPException(404, 'Saved nomination not found.')
    rewrite_id = entry.get('rewrite_id') or legacy_editor_id(entry['_id'])
    cached = deepcopy(existing or {})
    # Historical worktree state is optional, read-only and identity/owner checked.
    if SHARED_MEDIA_ROOT and not cached:
        path = SHARED_MEDIA_ROOT / 'previews' / 'image_rewrites.sqlite3'
        if path.is_file():
            try:
                with sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True) as legacy:
                    row = legacy.execute('SELECT state FROM rewrites WHERE id=?', (rewrite_id,)).fetchone()
                if row:
                    candidate = json.loads(row[0])
                    if (isinstance(candidate, dict) and candidate.get('owner') == owner and
                            str(candidate.get('entry_id')) == str(entry['_id']) and
                            not candidate.get('discarded')):
                        cached = candidate
            except (sqlite3.Error, OSError, ValueError, TypeError):
                logging.getLogger(__name__).warning('Legacy editor cache unavailable rewrite_id=%s', rewrite_id)
    old = text_fields(cached.get('result') or {})
    current = text_fields(entry)
    result = {key: value for key, value in old.items() if isinstance(value, (str, int, float, bool))}
    for key, value in current.items():
        if isinstance(value, (str, int, float, bool)) and (not isinstance(value, str) or value.strip() or key == 'crazyReplacement1Title'):
            result[key] = value
    body = result.get('crazyReplacement1Extract')
    if not isinstance(body, str) or not body.strip():
        raise HTTPException(422, 'This nomination has no recoverable saved story text.')
    result.update(rewrite_id=rewrite_id, nominated=True)
    result.setdefault('crazyReplacement1Title', '')
    for key in ('title', 'description', 'extract'):
        result.setdefault(key, '')
    state = {**deepcopy(cached), 'owner': owner, 'entry_id': str(entry['_id']),
             'result': result, 'restored_nomination': True,
             'legacy_editor': not bool(entry.get('rewrite_id'))}
    store.save(db, rewrite_id, state)
    logging.getLogger(__name__).debug('creation_restore rewrite_id=%s nomination_id=%s legacy_identity=%s',
                                      rewrite_id, entry['_id'], state['legacy_editor'])
    return result
