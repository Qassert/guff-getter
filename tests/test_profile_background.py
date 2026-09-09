import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from uuid import uuid4

from newsmuncher.services.profile_background import random_nominated_background


class BackgroundTests(unittest.TestCase):
    def test_only_available_nominated_metadata(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            ids = [str(uuid4()) for _ in range(3)]
            for identifier in ids[:2]:
                (directory / f"{identifier}.png").write_bytes(b"test image")
            collection = Mock()
            collection.find.return_value = [
                {"image_url": f"/generated-images/{identifier}.png"} for identifier in ids
            ] + [{"image_url": "/generated-images/../../secret.png"}, {"image_url": None}]
            with patch("newsmuncher.services.profile_background.random.randrange", return_value=0):
                result = random_nominated_background(collection, directory)
            self.assertEqual(result["rewrite_id"], ids[1])
            query, projection = collection.find.call_args.args
            self.assertIs(query["nominated"], True)
            self.assertNotIn("gallery_status", query)
            self.assertEqual(set(projection), {"_id", "image_url", "rewrite_id"})

    def test_empty_or_missing_images(self):
        collection = Mock()
        collection.find.return_value = []
        self.assertIsNone(random_nominated_background(collection))
        collection.find.return_value = [{"image_url": f"/generated-images/{uuid4()}.png"}]
        self.assertIsNone(random_nominated_background(collection))
