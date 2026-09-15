"""Offline harness tests; all SDK/HTTP boundaries replaced."""
import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import compare_tts as tts


class ComparisonTests(unittest.TestCase):
    def setUp(self):
        self.original_output = tts.OUTPUT_DIR
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.output = Path(self.tmp.name) / 'tts-comparison'
        for target, kwargs in (
            ('OUTPUT_DIR', {'new': self.output}), ('load_dotenv', {}),
            ('requests.post', {}),
        ):
            p = patch.object(tts, target, **kwargs) if '.' not in target else patch(
                'scripts.compare_tts.' + target, **kwargs)
            mock = p.start()
            self.addCleanup(p.stop)
            setattr(self, target.replace('.', '_'), mock)
        sdk = patch('newsmuncher.services.openai_tts.OpenAI')
        self.OpenAI = sdk.start()
        self.addCleanup(sdk.stop)
        env = patch.dict(os.environ, {key: 'test-key' for key in tts.KEYS.values()}, clear=True)
        env.start()
        self.addCleanup(env.stop)
        out = patch('sys.stdout', new_callable=io.StringIO)
        self.stdout = out.start()
        self.addCleanup(out.stop)
        self.response = self.requests_post.return_value.__enter__.return_value
        self.response.status_code = 200
        self.response.headers = {'Content-Type': 'audio/mpeg'}
        self.response.content = b'ID3mock'
        self.speech = self.OpenAI.return_value.__enter__.return_value.audio.speech
        self.speech.with_streaming_response.create.return_value.__enter__.return_value.read.return_value = b'ID3mock'

    def test_random_voice_and_one_output_per_provider(self):
        for provider in tts.KEYS:
            with self.subTest(provider=provider), patch.object(tts.random, 'choice') as choose:
                choose.return_value = tts.VOICE_POOLS[provider][-1]
                self.assertEqual(tts.main(['--provider', provider]), 0)
                choose.assert_called_once_with(tts.VOICE_POOLS[provider])
                files = list(self.output.glob(f'{provider}-*.mp3'))
                self.assertEqual(len(files), 1)
                self.assertIn(choose.return_value[1], files[0].name)
                self.assertEqual(files[0].read_bytes(), b'ID3mock')
        self.assertEqual(self.requests_post.call_count, 2)
        self.speech.with_streaming_response.create.assert_called_once()

    def test_missing_keys_never_call_providers(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(tts.main(['--provider', 'all']), 1)
        self.OpenAI.assert_not_called()
        self.requests_post.assert_not_called()
        self.assertFalse(self.output.exists())
        self.assertEqual(self.stdout.getvalue().count('SKIPPED:'), 3)

    def test_dry_run_with_keys_calls_nothing_and_writes_nothing(self):
        self.assertEqual(tts.main(['--provider', 'all', '--dry-run']), 0)
        self.OpenAI.assert_not_called()
        self.requests_post.assert_not_called()
        self.assertFalse(self.output.exists())
        self.assertEqual(self.stdout.getvalue().count('DRY RUN:'), 3)
        self.assertNotIn('test-key', self.stdout.getvalue())

    def test_default_output_is_project_relative(self):
        self.assertEqual(self.original_output,
                         Path(tts.__file__).resolve().parents[1] / 'data/tts-comparison')

    def test_same_input_and_provider_contracts(self):
        self.assertEqual(tts.main(['--provider', 'all']), 0)
        self.OpenAI.assert_called_once_with(api_key='test-key', max_retries=0, timeout=60)
        kwargs = self.speech.with_streaming_response.create.call_args.kwargs
        self.assertEqual(kwargs['input'], tts.SAMPLE_TEXT)
        self.assertEqual(kwargs['response_format'], 'mp3')
        eleven, cartesia = self.requests_post.call_args_list
        self.assertEqual(eleven.kwargs['json']['text'], tts.SAMPLE_TEXT)
        self.assertEqual(eleven.kwargs['params']['output_format'], 'mp3_44100_128')
        self.assertEqual(cartesia.kwargs['json']['transcript'], tts.SAMPLE_TEXT)
        self.assertIn(cartesia.kwargs['json']['voice'], dict(tts.VOICE_POOLS['cartesia']).values())
        self.assertEqual(cartesia.kwargs['headers']['Cartesia-Version'], tts.CARTESIA_VERSION)
        for call in (eleven, cartesia):
            self.assertFalse(call.kwargs['allow_redirects'])
            self.assertEqual(call.kwargs['timeout'], 60)

    def test_failure_continues_without_retry_or_secret_output(self):
        self.speech.with_streaming_response.create.side_effect = RuntimeError('test-key')
        self.assertEqual(tts.main(['--provider', 'all']), 1)
        self.speech.with_streaming_response.create.assert_called_once()
        self.assertEqual(self.requests_post.call_count, 2)
        self.assertEqual(len(list(self.output.glob('*.mp3'))), 2)
        self.assertNotIn('test-key', self.stdout.getvalue())

    def test_http_error_or_non_audio_does_not_write(self):
        self.response.headers = {'Content-Type': 'application/json'}
        self.assertEqual(tts.main(['--provider', 'cartesia']), 1)
        self.assertEqual(list(self.output.iterdir()), [])
        self.response.raise_for_status.side_effect = RuntimeError('test-key')
        self.assertEqual(tts.main(['--provider', 'elevenlabs']), 1)
        self.assertEqual(list(self.output.iterdir()), [])
        self.assertNotIn('test-key', self.stdout.getvalue())


if __name__ == '__main__':
    unittest.main()
