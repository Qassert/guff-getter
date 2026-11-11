"""All recovery tests use isolated SQLite and mocked image providers."""
from copy import deepcopy
from unittest.mock import MagicMock, patch
import httpx
import pytest
from openai import BadRequestError
import test_image_generation as fixtures
from newsmuncher.services.image_generation import is_content_rejection
from newsmuncher.services.media_description import revise_media_description, ensure_media_description


def rejection(code='moderation_blocked', status=400):
    return BadRequestError('provider refused', response=httpx.Response(status,
        request=httpx.Request('POST', 'https://provider.invalid/images')),
        body={'error': {'code': code, 'type': 'image_generation_user_error'}})


@pytest.fixture
def setup():
    f = fixtures.ImageTests(); f.setUp()
    routes = f.previews()
    original = {**f.result, 'crazyReplacement1Title': 'Fax at Evensong',
                'crazyReplacement1Extract': 'The vicar prints his scrotum. The choir sings beside a fax machine.'}
    rid = f.store.create(original, 'alice')['rewrite_id']
    try:
        yield f, routes, rid, original
    finally:
        f.tearDown(); f.doCleanups()


def test_content_rejection_revises_once_and_keeps_identity_story_and_shared_concept(setup):
    f, routes, rid, original = setup
    provider = MagicMock()
    def success(prompt, image_id):
        with f.store.transaction() as db:
            claim = f.store.read(db, rid, 'alice')['image_attempt']
            assert claim['image_id'] == image_id and claim['content_retry_count'] == 1
        return {'image_url': '/generated-images/'+image_id+'.png', 'image_prompt': prompt}
    calls = []
    def generate(prompt, image_id):
        calls.append((prompt, image_id))
        if len(calls) == 1: raise rejection()
        return success(prompt, image_id)
    provider.generate_image.side_effect = generate
    with patch.object(routes, 'get_provider', return_value=provider), patch.object(routes, 'sync_image_metadata'):
        result = routes.generate_image(routes.ImageRequest(rewrite_id=rid), 'alice')
    assert len(calls) == 2 and calls[0][1] != calls[1][1]
    assert calls[0][0] != calls[1][0]
    assert 'fax machine' in calls[1][0] and 'vicar' in calls[1][0] and 'choir' in calls[1][0]
    assert 'scrotum' not in calls[1][0]
    with f.store.transaction() as db: state = f.store.read(db, rid, 'alice')
    assert state['result']['rewrite_id'] == rid and state['entry_id'] is None
    assert state['result']['crazyReplacement1Extract'] == original['crazyReplacement1Extract']
    assert state['image_attempt']['status'] == 'complete'
    assert state['image_attempt_history'][0]['failure_code'] == 'moderation_blocked'
    description = ensure_media_description(state)
    assert description['strategy'] == 'provider_rejection_scene_rebuild'
    from newsmuncher.services.image_generation import build_end_image_prompt
    assert description['concept'] in build_end_image_prompt(state['result'], media_description=description)


def test_second_rejection_stops_and_replayed_request_cannot_spend(setup):
    f, routes, rid, _ = setup
    provider = MagicMock(); provider.generate_image.side_effect = rejection()
    with patch.object(routes, 'get_provider', return_value=provider):
        with pytest.raises(routes.HTTPException) as error:
            routes.generate_image(routes.ImageRequest(rewrite_id=rid), 'alice')
        assert error.value.status_code == 422 and 'safer visual rewrite' in error.value.detail
        with pytest.raises(routes.HTTPException):
            routes.generate_image(routes.ImageRequest(rewrite_id=rid), 'alice')
    assert provider.generate_image.call_count == 2


@pytest.mark.parametrize('code,status', [('invalid_size',400),('insufficient_quota',400),
    ('invalid_api_key',401),('rate_limit_exceeded',429),('server_error',500)])
def test_non_content_failures_are_never_retried(setup, code, status):
    f, routes, rid, _ = setup
    provider = MagicMock(); provider.generate_image.side_effect = rejection(code,status)
    with patch.object(routes, 'get_provider', return_value=provider):
        with pytest.raises(routes.HTTPException): routes.generate_image(routes.ImageRequest(rewrite_id=rid), 'alice')
    assert provider.generate_image.call_count == 1
    assert not is_content_rejection(rejection(code,status))


