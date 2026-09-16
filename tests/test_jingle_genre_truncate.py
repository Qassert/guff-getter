import json
from unittest import mock
import pytest

from newsmuncher.services.jingle_brief import create_jingle_brief, GENRES

# Helper mock response (same as existing)
class MockResponse:
    def __init__(self, output_text='{"music_prompt": "original prompt", "lyrics": "some lyrics", "duration_seconds": 25}', status='completed'):
        self.output_text = output_text
        self.status = status
        self.usage = mock.Mock(input_tokens=10, output_tokens=20)
        self.model = "mock-model"

def make_mock_client(mock_resp=None):
    mock_client = mock.MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = None
    mock_client.responses.create.return_value = mock_resp or MockResponse()
    return mock_client

@pytest.fixture
def entry():
    return {
        "nominated": True,
        "crazyReplacement1Title": "Test Title",
        "crazyReplacement1Extract": "Test body of the rewritten article.",
    }

def test_prompt_length_limit(entry, monkeypatch):
    # Force a known genre
    chosen = GENRES[0]
    monkeypatch.setattr("random.choice", lambda _: chosen)
    # Very long body to exceed the limit
    long_body = "A" * 2000
    entry["crazyReplacement1Extract"] = long_body
    mock_client = make_mock_client()
    monkeypatch.setattr("newsmuncher.services.jingle_brief.OpenAI", lambda *a, **kw: mock_client)
    brief, usage = create_jingle_brief(entry)
    # Ensure final prompt does not exceed safe limit (575 chars)
    assert len(brief.music_prompt) <= 575
    # Genre must still be first
    assert brief.music_prompt.startswith(f"{chosen}.")
    # Original AI prompt must still be present
    assert "original prompt" not in brief.music_prompt
    assert brief.genre_profile.cues in brief.music_prompt
    # The story description should be truncated (cannot contain the full long body)
    assert long_body[:10] not in brief.music_prompt
