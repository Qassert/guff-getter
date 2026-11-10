import pytest

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from newsmuncher.api import build
from newsmuncher.services import build_story


def client():
    app = FastAPI()
    app.include_router(build.router)
    return TestClient(app)


def recipe(**overrides):
    value = {
        'stuff': [{'text': 'Transparent bipolar wrench projector'}],
        'swear': [{'text': 'flap-mouthed bollock merchant'}],
        'modifier': [{'text': 'ceremonially', 'grammar': 'adverb'}],
        'person': [{'text': 'Dame Edith Crumble'}],
        'theme': [{'text': 'a flooded village fete'}],
    }
    value.update(overrides)
    return value


def generation_payload(target=60, **overrides):
    selected_recipe = recipe(**overrides)
    model = build.BuildRecipe.model_validate(selected_recipe)
    return {
        'recipe': selected_recipe,
        'target_words': target,
        'prompt': build.build_story_prompt(
            model, target, build.DEFAULT_BUILD_CREATIVE_PROMPT),
    }


def test_build_generation_uses_approximate_targets_and_accepts_overruns_without_persistence():
    original = build.story_provider
    seen = []
    build.story_provider = lambda prompt, maximum: seen.append((prompt, maximum)) or ' '.join([f'w{i}' for i in range(round(maximum * 0.8) - 1)] + ['Punchline.'])
    try:
        responses = {
            target: client().post('/build/generate', json=generation_payload(target))
            for target in (30, 60, 90)
        }
    finally:
        build.story_provider = original
    assert {target: response.status_code for target, response in responses.items()} == {30: 200, 60: 200, 90: 200}
    assert {target: len(response.json()['story'].split()) for target, response in responses.items()} == {30: 36, 60: 72, 90: 108}
    assert [maximum for _, maximum in seen] == [45, 90, 135]
    for target, (prompt, maximum) in zip((30, 60, 90), seen):
        assert 'Transparent bipolar wrench projector' in prompt
        assert 'flap-mouthed bollock merchant' in prompt
        assert 'dangerously unhinged comedy writer' in prompt
        assert 'raw genetic material for a comedic monstrosity' in prompt
        assert 'Start in the middle of madness' in prompt
        assert 'Finish with a detonation' in prompt
        assert f'Aim for approximately {target} words' in prompt
        assert 'You may go slightly over' in prompt
        assert 'use fewer rather than forcing everything' in prompt
        assert 'never exceeding' not in prompt


def test_build_prompt_omits_empty_categories_instead_of_describing_absences():
    prompt = build.build_story_prompt(build.BuildRecipe.model_validate({
        'stuff': [{'text': 'Leaf trowel espresso machine'}],
        'swear': [{'text': 'Waffle prodder'}],
        'modifier': [{'text': 'Romantically bankrupt'}],
    }), 60, build.DEFAULT_BUILD_CREATIVE_PROMPT)
    assert 'Objects: Leaf trowel espresso machine' in prompt
    assert 'Swear words: Waffle prodder' in prompt
    assert 'Modifiers: Romantically bankrupt' in prompt
    assert 'People:' not in prompt
    assert 'Theme or setting:' not in prompt
    assert 'None selected' not in prompt


def test_build_generation_rejects_empty_and_oversized_payloads():
    empty = client().post('/build/generate', json={**generation_payload(), 'recipe': {}})
    oversized = client().post('/build/generate', json={
        **generation_payload(), 'recipe': {'stuff': [{'text': 'x' * 161}]}})
    assert empty.status_code == 422
    assert oversized.status_code == 422


def test_build_generation_rejects_missing_or_invalid_story_lengths_without_provider_call():
    original = build.story_provider
    provider = MagicMock(return_value='This must not be called.')
    build.story_provider = provider
    try:
        responses = [
            client().post('/build/generate', json={'recipe': recipe()}),
            client().post('/build/generate', json={**generation_payload(), 'target_words': 80}),
            client().post('/build/generate', json={**generation_payload(), 'target_words': 31}),
        ]
    finally:
        build.story_provider = original
    assert all(response.status_code == 422 for response in responses)
    provider.assert_not_called()


