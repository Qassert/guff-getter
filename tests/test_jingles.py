"""App jingle tests use local temp files and mocked providers/Mongo only."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch

from jingle_service.contract import MusicBrief
from newsmuncher.services.jingles import Jingles, LocalAudio, JingleError, modal_audio

MP3 = b"ID3" + b"\0" * 2000


class JingleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)
        self.entry = {"_id": "a" * 24, "rewrite_id": "rewrite-1", "nominated": True,
                      "image_owner": "pet", "crazyReplacement1Title": "Teapot mayor",
                      "crazyReplacement1Extract": "Biscuits take the bus."}
        self.collection = Mock()
        self.collection.find_one.side_effect = lambda query: self.entry.copy()
        self.brief = Mock(return_value=(MusicBrief(music_prompt="Brass", lyrics="Toot"), {"input_tokens": 10}))
        self.provider = Mock(return_value=MP3)
        self.today = datetime(2026, 9, 10, tzinfo=timezone.utc)
        self.limit = 20
        self.service = Jingles(self.path / "state.db", LocalAudio(self.path / "audio"),
            self.brief, self.provider, enabled=lambda: True, limit=lambda: self.limit,
            now=lambda: self.today)

    def generate(self):
        return self.service.generate(self.collection, "rewrite-1", "pet")

    def test_success_storage_and_nomination_snapshot(self):
        result = self.generate()
        self.assertEqual(result["jingle_status"], "complete")
        self.assertEqual(self.service.audio.path("a"*24).read_bytes(), MP3)
        metadata = self.collection.update_one.call_args.args[1]["$set"]
        self.assertEqual(metadata["jingle_text_snapshot"]["title"], "Teapot mayor")
        self.assertEqual(metadata["jingle_provider"], "modal")
        self.assertEqual(metadata["jingle_prompt"]["duration_seconds"], 25)
        self.brief.assert_called_once()
        self.provider.assert_called_once()

    def test_draft_foreign_and_missing_owner_never_generate(self):
        for nominated, owner in [(False, "pet"), (True, "other"), (True, None)]:
            self.entry["nominated"] = nominated
            with self.assertRaises(JingleError):
                self.service.generate(self.collection, "rewrite-1", owner)
        self.provider.assert_not_called()
        self.brief.assert_not_called()

    def test_missing_nomination_is_rejected(self):
        self.collection.find_one.side_effect = None
        self.collection.find_one.return_value = None
        with self.assertRaises(JingleError):
            self.generate()
        self.provider.assert_not_called()

    def test_repeated_generate_and_status_do_not_spend(self):
        first = self.generate()
        self.limit = 0
        second = self.generate()
        restored = self.service.status(self.collection, "rewrite-1", "pet")
        self.assertEqual(first["jingle_url"], second["jingle_url"])
        self.assertEqual(restored["jingle_url"], first["jingle_url"])
        self.provider.assert_called_once()
        with self.service.transaction() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM jingle_claims").fetchone()[0], 1)

    def test_two_workers_share_claim(self):
        entered, release = threading.Event(), threading.Event()
        def slow(*args):
            entered.set()
            release.wait(5)
            return MP3
        self.provider.side_effect = slow
        other = Jingles(self.service.database, self.service.audio, self.brief, self.provider,
                        enabled=lambda: True, limit=lambda: 20, now=lambda: self.today)
        with ThreadPoolExecutor(2) as pool:
            running = pool.submit(self.generate)
            self.assertTrue(entered.wait(3))
            duplicate = other.generate(self.collection, "rewrite-1", "pet")
            self.assertFalse(duplicate["can_generate"])
            release.set()
            self.assertEqual(running.result()["jingle_status"], "complete")
        self.provider.assert_called_once()

    def test_global_daily_cap_and_utc_reset(self):
        self.limit = 1
        self.generate()
        self.entry["_id"] = "b"*24
        with self.assertRaises(JingleError) as caught:
            self.generate()
        self.assertEqual(caught.exception.status, 429)
        self.provider.assert_called_once()
        self.today += timedelta(days=1)
        self.generate()
        self.assertEqual(self.provider.call_count, 2)

    def test_provider_timeout_blocks_blind_retry(self):
        self.provider.side_effect = TimeoutError()
        result = self.generate()
        self.assertEqual(result["jingle_status"], "uncertain")
        self.assertFalse(result["can_generate"])
        self.generate()
        self.provider.assert_called_once()
        self.assertFalse(self.service.audio.exists("a"*24))
        self.assertTrue(self.entry["nominated"])

    def test_brief_failure_explicit_retry_and_quota(self):
        self.brief.side_effect = ValueError("refusal")
        result = self.generate()
        self.assertEqual(result["jingle_status"], "brief_failed")
        self.assertTrue(result["can_generate"])
        self.provider.assert_not_called()
        self.brief.side_effect = None
        self.generate()
        self.provider.assert_called_once()
        with self.service.transaction() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM jingle_claims").fetchone()[0], 2)

    def test_nomination_update_keeps_existing_jingle(self):
        original = self.generate()
        self.entry["crazyReplacement1Title"] = "Edited later"
        result = self.generate()
        self.assertEqual(original["jingle_url"], result["jingle_url"])
        self.assertTrue(result["text_changed"])
        self.provider.assert_called_once()

    def test_file_survives_metadata_sync_failure(self):
        self.collection.update_one.side_effect = OSError("Mongo unavailable")
        result = self.generate()
        self.assertTrue(result["metadata_pending"])
        self.collection.update_one.side_effect = None
        self.assertFalse(self.service.status(self.collection, "rewrite-1", "pet")["metadata_pending"])
        self.provider.assert_called_once()

    def test_file_recovery_and_missing_file_never_regenerate(self):
        self.generate()
        with self.service.transaction() as db:
            state = self.service.read(db, "a"*24)
            state["status"] = "submitted"
            self.service.save(db, "a"*24, state)
        self.assertEqual(self.service.status(self.collection, "rewrite-1", "pet")["jingle_status"], "complete")
        self.entry["jingle_url"] = "/generated-audio/" + "a"*24 + ".mp3"
        self.service.audio.path("a"*24).unlink()
        result = self.generate()
        self.assertEqual(result["jingle_status"], "unavailable")
        self.provider.assert_called_once()

    def test_invalid_audio_and_identity(self):
        self.provider.return_value = b"<html>Error</html>"
        self.assertEqual(self.generate()["jingle_status"], "uncertain")
        self.assertFalse(self.service.audio.exists("a"*24))
        with self.assertRaises(ValueError):
            self.service.audio.path("../../secret")

    def test_provider_makes_one_post_and_checks_content(self):
        response = Mock()
        response.status_code = 200
        response.headers = {"Content-Type": "audio/mpeg"}
        response.iter_content.return_value = [MP3]
        with patch("newsmuncher.services.jingles.configured", return_value=True), patch.dict(
                "os.environ", {"MODAL_JINGLE_ENDPOINT": "https://test.modal.run",
                               "MODAL_JINGLE_KEY": "fake", "MODAL_JINGLE_SECRET": "fake"}), patch(
                "newsmuncher.services.jingles.requests.post") as post:
            post.return_value.__enter__.return_value = response
            self.assertEqual(modal_audio(self.brief.return_value[0], "id"), MP3)
            post.assert_called_once()
            self.assertFalse(post.call_args.kwargs["allow_redirects"])
            self.assertTrue(post.call_args.kwargs["stream"])

class JingleRouteTests(unittest.TestCase):
    def test_routes_call_service_with_cookie_and_never_accept_client_text(self):
        import importlib.util
        import sys
        import types
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        fake_entries = types.ModuleType("newsmuncher.api.entries")
        fake_entries.collection = Mock()
        spec = importlib.util.spec_from_file_location("jingle_test_routes", "newsmuncher/api/jingles.py")
        module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"newsmuncher.api.entries": fake_entries}):
            spec.loader.exec_module(module)
        module.service = Mock()
        module.service.generate.return_value = {"jingle_status": "complete", "jingle_url": "/generated-audio/a.mp3"}
        module.service.status.return_value = {"jingle_status": "none", "can_generate": True}
        app = FastAPI()
        app.include_router(module.router)
        with TestClient(app) as client:
            client.cookies.set("active_pet", "pet")
            response = client.post("/jingles/rewrite", json={"nominated": True, "title": "untrusted"})
            self.assertEqual(response.status_code, 200)
            module.service.generate.assert_called_once_with(fake_entries.collection, "rewrite", "pet")
            self.assertEqual(client.get("/jingles/rewrite").status_code, 200)
            self.assertEqual(module.service.generate.call_count, 1)
            module.service.generate.side_effect = JingleError(429, "Daily limit reached")
            self.assertEqual(client.post("/jingles/rewrite").status_code, 429)

    def test_cap_concurrent_distinct_nominations(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            brief = Mock(return_value=(MusicBrief(music_prompt="Brass", lyrics="Toot"), {}))
            provider = Mock(return_value=MP3)
            service = Jingles(path/"state.db", LocalAudio(path/"audio"), brief, provider,
                               enabled=lambda: True, limit=lambda: 1)
            entries = [{"_id": c*24, "rewrite_id": c, "nominated": True, "image_owner": "pet",
                        "crazyReplacement1Title": "A", "crazyReplacement1Extract": "B"} for c in "ab"]
            collection = Mock()
            collection.find_one.side_effect = lambda q: next(e for e in entries if e["rewrite_id"] == q["rewrite_id"])
            def run(key):
                try:
                    return service.generate(collection, key, "pet")["jingle_status"]
                except JingleError as exc:
                    return exc.status
            with ThreadPoolExecutor(2) as pool:
                results = list(pool.map(run, "ab"))
            self.assertIn(429, results)
            self.assertIn("complete", results)
            provider.assert_called_once()
