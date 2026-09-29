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
        result=routes.loading_images('alice')['images']
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
