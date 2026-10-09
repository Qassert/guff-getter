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

from newsmuncher.services.promotion_gallery import PromotionGallery, minimum_seen_count
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
    entries.docs.append(dict(_id=ObjectId(), nominated=True,
                             promotion_gallery_seen_count=minimum_seen_count(entries)))
    assert entries.docs[-1]['promotion_gallery_seen_count'] == min(
        d['promotion_gallery_seen_count'] for d in entries.docs[:-1])


def test_new_nomination_starts_at_existing_gallery_floor_without_changing_history():
    db = Database()
    original = [dict(_id=ObjectId(), nominated=True, promotion_gallery_seen_count=count)
                for count in (6, 8, 12)]
    entries = Collection(db, copy.deepcopy(original))

    count = minimum_seen_count(entries)
    entries.docs.append(dict(_id=ObjectId(), nominated=True,
                             promotion_gallery_seen_count=count))

    assert count == 6
    assert [entry['promotion_gallery_seen_count'] for entry in entries.docs[:-1]] == [6, 8, 12]


def test_new_nomination_in_empty_gallery_starts_at_zero():
    db = Database()
    assert minimum_seen_count(Collection(db)) == 0


def test_new_nomination_preserves_shared_minimum_and_excludes_itself():
    db = Database()
    entries = Collection(db, [
        dict(_id=ObjectId(), nominated=True, promotion_gallery_seen_count=4),
        dict(_id=ObjectId(), nominated=True, promotion_gallery_seen_count=4),
        dict(_id=ObjectId(), nominated=True, promotion_gallery_seen_count=9),
    ])
    new_id = ObjectId()
    entries.docs.append(dict(_id=new_id, nominated=True, promotion_gallery_seen_count=99))

    assert minimum_seen_count(entries, exclude=new_id) == 4


def test_rotation_keeps_every_creation_at_the_shared_minimum_eligible(setup):
    service, entries, _ = setup
    for entry, count in zip(entries.docs, (4, 4, 9)):
        entry['promotion_gallery_seen_count'] = count
    eligible_ids = []
    service.choose = lambda candidates: eligible_ids.extend(str(item['_id']) for item in candidates) or candidates[0]

    selected = service.select('viewer')

    expected = [str(entries.docs[0]['_id']), str(entries.docs[1]['_id'])]
    assert eligible_ids == expected
    assert selected['item']['id'] in expected
    assert [entry['promotion_gallery_seen_count'] for entry in entries.docs] == [4, 4, 9]


def test_next_avoids_current_even_when_it_is_the_only_minimum(setup):
    service, entries, _ = setup
    current = entries.docs[0]
    current['promotion_gallery_seen_count'] = 0
    entries.docs[1]['promotion_gallery_seen_count'] = 6
    entries.docs[2]['promotion_gallery_seen_count'] = 8

    selected = service.select('viewer', previous=str(current['_id']))

    assert selected['item']['id'] == str(entries.docs[1]['_id'])
    assert [entry['promotion_gallery_seen_count'] for entry in entries.docs] == [0, 6, 8]


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
    assert all(result[k + '_url'] for k in ('image', 'jingle'))
    assert 'narration_url' not in result
    assert result['image_style'] is None
    entry['image_style'] = 'Cyberpunk'
    assert service.serialize(entry)['image_style'] == 'Cyberpunk'
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
    assert 'aria-label="Next creation"' in response.text and 'galleryPage' in response.text
    assert '/pets/pet_profile/pet' in response.text
    assert 'mode-nav-gallery mode-nav-active" aria-current="page" aria-label="GALLERY"' in response.text
    assert 'mode-nav-create" href="/pets/pet_profile/pet" aria-label="CREATE"' in response.text
    assert 'id="galleryEdit"' in response.text
    assert 'id="galleryBackdrop"' in response.text
    assert response.text.count('images/buttons/Coral Arrow on Cowhide Cushion.png') == 2
    assert 'data-arrow-click-sound="http://testserver/static/audio/effects/ui/cartoon-double-boing-pop.wav"' in response.text
    arrow_sound = client.get('/static/audio/effects/ui/cartoon-double-boing-pop.wav')
    assert arrow_sound.status_code == 200 and arrow_sound.headers['content-type'] == 'audio/x-wav'
    assert len(arrow_sound.content) > 44
    arrow = client.get('/static/images/buttons/Coral%20Arrow%20on%20Cowhide%20Cushion.png')
    assert arrow.status_code == 200
    assert arrow.headers['content-type'] == 'image/png'
    assert len(arrow.content) > 0
    assert 'promotion-gallery.js' in response.text
    assert 'script.js' not in response.text and 'MAKE JINGLE' not in response.text
    assert '/promotion-gallery/' in Path('newsmuncher/templates/pet_profile.html').read_text()


