"""Temporary SQLite/media and fake Mongo only; all HTTP is forbidden."""
import copy
import importlib.util
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

from bson import ObjectId
from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient
import pytest
import requests

from newsmuncher.services.image_generation import RewriteStore, build_image_prompt
from newsmuncher.services.video import Videos, VideoError
from newsmuncher.services import wavespeed

PNG = b'\x89PNG\r\n\x1a\n' + b'fixture'
MP4 = b'\0\0\0\x18ftypmp42fixture'


class Collection:
    def __init__(self):
        self.entry = None
    def find_one(self, query):
        if self.entry and all(self.entry.get(k) == v for k, v in query.items()):
            return copy.deepcopy(self.entry)
    def update_one(self, query, update):
        if self.find_one(query):
            self.entry.update(copy.deepcopy(update['$set']))


@pytest.fixture
def setup(tmp_path, monkeypatch):
    monkeypatch.setenv('WAVESPEED_API_KEY', 'mock-secret')
    monkeypatch.setattr(requests.sessions.Session, 'request', lambda *a, **k: pytest.fail('Live HTTP forbidden'))
    store = RewriteStore(tmp_path / 'rewrite.sqlite3')
    result = store.create({'crazyReplacement1Title': 'Penguin disco',
                          'crazyReplacement1Extract': 'A penguin opens a cupboard.',
                          'image_style': '1970s British folk-horror film'}, 'pet')
    key = result['rewrite_id']
    images = tmp_path / 'images'
    images.mkdir()
    (images / f'{key}.png').write_bytes(PNG)
    calls = []
    def provider(source, target, prompt, seed, record, checkpoint, api_key, last_source=None):
        calls.append((source, prompt, seed, last_source))
        assert api_key == 'mock-secret'
        assert source.read_bytes() == PNG
        assert last_source is not None and last_source.read_bytes() == PNG
        record['request_id'] = 'safe-id'
        checkpoint()
        target.write_bytes(MP4)
    class ImageProvider:
        def __init__(self): self.calls = []
        def generate_image(self, prompt, image_id):
            self.calls.append(('generate', prompt, image_id, None))
            (images / f'{image_id}.png').write_bytes(PNG)
            return {'image_url': f'/generated-images/{image_id}.png',
                    'image_prompt': prompt, 'image_model': 'mock-image',
                    'image_provider': 'mock', 'image_generated_at': 'now'}
        def generate_referenced_image(self, prompt, image_id, reference):
            self.calls.append(('edit', prompt, image_id, reference))
            return self.generate_image(prompt, image_id)
    service = Videos(store, tmp_path / 'video', images, provider, ImageProvider())
    with store.transaction() as db:
        state = store.read(db, key, 'pet')
        state['result']['image_url'] = f'/generated-images/{key}.png'
        store.save(db, key, state)
    return service, Collection(), key, calls


def state(service, key):
    with service.store.transaction() as db:
        return service.store.read(db, key, 'pet')


def nominate(service, collection, key):
    entry_id = ObjectId()
    collection.entry = {'_id': entry_id, 'rewrite_id': key, 'image_owner': 'pet', 'nominated': True}
    with service.store.transaction() as db:
        doc = service.store.read(db, key, 'pet')
        doc['entry_id'] = str(entry_id)
        service.store.save(db, key, doc)


def test_views_never_generate_and_explicit_job_is_reused_after_restart(setup):
    service, collection, key, calls = setup
    assert service.status(collection, key, 'pet')['can_generate']
    assert not calls
    assert service.claim(collection, key, 'pet')[1]
    assert not service.claim(collection, key, 'pet')[1]
    assert not calls  # Only a scheduled worker executes, not claim/status.
    service.run(collection, key, 'pet')
    reopened = Videos(service.store, service.directory, service.images, service.provider,
                      service.image_provider)
    assert reopened.status(collection, key, 'pet')['video_status'] == 'complete'
    assert not reopened.claim(collection, key, 'pet')[1]
    reopened.run(collection, key, 'pet')
    assert len(calls) == 1
    video = state(service, key)['video']
    assert video['duration'] == 8 and video['resolution'] == '480p'
    assert 'mock-secret' not in json.dumps(video)
    assert list(service.directory.iterdir()) == [service.path(key)]


