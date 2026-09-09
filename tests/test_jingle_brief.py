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

    def test_wire_contract_limits_duration_and_input(self):
        with self.assertRaises(ValueError):
            GenerationRequest(request_id="bad", music_prompt="test", lyrics="test", duration_seconds=90)

    def test_generated_assets_ignored(self):
        self.assertIn("/data/generated_audio/*", Path(".gitignore").read_text())
        self.assertIn(".venv-modal/", Path(".gitignore").read_text())
