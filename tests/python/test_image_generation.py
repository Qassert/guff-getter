"""Offline image tests: all model, HTTP and MongoDB dependencies are replaced."""
import base64
import importlib
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import MagicMock, patch

from newsmuncher.services.image_generation import (RewriteStore, build_image_prompt,
    build_end_image_prompt, build_transformation_map, OpenAIImageProvider, LocalStubProvider)


class ImageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = RewriteStore(Path(self.tmp.name) / 'images.sqlite3')
        self.images = Path(self.tmp.name) / 'generated'
        self.png = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aF1kAAAAASUVORK5CYII=')
        self.api_patch = patch('newsmuncher.services.image_generation.OpenAI')
        self.openai = self.api_patch.start()
        self.addCleanup(self.api_patch.stop)
        self.api = self.openai.return_value.__enter__.return_value.images.generate
        self.api.return_value = types.SimpleNamespace(data=[types.SimpleNamespace(b64_json=base64.b64encode(self.png).decode())])
        self.edit_api = self.openai.return_value.__enter__.return_value.images.edit
        self.edit_api.return_value = types.SimpleNamespace(data=[types.SimpleNamespace(b64_json=base64.b64encode(self.png).decode())])
        directory = patch('newsmuncher.services.image_generation.GENERATED_IMAGES_DIR', self.images)
        directory.start()
        self.addCleanup(directory.stop)
        env = patch('newsmuncher.services.image_generation.load_dotenv')
        env.start()
        self.addCleanup(env.stop)
        self.result = dict(title='SECRET SOURCE', extract='SECRET SOURCE',
                          crazyReplacement1Title='Moon soup', crazyReplacement1Extract='A cat paints the moon.')

    def tearDown(self):
        self.tmp.cleanup()

    def test_prompt_and_stub(self):
        prompt = build_image_prompt(self.result)
        self.assertNotIn('SECRET SOURCE', prompt)
        self.assertNotIn('Moon soup', prompt)
        self.assertNotIn('Scene title:', prompt)
        self.assertIn('A cat paints the moon.', prompt)
        image = LocalStubProvider().generate_image(prompt)
        self.assertEqual(image['image_provider'], 'local-stub')
        self.assertTrue(Path('newsmuncher' + image['image_url']).exists())
        self.assertFalse(image['image_url'].startswith('data:'))

    def test_start_and_independent_end_prompts_are_distinct(self):
        start = build_image_prompt(self.result, 'Editorial')
        end = build_end_image_prompt(self.result, 'Editorial')
        self.assertNotEqual(start, end)
        self.assertIn('A cat paints the moon.', start)
        self.assertIn('A cat paints the moon.', end)
        self.assertIn('Preserve the same characters', end)
        self.assertIn('Visual style: Editorial.', start)
        self.assertIn('Visual style: Editorial.', end)
        self.assertIn('centre foreground', start)
        self.assertIn('centre foreground', end)

    def test_transformation_map_is_stable_and_spatial(self):
        first = build_transformation_map(self.result)
        self.assertEqual(first, build_transformation_map(self.result))
        self.assertEqual([item['region'] for item in first], [
            'centre foreground', 'left midground', 'right foreground',
            'background centre', 'upper background'])
        self.assertEqual(len({item['destination'] for item in first}), 5)

    def test_reference_generation_uses_start_png_as_high_fidelity_input(self):
        reference = self.images / 'reference.png'
        reference.parent.mkdir(parents=True, exist_ok=True)
        reference.write_bytes(self.png)
        identifier = '00000000-0000-0000-0000-000000000123'
        metadata = OpenAIImageProvider().generate_referenced_image('transform', identifier, reference)
        self.edit_api.assert_called_once()
        kwargs = self.edit_api.call_args.kwargs
        self.assertEqual(kwargs['model'], 'gpt-image-1.5')
        self.assertEqual(kwargs['input_fidelity'], 'high')
        self.assertEqual(kwargs['prompt'], 'transform')
        self.assertEqual(Path(kwargs['image'].name), reference)
        self.assertEqual(metadata['image_url'], f'/generated-images/{identifier}.png')

    def test_style_selected_once_persisted_and_restored(self):
        routes = self.previews()
        rid = self.store.create(self.result, 'alice')['rewrite_id']
        with patch.object(routes, 'choose_image_style', return_value='Cyberpunk') as choose:
            metadata = routes.generate_image(routes.ImageRequest(rewrite_id=rid), 'alice')
            routes.store = RewriteStore(self.store.path)
            for _ in range(2):
                self.assertEqual(routes.get_image_result(rid, 'alice')['image_style'], 'Cyberpunk')
                self.assertEqual(routes.generate_image(routes.ImageRequest(rewrite_id=rid), 'alice'), metadata)
            choose.assert_called_once_with()
        self.assertEqual(metadata['image_style'], 'Cyberpunk')
        self.assertIn('Visual style: Cyberpunk.', self.api.call_args.kwargs['prompt'])
        self.assertIn('A cat paints the moon.', self.api.call_args.kwargs['prompt'])
        self.assertEqual(self.api.call_count, 1)
        routes.send_prompt.assert_not_called()
        with self.store.transaction() as db:
            state = self.store.read(db, rid, 'alice')
            self.assertEqual(state['image_attempt']['image_style'], 'Cyberpunk')
            self.assertEqual(state['result']['image_style'], 'Cyberpunk')

    def test_failure_retains_style_and_existing_metadata_without_retry(self):
        routes = self.previews()
        result = self.store.create({**self.result, 'image_prompt': 'previous metadata'}, 'alice')
        rid = result['rewrite_id']
        self.api.side_effect = TimeoutError('uncertain')
        with patch.object(routes, 'choose_image_style', return_value='Pixel art') as choose:
            for _ in range(2):
                with self.assertRaises(routes.HTTPException):
                    routes.generate_image(routes.ImageRequest(rewrite_id=rid), 'alice')
            choose.assert_called_once_with()
        with self.store.transaction() as db:
            state = self.store.read(db, rid, 'alice')
            self.assertEqual(state['result'], result)
            self.assertEqual(state['image_attempt']['image_style'], 'Pixel art')
        self.assertEqual(self.api.call_count, 1)

    def test_legacy_style_unknown_without_metadata_replacement(self):
        routes = self.previews()
        old = LocalStubProvider().generate_image('original prompt')
        rid = self.store.create({**self.result, **old}, 'alice')['rewrite_id']
        with patch.object(routes, 'choose_image_style') as choose:
            restored = routes.get_image_result(rid, 'alice')
            cached = routes.generate_image(routes.ImageRequest(rewrite_id=rid), 'alice')
            choose.assert_not_called()
        self.assertIsNone(restored['image_style'])
        self.assertEqual(cached, {**old, 'image_style': None})
        self.api.assert_not_called()

    def test_durable_identity_and_owner(self):
        a = self.store.create(self.result, 'alice')
        b = self.store.create(self.result, 'alice')
        self.assertNotEqual(a['rewrite_id'], b['rewrite_id'])
        reopened = RewriteStore(self.store.path)
        with reopened.transaction() as db:
            self.assertEqual(reopened.read(db, a['rewrite_id'], 'alice')['result'], a)
            with self.assertRaises(PermissionError): reopened.read(db, a['rewrite_id'], 'bob')

    def previews(self):
        # Import route definitions without importing text generation/OpenAI at all.
        clean = types.ModuleType('newsmuncher.utils.clean_data')
        for name in ('prepare_prompt','send_prompt','format_shizzalise_result','copy_edit_pass','claim_used_words'):
            setattr(clean, name, MagicMock())
        source = types.ModuleType('newsmuncher.utils.source_preprocessing')
        source.log_overlap = MagicMock()
        with patch.dict(sys.modules, {'newsmuncher.utils.clean_data': clean,
                                     'newsmuncher.utils.source_preprocessing': source}):
            spec = importlib.util.spec_from_file_location('image_test_previews', 'newsmuncher/api/previews.py')
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        module.store = self.store
        module.TEMP_SHIZZ_FILE = Path(self.tmp.name) / 'shizz.json'
        module.TEMP_FILE = Path(self.tmp.name) / 'temp.json'
        return module

    def test_banking_before_and_after_image(self):
        for image_first in (True, False):
            with self.subTest(image_first=image_first):
                routes = self.previews()
                result = self.store.create(self.result, 'alice')
                rid = result['rewrite_id']
                req = types.SimpleNamespace(cookies={'active_pet':'alice'})
                response = MagicMock()
                response.json.return_value = {'id':'saved-id'}
                with patch.object(routes.requests, 'post', return_value=response) as post, patch.object(routes.requests, 'patch', return_value=response) as update:
                    if image_first: routes.generate_image(routes.ImageRequest(rewrite_id=rid), 'alice')
                    routes.bank_image_rewrite(req, rid)
                    if not image_first: routes.generate_image(routes.ImageRequest(rewrite_id=rid), 'alice')
                    self.assertEqual('image_url' in post.call_args.kwargs['json'], image_first)
                    self.assertEqual(update.call_count, int(not image_first))
                    routes.bank_image_rewrite(req, rid)
                    self.assertEqual(post.call_count, 1)
                with self.store.transaction() as db:
                    state = self.store.read(db, rid, 'alice')
                    self.assertEqual(state['entry_id'], 'saved-id')
                    self.assertIn('image_url', state['result'])

    def test_provider_failure_preserves_text(self):
        routes = self.previews()
        result = self.store.create(self.result, 'alice')
        provider = MagicMock()
        provider.generate_image.side_effect = RuntimeError('failure')
        with patch.object(routes, 'get_provider', return_value=provider):
            with self.assertRaises(routes.HTTPException) as error:
                routes.generate_image(routes.ImageRequest(rewrite_id=result['rewrite_id']), 'alice')
            self.assertEqual(error.exception.status_code, 502)
        with self.store.transaction() as db:
            self.assertEqual(self.store.read(db, result['rewrite_id'], 'alice')['result'], result)

    def test_definite_failure_gets_one_claimed_automatic_retry(self):
        routes = self.previews()
        rid = self.store.create(self.result, 'alice')['rewrite_id']
        success = LocalStubProvider().generate_image('retry prompt')
        provider = MagicMock()
        provider.generate_image.side_effect = [routes.DefinitiveImageFailure('empty'), success]
        with patch.object(routes, 'get_provider', return_value=provider):
            result = routes.generate_image(routes.ImageRequest(rewrite_id=rid), 'alice')
        self.assertEqual(result['image_url'], success['image_url'])
        self.assertEqual(provider.generate_image.call_count, 2)
        with self.store.transaction() as db:
            state = self.store.read(db, rid, 'alice')
        self.assertEqual(state['image_attempt']['retry_count'], 1)
        self.assertEqual(state['image_attempt']['status'], 'complete')
        self.assertEqual(state['image_attempt_history'][0]['status'], 'definitive_failed')

    def test_two_definite_failures_stop_and_allow_explicit_redo(self):
        routes = self.previews()
        rid = self.store.create(self.result, 'alice')['rewrite_id']
        provider = MagicMock()
        provider.generate_image.side_effect = [routes.DefinitiveImageFailure('empty'),
            routes.DefinitiveImageFailure('empty again')]
        with patch.object(routes, 'get_provider', return_value=provider):
            with self.assertRaises(routes.HTTPException) as error:
                routes.generate_image(routes.ImageRequest(rewrite_id=rid), 'alice')
        self.assertEqual(error.exception.status_code, 422)
        self.assertEqual(provider.generate_image.call_count, 2)
        with self.store.transaction() as db:
            state = self.store.read(db, rid, 'alice')
        self.assertEqual(state['image_attempt']['status'], 'definitive_failed')
        self.assertTrue(routes.get_image_result(rid, 'alice')['image_generation_failed'])
        replacement = LocalStubProvider().generate_image('user-approved redo')
        with patch.object(routes, 'get_provider', return_value=types.SimpleNamespace(generate_image=lambda *_: replacement)):
            result = routes.redo_image(routes.RedoImageRequest(rewrite_id=rid), 'alice')
        self.assertEqual(result['image_url'], replacement['image_url'])

    def test_ambiguous_failure_never_retries_automatically(self):
        routes = self.previews()
        rid = self.store.create(self.result, 'alice')['rewrite_id']
        provider = MagicMock(); provider.generate_image.side_effect = TimeoutError('uncertain')
        with patch.object(routes, 'get_provider', return_value=provider):
            with self.assertRaises(routes.HTTPException) as error:
                routes.generate_image(routes.ImageRequest(rewrite_id=rid), 'alice')
            self.assertEqual(error.exception.status_code, 502)
            with self.assertRaises(routes.HTTPException):
                routes.generate_image(routes.ImageRequest(rewrite_id=rid), 'alice')
        self.assertEqual(provider.generate_image.call_count, 1)

    def test_rewrite_off_payload_and_on_identity(self):
        routes = self.previews()
        routes.load_prompt = MagicMock(return_value='prompt')
        routes.prepare_prompt.return_value = {'full_prompt':'prompt', 'preprocessing':None, 'contenders':{}}
        routes.send_prompt.return_value = {'title':'Moon soup', 'extract':'A cat paints the moon.'}
        routes.format_shizzalise_result.return_value = self.result
        # Make copy_edit_pass return None so it falls back to pass-1 result
        routes.copy_edit_pass.return_value = None
        for enabled in (False, True):
            result = routes.shizzalise_data(routes.ShizzRequest(title='source', description='', extract='source', generate_images=enabled), 'alice', 'alice')
            self.assertIn('rewrite_id', result)
            self.assertFalse(result['nominated'])
            self.assertNotIn('generate_images', result)
            self.assertEqual(result['crazyReplacement1Title'], 'Moon soup')

    def test_legacy_and_image_document_storage(self):
        client = MagicMock()
        with patch('pymongo.MongoClient', return_value=client), patch('dotenv.load_dotenv'):
            spec = importlib.util.spec_from_file_location('image_test_entries', 'newsmuncher/api/entries.py')
            routes = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(routes)
        routes.collection = MagicMock()
        request = types.SimpleNamespace(cookies={'active_pet':'alice'})
        for image in (False, True):
            payload = dict(title='title', description='', extract='text')
            if image: payload.update(rewrite_id='rewrite', image_style='Cyberpunk', **LocalStubProvider().generate_image('prompt'))
            routes.create_entry(routes.Post(**payload), request)
            saved = ({**routes.collection.update_one.call_args.args[1]['$setOnInsert'], **routes.collection.update_one.call_args.args[1]['$set']} if image else routes.collection.insert_one.call_args.args[0])
            self.assertEqual('image_url' in saved, image)
            if image:
                self.assertEqual(saved['image_owner'], 'alice')
                self.assertEqual(saved['image_style'], 'Cyberpunk')

    def test_image_endpoint_is_separate_and_owner_checked(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        routes = self.previews()
        result = self.store.create(self.result, 'alice')
        app = FastAPI()
        app.include_router(routes.router, prefix='/temp')
        with TestClient(app) as client:
            client.cookies.set('active_pet', 'bob')
            self.assertEqual(client.post('/temp/generate_image', json={'rewrite_id':result['rewrite_id']}).status_code, 403)
            client.cookies.set('active_pet', 'alice')
            response = client.post('/temp/generate_image', json={'rewrite_id':result['rewrite_id']})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()['image_provider'], 'openai')
            routes.send_prompt.assert_not_called()

    def test_openai_settings_storage_repeat_and_restore(self):
        routes = self.previews()
        rid = self.store.create(self.result, 'alice')['rewrite_id']
        payload = routes.ImageRequest(rewrite_id=rid)
        metadata = routes.generate_image(payload, 'alice')
        self.assertEqual((self.images / f'{rid}.png').read_bytes(), self.png)
        self.assertEqual(metadata['image_provider'], 'openai')
        self.assertEqual(metadata['image_url'], f'/generated-images/{rid}.png')
        self.assertEqual(routes.generate_image(payload, 'alice'), metadata)
        self.assertEqual(routes.get_image_result(rid, 'alice')['image_url'], metadata['image_url'])
        self.assertEqual(self.api.call_count, 1)
        self.openai.assert_called_once_with(max_retries=0, timeout=180.0)
        self.assertEqual(self.api.call_args.kwargs, dict(model='gpt-image-1.5', quality='low',
            size='1024x1024', n=1, output_format='png', prompt=build_image_prompt(self.result, metadata['image_style'])))
        self.assertNotIn('SECRET SOURCE', metadata['image_prompt'])
        self.assertEqual(list(self.images.glob('*.tmp')), [])

    def test_concurrent_claim_prevents_duplicate(self):
        import threading
        from concurrent.futures import ThreadPoolExecutor
        routes = self.previews()
        rid = self.store.create(self.result, 'alice')['rewrite_id']
        payload = routes.ImageRequest(rewrite_id=rid)
        entered, release = threading.Event(), threading.Event()
        reply = self.api.return_value
        def blocked(**kwargs):
            entered.set()
            if not release.wait(5): raise RuntimeError('Test timed out')
            return reply
        self.api.side_effect = blocked
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(routes.generate_image, payload, 'alice')
            self.assertTrue(entered.wait(5))
            try:
                with self.assertRaises(routes.HTTPException) as error:
                    routes.generate_image(payload, 'alice')
                self.assertEqual(error.exception.status_code, 409)
            finally:
                release.set()
            self.assertEqual(first.result()['image_provider'], 'openai')
        self.assertEqual(self.api.call_count, 1)

    def test_timeout_marker_survives_reopen(self):
        routes = self.previews()
        rid = self.store.create(self.result, 'alice')['rewrite_id']
        self.api.side_effect = TimeoutError('uncertain')
        with self.assertRaises(routes.HTTPException): routes.generate_image(routes.ImageRequest(rewrite_id=rid), 'alice')
        routes.store = RewriteStore(self.store.path)
        with self.assertRaises(routes.HTTPException) as error:
            routes.generate_image(routes.ImageRequest(rewrite_id=rid), 'alice')
        self.assertEqual(error.exception.status_code, 409)
        self.assertEqual(self.api.call_count, 1)
        self.assertEqual(routes.get_image_result(rid, 'alice')['crazyReplacement1Extract'], self.result['crazyReplacement1Extract'])

    def test_recover_file_with_incomplete_metadata(self):
        routes = self.previews()
        rid = self.store.create(self.result, 'alice')['rewrite_id']
        self.images.mkdir()
        (self.images / f'{rid}.png').write_bytes(self.png)
        metadata = routes.generate_image(routes.ImageRequest(rewrite_id=rid), 'alice')
        self.assertEqual(metadata['image_url'], f'/generated-images/{rid}.png')
        self.assertEqual(metadata['image_prompt'], build_image_prompt(self.result))
        self.api.assert_not_called()
        with self.store.transaction() as db:
            self.assertEqual(self.store.read(db, rid, 'alice')['result']['image_url'], metadata['image_url'])

    def test_mongo_failure_keeps_local_success(self):
        routes = self.previews()
        rid = self.store.create(self.result, 'alice')['rewrite_id']
        with self.store.transaction() as db:
            state = self.store.read(db, rid, 'alice')
            state['entry_id'] = 'banked'
            self.store.save(db, rid, state)
        with patch.object(routes.requests, 'patch', side_effect=routes.requests.RequestException('offline')):
            metadata = routes.generate_image(routes.ImageRequest(rewrite_id=rid), 'alice')
            self.assertEqual(routes.generate_image(routes.ImageRequest(rewrite_id=rid), 'alice'), metadata)
        self.assertEqual(self.api.call_count, 1)

    def test_atomic_write_failure_never_regenerates(self):
        routes = self.previews()
        rid = self.store.create(self.result, 'alice')['rewrite_id']
        with patch('newsmuncher.services.image_generation.os.replace', side_effect=OSError('disk failure')):
            with self.assertRaises(routes.HTTPException): routes.generate_image(routes.ImageRequest(rewrite_id=rid), 'alice')
        with self.assertRaises(routes.HTTPException): routes.generate_image(routes.ImageRequest(rewrite_id=rid), 'alice')
        self.assertEqual(self.api.call_count, 1)
        self.assertEqual(list(self.images.glob('*')), [])

    def test_partial_existing_url_never_regenerates(self):
        routes = self.previews()
        rid = self.store.create({**self.result, 'image_url':'/static/image-stub.svg'}, 'alice')['rewrite_id']
        metadata = routes.generate_image(routes.ImageRequest(rewrite_id=rid), 'alice')
        self.assertEqual(metadata['image_url'], '/static/image-stub.svg')
        self.api.assert_not_called()
        self.assertEqual(routes.get_image_result(rid, 'alice')['image_url'], metadata['image_url'])

    def test_png_survives_metadata_failure_and_recovers(self):
        routes = self.previews()
        rid = self.store.create(self.result, 'alice')['rewrite_id']
        original = self.store.save
        def fail_completed(db, key, state):
            if state['result'].get('image_url'): raise OSError('metadata failure')
            return original(db, key, state)
        with patch.object(self.store, 'save', side_effect=fail_completed):
            with self.assertRaises(routes.HTTPException): routes.generate_image(routes.ImageRequest(rewrite_id=rid), 'alice')
        restored = routes.generate_image(routes.ImageRequest(rewrite_id=rid), 'alice')
        self.assertEqual(restored['image_provider'], 'openai')
        self.assertIn('Visual style: ' + restored['image_style'], restored['image_prompt'])
        self.assertEqual(self.api.call_count, 1)

    def test_nomination_current_response_both_paths(self):
        import json
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        for images in (False, True):
            for edited in (False, True):
                with self.subTest(images=images, edited=edited):
                    routes = self.previews()
                    result = self.store.create(self.result, 'alice') if images else dict(self.result)
                    routes.TEMP_FILE.write_text('{}')
                    routes.TEMP_SHIZZ_FILE.write_text(json.dumps(result))
                    payload = dict(crazyReplacement1Title='Edited title' if edited else self.result['crazyReplacement1Title'],
                                   crazyReplacement1Extract='Edited body' if edited else self.result['crazyReplacement1Extract'])
                    response = MagicMock()
                    response.json.return_value = {'id':'saved-id'}
                    app = FastAPI(); app.include_router(routes.router, prefix='/temp')
                    with patch.object(routes.requests, 'post', return_value=response) as post, TestClient(app) as client:
                        client.cookies.set('active_pet', 'alice')
                        url = '/temp/confirm_data' + ('?rewrite_id=' + result['rewrite_id'] if images else '')
                        self.assertEqual(client.post(url, json=payload).status_code, 200)
                        self.assertEqual(post.call_count, 1)
                        saved = post.call_args.kwargs['json']
                        for key, value in payload.items(): self.assertEqual(saved[key], value)
                        self.assertEqual(saved['title'], self.result['title'])
                        self.assertEqual(saved['extract'], self.result['extract'])
                    if images:
                        with self.store.transaction() as db:
                            saved = self.store.read(db, result['rewrite_id'], 'alice')['result']
                            self.assertEqual(saved['crazyReplacement1Title'], payload['crazyReplacement1Title'])

    def test_renomination_updates_existing_entry_without_duplicate_insert(self):
        routes = self.previews()
        result = self.store.create(self.result, 'alice')
        rid = result['rewrite_id']
        with self.store.transaction() as db:
            state = self.store.read(db, rid, 'alice')
            state['entry_id'] = 'saved-id'
            self.store.save(db, rid, state)
        payload = routes.NominationResponse(crazyReplacement1Title='', crazyReplacement1Extract='New body')
        request = types.SimpleNamespace(cookies={'active_pet':'alice'})
        with patch.object(routes.requests, 'put', return_value=MagicMock()) as put, patch.object(routes.requests, 'post') as post:
            routes.bank_image_rewrite(request, rid, payload)
            routes.bank_image_rewrite(request, rid, payload)
            put.assert_called_once()
            self.assertEqual(put.call_args.kwargs['params'], payload.model_dump())
            post.assert_not_called()

    def test_javascript(self):
        import subprocess
        subprocess.run(['node', 'tests/frontend/image_flow.test.js'], check=True)
        subprocess.run(['node', 'tests/frontend/image_background.test.js'], check=True)
        subprocess.run(['node', 'tests/frontend/profile_editing.test.js'], check=True)