def test_concurrent_claims_and_duplicate_worker_delivery_pay_once(setup):
    service, collection, key, calls = setup
    with ThreadPoolExecutor(4) as pool:
        results = list(pool.map(lambda _: service.claim(collection, key, 'pet')[1], range(8)))
    assert sum(results) == 1
    with ThreadPoolExecutor(4) as pool:
        list(pool.map(lambda _: service.run(collection, key, 'pet'), range(8)))
    assert len(calls) == 1


def test_ambiguous_failure_is_permanent_and_safe(setup):
    service, collection, key, calls = setup
    def fail(*args, **kwargs):
        calls.append('paid')
        raise requests.Timeout('mock-secret https://signed.invalid')
    service.provider = fail
    service.claim(collection, key, 'pet')
    service.run(collection, key, 'pet')
    assert service.status(collection, key, 'pet')['video_status'] == 'failed_or_uncertain'
    assert not service.claim(collection, key, 'pet')[1]
    service.run(collection, key, 'pet')
    assert len(calls) == 1
    assert 'mock-secret' not in json.dumps(state(service, key))


@pytest.mark.parametrize('before', [True, False])
def test_nomination_sync_before_or_after_generation(setup, before):
    service, collection, key, calls = setup
    if before:
        nominate(service, collection, key)
    service.claim(collection, key, 'pet')
    service.run(collection, key, 'pet')
    if not before:
        nominate(service, collection, key)
        service.sync(collection, key, 'pet')
    assert collection.entry['video']['status'] == 'complete'
    assert collection.entry['video']['rewrite_id'] == key
    assert len(calls) == 1


def test_recovered_claim_file_and_missing_completed_file_never_regenerate(setup):
    service, collection, key, calls = setup
    service.claim(collection, key, 'pet')
    service.path(key).write_bytes(MP4)
    assert service.status(collection, key, 'pet')['video_status'] == 'complete'
    assert not service.claim(collection, key, 'pet')[1]
    service.path(key).unlink()
    assert service.status(collection, key, 'pet')['video_status'] == 'failed_or_uncertain'
    assert not service.claim(collection, key, 'pet')[1]
    assert not calls


def test_unknown_existing_mongo_claim_blocks_a_second_generation(setup):
    service, collection, key, calls = setup
    nominate(service, collection, key)
    collection.entry['video'] = None
    assert not service.claim(collection, key, 'pet')[1]
    assert not service.status(collection, key, 'pet')['can_generate']
    assert not calls


def test_owner_image_config_validation_before_claim(setup, monkeypatch):
    service, collection, key, calls = setup
    with pytest.raises(VideoError): service.claim(collection, key, 'other')
    with pytest.raises(VideoError): service.status(collection, '../escape', 'pet')
    monkeypatch.delenv('WAVESPEED_API_KEY')
    with pytest.raises(VideoError): service.claim(collection, key, 'pet')
    monkeypatch.setenv('WAVESPEED_API_KEY', 'mock-secret')
    (service.images / f'{key}.png').unlink()
    assert not service.status(collection, key, 'pet')['can_generate']
    with pytest.raises(VideoError): service.claim(collection, key, 'pet')
    assert 'video' not in state(service, key) and not calls


def test_crashed_worker_becomes_uncertain_without_rescheduling(setup):
    service, collection, key, calls = setup
    service.claim(collection, key, 'pet')
    with service.store.transaction() as db:
        doc = service.store.read(db, key, 'pet')
        doc['video'].update(status='started', worker_started=True, requested_epoch=0)
        service.store.save(db, key, doc)
    assert service.status(collection, key, 'pet')['video_status'] == 'failed_or_uncertain'
    assert not service.claim(collection, key, 'pet')[1]
    service.run(collection, key, 'pet')
    assert not calls


