"""Shared navigation guard using the existing active-pet/adoption records."""
from urllib.parse import quote, urlsplit, unquote
from http.cookies import SimpleCookie

from fastapi import HTTPException
from fastapi.responses import JSONResponse, RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware


def return_destination(value, avatar=None):
    """Allow only local mode pages, never arbitrary or protocol-relative URLs."""
    value = value or '/create'
    try:
        parsed = urlsplit(value)
    except ValueError:
        return '/create'
    decoded = unquote(value)
    if (parsed.scheme or parsed.netloc or not value.startswith('/') or
            decoded.startswith('//') or '\\' in decoded or
            any(ord(c) < 32 for c in decoded)):
        return '/create'
    if parsed.path in ('/create', '/build', '/promotion-gallery', '/promotion-gallery/'):
        return value
    if parsed.path.startswith('/pets/pet_profile/') and parsed.path.count('/') == 3:
        if avatar:
            return ('/pets/pet_profile/' + quote(avatar, safe='') +
                    ('?' + parsed.query if parsed.query else '') +
                    ('#' + parsed.fragment if parsed.fragment else ''))
        return value
    return '/create'


def adoption_url(destination):
    return '/pets/view_pets?next=' + quote(return_destination(destination), safe='')


async def adopted_pet(request):
    # Import lazily to reuse the same collection without a circular router import.
    from newsmuncher.api.pets import pets_collection, db
    from newsmuncher.services.gallery_sessions import authenticate, COOKIE
    avatar = request.cookies.get('active_pet')
    if avatar:
        pet = await pets_collection.find_one({'avatar': avatar, 'adopted': True})
        if pet:
            return pet['avatar']
    # A still-valid existing login session must not require another adoption.
    if request.cookies.get(COOKIE):
        try:
            user = await authenticate(db['gallery_sessions'], pets_collection, request.cookies[COOKIE])
            return user['pet']
        except HTTPException as exc:
            if exc.status_code != 401:
                raise
    return None


class AdoptionAccessMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        path = request.url.path
        page = request.method == 'GET' and (
            path in ('/create', '/build', '/promotion-gallery', '/promotion-gallery/') or
            path.startswith('/pets/pet_profile/'))
        status = request.method == 'GET' and path == '/pets/adoption-status'
        munge = request.method == 'POST' and path in (
            '/build/generate', '/build/draft', '/temp/shizzalise_data')
        if not (page or status or munge):
            return await call_next(request)
        headers = {'Cache-Control': 'private, no-store'}
        try:
            pet = await adopted_pet(request)
        except Exception:
            return JSONResponse({'detail': 'Could not check your pet. Your work is safe; please retry.'},
                                status_code=503, headers=headers)
        destination = (str(request.url.path) + ('?' + request.url.query if request.url.query else ''))
        def complete(response):
            if pet and pet != request.cookies.get('active_pet'):
                response.set_cookie('active_pet', pet, httponly=True, max_age=86400,
                                    secure=request.url.scheme == 'https', samesite='strict')
            return response
        if status:
            return complete(JSONResponse({'adopted': bool(pet),
                'adoption_url': adoption_url(request.query_params.get('next'))}, headers=headers))
        if not pet:
            target = adoption_url(destination if page else (request.query_params.get('next') or
                ('/build' if path.startswith('/build') else '/create')))
            if page:
                return RedirectResponse(target, status_code=303, headers=headers)
            return JSONResponse({'detail': 'Adopt or sign in to your pet before MUNGE. Your current work remains on this page.',
                                 'adoption_url': target}, status_code=401, headers=headers)
        if path == '/create':
            query = '?' + request.url.query if request.url.query else ''
            return complete(RedirectResponse('/pets/pet_profile/' + quote(pet, safe='') + query,
                                    status_code=303, headers=headers))
        if pet != request.cookies.get('active_pet'):
            # Reuse an authenticated existing session for legacy downstream handlers
            # that still read active_pet directly. No new identity state is introduced.
            cookie = SimpleCookie()
            cookie['active_pet'] = pet
            value = request.headers.get('cookie', '') + '; ' + cookie.output(header='').strip()
            request.scope['headers'] = [(key, val) for key, val in request.scope['headers']
                                        if key.lower() != b'cookie'] + [(b'cookie', value.lstrip('; ').encode('latin-1'))]
        response = await call_next(request)
        response.headers.update(headers)
        return complete(response)
