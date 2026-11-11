"""Historical Gallery editor reads/writes use fake Mongo and temporary SQLite."""
from copy import deepcopy
from unittest.mock import patch
import pytest
from bson import ObjectId
from fastapi import FastAPI
from fastapi.testclient import TestClient
import test_image_generation as fixtures
from test_promotion_gallery import Collection, Database
from newsmuncher.api import entries
from newsmuncher.services import creation_restore

DICKENS = ('Charles Dickens unveiled his fourth dry-erase board, assembled by Serge Gainsbourg '
    'with a craft-storage bin and shit-horror buttons. It emerged on 9 February 2024 via cataracts '
    'and the chunder harp. A tern, Dickens contains wildcats, a vampire bat and heartbreak, and '
    "investigates Gainsbourg's peg bags alongside her pool vacuum and horses. Serge called the "
    'ostrich "a bogey treadmill mounted on a rim speaker made from a rim zeppelin of doom."')

@pytest.fixture
def setup():
    f=fixtures.ImageTests();f.setUp();routes=f.previews()
    old={'_id':ObjectId('ebaba1a0daa768613e7f4010'),'rewrite_id':'259c422f-9760-40ee-bd58-a3bd9154a46e',
         'image_owner':'alice','creationUser':None,'nominated':True,'crazyReplacement1done':True,
         'crazyReplacement1Title':'Charles Dickens unveiled his fourth dry-erase',
         'crazyReplacement1Extract':DICKENS,'title':'Venus (Zara Larsson album)',
         'image_url':'/generated-images/259c422f-9760-40ee-bd58-a3bd9154a46e.png',
         'video':{'status':'complete','storage_key':'kept.mp4'},'jingle_url':'/kept.mp3'}
    collection=Collection(Database(),[deepcopy(old)])
    app=FastAPI();app.include_router(routes.router,prefix='/temp')
    client=TestClient(app);client.cookies.set('active_pet','alice')
    with patch.object(entries,'collection',collection),patch.object(creation_restore,'SHARED_MEDIA_ROOT',None):
        try: yield f,routes,client,collection,old
        finally: f.tearDown();f.doCleanups()


def test_real_historical_shape_restores_without_changing_nomination_or_media(setup):
    f,routes,client,collection,old=setup
    before=deepcopy(collection.docs)
    path='/temp/image_result/'+old['rewrite_id']
    first=client.get(path);assert first.status_code==200
    assert first.json()['crazyReplacement1Extract']==DICKENS
    assert first.json()['rewrite_id']==old['rewrite_id']
    assert first.json()['extract']=='' # never invent source text
    assert client.get(path).json()['crazyReplacement1Extract']==DICKENS
    assert collection.docs==before # load, refresh and cancel are read-only for Mongo
    assert not f.api.called and not f.edit_api.called
    response=client.patch('/temp/creation/'+old['rewrite_id']+'/text',json={
        'crazyReplacement1Title':old['crazyReplacement1Title'],'crazyReplacement1Extract':DICKENS+' Encore.'})
    assert response.status_code==200
    assert client.get(path).json()['crazyReplacement1Extract']==DICKENS+' Encore.'
    saved=collection.find_one({'_id':old['_id']})
    assert saved['video']==old['video'] and saved['image_url']==old['image_url'] and saved['jingle_url']==old['jingle_url']


def test_missing_rewrite_id_uses_entry_identity_and_can_save_without_migration(setup):
    f,routes,client,collection,old=setup
    collection.docs[0].pop('rewrite_id')
    response=client.get('/temp/gallery_creation/'+str(old['_id']))
    assert response.status_code==200
    rid=response.json()['rewrite_id'];assert rid==creation_restore.legacy_editor_id(old['_id'])
    assert 'rewrite_id' not in collection.docs[0]
    assert client.patch('/temp/creation/'+rid+'/text',json={
        'crazyReplacement1Title':'Edited','crazyReplacement1Extract':'Saved older story.'}).status_code==200
    assert 'rewrite_id' not in collection.docs[0]
    assert client.get('/temp/gallery_creation/'+str(old['_id'])).json()['crazyReplacement1Extract']=='Saved older story.'


def test_encoded_legacy_result_and_optional_nulls_are_normalised(setup):
    import json
    f,routes,client,collection,old=setup
    entry=collection.docs[0]
    entry.pop('crazyReplacement1Title');entry.pop('crazyReplacement1Extract')
    entry['result']=json.dumps({'crazyReplacement1Extract':DICKENS})
    entry['description']=None
    entry['crazyReplacement1Extract']=None
    response=client.get('/temp/image_result/'+old['rewrite_id'])
    assert response.status_code==200 and response.json()['crazyReplacement1Extract']==DICKENS
    assert response.json()['crazyReplacement1Title']==''


def test_wrong_owner_missing_body_and_missing_record_fail_explicitly(setup):
    f,routes,client,collection,old=setup
    client.cookies.set('active_pet','bob')
    assert client.get('/temp/image_result/'+old['rewrite_id']).status_code==403
    client.cookies.set('active_pet','alice');collection.docs[0].pop('crazyReplacement1Extract')
    assert client.get('/temp/image_result/'+old['rewrite_id']).status_code==422
    assert client.get('/temp/image_result/missing').status_code==404


@pytest.mark.parametrize('engine',['build','current'])
def test_consecutive_modern_origins_keep_selected_identity(setup,engine):
    f,routes,client,collection,old=setup
    newer={**deepcopy(old),'_id':ObjectId(),'rewrite_id':'d92ba13a-48d6-4acb-bd1c-bfd51192907e',
           'munge_engine':engine,'crazyReplacement1Extract':'A goat pilots a kettle.'}
    collection.docs.append(newer)
    for record in [old,newer,old]:
        response=client.get('/temp/image_result/'+record['rewrite_id'])
        assert response.status_code==200
        assert response.json()['crazyReplacement1Extract']==record['crazyReplacement1Extract']
        assert response.json()['rewrite_id']==record['rewrite_id']


def test_restored_cache_reads_latest_mongo_text_on_next_edit(setup):
    f,routes,client,collection,old=setup
    path='/temp/image_result/'+old['rewrite_id']
    assert client.get(path).json()['crazyReplacement1Extract']==DICKENS
    collection.docs[0]['crazyReplacement1Extract']='Saved from a different browser.'
    assert client.get(path).json()['crazyReplacement1Extract']=='Saved from a different browser.'


def test_nullable_legacy_owner_can_save_without_requiring_new_fields(setup):
    f,routes,client,collection,old=setup
    record=collection.docs[0];record.pop('rewrite_id');record['image_owner']=None;record['creationUser']='alice'
    response=client.get('/temp/gallery_creation/'+str(old['_id']));assert response.status_code==200
    rid=response.json()['rewrite_id']
    assert client.patch('/temp/creation/'+rid+'/text',json={
        'crazyReplacement1Title':'Legacy','crazyReplacement1Extract':'Saved again.'}).status_code==200


def test_incomplete_historical_local_state_uses_saved_nomination_text(setup):
    f,routes,client,collection,old=setup
    with f.store.transaction() as db:
        f.store.save(db,old['rewrite_id'],{'owner':'alice','entry_id':str(old['_id']),
            'result':{'rewrite_id':old['rewrite_id'],'crazyReplacement1Extract':None}})
    response=client.get('/temp/image_result/'+old['rewrite_id'])
    assert response.status_code==200 and response.json()['crazyReplacement1Extract']==DICKENS
