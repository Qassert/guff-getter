import json
from unittest.mock import MagicMock, patch

import pytest
import requests

from newsmuncher.jobs import fetch_historical_funny, fetch_people, fetch_poem
from newsmuncher.jobs.source_content import get_json, plain_text, reduce_description


class Client:
    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None


def test_reducer_strips_html_decodes_entities_and_keeps_short_text():
    assert plain_text("<p>Tea &amp; toast</p>  \n <b>now</b>") == "Tea & toast now"
    assert reduce_description("A short sentence. Another one.") == "A short sentence. Another one."


def test_reducer_keeps_ordered_sentences_near_eighty_words():
    sentences = [" ".join([f"s{index}"] * 18) + "." for index in range(6)]
    result = reduce_description(" ".join(sentences))
    assert result.split()[0] == "s0"
    assert 80 <= len(result.split()) <= 100
    assert "s4" in result and "s5" not in result


def test_reducer_bounds_one_exceptionally_long_sentence():
    result = reduce_description(" ".join(f"word{i}" for i in range(140)) + ".")
    assert len(result.split()) == 80
    assert result.endswith("…")


def test_rate_limit_honours_retry_after_once():
    limited = MagicMock(status_code=429, headers={"Retry-After": "2"})
    success = MagicMock(status_code=200, headers={})
    success.json.return_value = {"ok": True}
    client = MagicMock()
    client.get.side_effect = [limited, success]
    with patch("newsmuncher.jobs.source_content.time.sleep") as sleep:
        assert get_json(client, "https://example.test") == {"ok": True}
    sleep.assert_called_once_with(2.0)
    assert client.get.call_count == 2


def test_rate_limit_does_not_wait_beyond_request_budget():
    limited = MagicMock(status_code=429, headers={"Retry-After": "60"})
    client = MagicMock(); client.get.return_value = limited
    with pytest.raises(requests.HTTPError), patch("newsmuncher.jobs.source_content.time.sleep") as sleep:
        get_json(client, "https://example.test")
    sleep.assert_not_called()


def test_nasa_adapter_preserves_title_url_and_reduces_description(tmp_path):
    long_text = " ".join(("Sentence " + "word " * 19 + ".") for _ in range(6))
    payload = {"collection": {"items": [{"data": [{
        "nasa_id": "ABC123", "title": "Inflatable contraption",
        "date_created": "2026-01-02T00:00:00Z", "description": long_text,
    }]}]}}
    with patch.object(fetch_poem, "TEMP_FILE", tmp_path / "source.json"), \
         patch.object(fetch_poem, "source_session", return_value=Client()), \
         patch.object(fetch_poem, "get_json", return_value=payload):
        result = fetch_poem.fetch_data()
    assert result["title"] == "Inflatable contraption"
    assert result["source_url"] == "https://images.nasa.gov/details/ABC123"
    assert 80 <= len(result["extract"].split()) <= 100
    assert json.loads((tmp_path / "source.json").read_text()) == result


def test_hacker_news_adapter_strips_html_and_flags_reuse_rights(tmp_path):
    item = {"id": 42, "title": "Ask HN: Odd machinery", "by": "writer",
            "text": "<p>" + " ".join(f"word{i}" for i in range(120)) + "</p>"}
    def response(_client, url, **_kwargs):
        return [42] if url.endswith("askstories.json") else item
    with patch.object(fetch_people, "TEMP_FILE", tmp_path / "source.json"), \
         patch.object(fetch_people, "source_session", return_value=Client()), \
         patch.object(fetch_people, "get_json", side_effect=response):
        result = fetch_people.fetch_data()
    assert result["source_url"].endswith("item?id=42")
    assert result["source_author"] == "writer"
    assert "reuse rights unconfirmed" in result["description"]
    assert "<p>" not in result["extract"] and len(result["extract"].split()) == 80


def test_openalex_adapter_reconstructs_abstract_and_keeps_cc0_attribution(tmp_path):
    words = [f"word{i}" for i in range(120)]
    work = {"id": "https://openalex.org/W1", "doi": "https://doi.org/10.1/test",
            "display_name": "A peculiar apparatus", "publication_year": 2025,
            "type": "article", "abstract_inverted_index": {word: [i] for i, word in enumerate(words)}}
    with patch.object(fetch_historical_funny, "TEMP_FILE", tmp_path / "source.json"), \
         patch.object(fetch_historical_funny, "source_session", return_value=Client()), \
         patch.object(fetch_historical_funny, "get_json", return_value={"results": [work]}):
        result = fetch_historical_funny.fetch_historical_funny_from_api("dating")
    assert result["title"] == "A peculiar apparatus"
    assert result["source_url"] == "https://doi.org/10.1/test"
    assert result["source_licence"].startswith("CC0")
    assert len(result["extract"].split()) == 80


def test_drivel_path_remains_on_reusable_api(tmp_path):
    response = MagicMock()
    response.json.return_value = [{"id": "one", "title": "Drivel", "description": "Old",
                                   "extract": "Story", "numberOftimesUsed": 0}]
    response.raise_for_status.return_value = None
    with patch.object(fetch_historical_funny, "TEMP_FILE", tmp_path / "source.json"), \
         patch.object(fetch_historical_funny.requests, "get", return_value=response), \
         patch.object(fetch_historical_funny.requests, "put", return_value=response):
        result = fetch_historical_funny.fetch_historical_funny_from_api()
    assert result == {"title": "Drivel", "description": "Old", "extract": "Story"}