def test_build_generation_rejects_blank_or_oversized_edited_prompts():
    blank = client().post('/build/generate', json={
        **generation_payload(), 'prompt': '   '})
    oversized = client().post('/build/generate', json={
        **generation_payload(), 'prompt': 'x' * 10001})
    assert blank.status_code == 422
    assert oversized.status_code == 422


def test_build_generation_reports_timeout_without_losing_recipe():
    original = build.story_provider
    build.story_provider = lambda _prompt, _maximum: (_ for _ in ()).throw(TimeoutError())
    try:
        response = client().post('/build/generate', json=generation_payload())
    finally:
        build.story_provider = original
    assert response.status_code == 504
    assert 'timed out' in response.json()['detail']


def test_provider_reuses_responses_api_model_and_word_limit_without_live_call():
    response = SimpleNamespace(output_text=(
        '{"story":"' + ' '.join(f'word{i}' for i in range(85)) + '",'
        '"headline":"Vicar Detonates Eighty-Five Words Inside A Ceremonial Custard Trousers Inquiry"}'
    ))
    client_mock = MagicMock()
    client_mock.__enter__.return_value = client_mock
    client_mock.responses.create.return_value = response
    with patch.object(build_story, 'OpenAI', return_value=client_mock):
        generated = build_story.generate_build_story('local test prompt', 99)
    call = client_mock.responses.create.call_args.kwargs
    assert call['model'] == 'gpt-6-sol'
    assert call['input'][1] == {'role': 'user', 'content': 'local test prompt'}
    assert 'rather than quoting them in dialogue' in call['input'][0]['content']
    assert 'approximate word target' in call['input'][0]['content']
    assert 'at most' not in call['input'][0]['content']
    assert '12–18-word headline' in call['input'][0]['content']
    assert 'singing or rapping' in call['input'][0]['content']
    assert call['text']['format']['name'] == 'build_story_with_headline'
    assert len(generated['story'].split()) == 85
    assert generated['headline'].startswith('Vicar Detonates')


def test_build_generation_uses_complete_edited_prompt_without_rebuilding_ingredients():
    original = build.story_provider
    seen = []
    build.story_provider = lambda prompt, maximum: seen.append((prompt, maximum)) or 'Edited prompt result.'
    try:
        response = client().post('/build/generate', json={
            **generation_payload(30),
            'prompt': 'Make the replacement gazebo obey malicious pastry physics.\n\n'
                      'Story length: stale instruction',
        })
    finally:
        build.story_provider = original
    assert response.status_code == 200
    assert 'malicious pastry physics' in seen[0][0]
    assert 'Transparent bipolar wrench projector' not in seen[0][0]
    assert 'stale instruction' not in seen[0][0]
    assert 'Aim for approximately 30 words' in seen[0][0]
    assert seen[0][0].count('Story length:') == 1
    assert seen[0][1] == 45


def test_build_draft_is_created_only_by_explicit_nomination_preparation():
    with patch.object(build.store, 'create', return_value={'rewrite_id': 'draft-id'}) as create:
        story = 'An edited story remains the authoritative version.'
        response = client().post('/build/draft', json={
            'story': story,
            'headline': 'Edited Story Becomes Authoritative During A Violent Custard Tribunal',
            'headline_story': story,
        },
                                 cookies={'active_pet': 'builder'})
    assert response.status_code == 200
    assert response.json()['rewrite_id'] == 'draft-id'
    saved, owner = create.call_args.args
    assert owner == 'builder'
    assert saved['crazyReplacement1Extract'] == 'An edited story remains the authoritative version.'
    assert saved['crazyReplacement1Title'] == (
        'Edited Story Becomes Authoritative During A Violent Custard Tribunal')
    assert saved['munge_engine'] == 'build'


