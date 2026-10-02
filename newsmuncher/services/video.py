"""One non-expiring animation claim per existing rewrite; status never generates."""
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import secrets
import time
from uuid import UUID, uuid4

from bson import ObjectId

from newsmuncher.config import GENERATED_IMAGES_DIR, GENERATED_VIDEO_DIR
from newsmuncher.services.image_generation import store, get_provider, build_end_image_prompt
from newsmuncher.services.video_prompt import build_transition_prompt
from newsmuncher.services.wavespeed import MODEL, create_video, read_image


class VideoError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


def now():
    return datetime.now(timezone.utc).isoformat()


class Videos:
    def __init__(self, rewrites=store, directory=GENERATED_VIDEO_DIR,
                 images=GENERATED_IMAGES_DIR, provider=create_video, image_provider=None):
        self.store, self.directory, self.images, self.provider = rewrites, Path(directory), Path(images), provider
        self.image_provider = image_provider

    def path(self, key):
        try:
            if str(UUID(key)) != key:
                raise ValueError()
        except (ValueError, TypeError, AttributeError):
            raise VideoError(404, 'Rewrite unavailable.') from None
        return self.directory / f'{key}.mp4'

    def read(self, db, key, owner):
        self.path(key)
        if not owner:
            raise VideoError(401, 'Sign in to your pet first.')
        try:
            state = self.store.read(db, key, owner)
        except (LookupError, PermissionError):
            raise VideoError(404, 'Rewrite unavailable.') from None
        if state.get('discarded') or state.get('generating'):
            raise VideoError(409, 'Rewrite is no longer available or still being written.')
        return state

    def source(self, key, state):
        url = state['result'].get('image_url', '')
        try:
            image_id = str(UUID(url.removeprefix('/generated-images/').removesuffix('.png')))
        except (ValueError, AttributeError):
            raise VideoError(409, 'Generate an image for this rewrite first.') from None
        path = self.images / f'{image_id}.png'
        if url != f'/generated-images/{image_id}.png' or path.is_symlink() or not path.is_file():
            raise VideoError(409, 'Generate an image for this rewrite first.')
        return path

    def has_video(self, key):
        path = self.path(key)
        try:
            if path.is_symlink() or not path.is_file():
                return False
            with path.open('rb') as stream:
                header = stream.read(12)
            return len(header) == 12 and header[4:8] == b'ftyp'
        except OSError:
            return False

    def public(self, key, state):
        if state.get('video_detached'):
            return {'rewrite_id': key, 'video_status': 'superseded', 'can_generate': False}
        video = state.get('video')
        if video is None and 'video' not in state:
            try:
                self.source(key, state)
                available = not self.path(key).exists() and not self.path(key).is_symlink()
            except VideoError:
                available = False
            return {'rewrite_id': key, 'video_status': 'none', 'can_generate': available}
        status = video.get('status') if isinstance(video, dict) else 'failed_or_uncertain'
        if status == 'complete' and self.has_video(key):
            return {'rewrite_id': key, 'video_status': 'complete', 'can_generate': False,
                    'video_url': f'/videos/{key}/media'}
        if status in ('queued', 'started') and time.time() - video.get('requested_epoch', 0) < 1800:
            return {'rewrite_id': key, 'video_status': status, 'can_generate': False}
        return {'rewrite_id': key, 'video_status': 'failed_or_uncertain', 'can_generate': False,
                'message': 'Animation unavailable or interrupted. Operator review is needed; no automatic retry.'}

    def status(self, collection, key, owner):
        with self.store.transaction() as db:
            state = self.read(db, key, owner)
            video = state.get('video')
            # Recover only a published, valid local file belonging to our durable claim.
            if isinstance(video, dict) and video.get('rewrite_id') == key and self.has_video(key):
                if video.get('status') != 'complete':
                    video.update(status='complete', created_at=now())
                    self.store.save(db, key, state)
            result = self.public(key, state)
        self.sync(collection, key, owner)
        return result

    def sync(self, collection, key, owner):
        # Metadata-only repair is safe from status and banking. Never schedules a job.
        with self.store.transaction() as db:
            state = self.read(db, key, owner)
            video, entry_id = state.get('video'), state.get('entry_id')
            if state.get('video_detached') or not isinstance(video, dict) or not entry_id or not ObjectId.is_valid(entry_id):
                return
            metadata = {k: v for k, v in video.items() if k not in ('worker_started', 'requested_epoch')}
            try:
                # Keep synchronization ordered with rewrite updates; an older status
                # reader must not overwrite a just-completed nomination with 'started'.
                collection.update_one({'_id': ObjectId(entry_id), 'rewrite_id': key,
                                       'image_owner': owner, 'nominated': True}, {'$set': {'video': metadata}})
            except Exception:
                pass  # Local claim survives; later status/bank reads repair metadata.

    def claim(self, collection, key, owner):
        # BEGIN IMMEDIATE serializes claims across processes on the shared rewrite store.
        self.path(key)
        with self.store.transaction() as db:
            state = self.read(db, key, owner)
            if 'video' in state or self.path(key).exists() or self.path(key).is_symlink():
                return self.public(key, state), False
            # Fail closed if the nomination has an earlier claim (e.g. restored SQLite).
            if state.get('entry_id'):
                entry = collection.find_one({'_id': ObjectId(state['entry_id']),
                    'rewrite_id': key, 'image_owner': owner, 'nominated': True})
                if not entry:
                    raise VideoError(404, 'Nomination unavailable.')
                if 'video' in entry:
                    state['video'] = entry['video']
                    self.store.save(db, key, state)
                    return self.public(key, state), False
            if not os.environ.get('WAVESPEED_API_KEY', '').strip():
                raise VideoError(503, 'Animation is not configured.')
            source = self.source(key, state)
            try:
                image, _, _ = read_image(source)
            except Exception:
                raise VideoError(422, 'Stored image is invalid.') from None
            self.directory.mkdir(parents=True, exist_ok=True)
            shared_style = state['result'].get('image_style')
            state['video'] = {'rewrite_id': key, 'status': 'queued', 'provider': 'wavespeed',
                'model': MODEL, 'duration': 8, 'resolution': '480p',
                'prompt': build_transition_prompt(state['result'], shared_style),
                'shared_visual_style': shared_style, 'seed': secrets.randbelow(2**31),
                'source_sha256': hashlib.sha256(image).hexdigest(), 'requested_at': now(),
                'requested_epoch': time.time(), 'storage_key': f'{key}.mp4',
                'end_frame': {'mode': 'independent_end_frame', 'status': 'queued',
                    'image_id': str(uuid4()),
                    'image_style': shared_style}}
            state['video']['end_frame']['image_prompt'] = build_end_image_prompt(
                state['result'], state['video']['end_frame']['image_style'])
            self.store.save(db, key, state)
            return self.public(key, state), True

    def replace(self, collection, key, owner):
        """Retire animation state after an explicit successful image replacement."""
        with self.store.transaction() as db:
            state = self.read(db, key, owner)
            if isinstance(state.get('video'), dict):
                state.setdefault('video_history', []).append(state['video'])
            state.pop('video', None)
            state.pop('video_detached', None)
            self.store.save(db, key, state)
            entry_id = state.get('entry_id')
        if entry_id and ObjectId.is_valid(entry_id):
            collection.update_one({'_id':ObjectId(entry_id),'rewrite_id':key,
                                   'image_owner':owner,'nominated':True}, {'$unset':{'video':''}})
        path = self.path(key)
        if path.is_file() and not path.is_symlink():
            path.unlink()

    def run(self, collection, key, owner):
        # A duplicate task delivery cannot execute the same durable claim twice.
        with self.store.transaction() as db:
            state = self.read(db, key, owner)
            video = state.get('video')
            if not isinstance(video, dict) or video.get('status') != 'queued' or video.get('worker_started'):
                return
            video.update(worker_started=True, status='started')
            self.store.save(db, key, state)
        def checkpoint():
            with self.store.transaction() as db:
                current = self.read(db, key, owner)
                current['video'] = dict(video)
                self.store.save(db, key, current)
        try:
            source = self.source(key, state)
            data, _, _ = read_image(source)
            if hashlib.sha256(data).hexdigest() != video['source_sha256']:
                raise VideoError(409, 'Source image changed after animation was requested.')
            api_key = os.environ.get('WAVESPEED_API_KEY', '').strip()
            if not api_key:
                raise VideoError(503, 'Animation configuration unavailable.')
            last_source = None
            end_frame = video.get('end_frame')
            if isinstance(end_frame, dict):
                last_source = self.images / f"{end_frame['image_id']}.png"
                if end_frame.get('status') != 'complete':
                    end_frame['status'] = 'started'
                    checkpoint()  # Permanent paid-image claim before contacting the provider.
                    generated = (self.image_provider or get_provider()).generate_image(
                        end_frame['image_prompt'], end_frame['image_id'])
                    end_frame.update(generated, status='complete')
                    data, _, _ = read_image(last_source)
                    end_frame['source_sha256'] = hashlib.sha256(data).hexdigest()
                    checkpoint()
                elif not last_source.is_file():
                    raise VideoError(409, 'Stored end frame is unavailable.')
            self.provider(source, self.path(key), video['prompt'], video['seed'], video,
                          checkpoint, api_key, last_source=last_source)
            if not self.has_video(key):
                raise VideoError(502, 'Animation output unavailable.')
            video.update(status='complete', created_at=now())
            checkpoint()
        except Exception:
            video['status'] = 'failed_or_uncertain'
            if 'error' not in video:
                video['error'] = {'stage': 'local_preparation_or_persistence', 'http_status': None,
                                  'exception_type': 'VideoError', 'exception_message': 'Local animation work interrupted.'}
            try:
                checkpoint()
            except Exception:
                pass  # Original claim survives; never clear it or submit again.
        try:
            self.sync(collection, key, owner)
        except VideoError:
            # Discarded drafts cannot expose their orphaned outputs.
            self.path(key).unlink(missing_ok=True)


service = Videos()
