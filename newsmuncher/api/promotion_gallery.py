"""Private Promotion Gallery: stored nominations and assets only."""
import logging
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from urllib.parse import quote
from uuid import UUID, uuid4
from newsmuncher.config import TEMPLATES_DIR
from pydantic import BaseModel, Field

from newsmuncher.api.entries import collection, db
from newsmuncher.api.pets import db as pet_db, pets_collection
from newsmuncher.services.gallery_sessions import authenticate, COOKIE
from newsmuncher.services.promotion_gallery import PromotionGallery
from newsmuncher.services.image_generation import store, IMAGE_FIELDS
from newsmuncher.services.video_pingpong import service as pingpong

router = APIRouter(prefix='/promotion-gallery', tags=['Promotion Gallery'])
service = PromotionGallery(collection, db['promotion_gallery_views'])
log = logging.getLogger(__name__)


async def viewer(request: Request):
    if request.method != 'GET':
        # A custom header forces cross-origin browsers through a denied CORS preflight.
        if request.headers.get('X-Gallery-Request') != '1':
            raise HTTPException(403, 'Same-origin gallery request required.')
        origin = request.headers.get('origin')
        if origin and origin != str(request.base_url).rstrip('/'):
            raise HTTPException(403, 'Same-origin gallery request required.')
    return await authenticate(pet_db['gallery_sessions'], pets_collection, request.cookies.get(COOKIE))


def response(value):
    return JSONResponse(value, headers={'Cache-Control': 'private, no-store'})


@router.get('/next')
def next_item(previous: str | None = None, user=Depends(viewer)):
    return response(service.select(user['id'], previous))


class Displayed(BaseModel):
    view_token: str = Field(min_length=36, max_length=36)


@router.post('/displayed')
def displayed(payload: Displayed, user=Depends(viewer)):
    return response(service.displayed(user['id'], payload.view_token))


@router.post('/items/{key}/promote')
def promote(key: str, user=Depends(viewer)):
    return response(service.promote(key))


@router.get('/items/{key}')
def item(key: str, user=Depends(viewer)):
    return response(service.serialize(service.entry(key)))