def test_build_draft_replaces_stale_or_missing_headline_without_losing_edits():
    edited = ('The edited bishop inflated a municipal badger. '
              'Its trousers were convicted before lunch.')
    for payload in (
        {'story': edited, 'headline': 'Stale headline about another tale',
         'headline_story': 'The original unedited story.'},
        {'story': edited},
        {'story': edited, 'headline': {'invalid': True}},
    ):
        with patch.object(build.store, 'create', return_value={'rewrite_id': 'draft-id'}) as create:
            response = client().post('/build/draft', json=payload,
                                     cookies={'active_pet': 'builder'})
        if isinstance(payload.get('headline'), dict):
            assert response.status_code == 422
            create.assert_not_called()
            continue
        assert response.status_code == 200
        saved = create.call_args.args[0]
        assert saved['crazyReplacement1Extract'] == edited
        assert saved['crazyReplacement1Title'] == (
            'The edited bishop inflated a municipal badger')


def test_generation_bounds_headline_independently_from_story():
    original = build.story_provider
    build.story_provider = lambda _prompt, _maximum: {
        'story': ' '.join([f'story{i}' for i in range(39)] + ['Punchline.']),
        'headline': ' '.join(f'headline{i}' for i in range(30)),
    }
    try:
        response = client().post('/build/generate', json=generation_payload(30))
    finally:
        build.story_provider = original
    assert response.status_code == 200
    assert len(response.json()['story'].split()) == 40
    assert response.json()['story'].endswith('Punchline.')
    assert len(response.json()['headline'].split()) == 18


def test_build_draft_requires_an_active_pet():
    with patch.object(build.store, 'create') as create:
        response = client().post('/build/draft', json={'story': 'Keep this local.'})
    assert response.status_code == 401
    create.assert_not_called()


def test_build_template_has_build_only_footer_override_and_functional_munge():
    template = open('newsmuncher/templates/build.html', encoding='utf-8').read()
    assert '{% block footer %}{% endblock %}' in template
    assert 'data-generate-url="/build/generate"' in template
    assert template.count('data-munge-target=') == 1  # One Jinja loop declaration.
    assert 'for target in (30, 60, 90)' in template
    assert 'MUNGE {{ target }}' in template
    assert 'data-build-result' in template
    assert '>MUNCH</button>' not in template


def test_build_provider_uses_the_same_bounded_nonreasoning_settings_as_create():
    response = SimpleNamespace(status='completed', output=[], output_text='{"story":"The bishop floated away.","headline":"Bishop floats"}')
    mocked = MagicMock()
    mocked.__enter__.return_value = mocked
    mocked.responses.create.return_value = response
    with patch.object(build_story, 'OpenAI', return_value=mocked):
        for maximum in (45, 90, 135):
            result = build_story.generate_build_story('A local prompt', maximum)
            assert result['story'] == 'The bishop floated away.'
    call = mocked.responses.create.call_args.kwargs
    assert call['reasoning'] == {'effort': 'none'}
    assert call['max_output_tokens'] == 750
    assert call['store'] is False
    assert mocked.responses.create.call_count == 3  # One request per MUNGE; no retries.


def test_provider_response_failures_are_safe_and_never_return_partial_stories():
    import pytest
    cases = [
        (SimpleNamespace(status='incomplete', output=[], output_text='{"story":"partial'), 'incomplete', 502),
        (SimpleNamespace(status='completed', output=[SimpleNamespace(content=[SimpleNamespace(type='refusal')])], output_text=''), 'refusal', 422),
        (SimpleNamespace(status='completed', output=[], output_text='not JSON'), 'invalid_json', 502),
        (SimpleNamespace(status='completed', output=[], output_text='[]'), 'invalid_shape', 502),
        (SimpleNamespace(status='completed', output=[], output_text='{"story":{"bad":"shape"}}'), 'empty_story', 502),
        (SimpleNamespace(status='completed', output=[], output_text='{"story":""}'), 'empty_story', 502),
    ]
    for response, code, status in cases:
        mocked = MagicMock()
        mocked.__enter__.return_value = mocked
        mocked.responses.create.return_value = response
        with patch.object(build_story, 'OpenAI', return_value=mocked):
            with pytest.raises(build_story.BuildStoryResponseError) as error:
                build_story.generate_build_story('A local prompt', 66)
        assert error.value.code == code
        assert error.value.status_code == status
        mocked.responses.create.assert_called_once()


