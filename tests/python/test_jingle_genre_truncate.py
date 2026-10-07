import pytest

from newsmuncher.services.jingle_brief import create_jingle_brief, GENRES

@pytest.fixture
def entry():
    return {
        "nominated": True,
        "crazyReplacement1Title": "Test Title",
        "crazyReplacement1Extract": "Test body of the rewritten article.",
    }

def test_body_is_never_included_in_deterministic_music_plan(entry, monkeypatch):
    # Force a known genre
    chosen = GENRES[0]
    monkeypatch.setattr("random.choice", lambda _: chosen)
    # Very long body to exceed the limit
    long_body = "A" * 2000
    entry["crazyReplacement1Extract"] = long_body
    brief, usage = create_jingle_brief(entry)
    # Ensure final prompt does not exceed safe limit (575 chars)
    assert len(brief.music_prompt) <= 575
    # Genre must still be first
    assert brief.music_prompt.startswith(f"{chosen}.")
    assert brief.genre_profile.cues in brief.music_prompt
    # The story description should be truncated (cannot contain the full long body)
    assert long_body[:10] not in brief.music_prompt
    assert brief.lyrics == entry['crazyReplacement1Title']
    assert usage is None