@router.post('/items/{key}/prepare-completion')
def prepare_completion(key: str, user=Depends(viewer)):
    """Give an owner-matched legacy nomination one durable modern rewrite identity."""
    entry = service.entry(key)
    owner = entry.get('image_owner') or entry.get('creationUser')
    if owner != user['pet']:
        raise HTTPException(403, 'Only this creation’s owner can complete its media.')
    try:
        rewrite_id = str(UUID(str(entry.get('rewrite_id'))))
    except (ValueError, TypeError, AttributeError):
        candidate = str(uuid4())
        service.entries.update_one({'_id': entry['_id'], '$or': [
            {'rewrite_id': {'$exists': False}}, {'rewrite_id': None}, {'rewrite_id': ''}
        ]}, {'$set': {'rewrite_id': candidate, 'image_owner': owner}})
        entry = service.entry(key)
        try:
            rewrite_id = str(UUID(str(entry.get('rewrite_id'))))
        except (ValueError, TypeError, AttributeError):
            raise HTTPException(409, 'Creation identity could not be prepared safely.') from None
    # Gallery historically treated crazyReplacement1done as nominated. Modern media
    # services require the equivalent explicit flag and owner on the same Mongo item.
    service.entries.update_one({'_id': entry['_id'], 'rewrite_id': rewrite_id}, {'$set': {
        'nominated': True, 'image_owner': owner
    }})
    entry = service.entry(key)
    result = {
        'rewrite_id': rewrite_id,
        'crazyReplacement1Title': entry.get('crazyReplacement1Title') or '',
        'crazyReplacement1Extract': entry.get('crazyReplacement1Extract') or '',
        'creationUser': owner,
        'nominated': True,
    }
    result.update({field: entry.get(field) for field in IMAGE_FIELDS if entry.get(field) is not None})
    with store.transaction() as rewrite_db:
        row = rewrite_db.execute('SELECT state FROM rewrites WHERE id=?', (rewrite_id,)).fetchone()
        if row:
            try:
                state = store.read(rewrite_db, rewrite_id, owner)
            except (LookupError, PermissionError):
                raise HTTPException(409, 'Creation identity belongs to another rewrite.') from None
            if str(state.get('entry_id') or entry['_id']) != str(entry['_id']):
                raise HTTPException(409, 'Creation identity does not match its nomination.')
            changed = False
            if not state.get('entry_id'):
                state['entry_id'] = str(entry['_id'])
                changed = True
            stored_result = state.setdefault('result', {})
            for field, value in result.items():
                if field not in stored_result and value is not None:
                    stored_result[field] = value
                    changed = True
            if changed:
                store.save(rewrite_db, rewrite_id, state)
        else:
            state = {'owner': owner, 'entry_id': str(entry['_id']), 'result': result}
            store.save(rewrite_db, rewrite_id, state)
    # A historical SQLite rewrite may retain title/body that its older Mongo adapter
    # omitted. Restore only genuinely absent fields; never replace persisted text.
    stored_result = state.get('result') or {}
    for field in ('crazyReplacement1Title', 'crazyReplacement1Extract'):
        value = stored_result.get(field)
        current = entry.get(field)
        if (not isinstance(current, str) or not current.strip()) and isinstance(value, str) and value.strip():
            service.entries.update_one({'_id': entry['_id'], 'rewrite_id': rewrite_id, '$or': [
                {field: {'$exists': False}}, {field: None}, {field: ''}
            ]}, {'$set': {field: value}})
    entry = service.entry(key)
    hydrated = service.serialize(entry)
    log.info('[complete] %s hydrate: ready; image=%s; title=%s; body=%s', rewrite_id,
             'existing' if hydrated.get('image_url') else 'missing',
             'existing' if (entry.get('crazyReplacement1Title') or '').strip() else 'missing',
             'existing' if (entry.get('crazyReplacement1Extract') or '').strip() else 'missing')
    return response(hydrated)


@router.get('/items/{key}/media/{kind}')
def media(key: str, kind: str, background_tasks: BackgroundTasks, user=Depends(viewer)):
    entry = service.entry(key)
    path = service.media_path(entry, kind)
    if not path:
        raise HTTPException(404, 'Stored media unavailable.')
    if kind == 'video':
        original = service.original_video_path(entry)
        if original:
            rewrite_id = original.stem
            log.info('[pingpong] %s original found', rewrite_id)
            if path != original:
                log.info('[pingpong] %s serving derivative', rewrite_id)
            elif pingpong.can_attempt(original):
                log.info('[pingpong] %s derivative missing - scheduling', rewrite_id)
                # Serve the original immediately. A later request transparently receives
                # the completed local derivative through a versioned authenticated URL.
                background_tasks.add_task(pingpong.derive, original)
            else:
                reason = pingpong.failure_reason(original)
                if reason:
                    log.warning('[pingpong] %s derivation failed: %s', rewrite_id, reason)
    return FileResponse(path, media_type={'image': 'image/png', 'video': 'video/mp4'}.get(kind, 'audio/mpeg'),
                        headers={'Cache-Control': 'private, no-store'})


@router.get('/')
async def gallery_page(request: Request):
    try:
        user = await viewer(request)
    except HTTPException as exc:
        if exc.status_code != 401:
            raise
        user = None
    pet = user['pet'] if user else request.cookies.get('active_pet', '')
    pet_path = quote(pet, safe='')
    return Jinja2Templates(directory=TEMPLATES_DIR).TemplateResponse(
        request=request, name='promotion_gallery.html', context={
            'signed_in': user is not None,
            'creation_url': f'/pets/pet_profile/{pet_path}' if user else '/pets/view_pets',
            'login_url': f'/pets/select/{pet_path}' if pet else '/pets/view_pets',
        }, headers={'Cache-Control': 'private, no-store'})
