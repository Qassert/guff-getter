"""Private Promotion Gallery: stored nominations and assets only."""
import logging
import hashlib
import json
from bson import ObjectId
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
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
def next_item(previous: str | None = None, shown: str | None = None,
              chronological_index: int = Query(0, ge=0, le=3), user=Depends(viewer)):
    shown_ids = tuple(key for key in (shown or '').split(',') if ObjectId.is_valid(key))
    return response(service.select(user['id'], previous, shown_ids, chronological_index))


class Displayed(BaseModel):
    view_token: str = Field(min_length=36, max_length=36)


@router.post('/displayed')
def displayed(payload: Displayed, user=Depends(viewer)):
    return response(service.displayed(user['id'], payload.view_token))


@router.post('/items/{key}/promote')
def promote(key: str, user=Depends(viewer)):
    return response(service.promote(key))


def editor_entry(entry):
    """Read-time text normalisation shared with CREATE; never write Gallery text."""
    from newsmuncher.services.creation_restore import text_fields
    normalized = text_fields(entry)
    owner = entry.get('image_owner') or entry.get('creationUser')
    if (not normalized.get('crazyReplacement1Extract') or
            not isinstance(normalized.get('crazyReplacement1Title'), str)) and owner:
        with store.transaction() as db:
            try:
                from newsmuncher.services.creation_restore import legacy_editor_id
                state = store.read(db, entry.get('rewrite_id') or legacy_editor_id(entry['_id']), owner)
            except (LookupError, PermissionError):
                state = {}
            if str(state.get('entry_id')) == str(entry['_id']):
                cached = text_fields(state.get('result') or {})
                for field in ('crazyReplacement1Title', 'crazyReplacement1Extract'):
                    missing = (not normalized.get(field) if field == 'crazyReplacement1Extract'
                               else not isinstance(normalized.get(field), str))
                    if missing and isinstance(cached.get(field), str):
                        normalized[field] = cached[field]
    return {**entry, **normalized}


@router.get('/items/{key}')
def item(key: str, user=Depends(viewer)):
    return response(service.serialize(editor_entry(service.entry(key))))


def enhancement_revision(entry):
    value = editor_entry(entry)
    text = [value.get('crazyReplacement1Title') or '', value.get('crazyReplacement1Extract') or '']
    return hashlib.sha256(json.dumps(text, ensure_ascii=False).encode()).hexdigest()


class CommitEnhancement(BaseModel):
    confirmed: bool
    revision: str = Field(pattern=r'^[0-9a-f]{64}$')


@router.post('/items/{key}/commit-enhancement')
def commit_enhancement(key: str, payload: CommitEnhancement, user=Depends(viewer)):
    """Explicitly commit only the compatibility metadata approved in the UI."""
    if payload.confirmed is not True:
        raise HTTPException(400, 'Explicit confirmation is required.')
    entry = service.entry(key)
    owner = entry.get('image_owner') or entry.get('creationUser')
    if owner != user['pet']:
        raise HTTPException(403, 'Only this creation’s owner can prepare it for enhancement.')
    if enhancement_revision(entry) != payload.revision:
        raise HTTPException(409, 'Saved story changed; review it again before confirming.')
    try:
        rewrite_id = str(UUID(str(entry.get('rewrite_id'))))
    except (ValueError, TypeError, AttributeError):
        if entry.get('rewrite_id') not in (None, ''):
            raise HTTPException(409, 'Existing media identity is invalid; operator review is required.')
        rewrite_id = str(uuid4())
    from newsmuncher.services.creation_restore import legacy_editor_id, restore_nomination
    previous_state = None
    with store.transaction() as db:
        try:
            candidate = store.read(db, entry.get('rewrite_id') or legacy_editor_id(entry['_id']), owner)
            if str(candidate.get('entry_id')) == str(entry['_id']):
                previous_state = candidate
        except (LookupError, PermissionError):
            pass
    query = {'_id': entry['_id']}
    # Prevent a confirmation from committing over a concurrent edit or owner change.
    for field in ('rewrite_id', 'image_owner', 'creationUser', 'crazyReplacement1Title',
                  'crazyReplacement1Extract', 'result'):
        query[field] = entry[field] if field in entry else {'$exists': False}
    updated = service.entries.update_one(query, {'$set': {
        'rewrite_id': rewrite_id, 'image_owner': owner, 'nominated': True}})
    if updated.matched_count != 1:
        raise HTTPException(409, 'Nomination changed; no compatibility update was committed.')
    if previous_state:
        with store.transaction() as db:
            restore_nomination(service.entry(key), owner, store, db, existing=previous_state)
    return prepare_completion(key, user)


@router.post('/items/{key}/prepare-completion')
def prepare_completion(key: str, user=Depends(viewer)):
    """Prepare a local snapshot only; saved nominations and media are read-only."""
    from newsmuncher.services.creation_restore import restore_nomination, legacy_editor_id
    entry = service.entry(key)
    owner = entry.get('image_owner') or entry.get('creationUser')
    if owner != user['pet']:
        raise HTTPException(403, 'Only this creation’s owner can enhance its media.')
    ready = True
    try:
        rewrite_id = str(UUID(str(entry.get('rewrite_id'))))
    except (ValueError, TypeError, AttributeError):
        rewrite_id = legacy_editor_id(entry['_id'])
        ready = False
    ready = ready and entry.get('nominated') is True and entry.get('image_owner') == owner
    with store.transaction() as db:
        row = db.execute('SELECT state FROM rewrites WHERE id=?', (rewrite_id,)).fetchone()
        existing = None
        if row:
            try:
                existing = store.read(db, rewrite_id, owner)
            except (LookupError, PermissionError):
                raise HTTPException(409, 'Creation identity belongs to another rewrite.') from None
            if str(existing.get('entry_id') or entry['_id']) != str(entry['_id']):
                raise HTTPException(409, 'Creation identity does not match its nomination.')
        restored = restore_nomination(entry, owner, store, db, existing=existing)
    hydrated = service.serialize({**entry, **restored})
    hydrated['can_enhance'] = ready
    if not ready:
        hydrated['enhancement_revision'] = enhancement_revision(entry)
        hydrated['enhancement_error'] = ('This older nomination has no committed media identity. '
            'Its text can be opened with EDIT; ENHANCE stopped without changing the saved record or submitting generation.')
    log.debug('enhance_prepare nomination_id=%s rewrite_id=%s ready=%s', key, rewrite_id, ready)
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
            elif service.owns_video(original) and pingpong.can_attempt(original):
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
            'login_url': (f'/pets/select/{pet_path}?next=%2Fpromotion-gallery%2F' if pet
                          else '/pets/view_pets?next=%2Fpromotion-gallery%2F'),
        }, headers={'Cache-Control': 'private, no-store'})
