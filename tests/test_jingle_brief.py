"""No live providers, MongoDB or GPU in these tests."""
import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from pathlib import Path

from newsmuncher.services.jingle_brief import create_jingle_brief
from jingle_service.contract import GenerationRequest


class JingleBriefTests(unittest.TestCase):
    def test_draft_is_rejected_before_api(self):
        with patch("newsmuncher.services.jingle_brief.OpenAI") as client:
            with self.assertRaises(ValueError):
                create_jingle_brief({"nominated": False})
            client.assert_not_called()

    def test_uses_only_rewrite_and_one_bounded_call(self):
        with patch("newsmuncher.services.jingle_brief.OpenAI") as client, patch(
                "newsmuncher.services.jingle_brief.load_dotenv"):
            api = client.return_value.__enter__.return_value.responses.create
            api.return_value = SimpleNamespace(
                status="completed", model="gpt-4.1-mini",
                usage=SimpleNamespace(input_tokens=100, output_tokens=80),
                output_text=json.dumps({"music_prompt": "Wonky brass", "lyrics": "Toot toot",
                                        "duration_seconds": 25}),
            )
            brief, usage = create_jingle_brief({
                "nominated": True, "title": "SECRET SOURCE",
                "extract": "SECRET ORIGINAL BODY",
                "crazyReplacement1Title": "Teapot town",
                "crazyReplacement1Extract": "The mayor whistles biscuits.",
            })
            self.assertEqual(brief.duration_seconds, 25)
            self.assertEqual(usage["output_tokens"], 80)
            api.assert_called_once()
            payload = api.call_args.kwargs
            self.assertNotIn("SECRET", payload["input"])
            self.assertIn("Teapot town", payload["input"])
            self.assertEqual(payload["max_output_tokens"], 400)
            self.assertEqual(client.call_args.kwargs["max_retries"], 0)

    def test_compact_lyrics_prompt_and_intact_lines(self):
        from jingle_service.genres import GENRE_PROFILES
        lyrics = ("Teapot mayor shakes the moon\n"
                  "Biscuit trumpets hum a tune\n"
                  "Ferret bankers stamp and sway\n"
                  "Moonlit kettles steal the day")
        with patch("newsmuncher.services.jingle_brief.OpenAI") as client, patch(
                "newsmuncher.services.jingle_brief.load_dotenv"), patch(
                "newsmuncher.services.jingle_brief.random.choice", return_value="Acid House") as choose:
            api = client.return_value.__enter__.return_value.responses.create
            api.return_value = SimpleNamespace(status="completed", model="mock",
                usage=SimpleNamespace(input_tokens=10, output_tokens=20),
                output_text=json.dumps({"music_prompt": "ignored decorative prose",
                                        "lyrics": lyrics, "duration_seconds": 25}))
            brief, _ = create_jingle_brief({"nominated": True,
                "crazyReplacement1Title": "Teapot mayor",
                "crazyReplacement1Extract": "Ferret bankers dance with biscuit trumpets."})
            api.assert_called_once()
            choose.assert_called_once()
            instructions = api.call_args.kwargs["instructions"]
            for phrase in ("16–28 words total", "4 short lines", "3–7 words per line",
                           "newline characters", "Light rhyme and repetition",
                           "stage directions", "tongue-twister", "not just four isolated words",
                           "Keep lyrics separate from music_prompt"):
                self.assertIn(phrase, instructions)
            self.assertEqual(brief.lyrics, lyrics)  # no cutting, padding or rewriting
            self.assertEqual(len(brief.lyrics.splitlines()), 4)
            self.assertTrue(16 <= len(brief.lyrics.split()) <= 28)
            self.assertTrue(all(3 <= len(line.split()) <= 7 for line in brief.lyrics.splitlines()))
            self.assertEqual(brief.genre_profile, GENRE_PROFILES["Acid House"])
            self.assertEqual(brief.music_prompt, GENRE_PROFILES["Acid House"].caption())
            self.assertEqual(brief.genre_params(), {"bpm": 125, "timesignature": "4"})
            self.assertEqual(brief.duration_seconds, 25)
            self.assertNotIn("reference_audio", brief.model_dump())

    def test_wire_contract_limits_duration_and_input(self):
        with self.assertRaises(ValueError):
            GenerationRequest(request_id="bad", music_prompt="test", lyrics="test", duration_seconds=90)

    def test_generated_assets_ignored(self):
        self.assertIn("/data/generated_audio/*", Path(".gitignore").read_text())
        self.assertIn(".venv-modal/", Path(".gitignore").read_text())

class BenchmarkFailureTests(unittest.TestCase):
    def test_failed_gpu_request_is_recorded_and_never_repeated(self):
        import tempfile
        from unittest.mock import Mock
        import requests
        from scripts import benchmark_jingle
        response = requests.Response()
        response.status_code = 502
        response._content = b'Generation failed'
        with tempfile.TemporaryDirectory() as folder, patch.object(
                benchmark_jingle, 'DATA_DIR', Path(folder)), patch.object(
                benchmark_jingle, 'load_dotenv'), patch.dict(
                'os.environ', {'MODAL_JINGLE_ENDPOINT': 'https://example.modal.run',
                               'MODAL_JINGLE_KEY': 'test', 'MODAL_JINGLE_SECRET': 'test'}), patch(
                'sys.argv', ['benchmark', '--generate']), patch.object(
                benchmark_jingle.requests, 'post', return_value=response) as post:
            with self.assertRaises(requests.HTTPError):
                benchmark_jingle.main()
            report = json.loads((Path(folder) / 'generated_audio/benchmark-report.json').read_text())
            self.assertEqual(report['http_status'], 502)
            self.assertIsNone(report['audio_file'])
            with self.assertRaises(SystemExit):
                benchmark_jingle.main()
            post.assert_called_once()
