"""Replacement claims use temporary storage and mocked image/Mongo providers only."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

import pytest
import test_image_generation as fixtures
from newsmuncher.services.video import Videos
from newsmuncher.services.image_generation import choose_image_style


@pytest.fixture
def setup():
    fixture = fixtures.ImageTests()
    fixture.setUp()
    routes = fixture.previews()
    rid = fixture.store.create(fixture.result, 'alice')['rewrite_id']
    original = routes.generate_image(routes.ImageRequest(rewrite_id=rid), 'alice')
    request = routes.RedoImageRequest(rewrite_id=rid, previous_image_url=original['image_url'])
    try:
        yield fixture, routes, rid, original, request
    finally:
        fixture.tearDown()
        fixture.doCleanups()


def test_replacement_persistence_identity_replay_and_bank(setup):
    f, routes, rid, old, request = setup
    with patch.object(routes, 'choose_image_style', return_value='Futuristic') as choose:
        new = routes.redo_image(request, 'alice')
        assert routes.redo_image(request, 'alice') == new
        choose.assert_called_once_with(exclude=old['image_style'])
    assert new['image_url'] != old['image_url']
    assert new['image_style'] == 'Futuristic'
    assert 'Moon soup' not in new['image_prompt']
    assert 'A cat paints the moon.' in new['image_prompt']
    assert f.api.call_count == 2
    assert (f.images / (rid + '.png')).exists()  # Superseded output retained.
    restored = routes.get_image_result(rid, 'alice')
    assert restored['image_url'] == new['image_url']
    assert restored['image_style'] == 'Futuristic'
    assert restored['crazyReplacement1Title'] == f.result['crazyReplacement1Title']
    assert not restored['image_redo_pending']
    routes.claim_used_words.assert_not_called()
    response = MagicMock(); response.json.return_value = {'id':'saved'}
    with patch.object(routes.requests, 'post', return_value=response) as post:
        routes.bank_image_rewrite(SimpleNamespace(cookies={'active_pet':'alice'}), rid)
        assert post.call_args.kwargs['json']['image_url'] == new['image_url']
    with pytest.raises(routes.HTTPException):
        routes.redo_image(routes.RedoImageRequest(rewrite_id=rid, previous_image_url=new['image_url']), 'alice')


def test_failed_attempt_preserves_image_blocks_paid_retry_and_nomination(setup):
    f, routes, rid, old, request = setup
    f.api.side_effect = TimeoutError('uncertain')
    with pytest.raises(routes.HTTPException): routes.redo_image(request, 'alice')
    with pytest.raises(routes.HTTPException): routes.redo_image(request, 'alice')
    result = routes.get_image_result(rid, 'alice')
    assert result['image_url'] == old['image_url']
    assert result['image_style'] == old['image_style']
    assert result['image_redo_pending']
    with pytest.raises(routes.HTTPException):
        routes.bank_image_rewrite(SimpleNamespace(cookies={'active_pet':'alice'}), rid)
    assert f.api.call_count == 2


def test_concurrent_click_and_nomination_are_blocked(setup):
    f, routes, rid, old, request = setup
    entered, release = Event(), Event()
    response = f.api.return_value
    def wait(**kwargs):
        entered.set()
        assert release.wait(5)
        return response
    f.api.side_effect = wait
    with ThreadPoolExecutor() as pool:
        work = pool.submit(routes.redo_image, request, 'alice')
        assert entered.wait(5)
        try:
            with pytest.raises(routes.HTTPException): routes.redo_image(request, 'alice')
            with pytest.raises(routes.HTTPException):
                routes.bank_image_rewrite(SimpleNamespace(cookies={'active_pet':'alice'}), rid)
        finally:
            release.set()
        assert work.result()['image_url'] != old['image_url']
    assert f.api.call_count == 2


def test_requires_current_image_and_not_pending_nomination(setup):
    f, routes, rid, old, request = setup
    other = f.store.create(f.result, 'alice')['rewrite_id']
    with pytest.raises(routes.HTTPException):
        routes.redo_image(routes.RedoImageRequest(rewrite_id=other, previous_image_url=old['image_url']), 'alice')
    with f.store.transaction() as db:
        state = f.store.read(db, rid, 'alice'); state['nomination_pending'] = True
        f.store.save(db, rid, state)
    with pytest.raises(routes.HTTPException): routes.redo_image(request, 'alice')
    assert f.api.call_count == 1


def test_file_recovery_and_old_video_detached(setup):
    f, routes, rid, old, request = setup
    with f.store.transaction() as db:
        state = f.store.read(db, rid, 'alice')
        state['video'] = {'status':'complete', 'rewrite_id':rid}
        f.store.save(db, rid, state)
    with patch.object(routes, 'finish_image_redo', side_effect=OSError('metadata failure')):
        with pytest.raises(routes.HTTPException): routes.redo_image(request, 'alice')
    restored = routes.get_image_result(rid, 'alice')
    assert restored['image_url'] != old['image_url']
    assert not restored['image_redo_pending']
    video = Videos(f.store, f.images / 'videos', f.images)
    with f.store.transaction() as db:
        state = f.store.read(db, rid, 'alice')
        assert state['video_detached']
        assert not video.public(rid, state).get('video_url')
        assert video.source(rid, state).name == restored['image_url'].split('/')[-1]
    assert f.api.call_count == 2


def test_replacement_style_excludes_current():
    for _ in range(30):
        assert choose_image_style(exclude='Minimalism') != 'Minimalism'


def test_late_recovered_worker_cannot_overwrite_newer_replacement(setup):
    f, routes, rid, old, request = setup
    provider = routes.get_provider()
    entered, release = Event(), Event()
    calls = []
    def generate(prompt, image_id):
        metadata = provider.generate_image(prompt, image_id)
        calls.append(image_id)
        if len(calls) == 1:
            entered.set()
            assert release.wait(5)
        return metadata
    with patch.object(routes, 'get_provider', return_value=SimpleNamespace(generate_image=generate)):
        with ThreadPoolExecutor() as pool:
            work = pool.submit(routes.redo_image, request, 'alice')
            assert entered.wait(5)
            try:
                recovered = routes.get_image_result(rid, 'alice')
                latest = routes.redo_image(routes.RedoImageRequest(rewrite_id=rid,
                    previous_image_url=recovered['image_url']), 'alice')
            finally:
                release.set()
            work.result()
    assert routes.get_image_result(rid, 'alice')['image_url'] == latest['image_url']
    assert f.api.call_count == 3
