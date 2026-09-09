"""Lifecycle tests extend offline fixtures, never connect to Mongo/OpenAI."""
import json
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
import unittest
import test_image_generation as fixtures


class DraftLifecycleTests(unittest.TestCase):
    setUp = fixtures.ImageTests.setUp
    tearDown = fixtures.ImageTests.tearDown
    previews = fixtures.ImageTests.previews
    def new(self, title='draft', session='browser'):
        rid = self.store.begin_draft(self.result, 'alice', session)
        result = {**self.result, 'crazyReplacement1Title': title}
        return self.store.complete_draft(rid, 'alice', result)

    def state(self, rid):
        with self.store.transaction() as db:
            return self.store.read(db, rid, 'alice')

    def nominate(self, routes, result):
        return routes.bank_image_rewrite(SimpleNamespace(cookies={'active_pet':'alice'}), result['rewrite_id'])

    def test_replace_draft_cleans_image_and_metadata(self):
        routes = self.previews()
        a = self.new('A')
        routes.generate_image(routes.ImageRequest(rewrite_id=a['rewrite_id']), 'alice')
        path = self.images / (a['rewrite_id'] + '.png')
        self.assertTrue(path.exists())
        b = self.new('B')
        self.assertNotEqual(a['rewrite_id'], b['rewrite_id'])
        self.assertTrue(self.state(a['rewrite_id'])['discarded'])
        self.assertEqual(self.state(a['rewrite_id'])['result'], {'rewrite_id':a['rewrite_id']})
        self.assertFalse(path.exists())
        with self.assertRaises(routes.HTTPException): routes.get_image_result(a['rewrite_id'], 'alice')

    def test_a_b_d_permanent_c_discarded(self):
        routes = self.previews()
        response = MagicMock(); response.json.return_value = {'id':'permanent'}
        with patch.object(routes.requests,'post',return_value=response) as post:
            a=self.new('A'); self.nominate(routes,a)
            b=self.new('B'); self.nominate(routes,b)
            c=self.new('C'); d=self.new('D'); self.nominate(routes,d)
            self.nominate(routes,d)
            self.assertEqual([call.kwargs['json']['crazyReplacement1Title'] for call in post.call_args_list], ['A','B','D'])
        for r in [a,b,d]:
            self.assertTrue(self.state(r['rewrite_id'])['result']['nominated'])
            self.assertEqual(self.state(r['rewrite_id'])['result']['gallery_status'],'pending')
        self.assertTrue(self.state(c['rewrite_id'])['discarded'])

    def test_nominated_image_survives_next_draft(self):
        routes=self.previews(); a=self.new('A')
        routes.generate_image(routes.ImageRequest(rewrite_id=a['rewrite_id']),'alice')
        response=MagicMock(); response.json.return_value={'id':'saved'}
        with patch.object(routes.requests,'post',return_value=response):self.nominate(routes,a)
        self.new('B')
        self.assertTrue((self.images/(a['rewrite_id']+'.png')).exists())

    def test_late_image_discarded_without_paid_retry(self):
        routes=self.previews(); a=self.new('A')
        entered, release=threading.Event(),threading.Event(); reply=self.api.return_value
        def blocked(**kwargs):
            entered.set(); release.wait(5); return reply
        self.api.side_effect=blocked
        with ThreadPoolExecutor() as pool:
            future=pool.submit(routes.generate_image,routes.ImageRequest(rewrite_id=a['rewrite_id']),'alice')
            self.assertTrue(entered.wait(5))
            try:b=self.new('B')
            finally:release.set()
            with self.assertRaises(routes.HTTPException):future.result()
        self.assertFalse((self.images/(a['rewrite_id']+'.png')).exists())
        with self.assertRaises(routes.HTTPException):routes.generate_image(routes.ImageRequest(rewrite_id=a['rewrite_id']),'alice')
        self.assertEqual(self.api.call_count,1)
        self.assertFalse(self.state(b['rewrite_id']).get('discarded',False))

    def test_uncertain_nomination_protects_image(self):
        routes=self.previews(); a=self.new('A')
        routes.generate_image(routes.ImageRequest(rewrite_id=a['rewrite_id']),'alice')
        with patch.object(routes.requests,'post',side_effect=routes.requests.Timeout()):
            with self.assertRaises(routes.HTTPException):self.nominate(routes,a)
        self.new('B')
        self.assertTrue(self.state(a['rewrite_id'])['nomination_pending'])
        self.assertTrue((self.images/(a['rewrite_id']+'.png')).exists())

    def test_other_sessions_and_expiry(self):
        a=self.new('A'); b=self.new('B','other')
        self.assertFalse(self.state(a['rewrite_id']).get('discarded',False))
        with self.store.transaction() as db:
            state=self.store.read(db,a['rewrite_id'],'alice');state['expires_at']=time.time()-1
            self.store.save(db,a['rewrite_id'],state)
        self.new('C','third')
        self.assertTrue(self.state(a['rewrite_id'])['discarded'])
        self.assertFalse(self.state(b['rewrite_id']).get('discarded',False))

    def test_moderation_legacy_and_status_validation(self):
        from newsmuncher.services.moderation import nomination_state,moderation_fields,APPROVED_GALLERY_FILTER
        self.assertEqual(nomination_state({'crazyReplacement1done':True}),{'nominated':True,'gallery_status':'pending'})
        self.assertFalse(nomination_state({})['nominated'])
        for status in ['pending','approved','rejected']:self.assertEqual(moderation_fields(status),{'gallery_status':status})
        with self.assertRaises(ValueError):moderation_fields('anything')
        self.assertEqual(APPROVED_GALLERY_FILTER,{'nominated':True,'gallery_status':'approved'})

    def test_mongo_idempotency_and_pending_defaults(self):
        import importlib.util
        client=MagicMock()
        with patch('pymongo.MongoClient',return_value=client),patch('dotenv.load_dotenv'):
            spec=importlib.util.spec_from_file_location('lifecycle_entries','newsmuncher/api/entries.py')
            routes=importlib.util.module_from_spec(spec);spec.loader.exec_module(routes)
        routes.collection=MagicMock()
        post=routes.Post(title='source',description='',extract='source body',rewrite_id='stable',
                         crazyReplacement1Title='edited',crazyReplacement1Extract='edited body')
        request=SimpleNamespace(cookies={'active_pet':'alice'})
        first=routes.create_entry(post,request);second=routes.create_entry(post,request)
        self.assertEqual(first['id'],second['id'])
        routes.collection.insert_one.assert_not_called()
        update=routes.collection.update_one.call_args.args[1]
        self.assertTrue(update['$setOnInsert']['nominated'])
        self.assertEqual(update['$setOnInsert']['gallery_status'],'pending')
        self.assertEqual(update['$set']['crazyReplacement1Title'],'edited')
        self.assertTrue(routes.collection.update_one.call_args.kwargs['upsert'])

    def test_superseded_text_completion_cannot_restore_draft(self):
        a=self.store.begin_draft(self.result,'alice','browser')
        b=self.new('B')
        self.assertIsNone(self.store.complete_draft(a,'alice',self.result))
        self.assertEqual(self.state(b['rewrite_id'])['result']['crazyReplacement1Title'],'B')
