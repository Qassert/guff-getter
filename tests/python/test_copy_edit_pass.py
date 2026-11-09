"""Tests for the second‑pass AI copy‑editing.

All external calls are mocked; no live OpenAI or other paid services are used.
"""
import json
import os
import unittest
from unittest.mock import Mock, patch, MagicMock
from newsmuncher.utils.clean_data import (copy_edit_pass, sanitize_text, send_prompt,
                                          RewriteProviderQuotaExhausted)


class CopyEditPassTests(unittest.TestCase):
    def setUp(self):
        self.pass1_result = {
            'crazyReplacement1Title': 'Moon soup',
            'crazyReplacement1Extract': 'A cat paints the moon.  They doesnt know why.',
        }
        self.expected_pass2_input = {
            'extract': 'A cat paints the moon.  They doesnt know why.',
        }

    def _mock_openai(self, response_status='completed', response_json=None, side_effect=None):
        """Create a mocked OpenAI class that returns a client with responses.create."""
        mock_client = Mock()
        if side_effect:
            mock_client.responses.create.side_effect = side_effect
        else:
            mock_response = Mock()
            mock_response.status = response_status
            if response_json:
                mock_response.output_text = json.dumps(response_json)
            mock_client.responses.create.return_value = mock_response
        # Create a mock for the OpenAI class
        mock_openai_class = MagicMock()
        # When OpenAI() is called (with any arguments), return a context manager
        mock_context = Mock()
        mock_context.__enter__ = Mock(return_value=mock_client)
        mock_context.__exit__ = Mock(return_value=None)
        mock_openai_class.return_value = mock_context
        return mock_openai_class, mock_client

    def test_copy_edit_pass_receives_only_pass1_output(self):
        """The copy‑edit call receives ONLY pass‑1 title/extract, never source text."""
        mock_openai, mock_client = self._mock_openai(
            response_json={'title': 'Polished Moon Soup', 'extract': 'A cat paints the moon.  They do not know why.'}
        )
        with patch('newsmuncher.utils.clean_data.OpenAI', new=mock_openai):
            result = copy_edit_pass(self.pass1_result)
            self.assertIsNotNone(result)
            # Verify the call arguments
            call_args = mock_client.responses.create.call_args
            self.assertEqual(call_args.kwargs['model'], 'gpt-6-sol')
            input_messages = call_args.kwargs['input']
            # System prompt should mention preserving absurdity
            system_content = input_messages[0]['content']
            self.assertIn('accept that every single event', system_content)
            self.assertIn('preserve', system_content.lower())
            # User content must be the JSON of pass‑1 output only
            user_content = input_messages[1]['content']
            self.assertEqual(json.loads(user_content), self.expected_pass2_input)

    def test_copy_edit_pass_preserves_absurdity_instruction(self):
        """The system prompt explicitly tells the model not to sanitise or make things sensible."""
        mock_openai, mock_client = self._mock_openai(
            response_json={'title': 'Polished', 'extract': 'Polished extract.'}
        )
        with patch('newsmuncher.utils.clean_data.OpenAI', new=mock_openai):
            copy_edit_pass(self.pass1_result)
            system_prompt = mock_client.responses.create.call_args.kwargs['input'][0]['content']
            forbidden_phrases = [
                'make the story sensible',
                'sanitise it',
                'revert it toward normal journalism',
                'remove any weird or absurd details',
                'explain any jokes',
            ]
            for phrase in forbidden_phrases:
                self.assertIn(phrase, system_prompt)

    def test_copy_edit_pass_successful_returns_sanitized_result(self):
        """A successful copy‑edit call returns the sanitised title/extract."""
        mock_openai, mock_client = self._mock_openai(
            response_json={'title': 'Polished Moon Soup', 'extract': 'A cat paints the moon.  They do not know why.'}
        )
        with patch('newsmuncher.utils.clean_data.OpenAI', new=mock_openai):
            result = copy_edit_pass(self.pass1_result)
            self.assertEqual(result['crazyReplacement1Title'], 'Polished Moon Soup')
            self.assertEqual(result['crazyReplacement1Extract'], 'A cat paints the moon. They do not know why.')
            self.assertTrue(result['crazyReplacement1done'])
            self.assertEqual(result['flagForDeleteCount'], 0)
            self.assertEqual(result['flagForFunnyCount'], 0)
            self.assertEqual(result['chatHistory'], [])

    def test_copy_edit_pass_falls_back_on_failure(self):
        """Any exception or incomplete response returns None, causing the caller to fall back."""
        mock_openai, mock_client = self._mock_openai(response_status='incomplete', response_json=None)
        with patch('newsmuncher.utils.clean_data.OpenAI', new=mock_openai):
            result = copy_edit_pass(self.pass1_result)
            self.assertIsNone(result)

    def test_copy_edit_pass_falls_back_on_exception(self):
        """Network errors, timeouts, invalid JSON etc. also return None."""
        mock_openai, mock_client = self._mock_openai(side_effect=RuntimeError('API down'))
        with patch('newsmuncher.utils.clean_data.OpenAI', new=mock_openai):
            result = copy_edit_pass(self.pass1_result)
            self.assertIsNone(result)

    def test_first_pass_credit_exhaustion_is_preserved_as_typed_failure(self):
        error = RuntimeError('provider rejected request')
        error.status_code = 429
        error.body = {'type': 'insufficient_quota', 'code': 'credit_balance_exhausted'}
        mocked, _ = self._mock_openai(side_effect=error)
        with patch('newsmuncher.utils.clean_data.OpenAI', new=mocked):
            with self.assertRaises(RewriteProviderQuotaExhausted) as failure:
                send_prompt('mocked prompt')
        self.assertIn('no credits remaining', str(failure.exception))

    def test_copy_edit_pass_handles_empty_title_or_extract(self):
        """If pass‑1 result has missing or empty title/extract, return None early."""
        for bad_result in [
            {'crazyReplacement1Title': '', 'crazyReplacement1Extract': 'something'},
            {'crazyReplacement1Title': 'something', 'crazyReplacement1Extract': ''},
            {'crazyReplacement1Title': None, 'crazyReplacement1Extract': 'something'},
            {},
        ]:
            result = copy_edit_pass(bad_result)
            self.assertIsNone(result, f"Should return None for {bad_result}")

    def test_empty_polish_is_rejected(self):
        mocked, client = self._mock_openai(response_json={'title':' ', 'extract':'body'})
        with patch('newsmuncher.utils.clean_data.OpenAI', new=mocked):
            self.assertIsNone(copy_edit_pass(self.pass1_result))

    def test_copy_edit_pass_integration_with_previews(self):
        import test_image_generation as fixtures
        fixture = fixtures.ImageTests()
        fixture.setUp()
        try:
            routes = fixture.previews()
            contenders = {'nouns': ['pass-one', 'pass-two']}
            routes.prepare_prompt.return_value = {
                'full_prompt':'masked', 'preprocessing':None, 'contenders': contenders}
            routes.send_prompt.return_value = {'title':'crazy', 'extract':'crazy body'}
            first = {k:v for k,v in fixture.result.items() if k.startswith('crazy')}
            routes.format_shizzalise_result.return_value = first
            for polished in (None, {**first, 'crazyReplacement1Title':'Polished'}):
                routes.copy_edit_pass.return_value = polished
                result = routes.shizzalise_data(routes.ShizzRequest(title='ORIGINAL',description='',extract='SECRET'), 'alice','alice')
                routes.copy_edit_pass.assert_called_with(first)
                accepted = dict(polished or first)
                routes.claim_used_words.assert_called_with(contenders, accepted)
                self.assertNotIn('ORIGINAL', str(routes.copy_edit_pass.call_args))
                self.assertEqual(result['crazyReplacement1Title'], accepted['crazyReplacement1Title'])
        finally:
            fixture.tearDown()
            fixture.doCleanups()

    def test_final_title_uses_accepted_polished_body(self):
        import test_image_generation as fixtures
        fixture = fixtures.ImageTests()
        fixture.setUp()
        try:
            routes = fixture.previews()
            routes.prepare_prompt.return_value = {'full_prompt': 'masked', 'preprocessing': None, 'contenders': {}}
            routes.send_prompt.return_value = {'title': 'Alien invasion', 'extract': 'First body'}
            routes.format_shizzalise_result.return_value = dict(fixture.result)
            routes.copy_edit_pass.return_value = {
                'crazyReplacement1Title': 'Badgers sell lunar waffles',
                'crazyReplacement1Extract': 'Badgers sell lunar waffles outside Parliament.',
            }
            result = routes.shizzalise_data(routes.ShizzRequest(title='SOURCE', description='', extract='SECRET'), 'alice', 'alice')
            self.assertEqual(result['crazyReplacement1Title'], 'Badgers sell lunar waffles')
            self.assertNotIn('Moon', result['crazyReplacement1Title'])
            claimed = routes.claim_used_words.call_args.args[1]
            self.assertEqual(claimed['crazyReplacement1Extract'], result['crazyReplacement1Extract'])
            self.assertEqual(claimed['crazyReplacement1Title'], result['crazyReplacement1Title'])
        finally:
            fixture.tearDown()
            fixture.doCleanups()

    def test_failed_generation_never_attempts_word_claim(self):
        import test_image_generation as fixtures
        fixture = fixtures.ImageTests()
        fixture.setUp()
        try:
            routes = fixture.previews()
            routes.prepare_prompt.return_value = {
                'full_prompt': 'masked', 'preprocessing': None,
                'contenders': {'nouns': ['unused']},
            }
            routes.send_prompt.return_value = None
            with self.assertRaises(routes.HTTPException) as error:
                routes.shizzalise_data(
                    routes.ShizzRequest(title='source', description='', extract='source'),
                    'alice', 'alice')
            self.assertEqual(error.exception.status_code, 500)
            routes.claim_used_words.assert_not_called()
        finally:
            fixture.tearDown()
            fixture.doCleanups()

    def test_credit_exhaustion_returns_actionable_503_and_skips_copy_edit(self):
        import test_image_generation as fixtures
        fixture = fixtures.ImageTests()
        fixture.setUp()
        try:
            routes = fixture.previews()
            routes.prepare_prompt.return_value = {
                'full_prompt': 'masked', 'preprocessing': None, 'contenders': {},
            }
            routes.send_prompt.side_effect = routes.RewriteProviderQuotaExhausted(
                'The OpenAI API account has no credits remaining. Add API credits, then try MUNGE IT again.'
            )
            with self.assertRaises(routes.HTTPException) as error:
                routes.shizzalise_data(
                    routes.ShizzRequest(title='source', description='', extract='source'),
                    'alice', 'alice')
            self.assertEqual(error.exception.status_code, 503)
            self.assertIn('no credits remaining', error.exception.detail)
            routes.copy_edit_pass.assert_not_called()
            routes.claim_used_words.assert_not_called()
        finally:
            fixture.tearDown()
            fixture.doCleanups()

    def test_final_joke_guidance_uses_no_extra_provider_call_and_records_after_save(self):
        import test_image_generation as fixtures
        fixture = fixtures.ImageTests(); fixture.setUp()
        try:
            routes = fixture.previews()
            tracker = MagicMock()
            tracker.last_metrics = {}
            tracker.guidance.return_value = (
                "RECENT-JOKE VARIETY:\n- the recurring '17 accountants' group gag"
            )
            routes.FinalJokeMemory = MagicMock(return_value=tracker)
            routes.final_joke_memory_collection = MagicMock(return_value=object())
            routes.prepare_prompt.return_value = {
                'full_prompt': 'masked', 'preprocessing': None, 'contenders': {},
            }
            routes.send_prompt.return_value = {'title': 'new', 'extract': 'new body'}
            routes.format_shizzalise_result.return_value = dict(fixture.result)
            routes.copy_edit_pass.return_value = None
            with patch.dict(os.environ, {'NEWSMUNCHER_FINAL_JOKE_MEMORY': 'evaluation'}):
                result = routes.shizzalise_data(
                    routes.ShizzRequest(title='source', description='', extract='source'),
                    'alice', 'alice')
            self.assertEqual(routes.send_prompt.call_count, 1)
            self.assertEqual(routes.copy_edit_pass.call_count, 1)
            self.assertIn('17 accountants',
                          routes.prepare_prompt.call_args.kwargs['final_joke_guidance'])
            tracker.accept.assert_called_once()
            self.assertEqual(tracker.accept.call_args.args[0], result['rewrite_id'])
        finally:
            fixture.tearDown(); fixture.doCleanups()

    def test_failed_rewrite_does_not_record_final_jokes(self):
        import test_image_generation as fixtures
        fixture = fixtures.ImageTests(); fixture.setUp()
        try:
            routes = fixture.previews(); tracker = MagicMock()
            tracker.last_metrics = {}
            tracker.guidance.return_value = ''
            routes.FinalJokeMemory = MagicMock(return_value=tracker)
            routes.final_joke_memory_collection = MagicMock(return_value=object())
            routes.prepare_prompt.return_value = {
                'full_prompt': 'masked', 'preprocessing': None, 'contenders': {},
            }
            routes.send_prompt.return_value = None
            with patch.dict(os.environ, {'NEWSMUNCHER_FINAL_JOKE_MEMORY': 'evaluation'}):
                with self.assertRaises(routes.HTTPException):
                    routes.shizzalise_data(
                        routes.ShizzRequest(title='source', description='', extract='source'),
                        'alice', 'alice')
            tracker.accept.assert_not_called()
        finally:
            fixture.tearDown(); fixture.doCleanups()

    def test_final_joke_memory_read_failure_degrades_to_normal_rewrite(self):
        import test_image_generation as fixtures
        fixture = fixtures.ImageTests(); fixture.setUp()
        try:
            routes = fixture.previews(); tracker = MagicMock()
            tracker.guidance.side_effect = RuntimeError('database unavailable')
            routes.FinalJokeMemory = MagicMock(return_value=tracker)
            routes.final_joke_memory_collection = MagicMock(return_value=object())
            routes.prepare_prompt.return_value = {
                'full_prompt': 'masked', 'preprocessing': None, 'contenders': {},
            }
            routes.send_prompt.return_value = {'title': 'new', 'extract': 'new body'}
            routes.format_shizzalise_result.return_value = dict(fixture.result)
            routes.copy_edit_pass.return_value = None
            with patch.dict(os.environ, {'NEWSMUNCHER_FINAL_JOKE_MEMORY': 'evaluation'}):
                routes.shizzalise_data(
                    routes.ShizzRequest(title='source', description='', extract='source'),
                    'alice', 'alice')
            self.assertEqual(routes.send_prompt.call_count, 1)
            self.assertEqual(routes.prepare_prompt.call_args.kwargs['final_joke_guidance'], '')
            tracker.accept.assert_not_called()
        finally:
            fixture.tearDown(); fixture.doCleanups()

    def test_comedy_audit_logs_only_after_successful_persistence(self):
        import test_image_generation as fixtures
        fixture = fixtures.ImageTests(); fixture.setUp()
        try:
            routes = fixture.previews(); logger = MagicMock()
            routes.ComedyAuditLogger = MagicMock(return_value=logger)
            routes.build_audit_record = MagicMock(return_value={"rewrite_id": "recorded"})
            routes.prepare_prompt.return_value = {
                'full_prompt': 'masked', 'preprocessing': None,
                'contenders': {'slang': ['gravy']},
            }
            routes.send_prompt.return_value = {'title': 'new', 'extract': 'new body'}
            routes.format_shizzalise_result.return_value = dict(fixture.result)
            routes.copy_edit_pass.return_value = None
            with patch.dict(os.environ, {'NEWSMUNCHER_COMEDY_AUDIT_LOG': 'on'}):
                routes.shizzalise_data(
                    routes.ShizzRequest(title='source', description='', extract='source'),
                    'alice', 'alice')
            logger.append.assert_called_once_with({"rewrite_id": "recorded"})
            self.assertEqual(routes.build_audit_record.call_args.kwargs['source']['title'], 'source')
        finally:
            fixture.tearDown(); fixture.doCleanups()

    def test_failed_rewrite_does_not_write_comedy_audit(self):
        import test_image_generation as fixtures
        fixture = fixtures.ImageTests(); fixture.setUp()
        try:
            routes = fixture.previews(); logger = MagicMock()
            routes.ComedyAuditLogger = MagicMock(return_value=logger)
            routes.prepare_prompt.return_value = {
                'full_prompt': 'masked', 'preprocessing': None, 'contenders': {},
            }
            routes.send_prompt.return_value = None
            with patch.dict(os.environ, {'NEWSMUNCHER_COMEDY_AUDIT_LOG': 'on'}):
                with self.assertRaises(routes.HTTPException):
                    routes.shizzalise_data(
                        routes.ShizzRequest(title='source', description='', extract='source'),
                        'alice', 'alice')
            logger.append.assert_not_called()
        finally:
            fixture.tearDown(); fixture.doCleanups()

    def test_comedy_audit_failure_does_not_interrupt_persisted_rewrite(self):
        import test_image_generation as fixtures
        fixture = fixtures.ImageTests(); fixture.setUp()
        try:
            routes = fixture.previews(); logger = MagicMock()
            logger.append.side_effect = OSError('disk unavailable')
            routes.ComedyAuditLogger = MagicMock(return_value=logger)
            routes.build_audit_record = MagicMock(return_value={"rewrite_id": "recorded"})
            routes.prepare_prompt.return_value = {
                'full_prompt': 'masked', 'preprocessing': None, 'contenders': {},
            }
            routes.send_prompt.return_value = {'title': 'new', 'extract': 'new body'}
            routes.format_shizzalise_result.return_value = dict(fixture.result)
            routes.copy_edit_pass.return_value = None
            with patch.dict(os.environ, {'NEWSMUNCHER_COMEDY_AUDIT_LOG': 'on'}):
                result = routes.shizzalise_data(
                    routes.ShizzRequest(title='source', description='', extract='source'),
                    'alice', 'alice')
            self.assertEqual(result['crazyReplacement1Title'], fixture.result['crazyReplacement1Title'])
            logger.append.assert_called_once()
        finally:
            fixture.tearDown(); fixture.doCleanups()

    def test_topic_memory_is_soft_opt_in_and_records_after_persistence(self):
        import test_image_generation as fixtures
        fixture = fixtures.ImageTests(); fixture.setUp()
        try:
            routes = fixture.previews(); memory = MagicMock()
            memory.last_metrics = {}
            memory.guidance.return_value = 'RECENT COMEDY VARIETY: avoid the raffle callback'
            memory.recent_name_families.return_value = {}
            memory.penalties.return_value = routes.Counter()
            routes.TopicMemory = MagicMock(return_value=memory)
            routes.comedy_topic_memory_collection = MagicMock(return_value=object())
            routes.build_topic_event = MagicMock(return_value={'rewrite_id': 'topic-event'})
            routes.prepare_prompt.return_value = {
                'full_prompt': 'masked', 'preprocessing': None, 'contenders': {},
            }
            routes.send_prompt.return_value = {'title': 'new', 'extract': 'new body'}
            routes.format_shizzalise_result.return_value = dict(fixture.result)
            routes.copy_edit_pass.return_value = None
            with patch.dict(os.environ, {'NEWSMUNCHER_COMEDY_TOPIC_MEMORY': 'evaluation'}):
                routes.shizzalise_data(
                    routes.ShizzRequest(title='source', description='', extract='source'),
                    'alice', 'alice')
            self.assertEqual(routes.send_prompt.call_count, 1)
            self.assertIn('raffle', routes.prepare_prompt.call_args.kwargs['topic_guidance'])
            memory.record.assert_called_once_with({'rewrite_id': 'topic-event'})
        finally:
            fixture.tearDown(); fixture.doCleanups()

    def test_theme_sparks_reuse_selected_slate_without_another_provider_call(self):
        import test_image_generation as fixtures
        fixture = fixtures.ImageTests(); fixture.setUp()
        try:
            routes = fixture.previews()
            routes.ThemeIngredientConfig = MagicMock()
            routes.ThemeIngredientConfig.from_environment.return_value = MagicMock(enabled=True)
            routes.ThemeSparkConfig = MagicMock()
            routes.ThemeSparkConfig.from_environment.return_value = MagicMock(enabled=True)
            routes.generated_concept_collection = MagicMock(return_value=object())
            routes.generated_descriptor_collection = MagicMock(return_value=object())
            routes.comedy_thematic_diversity_collection = MagicMock(return_value=object())
            routes.comedy_theme_ingredient_collection = MagicMock(return_value=object())
            theme_memory = MagicMock(events=[], last_metrics={})
            routes.ThemeIngredientMemory = MagicMock(return_value=theme_memory)
            domain_memory = MagicMock(events=[], last_metrics={})
            domain_memory.select.return_value = [{"id": "mycology"}, {"id": "optics"}]
            routes.ThematicDiversityMemory = MagicMock(return_value=domain_memory)

            concepts = [
                {"phrase": f"concept {bank} {index}", "base": f"base {bank} {index}",
                 "target_bank": bank, "semantic_theme": "baseline"}
                for bank in ("nouns", "animals") for index in range(10)]
            themed_plan = {"prompt": [dict(item) for item in concepts],
                           "generated": list(concepts), "raw": [], "guidance": "",
                           "counts": {"generated": 18, "raw": 2, "thematic": 2}}
            themed_plan["prompt"][0].update(
                phrase="fungal kettle using refraction", thematic=True)
            themed_plan["prompt"][10].update(
                phrase="spore-adapted lunar badger", thematic=True)
            concept_registry = MagicMock(last_metrics={})
            concept_registry.last_accept_metrics = {}
            concept_registry.offer.return_value = concepts
            routes.ConceptRegistry = MagicMock(return_value=concept_registry)
            routes.ConceptSelectionConfig.from_environment.return_value = MagicMock(
                mode="generated", vocabulary_mode="off")
            routes.build_variant = MagicMock(return_value=themed_plan)

            descriptor_items = [
                {"phrase": f"descriptor {index}", "subject": f"subject {index}",
                 "grammatical_role": "predicate", "category": "absurd",
                 "semantic_theme": "baseline", "premise_key": f"p:{index}"}
                for index in range(10)]
            descriptor_items[0].update(
                phrase="responsive to mycelium during erosion",
                source="thematic_seed_catalogue")
            descriptor_registry = MagicMock(last_metrics={})
            descriptor_registry.last_accept_metrics = {}
            descriptor_registry.offer.return_value = descriptor_items
            routes.DescriptorRegistry = MagicMock(return_value=descriptor_registry)
            routes.DescriptorSelectionConfig.from_environment.return_value = MagicMock(
                mode="generated")

            builder = MagicMock()
            builder.apply_concepts.return_value = themed_plan
            builder.apply_descriptors.return_value = (descriptor_items, descriptor_items[1:])
            builder.selected = [
                {"text": "fungal kettle using refraction"},
                {"text": "spore-adapted lunar badger"},
                {"text": "responsive to mycelium during erosion"},
            ]
            builder.last_metrics = {}
            routes.ThematicIngredientBuilder = MagicMock(return_value=builder)
            routes.prepare_prompt.return_value = {
                "full_prompt": "masked", "preprocessing": None, "contenders": {}}
            routes.send_prompt.return_value = {"title": "new", "extract": "new body"}
            routes.format_shizzalise_result.return_value = dict(fixture.result)
            routes.copy_edit_pass.return_value = None

            routes.shizzalise_data(
                routes.ShizzRequest(title="source", description="", extract="source"),
                "alice", "alice")

            prompt_args = routes.prepare_prompt.call_args.kwargs
            assert len(prompt_args["concept_overrides"]["nouns"]) == 9
            # Four animals are visible; one thematic spark is placed separately.
            assert len(prompt_args["concept_overrides"]["animals"]) == 3
            assert len(prompt_args["descriptor_overrides"]) == 9
            assert [item["text"] for item in prompt_args["theme_sparks"]] == [
                "fungal kettle using refraction", "spore-adapted lunar badger",
                "responsive to mycelium during erosion [PRED]"]
            routes.send_prompt.assert_called_once()
            routes.copy_edit_pass.assert_called_once()
        finally:
            fixture.tearDown(); fixture.doCleanups()

    def test_concurrent_word_claim_conflict_does_not_complete_draft(self):
        import test_image_generation as fixtures
        fixture = fixtures.ImageTests()
        fixture.setUp()
        try:
            routes = fixture.previews()
            routes.prepare_prompt.return_value = {
                'full_prompt': 'masked', 'preprocessing': None,
                'contenders': {'nouns': ['moon']},
            }
            routes.send_prompt.return_value = {'title': 'Moon', 'extract': 'Body'}
            routes.format_shizzalise_result.return_value = self.pass1_result
            routes.copy_edit_pass.return_value = None
            routes.claim_used_words.side_effect = routes.WordClaimConflict('concurrent claim')
            with self.assertRaises(routes.HTTPException) as error:
                routes.shizzalise_data(
                    routes.ShizzRequest(title='source', description='', extract='source'),
                    'alice', 'alice')
            self.assertEqual(error.exception.status_code, 409)
            with fixture.store.transaction() as db:
                row = db.execute('SELECT state FROM rewrites').fetchone()
                state = json.loads(row[0])
            self.assertTrue(state['generating'])
            self.assertNotIn('crazyReplacement1Title', state['result'])
        finally:
            fixture.tearDown()
            fixture.doCleanups()


