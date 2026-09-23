"""Offline gallery tests; real routes, fake Mongo transactions and temporary media."""
import copy
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path
import sqlite3
import sys
import threading
from types import SimpleNamespace, ModuleType
from unittest.mock import AsyncMock, patch
from concurrent.futures import ThreadPoolExecutor

from bson import ObjectId
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
import pytest

from newsmuncher.services.promotion_gallery import PromotionGallery
from newsmuncher.services.gallery_sessions import authenticate, issue_session, digest

MISSING = object()


def matches(doc, query):
    for key, expected in query.items():
        if key == '$or':
            if not any(matches(doc, option) for option in expected):
                return False
            continue
        val = doc.get(key, MISSING)
        if isinstance(expected, dict):
            for op, arg in expected.items():
                if op == '$exists' and (val is not MISSING) != arg:
                    return False
                if op == '$ne' and val == arg:
                    return False
                if op == '$gt' and (val is MISSING or val <= arg):
                    return False
        elif val != expected:
            return False
    return True


class Database:
    def __init__(self):
        self.client = self
        self.lock = threading.RLock()
        self.collections = []

    @contextmanager
    def start_session(self):
        yield self

    def with_transaction(self, action, **kwargs):
        with self.lock:
            snapshot = [copy.deepcopy(c.docs) for c in self.collections]
            try:
                return action(self)
            except Exception:
                for c, docs in zip(self.collections, snapshot):
                    c.docs = docs
                raise


class Collection:
    def __init__(self, db, docs=()):
        self.database, self.docs = db, list(docs)
        db.collections.append(self)

    def create_index(self, *args, **kwargs):
        assert kwargs == {'expireAfterSeconds': 0}

    def find(self, query, projection=None):
        return copy.deepcopy([d for d in self.docs if matches(d, query)])

    def find_one(self, query, session=None):
        return next(iter(self.find(query)), None)

    def insert_one(self, doc):
        self.docs.append(copy.deepcopy(doc))

    def update_one(self, query, update, session=None):
        with self.database.lock:
            for d in self.docs:
                if matches(d, query):
                    d.update(copy.deepcopy(update['$set']))
                    return SimpleNamespace(matched_count=1)
            return SimpleNamespace(matched_count=0)

    def find_one_and_update(self, query, update, **kwargs):
        with self.database.lock:
            doc = self.find_one(query)
            if doc:
                self.update_one(query, update)
                return self.find_one({'_id': doc['_id']})


@pytest.fixture
def setup(tmp_path):
    db = Database()
    entries = Collection(db, [dict(_id=ObjectId(), nominated=True,
        crazyReplacement1Title=f'Title {i}', crazyReplacement1Extract=f'Body {i}', creationUser=f'pet-{i}') for i in range(3)])
    receipts = Collection(db)
    service = PromotionGallery(entries, receipts, tmp_path / 'images', tmp_path / 'narration',
        tmp_path / 'audio', tmp_path / 'jingles.sqlite3', choose=lambda xs: xs[-1])
    for path in (service.images, service.narration, service.audio):
        path.mkdir()
    return service, entries, receipts


def test_rotation_counts_only_display_and_promotion_stays(setup):
    service, entries, receipts = setup
    order = []
    for _ in range(6):
        selected = service.select('viewer')
        assert sum(d.get('promotion_gallery_seen_count', 0) for d in entries.docs) == len(order)
        order.append(selected['item']['id'])
        service.displayed('viewer', selected['view_token'])
        service.displayed('viewer', selected['view_token'])
    assert len(set(order[:3])) == 3 and len(set(order[3:])) == 3
    result = service.promote(order[0])
    assert result['promoted']
    assert service.promote(order[0]) == result
    assert len(entries.docs) == 3
    assert service.serialize(service.entry(order[0]))['promoted']
    entries.docs.append(dict(_id=ObjectId(), nominated=True))
    assert service.select('viewer')['item']['id'] == str(entries.docs[-1]['_id'])


