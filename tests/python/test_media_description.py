from copy import deepcopy

from newsmuncher.services.image_generation import (
    build_end_image_prompt, build_image_prompt, safe_provider_failure,
)
from newsmuncher.services.media_description import (
    FALLBACK, VERSION, build_media_description, ensure_media_description,
)
from newsmuncher.services.video_prompt import TRANSFORMATIONS, build_transition_prompt


def test_clean_title_and_body_are_preserved_as_visual_concept():
    description = build_media_description('Moon soup', 'A cat paints the moon beside a library.')
    assert description['version'] == VERSION
    assert description['sanitised'] is False
    assert description['categories'] == []
    assert 'Moon soup' in description['concept']
    assert 'A cat paints the moon' in description['concept']


def test_unsafe_source_uses_standalone_fallback_without_mutating_inputs():
    title = 'Aroused ceremonial machine'
    body = 'A librarian operates a brass filing cabinet in the village hall.'
    original = (title, body)
    description = build_media_description(title, body)
    assert (title, body) == original
    assert description['sanitised'] is True
    assert description['categories'] == ['sexual']
    assert description['concept'] == FALLBACK
    assert 'Aroused' not in description['concept']
    assert 'adult' not in description['concept'].lower()
    assert 'graphic' not in description['concept'].lower()


def test_unsafe_body_and_obfuscated_compounds_are_removed():
    for unsafe in ('shagging organ', 'm! n g e'.replace(' ', ''), 'testicular-chandelier',
                   's.p.u.n.k projector', 'Manboob clotpole'):
        description = build_media_description(
            'Civic appliance', f'A wheelie bin waits in the town hall; the {unsafe} causes a scene.')
        assert description['sanitised'] is True
        assert unsafe not in description['concept']
        assert description['concept'] == FALLBACK


def test_all_unsafe_material_uses_harmless_fallback():
    description = build_media_description('Pornographic contraption', 'The explicit sexual apparatus shags.')
    assert description['concept'] == FALLBACK


def test_durable_description_changes_only_when_nomination_text_changes():
    state = {'result': {'crazyReplacement1Title': 'Moon soup',
                        'crazyReplacement1Extract': 'A cat paints the moon.'}}
    first = ensure_media_description(state)
    assert ensure_media_description(state) is first
    state['result']['crazyReplacement1Extract'] = 'A dog paints the moon.'
    second = ensure_media_description(state)
    assert second['source_hash'] != first['source_hash']
    assert 'dog' in second['concept']


def test_previous_description_version_is_rebuilt_for_safe_retry():
    state = {
        'result': {
            'crazyReplacement1Title': 'Aroused ceremonial machine',
            'crazyReplacement1Extract':
                'A librarian operates a brass filing cabinet in the village hall.',
        },
        'media_description': {
            'version': 'media-safe-v2',
            'concept': 'Replace omitted adult or graphic material.',
            'source_hash': 'old',
        },
    }
    rebuilt = ensure_media_description(state)
    assert rebuilt['version'] == VERSION
    assert 'adult' not in rebuilt['concept'].lower()
    assert 'graphic' not in rebuilt['concept'].lower()


def test_start_end_and_video_prompts_share_concept_style_and_transformation():
    result = {'crazyReplacement1Title': 'Unsafe shagging title',
              'crazyReplacement1Extract': 'A library trolley waits beside a clock.'}
    untouched = deepcopy(result)
    description = build_media_description(result['crazyReplacement1Title'],
                                          result['crazyReplacement1Extract'])
    transformation = TRANSFORMATIONS[2]
    start = build_image_prompt(result, 'Editorial', description)
    end = build_end_image_prompt(result, 'Editorial', media_description=description,
                                 transformation=transformation)
    motion = build_transition_prompt(result, 'Editorial', transformation)
    assert result == untouched
    assert description['concept'] in start and description['concept'] in end
    assert 'Visual style: Editorial.' in start and 'Visual style: Editorial.' in end
    assert transformation['end_direction'] in end
    assert transformation['motion_direction'] in motion
    assert 'shagging' not in start.lower() + end.lower()


def test_sanitised_main_image_request_contains_no_self_described_unsafe_material():
    """Regression for the live moderation-blocked main-image request."""
    result = {'crazyReplacement1Title': 'Aroused ceremonial machine',
              'crazyReplacement1Extract':
                  'A librarian operates a brass filing cabinet in the village hall.'}
    untouched = deepcopy(result)
    description = build_media_description(result['crazyReplacement1Title'],
                                          result['crazyReplacement1Extract'])
    prompt = build_image_prompt(result, 'Editorial', description)
    assert result == untouched
    assert description['sanitised'] is True
    assert FALLBACK in prompt
    assert 'librarian' not in prompt.lower()
    assert all(term not in prompt.lower() for term in (
        'aroused', 'adult material', 'graphic material'))


def test_transformation_catalogue_is_bounded_and_distinct():
    assert len(TRANSFORMATIONS) == 5
    assert len({item['id'] for item in TRANSFORMATIONS}) == len(TRANSFORMATIONS)
    assert all(item['end_direction'] and item['motion_direction'] for item in TRANSFORMATIONS)


def test_provider_diagnostic_omits_request_identifier_and_prompt():
    class Rejection(Exception):
        status_code = 400
        body = {'error': {'code': 'moderation_blocked',
                          'message': 'Rejected req_secret123 safety_violations=[sexual]'}}
    diagnostic = safe_provider_failure(Rejection())
    assert diagnostic['failure_http_status'] == 400
    assert diagnostic['failure_code'] == 'moderation_blocked'
    assert 'req_secret123' not in diagnostic['failure_message']
    assert 'prompt' not in diagnostic
