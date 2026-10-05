import pytest
from newsmuncher.services.jingle_brief import create_jingle_brief, GENRES
from jingle_service.genres import GENRE_PROFILES

@pytest.fixture
def entry():
    return {'nominated': True, 'crazyReplacement1Title':
            'Local badger trains furious seagull to steal parking tickets while delighted tourists cheer'}

def test_saved_title_is_exact_lyric_without_text_model_call(entry, monkeypatch):
    monkeypatch.setattr('newsmuncher.services.jingle_brief.random.choice', lambda pool: 'Funk')
    brief, usage = create_jingle_brief(entry)
    assert brief.lyrics == entry['crazyReplacement1Title']
    assert usage is None
    assert brief.duration_seconds == 10
    assert brief.context_adherence == 'high'
    assert brief.genre_profile == GENRE_PROFILES['Funk']
    assert 'Funk' in brief.positive_styles
    assert any('immediate clear lead vocal' in style for style in brief.positive_styles)
    assert 'instrumental-only' in brief.negative_styles

@pytest.mark.parametrize('selected', GENRES)
def test_existing_random_genre_pool_maps_to_elevenlabs_styles(entry, monkeypatch, selected):
    monkeypatch.setattr('newsmuncher.services.jingle_brief.random.choice', lambda pool: selected)
    brief, _ = create_jingle_brief(entry)
    assert brief.genre_profile == GENRE_PROFILES[selected]
    assert selected in brief.positive_styles
    assert brief.music_prompt == GENRE_PROFILES[selected].caption()

def test_rejects_non_nominated_or_missing_title():
    with pytest.raises(ValueError): create_jingle_brief({'nominated': False, 'crazyReplacement1Title': 'x'})
    with pytest.raises(ValueError): create_jingle_brief({'nominated': True, 'crazyReplacement1Title': ''})