def test_legacy_and_exclusions(setup):
    service, entries, _ = setup
    entries.docs = [dict(_id=ObjectId(), nominated=False, crazyReplacement1done=True),
                    dict(_id=ObjectId(), title='Unnominated draft')]
    assert service.select('v') == {'item': None}
    with pytest.raises(HTTPException):
        service.promote(str(entries.docs[0]['_id']))
    entries.docs.append(dict(_id=ObjectId(), crazyReplacement1done=True, promotion_gallery_seen_count=None))
    selected = service.select('v')
    assert selected['item']['title'] == '' and selected['item']['image_url'] is None
    service.displayed('v', selected['view_token'])
    assert entries.docs[-1]['promotion_gallery_seen_count'] == 1


def test_receipts_expiry_viewer_and_rollback(setup):
    service, entries, receipts = setup
    selected = service.select('alice')
    token = selected['view_token']
    with pytest.raises(HTTPException):
        service.displayed('bob', token)
    with patch.object(entries, 'update_one', side_effect=RuntimeError('failed commit')):
        with pytest.raises(RuntimeError):
            service.displayed('alice', token)
    assert receipts.docs[0]['displayed'] is False
    service.displayed('alice', token)
    receipts.docs[0]['expires_at'] = datetime.now(timezone.utc) - timedelta(seconds=1)
    with pytest.raises(HTTPException):
        service.displayed('alice', token)
    assert sum(d.get('promotion_gallery_seen_count', 0) for d in entries.docs) == 1


def test_concurrent_receipts_count_each_actual_view_once(setup):
    service, entries, _ = setup
    a, b = service.select('a'), service.select('b')
    assert a['item']['id'] == b['item']['id']
    with ThreadPoolExecutor(4) as pool:
        list(pool.map(lambda args: service.displayed(*args),
                      [('a', a['view_token']), ('a', a['view_token']),
                       ('b', b['view_token']), ('b', b['view_token'])]))
    assert service.entry(a['item']['id'])['promotion_gallery_seen_count'] == 2


def test_existing_media_only_and_safe_paths(setup):
    service, entries, _ = setup
    entry = entries.docs[0]
    key = str(entry['_id'])
    image_id = '12345678-1234-4234-9234-123456789abc'
    entry.update(image_url=f'/generated-images/{image_id}.png',
        narration={'entry_id': key}, jingle_url=f'/generated-audio/{key}.mp3')
    for path in (service.images / f'{image_id}.png', service.narration / f'{key}.mp3', service.audio / f'{key}.mp3'):
        path.write_bytes(b'existing bytes')
    result = service.serialize(entry)
    assert all(result[k + '_url'] for k in ('image', 'narration', 'jingle'))
    entry['image_url'] = '/generated-images/../../secret.png'
    assert service.media_path(entry, 'image') is None
    entry['image_url'] = 'https://provider.invalid/image.png'
    assert service.media_path(entry, 'image') is None
    (service.narration / f'{key}.mp3').unlink()
    (service.narration / f'{key}.mp3').symlink_to(service.audio / f'{key}.mp3')
    assert service.media_path(entry, 'narration') is None
    entry.pop('jingle_url')
    with sqlite3.connect(service.jingles) as db:
        db.execute('CREATE TABLE jingles (id TEXT, state TEXT)')
        db.execute('INSERT INTO jingles VALUES (?, ?)', (key, json.dumps({'status': 'submitted', 'brief': {'lyrics': 'stored'}})))
    assert service.media_path(entry, 'jingle')
    with sqlite3.connect(service.jingles) as db:
        db.execute('UPDATE jingles SET state=?', (json.dumps({'status': 'retired', 'brief': {'lyrics': 'stored'}}),))
    assert service.media_path(entry, 'jingle') is None


