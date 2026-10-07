from unittest.mock import patch
import pytest
import test_image_generation as fixtures


def test_loading_images_owner_scope_limit_validity_and_no_provider_calls():
    f=fixtures.ImageTests(); f.setUp()
    try:
        routes=f.previews()
        f.images.mkdir()
        own=[]
        for i in range(9):
            row=f.store.create(f.result, 'alice' if i<7 else 'bob')
            rid=row['rewrite_id'];url=f'/generated-images/{rid}.png'
            (f.images / f'{rid}.png').write_bytes(f.png)
            with f.store.transaction() as db:
                state=f.store.read(db,rid,'alice' if i<7 else 'bob')
                state['result']['image_url']=url
                f.store.save(db,rid,state)
            if i<7: own.append(url)
        before=f.store.path.read_bytes()
        payload=routes.loading_images('alice')['images']
        assert all(item['jingle_url'] is None for item in payload)
        result=[item['image_url'] for item in payload]
        assert len(result)==5 and len(set(result))==5
        assert set(result)<=set(own)
        assert routes.loading_images('missing')['images']==[]
        with pytest.raises(routes.HTTPException): routes.loading_images(None)
        f.api.assert_not_called()
        assert f.store.path.read_bytes()==before
        # No arbitrary paths, external URLs, missing images or discarded records.
        with f.store.transaction() as db:
            for (rid,encoded) in db.execute('SELECT id,state FROM rewrites').fetchall():
                import json
                state=json.loads(encoded)
                if state['owner']=='alice':
                    state['result']['image_url']='https://invalid/private.png'
                    f.store.save(db,rid,state)
        assert routes.loading_images('alice')['images']==[]
    finally:
        f.tearDown();f.doCleanups()


def test_loading_image_uses_only_saved_jingle_for_its_nomination(tmp_path):
    from newsmuncher.services.jingles import Jingles, LocalAudio
    from unittest.mock import Mock
    f=fixtures.ImageTests();f.setUp()
    try:
        routes=f.previews()
        provider=Mock(side_effect=AssertionError('No provider calls'))
        jingles=Jingles(tmp_path/'jingles.db',LocalAudio(tmp_path/'audio'),provider,provider)
        key='a'*24
        with jingles.transaction() as db:
            jingles.save(db,key,{'status':'complete'})
        jingles.audio.save(key,b'ID3'+b'0'*2000)
        row=f.store.create(f.result,'alice');rid=row['rewrite_id']
        f.images.mkdir();(f.images/f'{rid}.png').write_bytes(f.png)
        with f.store.transaction() as db:
            state=f.store.read(db,rid,'alice');state['entry_id']=key
            state['result']['image_url']=f'/generated-images/{rid}.png'
            f.store.save(db,rid,state)
        before=jingles.database.read_bytes()
        with patch('newsmuncher.services.jingles.service',jingles):
            assert routes.loading_images('alice')['images']==[{'image_url':f'/generated-images/{rid}.png','jingle_url':jingles.audio.url(key)}]
            assert routes.loading_images('bob')['images']==[]
            assert jingles.database.read_bytes()==before
            with jingles.transaction() as db: jingles.save(db,key,{'status':'retired'})
            assert routes.loading_images('alice')['images'][0]['jingle_url'] is None
        provider.assert_not_called()
        assert jingles.saved_url('invalid') is None
    finally:
        f.tearDown();f.doCleanups()
