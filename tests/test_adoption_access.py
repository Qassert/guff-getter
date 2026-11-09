"""Navigation and adoption redirects use mocked existing pet records only."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.testclient import TestClient
from newsmuncher.api import pets
from newsmuncher.services.adoption_access import AdoptionAccessMiddleware, return_destination


def client():
    app = FastAPI()
    app.add_middleware(AdoptionAccessMiddleware)
    app.mount('/static', StaticFiles(directory='newsmuncher/static'), name='static')
    app.include_router(pets.router, prefix='/pets')
    @app.get('/build')
    @app.get('/promotion-gallery/')
    def page():
        return {'page': 'unchanged'}
    @app.post('/build/generate')
    @app.post('/temp/shizzalise_data')
    def munge(request: Request):
        return {'story': 'existing handler', 'pet': request.cookies.get('active_pet')}
    return TestClient(app)


@pytest.mark.parametrize('destination', ['/build', '/promotion-gallery/', '/pets/pet_profile/cat.jpg', '/create'])
def test_direct_and_repeated_navigation_without_adoption_goes_to_existing_flow(destination):
    browser = client()
    for _ in range(2):  # includes a fresh request/refresh rather than JS-only navigation
        response = browser.get(destination, follow_redirects=False)
        assert response.status_code == 303
        assert response.headers['location'].startswith('/pets/view_pets?next=')
        assert parse_qs(urlsplit(response.headers['location']).query)['next'] == [destination]
        assert response.headers['cache-control'] == 'private, no-store'


@pytest.mark.parametrize('avatar,adopted', [(None, False), ('old.jpg', False), ('cat.jpg', True)])
def test_existing_cookie_is_checked_against_adopted_record(avatar, adopted):
    collection = SimpleNamespace(find_one=AsyncMock(return_value={'avatar': avatar} if adopted else None))
    with patch.object(pets, 'pets_collection', collection):
        browser = client()
        if avatar:
            browser.cookies.set('active_pet', avatar)
        response = browser.get('/build', follow_redirects=False)
    assert response.status_code == (200 if adopted else 303)
    if avatar:
        collection.find_one.assert_awaited_once_with({'avatar': avatar, 'adopted': True})


def test_create_alias_uses_current_pet_and_keeps_draft_query():
    with patch.object(pets, 'pets_collection', SimpleNamespace(find_one=AsyncMock(return_value={'avatar': 'cat.jpg'}))):
        browser = client(); browser.cookies.set('active_pet', 'cat.jpg')
        response = browser.get('/create?rewrite_id=saved', follow_redirects=False)
    assert response.headers['location'] == '/pets/pet_profile/cat.jpg?rewrite_id=saved'


@pytest.mark.parametrize('path', ['/build/generate', '/temp/shizzalise_data'])
def test_late_missing_adoption_does_not_run_munge_or_follow_redirect(path):
    response = client().post(path, json={'prompt': 'keep this'})
    assert response.status_code == 401
    assert response.json()['adoption_url'].startswith('/pets/view_pets?next=')
    assert 'story' not in response.json()


def test_status_never_stores_an_alternate_adoption_cookie_and_db_errors_do_not_redirect():
    response = client().get('/pets/adoption-status?next=/build')
    assert response.json() == {'adopted': False, 'adoption_url': '/pets/view_pets?next=%2Fbuild'}
    assert 'set-cookie' not in response.headers
    with patch.object(pets, 'pets_collection', SimpleNamespace(find_one=AsyncMock(side_effect=RuntimeError('offline')))):
        browser = client(); browser.cookies.set('active_pet', 'cat.jpg')
        response = browser.get('/build', follow_redirects=False)
    assert response.status_code == 503
    assert 'location' not in response.headers


@pytest.mark.parametrize('value', ['https://evil.test', '//evil.test', '/%2fevil.test', '/\\evil.test', '/pets/view_pets', '/build%0d%0aLocation:x', '//['])
def test_return_destination_rejects_external_or_looping_targets(value):
    assert return_destination(value) == '/create'


@pytest.mark.parametrize('adopt', [True, False])
def test_successful_adoption_or_existing_pet_login_returns_to_original_page(adopt):
    pet = {'avatar': 'cat.jpg', 'name': 'Cat', 'password': 'hash', 'adopted': not adopt}
    collection = SimpleNamespace(find_one=AsyncMock(side_effect=[pet, None] if adopt else [pet]),
        create_index=AsyncMock(), update_one=AsyncMock(return_value=SimpleNamespace(matched_count=1)))
    with patch.object(pets, 'pets_collection', collection), patch.object(pets, 'issue_session', AsyncMock()) as issue, \
         patch.object(pets, 'get_password_hash', return_value='hash'), patch.object(pets, 'verify_password', return_value=True):
        route = 'adopt_pet' if adopt else 'use_pet'
        response = client().post(f'/pets/{route}/cat.jpg?next=%2Fbuild',
            data={'name': 'Cat', 'password': 'pass', 'confirm_password': 'pass'}, follow_redirects=False)
    assert response.status_code == 303
    assert response.headers['location'] == '/build'
    assert 'active_pet=cat.jpg' in response.headers['set-cookie']
    issue.assert_awaited_once()


def test_validation_failure_retains_return_destination_and_explanation():
    response = client().post('/pets/adopt_pet/cat.jpg?next=%2Fbuild',
        data={'name': 'Cat', 'password': 'one', 'confirm_password': 'two'})
    assert response.status_code == 200
    assert 'Passwords do not match' in response.text
    assert 'next=/build' in response.text or 'next=%2Fbuild' in response.text
    assert 'return you to your work' in response.text


def test_existing_authenticated_session_recovers_active_pet_without_new_adoption():
    from newsmuncher.services import gallery_sessions
    with patch.object(gallery_sessions, 'authenticate', AsyncMock(return_value={'pet': 'cat.jpg'})) as authenticate:
        browser = client(); browser.cookies.set('gallery_session', 'valid-session')
        response = browser.get('/pets/adoption-status?next=/build')
    assert response.json()['adopted'] is True
    assert 'active_pet=cat.jpg' in response.headers['set-cookie']
    authenticate.assert_awaited_once()


def test_late_build_failure_keeps_the_build_return_destination():
    response = client().post('/build/generate', json={})
    assert response.json()['adoption_url'] == '/pets/view_pets?next=%2Fbuild'


def test_pet_selection_page_is_not_guarded_and_explains_return_flow():
    class Cursor:
        async def to_list(self, _):
            return [{'avatar': 'cat.jpg', 'adopted': False}]
    with patch.object(pets, 'pets_collection', SimpleNamespace(find=lambda: Cursor())):
        response = client().get('/pets/view_pets?next=%2Fbuild')
    assert response.status_code == 200
    assert 'After adoption or sign-in' in response.text
    assert '/pets/select/cat.jpg?next=/build' in response.text


def test_existing_session_is_reused_by_legacy_munge_handlers():
    from newsmuncher.services import gallery_sessions
    with patch.object(gallery_sessions, 'authenticate', AsyncMock(return_value={'pet': 'cat.jpg'})):
        browser = client(); browser.cookies.set('gallery_session', 'valid-session')
        response = browser.post('/temp/shizzalise_data', json={})
    assert response.status_code == 200
    assert response.json()['pet'] == 'cat.jpg'
    assert 'active_pet=cat.jpg' in response.headers['set-cookie']


def test_create_return_uses_the_pet_just_adopted_or_signed_in():
    assert return_destination('/pets/pet_profile/old.jpg?rewrite_id=kept', 'new.jpg') == '/pets/pet_profile/new.jpg?rewrite_id=kept'


def test_existing_gallery_authorisation_stays_intact_and_login_returns_to_gallery():
    from fastapi import HTTPException
    from newsmuncher.api import promotion_gallery
    app = FastAPI()
    app.add_middleware(AdoptionAccessMiddleware)
    app.mount('/static', StaticFiles(directory='newsmuncher/static'), name='static')
    app.include_router(promotion_gallery.router)
    with patch.object(pets, 'pets_collection', SimpleNamespace(find_one=AsyncMock(return_value={'avatar': 'cat.jpg'}))), \
         patch.object(promotion_gallery, 'authenticate', AsyncMock(side_effect=HTTPException(401, 'Sign in'))):
        browser = TestClient(app); browser.cookies.set('active_pet', 'cat.jpg')
        response = browser.get('/promotion-gallery/')
    assert response.status_code == 200
    assert 'Your private collection awaits' in response.text
    assert '/pets/select/cat.jpg?next=%2Fpromotion-gallery%2F' in response.text
    assert 'id="galleryPage"' not in response.text


@pytest.mark.parametrize('path', ['/build', '/pets/pet_profile/cat.jpg', '/promotion-gallery/'])
def test_real_application_registers_guard_before_main_navigation_routes(path):
    from newsmuncher.main import app
    response = TestClient(app).get(path, follow_redirects=False)
    assert response.status_code == 303
    assert response.headers['location'].startswith('/pets/view_pets?next=')
