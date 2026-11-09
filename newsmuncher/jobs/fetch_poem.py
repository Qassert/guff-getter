"""NASA source adapter retained behind the historical POEM teat action."""

import json
import random

import requests

from newsmuncher.config import TEMP_FILE
from newsmuncher.jobs.source_content import get_json, reduce_description, source_session
from newsmuncher.utils.source_preprocessing import preserve_source_text


API_URL = "https://images-api.nasa.gov/search"
SEARCH_TERMS = ("experiment", "prototype", "deployment", "repair", "crew training", "test flight")


def fetch_data(min_words=35):
    """Fetch one descriptive NASA library record and store it temporarily."""
    try:
        with source_session() as client:
            payload = get_json(client, API_URL, params={
                "q": random.choice(SEARCH_TERMS),
                "media_type": "image,video",
                "page_size": 100,
            })
        candidates = []
        for item in payload.get("collection", {}).get("items", []):
            metadata = (item.get("data") or [{}])[0]
            original = metadata.get("description") or metadata.get("description_508") or ""
            if len(original.split()) < min_words:
                continue
            nasa_id = metadata.get("nasa_id")
            title = metadata.get("title")
            if nasa_id and title:
                candidates.append((metadata, original, nasa_id, title))
        if not candidates:
            raise ValueError("NASA returned no sufficiently descriptive records")

        metadata, original, nasa_id, title = random.choice(candidates)
        year = str(metadata.get("date_created") or "")[:4]
        temp_data = {
            "title": preserve_source_text(title),
            "description": "NASA Image and Video Library" + (f" ({year})" if year else ""),
            "extract": preserve_source_text(reduce_description(original)),
            "source_url": f"https://images.nasa.gov/details/{nasa_id}",
            "source_name": "NASA Image and Video Library",
        }
        with open(TEMP_FILE, "w", encoding="utf-8") as target:
            json.dump(temp_data, target, ensure_ascii=False, indent=2)
        return temp_data
    except (requests.RequestException, KeyError, TypeError, ValueError) as error:
        print(f"Could not fetch NASA source content: {error}")
        return None


if __name__ == "__main__":
    raise SystemExit(0 if fetch_data() else 1)
