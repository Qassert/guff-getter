"""Narration tests: in-memory locked Mongo adapter and fully mocked speech SDK."""
import copy
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import types
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from bson import ObjectId
from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from newsmuncher.services.narration import Narrations, NarrationError, VOICES, MODEL

MP3 = b'ID3' + b'x' * 2000
MISSING = object()


def value(doc, key):
    for part in key.split('.'):
        if not isinstance(doc, dict) or part not in doc:
            return MISSING
        doc = doc[part]
    return doc


def matches(doc, query):
    for key, expected in query.items():
        if key == '$or':
            if not any(matches(doc, option) for option in expected):
                return False
        elif isinstance(expected, dict) and '$exists' in expected:
            if (value(doc, key) is not MISSING) != expected['$exists']:
                return False
        elif value(doc, key) != expected:
            return False
    return True


class Cursor(list):
    def limit(self, n):
        return Cursor(self[:n])

    def sort(self, fields):
        for field, direction in reversed(fields):
            super().sort(key=lambda d: str(d.get(field, '')), reverse=direction < 0)
        return self


class Collection:
    def __init__(self, entry):
        self.docs = [entry]
        self.lock = threading.Lock()
        self.fail_completion = False

    def with_options(self, **kwargs):
        assert kwargs['write_concern'].document == {'w': 'majority'}
        return self

    def find_one(self, query):
        with self.lock:
            return next((copy.deepcopy(d) for d in self.docs if matches(d, query)), None)

    def find(self, query):
        with self.lock:
            return Cursor(copy.deepcopy([d for d in self.docs if matches(d, query)]))

    def update_one(self, query, update):
        with self.lock:
            if self.fail_completion and update['$set'].get('narration.status') == 'complete':
                raise RuntimeError('mongo unavailable')
            for doc in self.docs:
                if matches(doc, query):
                    for key, val in update['$set'].items():
                        target = doc
                        parts = key.split('.')
                        for part in parts[:-1]:
                            target = target.setdefault(part, {})
                        target[parts[-1]] = copy.deepcopy(val)
                    return types.SimpleNamespace(matched_count=1)
            return types.SimpleNamespace(matched_count=0)


@pytest.fixture
def setup(tmp_path):
    entry = {'_id': ObjectId(), 'rewrite_id': 'rewrite-1', 'nominated': True,
             'image_owner': 'pet', 'title': 'SECRET SOURCE',
             'crazyReplacement1Title': 'Teapot mayor',
             'crazyReplacement1Extract': 'Biscuits take the bus.'}
    collection = Collection(entry)
    service = Narrations(tmp_path / 'audio')
    with patch.dict(os.environ, {'OPENAI_API_KEY': 'mock-key'}, clear=True), \
         patch('newsmuncher.services.narration.load_dotenv'), \
         patch('newsmuncher.services.openai_tts.OpenAI') as sdk:
        speech = sdk.return_value.__enter__.return_value.audio.speech.with_streaming_response.create
        speech.return_value.__enter__.return_value.read.return_value = MP3
        yield service, collection, entry, sdk, speech


def generate(setup, text=None):
    service, collection, entry, _, _ = setup
    return service.generate(collection, str(entry['_id']), 'pet', text or {
        'title': entry['crazyReplacement1Title'], 'body': entry['crazyReplacement1Extract']})


def test_voice_snapshot_file_and_one_speech_call(setup):
    service, collection, entry, sdk, speech = setup
    edited = {'title': 'Edited mayor!', 'body': 'Twelve ferrets win.'}
    with patch('newsmuncher.services.narration.random.choice', return_value=VOICES[2]) as choice:
        result = generate(setup, edited)
    choice.assert_called_once_with(VOICES)
    state = entry['narration']
    assert state['voice'] == result['voice'] == 'coral'
    assert state['voice_name'] == 'Coral'
    assert state['snapshot'] == edited
    assert state['model'] == MODEL
    assert state['storage_key'] == f"{entry['_id']}.mp3"
    assert service.path(str(entry['_id'])).read_bytes() == MP3
    assert state['generated_at']
    speech.assert_called_once_with(model=MODEL, voice='coral', input='Twelve ferrets win.', response_format='mp3')
    sdk.assert_called_once_with(api_key='mock-key', max_retries=0, timeout=60)
    assert 'SECRET SOURCE' not in str(speech.call_args)
    assert entry['crazyReplacement1Title'] == 'Teapot mayor'