def test_provider_rejections_have_actionable_details_without_logging_sensitive_bodies(caplog):
    import httpx
    from openai import APIStatusError
    for status, code, expected in [
        (429, 'insufficient_quota', 'quota or billing restriction'),
        (429, 'rate_limit_exceeded', 'rate-limiting'),
        (404, 'model_not_found', 'model access'),
        (401, 'invalid_api_key', 'credentials'),
        (400, 'unsupported_parameter', 'rejected this request'),
    ]:
        caplog.clear()
        error = APIStatusError('sensitive-provider-message',
            response=httpx.Response(status, request=httpx.Request('POST', 'https://example.test/responses'),
                                    headers={'x-request-id': 'req_test123'}),
            body={'error': {'code': code, 'message': 'sensitive-provider-body'}})
        with patch.object(build, 'story_provider', side_effect=error):
            response = client().post('/build/generate', json=generation_payload())
        assert response.status_code == 502
        assert expected in response.json()['detail']
        assert code in caplog.text
        assert 'req_test123' in caplog.text
        assert 'sensitive-provider' not in caplog.text
        assert 'sensitive-provider' not in response.text


def test_refusal_returns_a_prompt_edit_message_instead_of_generic_bad_gateway():
    error = build_story.BuildStoryResponseError('refusal', 'Edit this prompt. Your recipe is still here.', 422)
    with patch.object(build, 'story_provider', side_effect=error):
        response = client().post('/build/generate', json=generation_payload())
    assert response.status_code == 422
    assert response.json()['detail'] == 'Edit this prompt. Your recipe is still here.'


@pytest.mark.parametrize('code,error_type,expected', [
    ('credit_balance_exhausted', 'insufficient_quota', 'exhausted API credit'),
    ('insufficient_quota', 'insufficient_quota', 'quota or billing restriction'),
    (None, 'insufficient_quota', 'quota or billing restriction'),
    ('organization_spend_limit_exceeded', 'insufficient_quota', 'organisation spending-limit'),
    ('project_spend_limit_exceeded', 'insufficient_quota', 'project spending-limit'),
    ('organization_usage_limit_exceeded', 'insufficient_quota', 'approved usage limit'),
    ('rate_limit_exceeded', 'tokens', 'rate-limiting'),
    (None, 'rate_limit_error', 'rate-limiting'),
    ('slow_down', 'rate_limit_error', 'rate-limiting'),
    ('unknown_provider_error', 'insufficient_quota', 'rejected this request'),
    (None, None, 'rejected this request'),
])
def test_provider_error_classification_preserves_code_type_and_endpoint(code, error_type, expected, caplog):
    import httpx
    from openai import APIStatusError
    error = APIStatusError('sensitive exception text',
        response=httpx.Response(429, request=httpx.Request('POST', 'https://example.test/responses'),
                                headers={'x-request-id': 'req_classification123'}),
        body={'error': {'code': code, 'type': error_type, 'message': 'sensitive body text'}})
    with patch.object(build, 'story_provider', side_effect=error):
        response = client().post('/build/generate', json=generation_payload())
    assert response.status_code == 502
    assert expected in response.json()['detail']
    assert 'Your recipe is still here.' in response.json()['detail']
    assert 'endpoint=/build/generate status=429' in caplog.text
    assert f'code={code or "unavailable"} type={error_type or "unavailable"}' in caplog.text
    assert 'request_id=req_classification123' in caplog.text
    assert 'sensitive' not in caplog.text
    assert 'Transparent bipolar wrench projector' not in caplog.text
    if code != 'credit_balance_exhausted':
        assert 'exhausted API credit' not in response.text
    if code in ('organization_spend_limit_exceeded', 'project_spend_limit_exceeded', 'organization_usage_limit_exceeded'):
        assert 'rate-limiting' not in response.text


