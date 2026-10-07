"""Offline deterministic jingle-plan and contract tests."""
from pathlib import Path
from unittest.mock import patch
import pytest

from newsmuncher.services.jingle_brief import create_jingle_brief
from jingle_service.contract import GenerationRequest


def test_draft_is_rejected_without_external_call():
    with pytest.raises(ValueError):
        create_jingle_brief({'nominated': False})


def test_uses_saved_title_unchanged_and_no_text_model():
    entry = {'nominated': True, 'title': 'SECRET SOURCE',
             'crazyReplacement1Title': 'Teapot town hosts moonlit biscuit parade',
             'crazyReplacement1Extract': 'Body is not sent as lyrics.'}
    with patch('newsmuncher.services.jingle_brief.random.choice', return_value='Funk'):
        brief, usage = create_jingle_brief(entry)
    assert brief.lyrics == entry['crazyReplacement1Title']
    assert brief.duration_seconds == 10
    assert brief.genre_profile.label == 'Funk'
    assert brief.context_adherence == 'high'
    assert usage is None


def test_generation_contract_supports_ten_second_elevenlabs_plan():
    request = GenerationRequest(request_id='12345678-1234-5678-9234-567812345678',
                                music_prompt='Funk', lyrics='Sing this exact headline',
                                duration_seconds=10)
    assert request.duration_seconds == 10


def test_generated_assets_ignored():
    assert '/data/generated_audio/*' in Path('.gitignore').read_text()
