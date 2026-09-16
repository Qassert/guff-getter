"""One durable Mongo claim per nomination. No retries or synthesis from status."""
from datetime import datetime, timezone
import os
from pathlib import Path
import random
import tempfile

from bson import ObjectId
from dotenv import load_dotenv
from pymongo.write_concern import WriteConcern

from newsmuncher.config import ENV_FILE, GENERATED_NARRATION_DIR
from newsmuncher.services.openai_tts import MODEL, VOICES, generate_openai


class NarrationError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


def owner_query(owner):
    if not owner:
        raise NarrationError(401, "Select a pet first.")
    return {"nominated": True, "$or": [{"image_owner": owner},
            {"image_owner": {"$exists": False}, "creationUser": owner}]}


def snapshot(entry):
    return {"title": entry.get("crazyReplacement1Title", ""),
            "body": entry.get("crazyReplacement1Extract", "")}


class Narrations:
    def __init__(self, directory=GENERATED_NARRATION_DIR, provider=generate_openai):
        self.directory = Path(directory)
        self.provider = provider

    def path(self, key):
        if not ObjectId.is_valid(key):
            raise NarrationError(404, "Nomination not found.")
        return self.directory / f"{ObjectId(key)}.mp3"

    def entry(self, collection, key, owner):
        self.path(key)
        entry = collection.find_one({"_id": ObjectId(key), **owner_query(owner)})
        if not entry or entry.get('nominated') is not True or (
                entry.get('image_owner') or entry.get('creationUser')) != owner:
            raise NarrationError(404, "No nomination belonging to this pet.")
        return entry

    def resolve(self, collection, rewrite_id, owner):
        entries = list(collection.find({"rewrite_id": rewrite_id, **owner_query(owner)}).limit(2))
        if len(entries) != 1:
            raise NarrationError(409 if entries else 404, "Nomination identity is missing or ambiguous.")
        return self.status(collection, str(entries[0]['_id']), owner)

    def has_audio(self, key):
        path = self.path(key)
        return path.is_file() and not path.is_symlink() and path.stat().st_size > 0

    def status(self, collection, key, owner):
        entry = self.entry(collection, key, owner)
        state = entry.get('narration')
        result = {"entry_id": key, "can_generate": False, "narration_status": "unavailable"}
        if 'narration' not in entry:
            result.update(can_generate=not self.path(key).exists(), narration_status='none')
            return result
        # Unknown/legacy metadata must never authorize another paid call.
        if (not isinstance(state, dict) or state.get('entry_id') != key
                or not all(field in state for field in ('voice', 'voice_name', 'snapshot'))):
            result['message'] = 'Narration metadata needs operator review; no regeneration.'
            return result
        exists = self.has_audio(key)
        if exists and state.get('status') in ('started', 'failed', 'complete'):
            pending = False
            if state['status'] != 'complete':
                try:
                    updated = collection.update_one(
                        {'_id': entry['_id'], **owner_query(owner), 'narration': state},
                        {'$set': {'narration.status': 'complete',
                                  'narration.generated_at': state.get('generated_at') or
                                  datetime.fromtimestamp(self.path(key).stat().st_mtime, timezone.utc).isoformat()}})
                    if updated.matched_count == 0:
                        # Recheck exact ownership/existence; never hide a confirmed deletion.
                        self.entry(collection, key, owner)
                        pending = True
                except NarrationError:
                    raise
                except Exception:
                    pending = True
            result.update(narration_status='complete', narration_url=f'/narrations/{key}/audio',
                          voice=state['voice'], voice_name=state['voice_name'],
                          text_changed=state['snapshot'] != snapshot(entry), metadata_pending=pending)
        else:
            status = state.get('status', 'unavailable')
            result.update(narration_status=status if status != 'complete' else 'unavailable',
                          voice_name=state.get('voice_name'),
                          message='Narration unavailable or request still pending. No automatic retry; '
                                  'an interrupted/failed request requires operator review.')
        return result

    def discover(self, collection, owner):
        entries = collection.find({**owner_query(owner), 'narration': {'$exists': True}}).sort(
            [('creationDate', -1), ('_id', -1)])
        saved = []
        for entry in entries:
            try:
                state = self.status(collection, str(entry['_id']), owner)
            except NarrationError as exc:
                if exc.status == 404:
                    continue
                raise
            if state.get('narration_url'):
                saved.append({**state, 'title': snapshot(entry)['title']})
        return {'narrations': saved}

    def generate(self, collection, key, owner, text_snapshot):
        # Majority acknowledgement before the paid call prevents rollback-based duplicate claims.
        collection = collection.with_options(write_concern=WriteConcern(w='majority'))
        existing = self.status(collection, key, owner)
        if not existing['can_generate']:
            return existing
        body = text_snapshot['body'].strip()
        if not body or len(body) > 3500:
            raise NarrationError(422, 'Narration needs a body of at most 3500 characters.')
        # Titles remain display/snapshot metadata only; never send them to speech synthesis.
        spoken = body
        load_dotenv(ENV_FILE, override=False)
        key_value = os.environ.get('OPENAI_API_KEY', '').strip()
        if not key_value:
            raise NarrationError(503, 'Narration is not configured (OPENAI_API_KEY missing).')
        self.directory.mkdir(parents=True, exist_ok=True)
        voice_name, voice = random.choice(VOICES)
        state = {'entry_id': key, 'status': 'started', 'voice': voice, 'voice_name': voice_name,
                 'model': MODEL, 'provider': 'openai', 'snapshot': dict(text_snapshot),
                 'storage_key': f'{key}.mp3', 'url': f'/narrations/{key}/audio',
                 'requested_at': datetime.now(timezone.utc).isoformat()}
        claim = collection.update_one(
            {'_id': ObjectId(key), **owner_query(owner), 'narration': {'$exists': False}},
            {'$set': {'narration': state}})
        if claim.matched_count != 1:
            return self.status(collection, key, owner)
        temporary = None
        try:
            audio = self.provider(key_value, voice, spoken)
            if not isinstance(audio, bytes) or len(audio) < 3 or not (
                    audio.startswith(b'ID3') or audio[0] == 255 and audio[1] & 224 == 224):
                raise ValueError('Invalid MP3')
            self.entry(collection, key, owner)  # Deletion during synthesis cannot attach to another entry.
            with tempfile.NamedTemporaryFile(dir=self.directory, suffix='.part', delete=False) as output:
                temporary = Path(output.name)
                output.write(audio)
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary, self.path(key))
            # Store timestamp; status can repair completion from the atomic file if this write fails.
            updated = collection.update_one(
                {'_id': ObjectId(key), **owner_query(owner), 'narration.entry_id': key},
                {'$set': {'narration.status': 'complete',
                          'narration.generated_at': datetime.now(timezone.utc).isoformat()}})
            if updated.matched_count != 1:
                raise NarrationError(404, 'Nomination disappeared; narration was not attached.')
        except NarrationError:
            try:
                self.path(key).unlink(missing_ok=True)
            except OSError:
                pass  # Inaccessible orphan; cleanup failure must not hide missing-entry status.
            raise
        except Exception:
            # A persisted file is recoverable; an uncertain provider outcome is never retried.
            if not self.has_audio(key):
                try:
                    collection.update_one({'_id': ObjectId(key), 'narration.entry_id': key},
                                          {'$set': {'narration.status': 'failed'}})
                except Exception:
                    pass
                raise NarrationError(502, 'Narration failed; story unchanged. No automatic retry.') from None
        finally:
            if temporary:
                temporary.unlink(missing_ok=True)
        return self.status(collection, key, owner)


service = Narrations()
