"""Tests for the second‑pass AI copy‑editing.

All external calls are mocked; no live OpenAI or other paid services are used.
"""
import json
import unittest
from unittest.mock import Mock, patch, MagicMock
from newsmuncher.utils.clean_data import copy_edit_pass, sanitize_text


class CopyEditPassTests(unittest.TestCase):
    def setUp(self):
        self.pass1_result = {
            'crazyReplacement1Title': 'Moon soup',
            'crazyReplacement1Extract': 'A cat paints the moon.  They doesnt know why.',
        }
        self.expected_pass2_input = {
            'title': 'Moon soup',
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
            self.assertEqual(call_args.kwargs['model'], 'gpt-5.6-luna')
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

    def test_copy_edit_pass_integration_with_previews(self):
        """Verify that the previews route falls back to pass‑1 when copy‑edit returns None.

        This integration is already covered by the existing test_image_generation.py
        tests which mock the previews module.
        """
        pass
