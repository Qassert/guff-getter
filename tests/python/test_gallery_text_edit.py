"""Real text-save/editor/gallery routes; temporary SQLite and fake Mongo only."""
import copy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from bson import ObjectId
from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
import test_image_generation as fixtures
from test_promotion_gallery import Collection, Database
from newsmuncher.services.image_generation import RewriteStore
from newsmuncher.services.promotion_gallery import PromotionGallery
from newsmuncher.api import entries, promotion_gallery


@pytest.fixture
def editing(tmp_path):
    fixture = fixtures.ImageTests(); fixture.setUp()
    routes = fixture.previews()
    rid = fixture.store.create(fixture.result, 'alice')['rewrite_id']
    key = ObjectId()
    entry = {'_id': key, 'rewrite_id': rid, 'image_owner': 'alice', 'creationUser': 'alice',
        'nominated': True, 'extract': 'Original source stays unchanged',
        'crazyReplacement1Title': 'Moon soup', 'crazyReplacement1Extract': 'Original saved story',
        'image_url': f'/generated-images/{rid}.png', 'image_style': 'Editorial',
        'jingle_file': 'kept.mp3', 'video_file': 'kept.mp4', 'promoted': True}
    other = {**copy.deepcopy(entry), '_id': ObjectId(), 'rewrite_id': 'other-rewrite'}
    db = Database(); collection = Collection(db, [copy.deepcopy(entry), copy.deepcopy(other)])
    with fixture.store.transaction() as connection:
        state = fixture.store.read(connection, rid, 'alice')
        state.update(entry_id=str(key), image_synced=True, image_attempt={'status': 'complete'},
                     video={'status': 'complete', 'file': 'keep.mp4'})
        state['result'].update({k:v for k,v in entry.items() if k != '_id'})
        fixture.store.save(connection, rid, state)
    media = [tmp_path / 'kept.png', tmp_path / 'kept.mp3', tmp_path / 'kept.mp4']
    for path in media: path.write_bytes(b'original media')
    service = PromotionGallery(collection, Collection(db), tmp_path, tmp_path, tmp_path,
                               tmp_path / 'missing-jingles.sqlite3')
    app = FastAPI(); app.include_router(routes.router, prefix='/temp')
    app.include_router(promotion_gallery.router)
    app.dependency_overrides[promotion_gallery.viewer] = lambda: {'id': 'viewer', 'pet': 'alice'}
    with patch.object(entries, 'collection', collection), patch.object(promotion_gallery, 'service', service):
        try:
            yield SimpleNamespace(browser=TestClient(app), routes=routes, rid=rid, key=key,
                fixture=fixture, collection=collection, original=entry, other=other, media=media)
        finally: fixture.tearDown()


def test_edit_save_gallery_refresh_and_reopen_preserve_other_records_and_media(editing):
    f = editing; f.browser.cookies.set('active_pet', 'alice')
    path = f'/promotion-gallery/items/{f.key}'
    assert f.browser.get(path).json()['body'] == 'Original saved story'
    response = f.browser.patch(f'/temp/creation/{f.rid}/text', json={
        'crazyReplacement1Title': 'Edited title', 'crazyReplacement1Extract': 'The latest saved story.'})
    assert response.status_code == 200
    for browser in [f.browser, TestClient(f.browser.app)]:
        # Fresh API reads model navigation/refresh/new browser without sessionStorage.
        assert browser.get(path).json()['body'] == 'The latest saved story.'
    reopen = f.browser.get(f'/temp/image_result/{f.rid}')
    assert reopen.status_code == 200
    assert reopen.json()['crazyReplacement1Extract'] == 'The latest saved story.'
    # A freshly opened durable store sees the same edit.
    restarted = RewriteStore(f.fixture.store.path)
    with restarted.transaction() as db:
        state = restarted.read(db, f.rid, 'alice')
    assert state['result']['crazyReplacement1Extract'] == 'The latest saved story.'
    assert state['image_attempt'] == {'status': 'complete'}
    assert state['video'] == {'status': 'complete', 'file': 'keep.mp4'}
    expected = {**f.original, 'crazyReplacement1Title': 'Edited title',
                'crazyReplacement1Extract': 'The latest saved story.'}
    assert f.collection.docs == [expected, f.other]
    assert all(path.read_bytes() == b'original media' for path in f.media)
    # Unchanged edits are successful, not a false 404 from modified_count == 0.
    assert f.browser.patch(f'/temp/creation/{f.rid}/text', json={
        'crazyReplacement1Title': 'Edited title', 'crazyReplacement1Extract': 'The latest saved story.'}).status_code == 200


@pytest.mark.parametrize('owner,status', [(None,401),('mallory',403)])
def test_text_edit_requires_original_owner_without_changing_either_store(editing, owner, status):
    f = editing
    if owner: f.browser.cookies.set('active_pet', owner)
    before = copy.deepcopy(f.collection.docs)
    response = f.browser.patch(f'/temp/creation/{f.rid}/text', json={
        'crazyReplacement1Title':'Attempt', 'crazyReplacement1Extract':'Must not be saved'})
    assert response.status_code == status
    assert f.collection.docs == before


def test_failed_mongo_save_does_not_claim_sqlite_text_was_saved(editing):
    f = editing; f.browser.cookies.set('active_pet','alice')
    with patch.object(f.collection, 'update_one', return_value=SimpleNamespace(matched_count=0)):
        response = f.browser.patch(f'/temp/creation/{f.rid}/text',json={
            'crazyReplacement1Title':'Missing', 'crazyReplacement1Extract':'Not saved'})
    assert response.status_code == 404
    with f.fixture.store.transaction() as db:
        state = f.fixture.store.read(db, f.rid, 'alice')
    assert state['result']['crazyReplacement1Extract'] == 'Original saved story'
