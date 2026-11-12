"""ENHANCE preparation reads saved records; all writes/providers are isolated mocks."""
import json
from pathlib import Path
from copy import deepcopy
from unittest.mock import patch
from bson import ObjectId
from test_gallery_text_edit import editing
from newsmuncher.api import promotion_gallery
from newsmuncher.services.video import Videos

FAX=json.loads(Path('tests/fixtures/fax_vicar_nomination.json').read_text())


def test_exact_fax_nomination_prepares_unchanged_and_reports_real_failure_kind(editing):
    f=editing;record=f.collection.docs[0]
    record.update(_id=ObjectId(FAX['id']),rewrite_id=FAX['rewrite_id'],
                  crazyReplacement1Title=FAX['title'],crazyReplacement1Extract=FAX['body'])
    before=deepcopy(f.collection.docs)
    with patch.object(promotion_gallery,'store',f.fixture.store):
        response=f.browser.post('/promotion-gallery/items/'+FAX['id']+'/prepare-completion')
    assert response.status_code==200
    assert response.json()['body']==FAX['body'] and response.json()['rewrite_id']==FAX['rewrite_id']
    assert response.json()['can_enhance'] is True
    assert f.collection.docs==before
    state={'result':{'crazyReplacement1Extract':FAX['body']},'video':{'status':'failed_or_uncertain',
        'error':{'stage':'end_image','http_status':400},'end_frame':{
            'status':'definitive_failed','failure_code':'moderation_blocked','failure_http_status':400}}}
    public=Videos(f.fixture.store).public(FAX['rewrite_id'],state)
    assert public['failure_kind']=='content_policy' and public['failure_stage']=='end_image'
    assert not public.get('end_image_retry_attempt_id') and public['can_generate'] is False
    assert state['result']['crazyReplacement1Extract']==FAX['body']
    assert not f.fixture.api.called


def test_prepare_normalises_older_json_without_backfilling_saved_text(editing):
    f=editing;record=f.collection.docs[0]
    record['result']=json.dumps({'crazyReplacement1Title':'Historical title','crazyReplacement1Extract':FAX['body']})
    record['crazyReplacement1Title']=None;record['crazyReplacement1Extract']=None
    with f.fixture.store.transaction() as db: db.execute('DELETE FROM rewrites WHERE id=?',(f.rid,))
    before=deepcopy(f.collection.docs)
    with patch.object(promotion_gallery,'store',f.fixture.store):
        response=f.browser.post(f'/promotion-gallery/items/{f.key}/prepare-completion')
        refreshed=f.browser.get(f'/promotion-gallery/items/{f.key}')
    assert response.status_code==200 and response.json()['body']==FAX['body']
    assert refreshed.json()['body']==FAX['body']
    assert f.collection.docs==before


def test_missing_legacy_identity_is_local_only_and_blocks_paid_enhancement(editing):
    f=editing;f.collection.docs[0].pop('rewrite_id');f.collection.docs[0].pop('nominated')
    f.collection.docs[0]['crazyReplacement1done']=True
    before=deepcopy(f.collection.docs)
    with patch.object(promotion_gallery,'store',f.fixture.store):
        response=f.browser.post(f'/promotion-gallery/items/{f.key}/prepare-completion')
    assert response.status_code==200 and response.json()['can_enhance'] is False
    assert 'no committed media identity' in response.json()['enhancement_error']
    assert f.collection.docs==before and not f.fixture.api.called


def test_missing_saved_body_is_data_failure_not_policy_rejection(editing):
    f=editing;f.collection.docs[0]['crazyReplacement1Extract']=None
    with f.fixture.store.transaction() as db: db.execute('DELETE FROM rewrites WHERE id=?',(f.rid,))
    before=deepcopy(f.collection.docs)
    with patch.object(promotion_gallery,'store',f.fixture.store):
        response=f.browser.post(f'/promotion-gallery/items/{f.key}/prepare-completion')
    assert response.status_code==422 and 'recoverable' in response.json()['detail']
    assert f.collection.docs==before and not f.fixture.api.called


def test_cache_only_historical_body_is_returned_without_changing_mongo(editing):
    f=editing;f.collection.docs[0]['crazyReplacement1Extract']=None
    before=deepcopy(f.collection.docs)
    with patch.object(promotion_gallery,'store',f.fixture.store):
        response=f.browser.post(f'/promotion-gallery/items/{f.key}/prepare-completion')
        refreshed=f.browser.get(f'/promotion-gallery/items/{f.key}')
    assert response.status_code==200 and response.json()['body']=='Original saved story'
    assert refreshed.json()['body']=='Original saved story' and f.collection.docs==before


def test_legacy_metadata_is_only_saved_after_explicit_fresh_confirmation(editing):
    f=editing;record=f.collection.docs[0]
    record.pop('rewrite_id');record.pop('nominated');record['crazyReplacement1done']=True
    before=deepcopy(record);url=f'/promotion-gallery/items/{f.key}'
    with patch.object(promotion_gallery,'store',f.fixture.store):
        prepared=f.browser.post(url+'/prepare-completion').json()
        assert f.collection.docs[0]==before
        declined=f.browser.post(url+'/commit-enhancement',json={'confirmed':False,'revision':prepared['enhancement_revision']})
        assert declined.status_code==400 and f.collection.docs[0]==before
        confirmed=f.browser.post(url+'/commit-enhancement',json={'confirmed':True,'revision':prepared['enhancement_revision']})
    assert confirmed.status_code==200 and confirmed.json()['can_enhance'] is True
    saved=f.collection.docs[0]
    assert saved['crazyReplacement1Extract']==before['crazyReplacement1Extract']
    for field in ('image_url','video_file','jingle_file','extract'): assert saved[field]==before[field]
    assert saved['rewrite_id']==confirmed.json()['rewrite_id'] and saved['nominated'] is True
    assert not f.fixture.api.called


def test_stale_confirmation_cannot_commit_metadata_over_new_story(editing):
    f=editing;f.collection.docs[0].pop('rewrite_id');url=f'/promotion-gallery/items/{f.key}'
    with patch.object(promotion_gallery,'store',f.fixture.store):
        prepared=f.browser.post(url+'/prepare-completion').json()
        f.collection.docs[0]['crazyReplacement1Extract']='Saved elsewhere'
        before=deepcopy(f.collection.docs)
        response=f.browser.post(url+'/commit-enhancement',json={'confirmed':True,'revision':prepared['enhancement_revision']})
    assert response.status_code==409 and f.collection.docs==before


def test_missing_optional_title_recovers_consistently_without_inventing_text(editing):
    f=editing;f.collection.docs[0]['crazyReplacement1Title']=None
    before=deepcopy(f.collection.docs)
    with patch.object(promotion_gallery,'store',f.fixture.store):
        prepared=f.browser.post(f'/promotion-gallery/items/{f.key}/prepare-completion')
        item=f.browser.get(f'/promotion-gallery/items/{f.key}')
    assert prepared.status_code==200 and prepared.json()['title']==item.json()['title']=='Moon soup'
    assert f.collection.docs==before