def test_discard_keeps_claim_and_prevents_late_submission(setup):
    service, collection, key, calls = setup
    service.claim(collection, key, 'pet')
    with patch('newsmuncher.services.image_generation.GENERATED_IMAGES_DIR', service.images):
        with service.store.transaction() as db:
            service.store.discard(db, key, service.store.read(db, key, 'pet'))
    assert 'video' in state(service, key)
    with pytest.raises(VideoError): service.run(collection, key, 'pet')
    assert not calls


def test_routes_gets_only_read_post_schedules_once_and_media_ranges(setup):
    service, collection, key, calls = setup
    entries = ModuleType('newsmuncher.api.entries'); entries.collection = collection
    gallery = ModuleType('newsmuncher.api.promotion_gallery')
    async def viewer(request: Request):
        if request.headers.get('X-Test-Login') != 'pet':
            raise HTTPException(401)
        if request.method == 'POST' and request.headers.get('X-Gallery-Request') != '1':
            raise HTTPException(403)
        return {'pet': 'pet'}
    gallery.viewer = viewer
    with patch.dict(sys.modules, {'newsmuncher.api.entries': entries, 'newsmuncher.api.promotion_gallery': gallery}):
        spec = importlib.util.spec_from_file_location('test_video_routes', 'newsmuncher/api/videos.py')
        routes = importlib.util.module_from_spec(spec); spec.loader.exec_module(routes)
    routes.service = service
    app = FastAPI(); app.include_router(routes.router)
    with TestClient(app) as client:
        assert client.get('/videos/' + key).status_code == 401
        client.headers['X-Test-Login'] = 'pet'
        assert client.get('/videos/' + key).json()['can_generate']
        assert not calls
        assert client.post('/videos/' + key).status_code == 403
        client.headers['X-Gallery-Request'] = '1'
        assert client.post('/videos/' + key).status_code == 202
        assert client.post('/videos/' + key).json()['video_status'] == 'complete'
        data = client.get('/videos/' + key).json()
        assert 'prompt' not in data and 'request_id' not in data
        assert client.get(data['video_url']).content == MP4
        partial = client.get(data['video_url'], headers={'Range': 'bytes=0-3'})
        assert partial.status_code == 206 and partial.content == MP4[:4]
    assert len(calls) == 1


@pytest.mark.parametrize('failure,expected', [(None, None), ('submit', 'model_submission'),
                                              ('poll', 'prediction_polling'), ('download', 'output_download')])
def test_app_uses_shared_transport_and_persists_safe_stage_diagnostics(setup, monkeypatch, failure, expected):
    from test_video_smoke_test import FakeSession
    service, collection, key, calls = setup
    service.provider = wavespeed.create_video
    fake = FakeSession(failure)
    monkeypatch.setattr(wavespeed.time, 'sleep', lambda _: None)
    with patch.object(wavespeed.requests, 'Session', return_value=fake):
        service.claim(collection, key, 'pet')
        service.run(collection, key, 'pet')
        service.run(collection, key, 'pet')
    video = state(service, key)['video']
    assert video['status'] == ('complete' if failure is None else 'failed_or_uncertain')
    if expected:
        assert video['error']['stage'] == expected
    assert len([c for c in fake.calls if c[0] == 'POST' and not c[1].endswith('/media/uploads')]) == 1
    if failure not in ('submit',):
        submission = next(c for c in fake.calls if c[0] == 'POST' and not c[1].endswith('/media/uploads'))
        assert submission[2]['json']['image'].startswith('https://storage.invalid/input')
        assert submission[2]['json']['last_image'].startswith('https://storage.invalid/input')
        assert len([c for c in fake.calls if c[1].endswith('/media/uploads')]) == 2
    assert not service.claim(collection, key, 'pet')[1]
    assert fake.trust_env is False
    encoded = json.dumps(video)
    for secret in ('mock-secret', 'secret=signed', 'secret=upload', 'secret=download', 'Authorization'):
        assert secret not in encoded