def test_generated_title_is_hard_capped_at_eighteen_words():
    from newsmuncher.utils.clean_data import format_shizzalise_result
    words = [f'word{i}' for i in range(25)]
    result = format_shizzalise_result({'title': ' '.join(words), 'extract': 'Body remains intact.'})
    assert result['crazyReplacement1Title'].split() == words[:18]
    assert result['crazyReplacement1Extract'] == 'Body remains intact.'


def test_repetition_replacement_prompt_is_bounded_and_preserves_madness():
    case = CopyEditPassTests()
    case.setUp()
    mocked, client = case._mock_openai(
        response_json={'title': 'Spore kettle', 'extract': 'A spore kettle swore.'})
    plan = {
        'targets': [{'text': value} for value in ('gravy', 'custard', 'marmalade')],
        'alternatives': [{'text': 'spore kettle'}, {'text': 'magnetic scribe'}],
        'maximum_substitutions': 2,
    }
    with patch('newsmuncher.utils.clean_data.OpenAI', new=mocked):
        assert copy_edit_pass(case.pass1_result, repetition_replacement=plan)
    prompt = client.responses.create.call_args.kwargs['input'][0]['content']
    assert 'at most 2 targeted vocabulary substitutions' in prompt
    assert 'gravy, custard, marmalade' in prompt
    assert 'spore kettle, magnetic scribe' in prompt
    for required in ('profanity', 'innuendo', 'surreal intensity',
                     'narrative sequence', 'comic timing'):
        assert required in prompt
    assert json.loads(client.responses.create.call_args.kwargs['input'][1]['content']) == \
        case.expected_pass2_input