def test_changed_snapshot_prevents_retry(setup):
    f, routes, rid, _ = setup
    provider=MagicMock()
    def generate(*args):
        with f.store.transaction() as db:
            state=f.store.read(db,rid,'alice');state['result']['crazyReplacement1Extract']='A goat pilots a kettle.';f.store.save(db,rid,state)
        raise rejection()
    provider.generate_image.side_effect=generate
    with patch.object(routes,'get_provider',return_value=provider):
        with pytest.raises(routes.HTTPException) as error: routes.generate_image(routes.ImageRequest(rewrite_id=rid),'alice')
    assert error.value.status_code==409 and provider.generate_image.call_count==1


def test_manual_redo_keeps_its_own_claim_and_one_retry_budget(setup):
    f,routes,rid,_=setup
    with f.store.transaction() as db:
        state=f.store.read(db,rid,'alice');state['image_attempt']={'image_id':rid,'status':'definitive_failed'};f.store.save(db,rid,state)
    provider=MagicMock();provider.generate_image.side_effect=[rejection(),{'image_url':'/generated-images/revised.png'}]
    with patch.object(routes,'get_provider',return_value=provider):
        result=routes.redo_image(routes.RedoImageRequest(rewrite_id=rid,previous_image_url=None),'alice')
    assert provider.generate_image.call_count==2
    with f.store.transaction() as db: state=f.store.read(db,rid,'alice')
    assert state['image_redo']['status']=='complete' and state['image_redo']['content_retry_count']==1


def test_safe_entity_revision_never_changes_story_or_uses_anatomical_actions():
    state={'result':{'crazyReplacement1Title':'Fertility fair',
        'crazyReplacement1Extract':'A ballbag booth displays breasts for cheeks. Seeds give the booth legs and it marches into the woods.'}}
    original=deepcopy(state['result']);d=revise_media_description(state)
    assert state['result']==original
    assert all(word in d['concept'] for word in ('booth','seeds','woods'))
    assert 'breasts' not in d['concept'] and 'ballbag' not in d['concept']


def test_retry_network_failure_is_uncertain_and_never_attempted_again(setup):
    f,routes,rid,_=setup
    provider=MagicMock();provider.generate_image.side_effect=[rejection(),TimeoutError('network')]
    with patch.object(routes,'get_provider',return_value=provider):
        with pytest.raises(routes.HTTPException) as error: routes.generate_image(routes.ImageRequest(rewrite_id=rid),'alice')
        assert error.value.status_code==502
        with pytest.raises(routes.HTTPException): routes.generate_image(routes.ImageRequest(rewrite_id=rid),'alice')
    assert provider.generate_image.call_count==2
    with f.store.transaction() as db: saved=f.store.read(db,rid,'alice')
    assert saved['image_attempt']['status']=='uncertain'


def test_replay_during_claimed_retry_cannot_submit_another_call(setup):
    f,routes,rid,_=setup
    provider=MagicMock();calls=[]
    def generate(prompt,image_id):
        calls.append(image_id)
        if len(calls)==1: raise rejection()
        with pytest.raises(routes.HTTPException) as error:
            routes.generate_image(routes.ImageRequest(rewrite_id=rid),'alice')
        assert error.value.status_code==409
        return {'image_url':'/generated-images/completed.png'}
    provider.generate_image.side_effect=generate
    with patch.object(routes,'get_provider',return_value=provider),patch.object(routes,'sync_image_metadata'):
        routes.generate_image(routes.ImageRequest(rewrite_id=rid),'alice')
    assert len(calls)==2


def test_story_changed_during_retry_never_receives_older_media(setup):
    f,routes,rid,_=setup
    provider=MagicMock();calls=[]
    def generate(prompt,image_id):
        calls.append(image_id)
        if len(calls)==1: raise rejection()
        with f.store.transaction() as db:
            state=f.store.read(db,rid,'alice');state['result']['crazyReplacement1Extract']='A goat pilots a kettle.';f.store.save(db,rid,state)
        return {'image_url':'/generated-images/obsolete.png'}
    provider.generate_image.side_effect=generate
    with patch.object(routes,'get_provider',return_value=provider):
        with pytest.raises(routes.HTTPException) as error: routes.generate_image(routes.ImageRequest(rewrite_id=rid),'alice')
    assert error.value.status_code==409
    with f.store.transaction() as db: saved=f.store.read(db,rid,'alice')
    assert saved['result']['crazyReplacement1Extract']=='A goat pilots a kettle.'
    assert not saved['result'].get('image_url')