def test_polish_accessibility_and_scoped_styles():
    css = Path('newsmuncher/static/css/gallery/promotion-gallery.css').read_text()
    template = Path('newsmuncher/templates/promotion_gallery.html').read_text()
    assert '@media (prefers-reduced-motion: reduce)' in css
    assert '.gallery-page.turning { animation: none; }' in css
    assert '@media (max-width: 620px)' in css
    assert '.promotion-gallery [hidden] { display: none !important; }' in css
    assert 'aria-live="polite"' in template and 'aria-label="Creation controls"' in template
    assert 'tabindex="-1"' not in template  # Native buttons/links, no focus trap.
    script = Path('newsmuncher/static/js/gallery/promotion-gallery.js').read_text()
    assert "[music, promote, edit, complete].forEach" in script
    assert "[get('galleryNext'), get('galleryBack')].forEach" in script
    assert 'control.addEventListener(\'click\', playArrowClickSound)' in script
    assert 'arrowClickPlayer.pause()' in script and 'arrowClickPlayer.currentTime = 0' in script


def test_gallery_arrows_share_the_action_button_diameter_and_circular_crop():
    css = Path('newsmuncher/static/css/gallery/promotion-gallery.css').read_text()
    arrow = css.split('.gallery-arrow {', 1)[1].split('}', 1)[0]
    arrow_image = css.split('.gallery-arrow img {', 1)[1].split('}', 1)[0]
    next_arrow = css.split('.gallery-arrow-next {', 1)[1].split('}', 1)[0]
    mobile = css.split('@media (max-width: 620px)', 1)[1]

    assert '--gallery-control-size: clamp(70px, 9.75vw, 101px)' in css
    assert 'width: var(--gallery-control-size)' in arrow
    assert 'height: var(--gallery-control-size)' in arrow
    assert 'aspect-ratio: 1' in arrow and 'border-radius: 50%' in arrow
    assert '--gallery-arrow-art-size: 68%' in arrow
    assert 'overflow: visible' in arrow
    assert 'object-fit: cover' in arrow_image and 'object-position: center' in arrow_image
    assert 'width: var(--gallery-arrow-art-size)' in arrow_image
    assert 'height: var(--gallery-arrow-art-size)' in arrow_image
    assert 'border-radius: 50%' in arrow_image and 'clip-path: circle(50%)' in arrow_image
    assert '.gallery-arrow-next img { transform: scaleX(.75); }' in css
    assert '.gallery-arrow-back img { transform: scaleX(-.75); }' in css
    assert 'width:' not in next_arrow and 'height:' not in next_arrow
    assert '--gallery-control-size: 62px' in mobile
    assert '.gallery-arrow-next {' not in mobile.split('@media (prefers-reduced-motion: reduce)', 1)[0]


def test_gallery_parchment_uses_one_seamless_stretched_nine_slice():
    css = Path('newsmuncher/static/css/gallery/promotion-gallery.css').read_text()
    gallery_page = css.split('.gallery-page {', 2)[2].split('}', 1)[0]

    assert "border-image: url('../../images/backgrounds/parchment.png') 300 240 240 240 fill / 1 / 0 stretch" in gallery_page
    assert '.gallery-page::before' not in css
    assert '.gallery-page::after' not in css