def test_repeat_refresh_restart_and_fresh_discovery_do_not_generate(setup):
    service, collection, entry, sdk, speech = setup
    first = generate(setup)
    assert generate(setup)['narration_url'] == first['narration_url']
    reopened = Narrations(service.directory)
    assert reopened.status(collection, str(entry['_id']), 'pet')['narration_url'] == first['narration_url']
    assert reopened.discover(collection, 'pet')['narrations'][0]['entry_id'] == str(entry['_id'])
    assert reopened.resolve(collection, 'rewrite-1', 'pet')['narration_url'] == first['narration_url']
    speech.assert_called_once()


def test_concurrent_service_instances_share_mongo_claim(setup):
    service, collection, entry, sdk, speech = setup
    entered, release = threading.Event(), threading.Event()
    def wait(**kwargs):
        entered.set()
        assert release.wait(3)
        return speech.return_value
    speech.side_effect = wait
    other = Narrations(service.directory)
    with ThreadPoolExecutor(2) as pool:
        first = pool.submit(generate, setup)
        assert entered.wait(3)
        duplicate = other.generate(collection, str(entry['_id']), 'pet', {'title': 'Other', 'body': 'Other'})
        assert not duplicate['can_generate']
        release.set()
        assert first.result()['narration_status'] == 'complete'
    speech.assert_called_once()


def test_missing_key_does_not_claim_or_call(setup):
    with patch.dict(os.environ, {}, clear=True), pytest.raises(NarrationError) as exc:
        generate(setup)
    assert exc.value.status == 503
    assert 'narration' not in setup[2]
    setup[3].assert_not_called()


def test_failure_preserves_story_and_never_retries(setup):
    service, collection, entry, sdk, speech = setup
    speech.side_effect = RuntimeError('mock-key')
    with pytest.raises(NarrationError) as exc:
        generate(setup)
    assert exc.value.status == 502 and 'mock-key' not in str(exc.value)
    assert entry['crazyReplacement1Extract'] == 'Biscuits take the bus.'
    assert generate(setup)['narration_status'] == 'failed'
    assert not service.path(str(entry['_id'])).exists()
    speech.assert_called_once()


def test_metadata_failure_repairs_without_synthesis(setup):
    service, collection, entry, sdk, speech = setup
    collection.fail_completion = True
    assert generate(setup)['metadata_pending'] is True
    assert entry['narration']['status'] == 'started'
    collection.fail_completion = False
    reopened = Narrations(service.directory)
    assert reopened.status(collection, str(entry['_id']), 'pet')['narration_status'] == 'complete'
    assert entry['narration']['status'] == 'complete'
    assert entry['narration']['generated_at']
    speech.assert_called_once()


def test_deletion_during_generation_cannot_attach(setup):
    service, collection, entry, sdk, speech = setup
    def delete(**kwargs):
        collection.docs.clear()
        return speech.return_value
    speech.side_effect = delete
    with pytest.raises(NarrationError) as exc:
        generate(setup)
    assert exc.value.status == 404
    assert not service.path(str(entry['_id'])).exists()


def test_ownership_and_ambiguous_rewrite_fail_closed(setup):
    service, collection, entry, sdk, speech = setup
    for owner in (None, 'other'):
        with pytest.raises(NarrationError):
            service.status(collection, str(entry['_id']), owner)
    collection.docs.append({**entry, '_id': ObjectId()})
    with pytest.raises(NarrationError) as exc:
        service.resolve(collection, 'rewrite-1', 'pet')
    assert exc.value.status == 409
    sdk.assert_not_called()


def test_updated_story_keeps_original_snapshot(setup):
    service, collection, entry, sdk, speech = setup
    generate(setup)
    original = copy.deepcopy(entry['narration']['snapshot'])
    entry['crazyReplacement1Title'] = 'New title'
    result = generate(setup)
    assert result['text_changed']
    assert entry['narration']['snapshot'] == original
    speech.assert_called_once()


def test_unowned_file_or_unknown_metadata_never_generates(setup):
    service, collection, entry, sdk, speech = setup
    service.directory.mkdir()
    service.path(str(entry['_id'])).write_bytes(MP3)
    assert generate(setup)['can_generate'] is False
    entry['narration'] = {'legacy': True}
    assert generate(setup)['can_generate'] is False
    sdk.assert_not_called()


