"""Hacker News source adapter retained behind the historical PEOPLE action."""

import json
import random

import requests

from newsmuncher.config import TEMP_FILE
from newsmuncher.jobs.source_content import get_json, plain_text, reduce_description, source_session
from newsmuncher.utils.source_preprocessing import preserve_source_text


API_ROOT = "https://hacker-news.firebaseio.com/v0"


def fetch_data(min_words=30, max_candidates=10):
    """Fetch a descriptive Ask HN text submission from the official API."""
    try:
        with source_session() as client:
            item_ids = get_json(client, f"{API_ROOT}/askstories.json")
            if not isinstance(item_ids, list):
                raise ValueError("Hacker News returned an invalid story list")
            candidates = list(item_ids[:80])
            random.shuffle(candidates)
            for item_id in candidates[:max_candidates]:
                item = get_json(client, f"{API_ROOT}/item/{item_id}.json")
                original = item.get("text") if isinstance(item, dict) else ""
                if len(plain_text(original).split()) < min_words:
                    continue
                title = item.get("title")
                if not title:
                    continue
                temp_data = {
                    "title": preserve_source_text(title),
                    "description": "Hacker News user submission (reuse rights unconfirmed)",
                    "extract": preserve_source_text(reduce_description(original)),
                    "source_url": f"https://news.ycombinator.com/item?id={item_id}",
                    "source_name": "Hacker News",
                    "source_author": item.get("by"),
                }
                with open(TEMP_FILE, "w", encoding="utf-8") as target:
                    json.dump(temp_data, target, ensure_ascii=False, indent=2)
                return temp_data
        raise ValueError("Hacker News returned no sufficiently descriptive Ask HN submissions")
    except (requests.RequestException, KeyError, TypeError, ValueError) as error:
        print(f"Could not fetch Hacker News source content: {error}")
        return None


if __name__ == "__main__":
    raise SystemExit(0 if fetch_data() else 1)
