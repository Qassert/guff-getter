import json
from unittest import mock

import pytest

from newsmuncher.services.jingle_brief import create_jingle_brief, GENRES

# Helper mock response
class MockResponse:
    def __init__(self, output_text="{\"music_prompt\": \"original prompt\", \"lyrics\": \"some lyrics\", \"duration_seconds\": 25}", status="completed"):
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

def test_genre_prefix_and_description(entry, monkeypatch):
    # Force a known genre
    chosen = GENRES[3]  # "Heavy Metal"
    monkeypatch.setattr("random.choice", lambda _: chosen)
    mock_client = make_mock_client()
    monkeypatch.setattr("newsmuncher.services.jingle_brief.OpenAI", lambda *a, **kw: mock_client)
    brief, usage = create_jingle_brief(entry)
    # Expect genre first
    assert brief.music_prompt.startswith(f"{chosen}.")
    # Profile owns sonic conditioning rather than decorative model prose
    assert "original prompt" not in brief.music_prompt
    assert brief.genre_profile.label == chosen
    # Story remains in lyrics rather than dilution of the production caption
    assert "Story subject:" not in brief.music_prompt
    assert brief.genre_profile.cues in brief.music_prompt
    # Confirm genre is from approved list
    assert chosen in GENRES

def test_no_extra_ai_calls(entry, monkeypatch):
    mock_client = make_mock_client()
    monkeypatch.setattr("newsmuncher.services.jingle_brief.OpenAI", lambda *a, **kw: mock_client)
    monkeypatch.setattr("random.choice", lambda _: GENRES[0])
    create_jingle_brief(entry)
    # Only one call to the provider's create method
    assert mock_client.responses.create.call_count == 1

def test_brief_structure(entry, monkeypatch):
    # Ensure the brief contains required fields
    mock_client = make_mock_client()
    monkeypatch.setattr("newsmuncher.services.jingle_brief.OpenAI", lambda *a, **kw: mock_client)
    monkeypatch.setattr("random.choice", lambda _: GENRES[1])
    brief, usage = create_jingle_brief(entry)
    # The brief should be a MusicBrief model; we can check attributes existence
    assert hasattr(brief, "music_prompt")
    assert hasattr(brief, "lyrics")
    assert hasattr(brief, "duration_seconds")
    assert brief.duration_seconds == 25