def test_legacy_claim_without_end_frame_keeps_single_image_provider_path(setup):
    service, collection, key, calls = setup
    service.claim(collection, key, 'pet')
    with service.store.transaction() as db:
        saved = service.store.read(db, key, 'pet')
        saved['video'].pop('end_frame')
        service.store.save(db, key, saved)
    received = []
    def legacy(source, target, prompt, seed, record, checkpoint, api_key, last_source=None):
        received.append(last_source)
        target.write_bytes(MP4)
    service.provider = legacy
    service.run(collection, key, 'pet')
    assert received == [None]
    assert state(service, key)['video']['status'] == 'complete'


def test_metadata_failure_recovers_stored_file_without_generation(setup):
    service, collection, key, calls = setup
    nominate(service, collection, key)
    service.claim(collection, key, 'pet')
    with patch.object(collection, 'update_one', side_effect=RuntimeError('offline')):
        service.run(collection, key, 'pet')
    assert 'video' not in collection.entry
    assert service.status(collection, key, 'pet')['video_status'] == 'complete'
    assert collection.entry['video']['status'] == 'complete'
    assert not service.claim(collection, key, 'pet')[1]
    assert len(calls) == 1


def test_untracked_and_symlink_media_fail_closed(setup):
    service, collection, key, calls = setup
    service.directory.mkdir()
    outside = service.directory.parent / 'untracked.mp4'; outside.write_bytes(MP4)
    service.path(key).symlink_to(outside)
    assert not service.status(collection, key, 'pet')['can_generate']
    assert not service.claim(collection, key, 'pet')[1]
    assert not calls


def test_discard_during_generation_cannot_attach_or_expose_output(setup):
    service, collection, key, calls = setup
    def late(source, target, prompt, seed, record, checkpoint, api_key, last_source=None):
        calls.append('paid')
        with patch('newsmuncher.services.image_generation.GENERATED_IMAGES_DIR', service.images):
            with service.store.transaction() as db:
                service.store.discard(db, key, service.store.read(db, key, 'pet'))
        target.write_bytes(MP4)
    service.provider = late
    service.claim(collection, key, 'pet')
    service.run(collection, key, 'pet')
    assert not service.path(key).exists()
    assert 'video' in state(service, key)
    with pytest.raises(VideoError): service.status(collection, key, 'pet')
    with pytest.raises(VideoError): service.claim(collection, key, 'pet')
    assert len(calls) == 1


def test_independent_end_frame_prompt_is_retained_and_assigned(setup):
    service, collection, key, calls = setup
    service.claim(collection, key, 'pet')
    claimed = state(service, key)['video']
    assert claimed['end_frame']['mode'] == 'composition_reference_end_frame'
    shared = claimed['shared_visual_style']
    start_prompt = build_image_prompt(state(service, key)['result'], shared)
    assert shared == '1970s British folk-horror film'
    assert start_prompt != claimed['end_frame']['image_prompt']
    assert f'Visual style: {shared}.' in start_prompt
    assert f'Visual style: {shared}.' in claimed['end_frame']['image_prompt']
    assert claimed['end_frame']['image_style'] == shared
    assert 'Preserve geometry; transform reality' in claimed['end_frame']['image_prompt']
    assert len(claimed['end_frame']['transformation_map']) == 5
    assert 'continuous surreal cinematic transformation' in claimed['prompt']
    assert f'same visual world: {shared}' in claimed['prompt']
    service.run(collection, key, 'pet')
    saved = state(service, key)['video']['end_frame']
    assert saved['status'] == 'complete'
    assert saved['image_url'].endswith(saved['image_id'] + '.png')
    assert calls[0][3].name == saved['image_id'] + '.png'
    assert service.image_provider.calls[0][0] == 'edit'
    assert service.image_provider.calls[0][3] == service.images / f'{key}.png'


def test_end_frame_failure_preserves_start_and_never_submits_video(setup):
    service, collection, key, calls = setup
    service.image_provider.generate_image = lambda *args: (_ for _ in ()).throw(RuntimeError('mock failure'))
    service.claim(collection, key, 'pet')
    service.run(collection, key, 'pet')
    saved = state(service, key)
    assert saved['result']['image_url'] == f'/generated-images/{key}.png'
    assert saved['video']['status'] == 'failed_or_uncertain'
    assert saved['video']['end_frame']['status'] == 'started'
    assert not calls
