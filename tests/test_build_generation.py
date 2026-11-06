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


def test_build_generation_uses_recipe_without_persistence_and_caps_response():
    original = build.story_provider
    seen = []
    build.story_provider = lambda prompt: seen.append(prompt) or ' '.join(f'w{i}' for i in range(95))
    try:
        response = client().post('/build/generate', json={'recipe': recipe()})
    finally:
        build.story_provider = original
    assert response.status_code == 200
    assert len(response.json()['story'].split()) == 80
    assert 'Transparent bipolar wrench projector' in seen[0]
    assert 'flap-mouthed bollock merchant' in seen[0]
    assert 'creative seeds rather than mandatory phrases' in seen[0]
    assert 'Avoid lazy dialogue' in seen[0]
    assert 'surprising punchline' in seen[0]
    assert 'never exceed 80 words' in seen[0]


def test_build_generation_rejects_empty_and_oversized_payloads():
    empty = client().post('/build/generate', json={'recipe': {}})
    oversized = client().post('/build/generate', json={'recipe': {'stuff': [{'text': 'x' * 161}]}})
    assert empty.status_code == 422
    assert oversized.status_code == 422


def test_build_generation_reports_timeout_without_losing_recipe():
    original = build.story_provider
    build.story_provider = lambda _prompt: (_ for _ in ()).throw(TimeoutError())
    try:
        response = client().post('/build/generate', json={'recipe': recipe()})
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
        story = build_story.generate_build_story('local test prompt')
    call = client_mock.responses.create.call_args.kwargs
    assert call['model'] == 'gpt-6-sol'
    assert call['input'][1] == {'role': 'user', 'content': 'local test prompt'}
    assert 'rather than quoting them in dialogue' in call['input'][0]['content']
    assert len(story.split()) == 80


def test_build_template_has_build_only_footer_override_and_functional_munge():
    template = open('newsmuncher/templates/build.html', encoding='utf-8').read()
    assert '{% block footer %}{% endblock %}' in template
    assert 'data-generate-url="/build/generate"' in template
    assert '>MUNGE</button>' in template
    assert 'data-build-result' in template
    assert '>MUNCH</button>' not in template