def test_creator_and_viewing_share_compact_mode_navigation():
    creator = Path('newsmuncher/templates/pet_profile.html').read_text()
    gallery = Path('newsmuncher/templates/promotion_gallery.html').read_text()
    shared_css = Path('newsmuncher/static/css/shared/styles.css').read_text()
    gallery_css = Path('newsmuncher/static/css/gallery/promotion-gallery.css').read_text()

    assert 'mode-nav-create mode-nav-active" aria-current="page" aria-label="CREATE"' in creator
    assert 'mode-nav-gallery" href="/promotion-gallery/" aria-label="GALLERY"' in creator
    assert 'href="/promotion-gallery/"' in creator
    assert 'mode-nav-create" href="{{ creation_url }}" aria-label="CREATE"' in gallery
    assert 'mode-nav-gallery mode-nav-active" aria-current="page" aria-label="GALLERY"' in gallery
    for obsolete in ('BACK TO NEWSMUNCHER', 'THE NOMINATED COLLECTION', '<h1', 'gallery-intro'):
        assert obsolete not in gallery
    assert 'justify-content: center' in shared_css.split('.mode-nav {', 1)[1].split('}', 1)[0]
    assert 'flex-wrap: wrap' in shared_css.split('.mode-nav {', 1)[1].split('}', 1)[0]
    assert '--mode-nav-button-width: clamp(133px, 20.3vw, 210px)' in shared_css
    assert 'width: var(--mode-nav-button-width)' in shared_css.split('.mode-nav-button {', 1)[1].split('}', 1)[0]
    assert '--mode-nav-button-width: min(32.9vw, 161px)' in shared_css
    assert '.workshop { max-width: 960px; margin-inline: auto; }' in shared_css
    creator_workshop = shared_css.split('.profile-page .workshop {', 1)[1].split('}', 1)[0]
    assert 'padding-top: 0' in creator_workshop
    assert 'position: relative' in creator_workshop
    assert 'id="galleryTitle"' not in gallery
    assert 'id="galleryBody"' in gallery
    assert 'width: min(960px' in gallery_css
    assert 'var(--accent)' not in gallery_css
    assert 'data-creation-url="{{ creation_url }}"' in gallery
    assert 'object-fit: cover' in gallery_css


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


def test_gallery_selection_makes_no_outbound_network_call(routes):
    import socket
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


def test_gallery_video_only_serves_completed_local_association(routes, setup, tmp_path):
    from uuid import uuid4
    client, _, _ = routes
    service, entries, _ = setup
    service.videos = tmp_path / 'videos'
    service.videos.mkdir()
    entry = entries.docs[-1]
    key, rewrite = str(entry['_id']), str(uuid4())
    entry['rewrite_id'] = rewrite
    entry['video'] = {'rewrite_id': rewrite, 'status': 'complete', 'storage_key': f'{rewrite}.mp4',
                      'request_id': 'not-for-gallery-ui', 'prompt': 'not-for-gallery-ui'}
    path = service.videos / f'{rewrite}.mp4'
    path.write_bytes(b'\0\0\0\x18ftypmp42fixture')
    url = f'/promotion-gallery/items/{key}/media/video'
    assert client.get(url).status_code == 401
    client.cookies.set('gallery_session', 'opaque')
    response = client.get(url, headers={'Range': 'bytes=0-3'})
    assert response.status_code == 206 and response.headers['content-type'] == 'video/mp4'
    result = service.serialize(entry)
    assert result['video_url'].startswith(url + '?v=original-')
    assert result['rewrite_id'] == rewrite
    assert 'not-for-gallery-ui' not in json.dumps(result)
    entry['video']['status'] = 'started'
    assert client.get(url).status_code == 404
    entry['video']['status'] = 'complete'
    entry['video']['storage_key'] = '../elsewhere.mp4'
    assert client.get(url).status_code == 404
    entry['video']['storage_key'] = f'{rewrite}.mp4'
    outside = tmp_path / 'other.mp4'; outside.write_bytes(path.read_bytes())
    path.unlink(); path.symlink_to(outside)
    assert client.get(url).status_code == 404
    assert service.serialize(entry)['video_url'] is None