@pytest.mark.parametrize('value', ['sk_secret_value', 'sk-secret-value', 'Bearer secret', 'prompt\ntext', {'secret': 'value'}, ['secret']])
def test_provider_diagnostics_redact_non_metadata_values(value):
    assert build.safe_provider_identifier(value) == 'redacted'
    assert build.safe_provider_identifier(value, request_id=True) == 'redacted'


def test_provider_diagnostics_do_not_log_headers_credentials_or_arbitrary_provider_content(caplog):
    import httpx
    from openai import APIStatusError
    error = APIStatusError('sk-secret-exception',
        response=httpx.Response(400, request=httpx.Request('POST', 'https://example.test/responses',
                                    headers={'authorization': 'Bearer sk-secret-header'}),
                                headers={'x-request-id': 'sk-secret-request-id'}),
        body={'code': 'sk-secret-code', 'type': 'user prompt secret', 'message': 'sk-secret-body'})
    with patch.object(build, 'story_provider', side_effect=error):
        response = client().post('/build/generate', json=generation_payload())
    assert response.status_code == 502
    assert 'code=redacted type=redacted request_id=redacted' in caplog.text
    assert 'sk-secret' not in caplog.text
    assert 'user prompt' not in caplog.text
    assert 'sk-secret' not in response.text


@pytest.mark.parametrize('target,words', [(30,34),(60,68),(90,102),(30,45),(60,90),(90,135)])
def test_build_returns_complete_over_target_stories_intact(target, words):
    story = ' '.join(['Story'] * (words - 4) + ['The', 'complete', 'final', 'punchline.'])
    with patch.object(build, 'story_provider', return_value={'story': story, 'headline': 'A retained headline'}):
        response = client().post('/build/generate', json=generation_payload(target))
    assert response.status_code == 200
    assert response.json()['story'] == story
    assert response.json()['story'].endswith('The complete final punchline.')


@pytest.mark.parametrize('target,ceiling', [(30,45),(60,90),(90,135)])
def test_excessive_story_is_rejected_without_returning_a_cut_off_story(target, ceiling):
    story = 'A complete opening sentence. ' + ' '.join(['word'] * ceiling) + ' A complete final punchline.'
    with patch.object(build, 'story_provider', return_value={'story':story,'headline':'Headline'}):
        response = client().post('/build/generate', json=generation_payload(target))
    assert response.status_code == 502
    assert 'excessively long' in response.json()['detail']
    assert 'previous story are still here' in response.json()['detail']
    assert 'story' not in response.json()
    with pytest.raises(build_story.BuildStoryResponseError, match='excessively long'):
        build_story.enforce_word_limit(story, ceiling)


def test_canonical_length_switch_preserves_manual_edits_and_matches_frontend():
    import json
    import subprocess
    original = 'Custom opening.\nKeep my sentence and punchline.\nStory length: Never exceed 33 words.\nCustom ending.'
    js = subprocess.check_output(['node','-e',
        "const b=require('./newsmuncher/static/build-page.js');process.stdout.write(JSON.stringify([30,60,90].map(t=>b.applyStoryLength(" + json.dumps(original) + ",t))));"], text=True)
    for target, frontend in zip((30,60,90), json.loads(js)):
        backend = build.apply_story_length(original, target)
        assert frontend == backend
        assert 'Custom opening.\nKeep my sentence and punchline.\nCustom ending.' in backend
        assert f'Aim for approximately {target} words' in backend
        assert backend.count('Story length:') == 1
        assert 'Never exceed' not in backend
