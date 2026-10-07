"""One non-expiring animation claim per existing rewrite; status never generates."""
from datetime import datetime, timezone
import hashlib
import logging
import os
from pathlib import Path
import secrets
import time
from uuid import UUID, uuid4

from bson import ObjectId

from newsmuncher.config import GENERATED_IMAGES_DIR, GENERATED_VIDEO_DIR
from newsmuncher.services.image_generation import (store, get_provider, build_end_image_prompt,
    build_transformation_map, choose_image_style)
from newsmuncher.services.video_prompt import build_transition_prompt
from newsmuncher.services.video_pingpong import service as pingpong
from newsmuncher.services.wavespeed import MODEL, create_video, read_image


log = logging.getLogger(__name__)


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
            return {'rewrite_id': key, 'video_status': 'none', 'end_image_status': 'none',
                    'can_generate': available}
        status = video.get('status') if isinstance(video, dict) else 'failed_or_uncertain'
        end_frame = video.get('end_frame') if isinstance(video, dict) else None
        end_status = end_frame.get('status', 'none') if isinstance(end_frame, dict) else 'none'
        if end_status == 'complete':
            end_path = self.images / f"{end_frame.get('image_id', '')}.png"
            if end_path.is_symlink() or not end_path.is_file():
                end_status = 'unavailable'
        if status == 'complete' and self.has_video(key):
            return {'rewrite_id': key, 'video_status': 'complete', 'can_generate': False,
                    'end_image_status': end_status, 'video_url': f'/videos/{key}/media'}
        if status in ('queued', 'started') and time.time() - video.get('requested_epoch', 0) < 1800:
            return {'rewrite_id': key, 'video_status': status, 'end_image_status': end_status,
                    'can_generate': False}
        result = {'rewrite_id': key, 'video_status': 'failed_or_uncertain', 'can_generate': False,
                'end_image_status': end_status,
                'message': 'Animation unavailable or interrupted. Operator review is needed; no automatic retry.'}
        if (isinstance(end_frame, dict) and end_status in ('started', 'uncertain') and
                isinstance(end_frame.get('image_id'), str)):
            result['end_image_retry_attempt_id'] = end_frame['image_id']
        return result

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
            start_style = state['result'].get('image_style')
            start_style = start_style.strip() if isinstance(start_style, str) and start_style.strip() else None
            end_style = choose_image_style(exclude=start_style)
            transformation_map = build_transformation_map(state['result'])
            state['video'] = {'rewrite_id': key, 'status': 'queued', 'provider': 'wavespeed',
                'model': MODEL, 'duration': 8, 'resolution': '480p',
                'prompt': build_transition_prompt(state['result']),
                'start_image_style': start_style, 'seed': secrets.randbelow(2**31),
                'source_sha256': hashlib.sha256(image).hexdigest(), 'requested_at': now(),
                'requested_epoch': time.time(), 'storage_key': f'{key}.mp4',
                'end_frame': {'mode': 'composition_reference_end_frame', 'status': 'queued',
                    'image_id': str(uuid4()),
                    'created_at': now(), 'stage': 'end',
                    'image_style': end_style, 'transformation_map': transformation_map}}
            state['video']['end_frame']['image_prompt'] = build_end_image_prompt(
                state['result'], end_style, transformation_map)
            self.store.save(db, key, state)
            return self.public(key, state), True

    def retry_uncertain_end_image(self, collection, key, owner, attempt_id):
        """Atomically consume one explicit retry for one exact uncertain end frame."""
        try:
            expected = str(UUID(str(attempt_id)))
        except (ValueError, TypeError, AttributeError):
            raise VideoError(409, 'End-image attempt is invalid.') from None
        with self.store.transaction() as db:
            state = self.read(db, key, owner)
            video = state.get('video')
            end_frame = video.get('end_frame') if isinstance(video, dict) else None
            if not isinstance(end_frame, dict) or end_frame.get('image_id') != expected:
                raise VideoError(409, 'End-image attempt changed; retry authorisation was not used.')
            if video.get('status') != 'failed_or_uncertain' or end_frame.get('status') not in ('started', 'uncertain'):
                raise VideoError(409, 'This end-image attempt is not eligible for uncertain-outcome recovery.')
            old_path = self.images / f'{expected}.png'
            if old_path.is_symlink():
                raise VideoError(409, 'Untrusted end-image path.')
            if old_path.is_file():
                raise VideoError(409, 'An end-image file already exists; operator review is required.')
            video.setdefault('end_frame_history', []).append({
                **end_frame, 'status': 'superseded_by_confirmed_retry'
            })
            replacement = {**end_frame, 'image_id': str(uuid4()), 'status': 'queued',
                           'stage': 'end', 'created_at': now(), 'retry_of': expected,
                           'confirmed_at': now()}
            for field in ('provider_call_entered_at', 'provider_response_received_at',
                          'persistence_completed_at', 'failure_category', 'failure_message'):
                replacement.pop(field, None)
            video['end_frame'] = replacement
            video['status'] = 'queued'
            video['worker_started'] = False
            video['retry_requested_at'] = now()
            video['requested_epoch'] = time.time()
            video.pop('error', None)
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
        pingpong.remove(path)

    def remove_local_media(self, key):
        """Remove an owned original and its purely local Gallery derivative."""
        path = self.path(key)
        pingpong.remove(path)
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
                    end_frame.setdefault('created_at', now())
                    end_frame['stage'] = 'end'
                    end_frame['provider_call_entered_at'] = now()
                    checkpoint()  # Permanent paid-image claim before contacting the provider.
                    image_provider = self.image_provider or get_provider()
                    reference_generation = getattr(image_provider, 'generate_referenced_image', None)
                    generated = (reference_generation(end_frame['image_prompt'], end_frame['image_id'], source)
                        if callable(reference_generation) else image_provider.generate_image(
                            end_frame['image_prompt'], end_frame['image_id']))
                    end_frame['provider_response_received_at'] = now()
                    end_frame.update(generated, status='complete')
                    data, _, _ = read_image(last_source)
                    end_frame['source_sha256'] = hashlib.sha256(data).hexdigest()
                    end_frame['persistence_completed_at'] = now()
                    checkpoint()
                elif not last_source.is_file():
                    raise VideoError(409, 'Stored end frame is unavailable.')
            self.provider(source, self.path(key), video['prompt'], video['seed'], video,
                          checkpoint, api_key, last_source=last_source)
            if not self.has_video(key):
                raise VideoError(502, 'Animation output unavailable.')
            video.update(status='complete', created_at=now())
            checkpoint()
            # This best-effort local post-process is outside provider state. Failure
            # leaves the completed original authoritative and cannot trigger a retry.
            try:
                if not pingpong.derive(self.path(key)):
                    log.info('Gallery ping-pong derivative unavailable for %s; using original.', key)
            except Exception as exc:
                log.warning('Gallery ping-pong post-process failed for %s: %s', key, exc)
        except Exception as exc:
            video['status'] = 'failed_or_uncertain'
            end_frame = video.get('end_frame')
            if isinstance(end_frame, dict) and end_frame.get('status') == 'started':
                end_frame['status'] = 'uncertain'
                end_frame['failure_category'] = type(exc).__name__
                end_frame['failure_message'] = (
                    str(exc)[:240] if isinstance(exc, VideoError)
                    else f'Image provider or local persistence raised {type(exc).__name__}.')
            if 'error' not in video:
                stage = 'end_image' if isinstance(end_frame, dict) and end_frame.get('status') == 'uncertain' else 'video'
                video['error'] = {'stage': stage, 'http_status': getattr(exc, 'status', None),
                                  'exception_type': type(exc).__name__,
                                  'exception_message': (str(exc)[:240] if isinstance(exc, VideoError)
                                                        else f'{stage} work raised {type(exc).__name__}.')}
            try:
                checkpoint()
            except Exception:
                pass  # Original claim survives; never clear it or submit again.
        try:
            self.sync(collection, key, owner)
        except VideoError:
            # Discarded drafts cannot expose their orphaned outputs.
            self.remove_local_media(key)


service = Videos()