@pytest.fixture
def routes(setup):
    service, entries, receipts = setup
    entry_mod, pets_mod = ModuleType('newsmuncher.api.entries'), ModuleType('newsmuncher.api.pets')
    entry_mod.collection, entry_mod.db = entries, {'promotion_gallery_views': receipts}
    sessions = SimpleNamespace(find_one=AsyncMock(return_value={'_id': 'viewer', 'pet': 'pet', 'password_version': digest('hash')}))
    pets = SimpleNamespace(find_one=AsyncMock(return_value={'avatar': 'pet', 'adopted': True, 'password': 'hash'}))
    pets_mod.db, pets_mod.pets_collection = {'gallery_sessions': sessions}, pets
    with patch.dict(sys.modules, {'newsmuncher.api.entries': entry_mod, 'newsmuncher.api.pets': pets_mod}):
        spec = importlib.util.spec_from_file_location('isolated_gallery', 'newsmuncher/api/promotion_gallery.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    module.service = service
    app = FastAPI()
    from fastapi.staticfiles import StaticFiles
    app.mount('/static', StaticFiles(directory='newsmuncher/static'), name='static')
    app.include_router(module.router)
    return TestClient(app), sessions, pets


def test_private_api_and_safe_media(routes, setup):
    client, sessions, pets = routes
    assert client.get('/promotion-gallery/next').status_code == 401
    client.cookies.set('active_pet', 'pet')
    assert client.get('/promotion-gallery/next').status_code == 401
    client.cookies.set('gallery_session', 'opaque')
    selected = client.get('/promotion-gallery/next')
    assert selected.status_code == 200 and 'no-store' in selected.headers['cache-control']
    data = selected.json()
    url = '/promotion-gallery/items/' + data['item']['id'] + '/promote'
    assert client.post(url).status_code == 403
    headers = {'X-Gallery-Request': '1'}
    assert client.post(url, headers={**headers, 'Origin': 'https://evil.invalid'}).status_code == 403
    assert client.post(url, headers=headers).json()['promoted'] is True
    assert client.post('/promotion-gallery/displayed', headers=headers, json={'view_token': data['view_token']}).json()['recorded']
    service, _, _ = setup
    entry = service.entry(data['item']['id'])
    key = str(entry['_id'])
    actual = next(d for d in service.entries.docs if d['_id'] == entry['_id'])
    actual['narration'] = {'entry_id': key}
    (service.narration / f'{key}.mp3').write_bytes(b'ID3' + b'x' * 100)
    media = client.get(f'/promotion-gallery/items/{key}/media/narration', headers={'Range': 'bytes=0-2'})
    assert media.status_code == 206 and media.content == b'ID3'
    assert client.get(f'/promotion-gallery/items/{key}/media/unknown').status_code == 404
    sessions.find_one.return_value = None
    assert client.get(f'/promotion-gallery/items/{key}/media/narration').status_code == 401


def test_session_issue_and_validation():
    import asyncio
    from starlette.responses import Response
    collection = SimpleNamespace(create_index=AsyncMock(), insert_one=AsyncMock(), find_one=AsyncMock())
    response = Response()
    request = SimpleNamespace(url=SimpleNamespace(scheme='https'))
    asyncio.run(issue_session(collection, response, request, {'avatar': 'pet', 'password': 'hash'}))
    cookie = response.headers['set-cookie']
    assert 'HttpOnly' in cookie and 'Secure' in cookie and 'SameSite=strict' in cookie
    record = collection.insert_one.call_args.args[0]
    assert record['password_version'] == digest('hash') and 'hash' not in record.values()
    collection.find_one.return_value = record
    pets = SimpleNamespace(find_one=AsyncMock(return_value={'avatar': 'pet', 'password': 'changed'}))
    with pytest.raises(HTTPException):
        asyncio.run(authenticate(collection, pets, 'token'))


def test_gallery_page_and_navigation(routes):
    client, _, _ = routes
    response = client.get('/promotion-gallery/')
    assert response.status_code == 200 and 'SIGN IN' in response.text
    assert 'promotion-gallery.js' not in response.text
    client.cookies.set('gallery_session', 'opaque')
    response = client.get('/promotion-gallery/')
    assert response.status_code == 200
    assert 'NEXT CREATION' in response.text and 'galleryPage' in response.text
    assert '/pets/pet_profile/pet' in response.text
    assert 'promotion-gallery.js' in response.text
    assert 'script.js' not in response.text and 'MAKE JINGLE' not in response.text
    assert '/promotion-gallery/' in Path('newsmuncher/templates/pet_profile.html').read_text()


def test_polish_accessibility_and_scoped_styles():
    css = Path('newsmuncher/static/promotion-gallery.css').read_text()
    template = Path('newsmuncher/templates/promotion_gallery.html').read_text()
    assert '@media (prefers-reduced-motion: reduce)' in css
    assert '.gallery-page.turning { animation: none; }' in css
    assert '@media (max-width: 620px)' in css
    assert '.promotion-gallery [hidden] { display: none !important; }' in css
    assert 'aria-live="polite"' in template and 'aria-label="Review and page navigation"' in template
    assert 'tabindex="-1"' not in template  # Native buttons/links, no focus trap.


def test_cycle_boundary_avoids_previous_and_int64_counts(setup):
    from bson.int64 import Int64
    from newsmuncher.services.promotion_gallery import seen
    service, entries, _ = setup
    assert seen({'promotion_gallery_seen_count': Int64(42)}) == 42
    assert seen({'promotion_gallery_seen_count': True}) == 0
    last = str(entries.docs[-1]['_id'])
    assert service.select('v', previous=last)['item']['id'] != last
    entries.docs = entries.docs[-1:]
    assert service.select('v', previous=last)['item']['id'] == last


def test_no_generation_dependency_or_outbound_network_in_gallery(routes):
    import ast
    import socket
    files = ['newsmuncher/services/promotion_gallery.py', 'newsmuncher/api/promotion_gallery.py']
    for file in files:
        tree = ast.parse(Path(file).read_text())
        imports = [n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
        assert not any(name and any(word in name for word in ('image_generation', 'jingle_brief', 'openai_tts')) for name in imports)
    client, _, _ = routes
    client.cookies.set('gallery_session', 'opaque')
    with patch.object(socket.socket, 'connect', side_effect=AssertionError('No live network')):
        selected = client.get('/promotion-gallery/next').json()
        assert selected['item']
        assert client.post('/promotion-gallery/displayed', json={'view_token': selected['view_token']}, headers={'X-Gallery-Request': '1'}).status_code == 200


@pytest.mark.parametrize('adopting', [False, True])
def test_successful_pet_login_and_adoption_issue_gallery_session(adopting):
    from unittest.mock import MagicMock
    pets = SimpleNamespace(find_one=AsyncMock(), create_index=AsyncMock(),
        update_one=AsyncMock(return_value=SimpleNamespace(matched_count=1)))
    sessions = SimpleNamespace(create_index=AsyncMock(), insert_one=AsyncMock())
    db = {'pets': pets, 'gallery_sessions': sessions}
    with patch('motor.motor_asyncio.AsyncIOMotorClient') as mongo:
        mongo.return_value.__getitem__.return_value = db
        spec = importlib.util.spec_from_file_location('isolated_gallery_pets', 'newsmuncher/api/pets.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    module.verify_password = MagicMock(return_value=True)
    module.get_password_hash = MagicMock(return_value='stored-hash')
    app = FastAPI()
    from fastapi.staticfiles import StaticFiles
    app.mount('/static', StaticFiles(directory='newsmuncher/static'), name='static')
    app.include_router(module.router, prefix='/pets')
    client = TestClient(app)
    if adopting:
        pets.find_one.side_effect = [{'avatar': 'pet.jpg', 'adopted': False}, None]
        response = client.post('/pets/adopt_pet/pet.jpg', data={
            'name': 'Andy', 'password': 'test-only', 'confirm_password': 'test-only'}, follow_redirects=False)
    else:
        pets.find_one.return_value = {'avatar': 'pet.jpg', 'adopted': True, 'password': 'stored-hash'}
        response = client.post('/pets/use_pet/pet.jpg', data={'password': 'test-only'}, follow_redirects=False)
    assert response.status_code == 303
    assert response.headers['location'] == '/pets/pet_profile/pet.jpg'
    assert client.cookies.get('active_pet') == 'pet.jpg'
    assert client.cookies.get('gallery_session')
    assert sessions.insert_one.await_count == 1
    record = sessions.insert_one.call_args.args[0]
    assert record['_id'] == digest(client.cookies.get('gallery_session'))
    assert record['password_version'] == digest('stored-hash')
    if not adopting:
        module.verify_password.return_value = False
        denied = client.post('/pets/use_pet/pet.jpg', data={'password': 'wrong'}, follow_redirects=False)
        assert 'Incorrect password' in denied.text
        assert sessions.insert_one.await_count == 1