def test_api_range_status_auth_and_missing_file(setup):
    service, collection, entry, sdk, speech = setup
    # Import only new route module, without real Mongo clients/other app startup.
    fake = types.ModuleType('newsmuncher.api.entries')
    fake.collection = collection
    with patch.dict(sys.modules, {'newsmuncher.api.entries': fake}):
        spec = importlib.util.spec_from_file_location('offline_narrations', 'newsmuncher/api/narrations.py')
        routes = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(routes)
    routes.service = service
    app = FastAPI()
    app.include_router(routes.router)
    with TestClient(app) as client:
        client.cookies.set('active_pet', 'pet')
        url = f"/narrations/{entry['_id']}"
        assert client.get(url).json()['can_generate']
        sdk.assert_not_called()
        response = client.post(url, json={'title': 'Teapot mayor', 'body': 'Biscuits take the bus.'})
        assert response.status_code == 200
        assert client.get(url + '/audio').content == MP3
        part = client.get(url + '/audio', headers={'Range': 'bytes=0-9'})
        assert part.status_code == 206 and part.content == MP3[:10]
        assert part.headers['content-range'] == f'bytes 0-9/{len(MP3)}'
        assert client.get(url + '/audio', headers={'Range': 'bytes=9000-'}).status_code == 416
        client.cookies.clear()
        assert client.get(url + '/audio').status_code == 401
        client.cookies.set('active_pet', 'other')
        assert client.get(url + '/audio').status_code == 404
        client.cookies.set('active_pet', 'pet')
        service.path(str(entry['_id'])).unlink()
        assert client.post(url, json={'title': 'Teapot mayor', 'body': 'Biscuits'}).json()['can_generate'] is False
        assert client.get(url + '/audio').status_code == 404
    speech.assert_called_once()


def test_frontend_and_template():
    subprocess.run(['node', '--check', 'newsmuncher/static/narration.js'], check=True)
    subprocess.run(['node', '--check', 'newsmuncher/static/script.js'], check=True)
    subprocess.run(['node', 'tests/narration.test.js'], check=True)
    from jinja2 import Environment, FileSystemLoader
    env = Environment(loader=FileSystemLoader('newsmuncher/templates'))
    env.globals['url_for'] = lambda name, **kw: '/static/' + kw['path']
    html = env.get_template('pet_profile.html').render(pet={})
    from html.parser import HTMLParser
    class IDs(HTMLParser):
        def __init__(self):
            super().__init__()
            self.ids = []
        def handle_starttag(self, tag, attrs):
            if 'id' in dict(attrs):
                self.ids.append(dict(attrs)['id'])
    parser = IDs()
    parser.feed(html)
    assert len(parser.ids) == len(set(parser.ids))
    assert html.count('id="narrationButton"') == 1
    assert 'onclick="narrationUI.act()"' in html
    assert 'preload="none"' in html
    assert 'id="narrationControls" class="narration-controls"' in html
    assert 'id="narrationControls" class="container"' not in html
    assert 'savedNarration' not in html
    assert 'PLAY saved narration' not in html
    assert 'class="site-footer"' not in html
    assert 'A little rough around the edges.' not in html
    assert 'id="jingleControls" class="jingle-controls" hidden' in html


def test_null_metadata_and_oversize_text_fail_without_spending(setup):
    service, collection, entry, sdk, speech = setup
    with pytest.raises(NarrationError) as exc:
        generate(setup, {'title': 'Long', 'body': 'x' * 3501})
    assert exc.value.status == 422
    entry['narration'] = None
    assert generate(setup)['can_generate'] is False
    sdk.assert_not_called()


def test_deletion_between_file_write_and_metadata_sync_is_missing(setup):
    service, collection, entry, sdk, speech = setup
    update = collection.update_one
    def delete_before_completion(query, values):
        if values['$set'].get('narration.status') == 'complete':
            collection.docs.clear()
        return update(query, values)
    collection.update_one = delete_before_completion
    with pytest.raises(NarrationError) as exc:
        generate(setup)
    assert exc.value.status == 404
    assert not service.path(str(entry['_id'])).exists()
    speech.assert_called_once()


def test_existing_title_inclusive_audio_reused_unchanged(setup):
    service, collection, entry, sdk, speech = setup
    key = str(entry['_id'])
    service.directory.mkdir(parents=True, exist_ok=True)
    original = b'ID3existing-title-and-body-audio'
    service.path(key).write_bytes(original)
    entry['narration'] = {'entry_id': key, 'status': 'complete',
        'voice': 'coral', 'voice_name': 'Coral',
        'snapshot': {'title': 'Old spoken title', 'body': 'Old spoken body'}}
    before = copy.deepcopy(entry['narration'])
    result = generate(setup, {'title': 'New title', 'body': 'New body'})
    assert result['narration_status'] == 'complete'
    assert entry['narration'] == before
    assert service.path(key).read_bytes() == original
    sdk.assert_not_called()


def test_body_only_preserves_internal_punctuation_and_newlines(setup):
    _, _, _, _, speech = setup
    body = '  Ferrets vote!\nBiscuits win?  '
    generate(setup, {'title': 'DO NOT SPEAK THIS TITLE', 'body': body})
    assert speech.call_args.kwargs['input'] == body.strip()
    speech.assert_called_once()
