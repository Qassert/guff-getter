"""Full-collection sorting uses metadata and never edits nomination records."""
from copy import deepcopy
from datetime import datetime,timedelta
from bson import ObjectId
from test_promotion_gallery import setup, routes
from newsmuncher.services.promotion_gallery import chronological_key


def collect(service,mode,seed='stable'):
    shown=[]
    for _ in range(100):
        result=service.select('viewer',shown[-1] if shown else None,shown,sort=mode,seed=seed)
        if not result['item']: return shown
        shown.append(result['item']['id'])
        if result['cycle_complete']: return shown
    raise AssertionError('Cycle did not finish')


def test_seeded_random_is_stable_unique_complete_and_has_no_latest_intro(setup):
    service,entries,_=setup;before=deepcopy(entries.docs)
    first=collect(service,'random','one')
    assert first==collect(service,'random','one')
    assert len(first)==len(set(first))==len(entries.docs)
    assert set(first)=={str(x['_id']) for x in entries.docs}
    # Different seeds produce different complete permutations, not a newest-first preamble.
    permutations={tuple(collect(service,'random',str(i))) for i in range(12)}
    assert len(permutations)>1
    assert entries.docs==before


def test_latest_covers_every_entry_beyond_first_three_and_ignores_edit_media_dates(setup):
    service,entries,_=setup
    for i in range(5):
        entries.docs.append({'_id':ObjectId(),'nominated':True,'nominated_at':datetime(2026,1,1)+timedelta(days=i),
            'crazyReplacement1Extract':'Saved story','image_generated_at':datetime(2099,1,1),
            'last_edited':datetime(2099,1,1)})
    expected=[str(x['_id']) for x in sorted(entries.docs,key=chronological_key,reverse=True)]
    before=deepcopy(entries.docs)
    assert collect(service,'latest')==expected
    assert len(expected)>3 and entries.docs==before


def test_latest_uses_nomination_timestamp_before_creation_date_and_stable_ties(setup):
    service,entries,_=setup
    entries.docs[:]=[
        {'_id':ObjectId('1'*24),'nominated':True,'nominated_at':datetime(2025,1,1),'creationDate':datetime(2099,1,1)},
        {'_id':ObjectId('2'*24),'nominated':True,'nominated_at':datetime(2025,1,1)},
        {'_id':ObjectId('3'*24),'nominated':True,'creationDate':datetime(2024,1,1)},
        {'_id':ObjectId('4'*24),'nominated':True}]
    assert collect(service,'latest')==['2'*24,'1'*24,'3'*24,'4'*24]


def test_random_cycle_does_not_repeat_previous_immediately_when_wrapping(setup):
    service,entries,_=setup
    order=collect(service,'random','one')
    result=service.select('viewer',previous=order[-1],sort='random',seed='new-cycle')
    assert result['item']['id']!=order[-1]


def test_public_api_defaults_random_validates_mode_and_sorts_complete_collection(routes,setup):
    client,_,_=routes;service,entries,_=setup
    client.cookies.set('active_pet','pet');client.cookies.set('gallery_session','opaque')
    before=deepcopy(entries.docs)
    default=client.get('/promotion-gallery/next').json()
    assert default['chronological'] is False
    latest=client.get('/promotion-gallery/next',params={'sort':'latest'}).json()
    assert latest['item']['id']==str(max(entries.docs,key=chronological_key)['_id'])
    a=client.get('/promotion-gallery/next',params={'sort':'random','seed':'stable'}).json()
    b=client.get('/promotion-gallery/next',params={'sort':'random','seed':'stable'}).json()
    assert a['item']['id']==b['item']['id']
    assert client.get('/promotion-gallery/next',params={'sort':'invalid'}).status_code==422
    assert entries.docs==before
