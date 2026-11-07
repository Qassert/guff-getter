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


def test_build_generation_uses_recipe_without_persistence_and_caps_each_length():
    original = build.story_provider
    seen = []
    build.story_provider = lambda prompt, maximum: seen.append((prompt, maximum)) or ' '.join(f'w{i}' for i in range(120))
    try:
        responses = {
            target: client().post('/build/generate', json=generation_payload(target))
            for target in (30, 60, 90)
        }
    finally:
        build.story_provider = original
    assert {target: response.status_code for target, response in responses.items()} == {30: 200, 60: 200, 90: 200}
    assert {target: len(response.json()['story'].split()) for target, response in responses.items()} == {30: 33, 60: 66, 90: 99}
    assert [maximum for _, maximum in seen] == [33, 66, 99]
    for target, (prompt, maximum) in zip((30, 60, 90), seen):
        assert 'Transparent bipolar wrench projector' in prompt
        assert 'flap-mouthed bollock merchant' in prompt
        assert 'creative seeds rather than mandatory phrases' in prompt
        assert 'Avoid lazy dialogue' in prompt
        assert 'surprising punchline' in prompt
        assert f'Aim for about {target} words' in prompt
        assert f'never exceed {maximum} words' in prompt


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
    response = SimpleNamespace(output_text=' '.join(f'word{i}' for i in range(85)))
    client_mock = MagicMock()
    client_mock.__enter__.return_value = client_mock
    client_mock.responses.create.return_value = response
    with patch.object(build_story, 'OpenAI', return_value=client_mock):
        story = build_story.generate_build_story('local test prompt', 99)
    call = client_mock.responses.create.call_args.kwargs
    assert call['model'] == 'gpt-6-sol'
    assert call['input'][1] == {'role': 'user', 'content': 'local test prompt'}
    assert 'rather than quoting them in dialogue' in call['input'][0]['content']
    assert 'at most 99 words' in call['input'][0]['content']
    assert len(story.split()) == 85


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
    assert 'Aim for about 30 words' in seen[0][0]
    assert seen[0][0].count('Story length:') == 1
    assert seen[0][1] == 33


def test_build_draft_is_created_only_by_explicit_nomination_preparation():
    with patch.object(build.store, 'create', return_value={'rewrite_id': 'draft-id'}) as create:
        response = client().post('/build/draft', json={'story': 'An edited story remains the authoritative version.'},
                                 cookies={'active_pet': 'builder'})
    assert response.status_code == 200
    assert response.json()['rewrite_id'] == 'draft-id'
    saved, owner = create.call_args.args
    assert owner == 'builder'
    assert saved['crazyReplacement1Extract'] == 'An edited story remains the authoritative version.'
    assert saved['munge_engine'] == 'build'


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