def test_route_reuses_copy_edit_call_for_repetition_replacement_and_falls_back():
    import test_image_generation as fixtures
    fixture = fixtures.ImageTests()
    fixture.setUp()
    try:
        routes = fixture.previews()
        memory = MagicMock(events=[], last_metrics={})
        memory.penalties.return_value = routes.Counter({'word:gravy': 18})
        routes.LexicalExposureMemory = MagicMock(return_value=memory)
        routes.comedy_lexical_exposure_collection = MagicMock(return_value=object())
        plan = {'targets': [{'text': 'gravy'}],
                'alternatives': [{'text': 'spore dispersal'}],
                'maximum_substitutions': 2}
        diagnostic = {'enabled': True, 'eligible_targets': plan['targets'],
                      'rejected_targets': [], 'alternatives': plan['alternatives'],
                      'maximum_substitutions': 2, 'copy_edit_fell_back': False}
        routes.build_repetition_replacement = MagicMock(return_value=(plan, diagnostic))
        routes.prepare_prompt.return_value = {
            'full_prompt': 'masked', 'preprocessing': None, 'contenders': {}}
        routes.send_prompt.return_value = {'title': 'new', 'extract': 'new body'}
        first = dict(fixture.result)
        routes.format_shizzalise_result.return_value = first
        routes.copy_edit_pass.return_value = None
        with patch.dict(os.environ, {
                'NEWSMUNCHER_REPETITION_REPLACEMENT': 'evaluation',
                'NEWSMUNCHER_LEXICAL_DIVERSITY': 'off'}):
            result = routes.shizzalise_data(
                routes.ShizzRequest(title='source', description='', extract='source'),
                'alice', 'alice')
        routes.copy_edit_pass.assert_called_once_with(
            first, repetition_replacement=plan)
        assert routes.send_prompt.call_count == 1
        assert result['crazyReplacement1Extract'] == first['crazyReplacement1Extract']
        memory.record.assert_called_once()
    finally:
        fixture.tearDown()
        fixture.doCleanups()


def test_phrase_replacement_prompt_requests_local_action_without_sanitising():
    case = CopyEditPassTests(); case.setUp()
    mocked, client = case._mock_openai(
        response_json={'title': 'Cardigan tribunal',
                       'extract': 'A backup cardigan swore at Parliament.'})
    plan = {
        'targets': [{'text': 'municipal licensing authority'}],
        'alternatives': [{'text': 'backup cardigan'}],
        'maximum_substitutions': 2, 'phrase_replacement': True,
        'inventive_fallback': True,
        'fallback_domain_cues': ['mycology', 'bridge engineering'],
    }
    with patch('newsmuncher.utils.clean_data.OpenAI', new=mocked):
        assert copy_edit_pass(case.pass1_result, repetition_replacement=plan)
    prompt = client.responses.create.call_args.kwargs['input'][0]['content']
    assert 'Make one or two targeted substitutions' in prompt
    assert 'highest-confidence repeated comic phrases' in prompt
    assert 'invent one fresh, grammatically compatible and equally absurd replacement' in prompt
    assert 'Change only the necessary phrase and local grammatical agreement' in prompt
    assert 'Do not change names or protected source details' in prompt
    assert 'outrageous British humour' in prompt and 'profanity' in prompt
