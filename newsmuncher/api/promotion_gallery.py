"""Private Promotion Gallery: stored nominations and assets only."""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from urllib.parse import quote
from newsmuncher.config import TEMPLATES_DIR
from pydantic import BaseModel, Field

from newsmuncher.api.entries import collection, db
from newsmuncher.api.pets import db as pet_db, pets_collection
from newsmuncher.services.gallery_sessions import authenticate, COOKIE
from newsmuncher.services.promotion_gallery import PromotionGallery

router = APIRouter(prefix='/promotion-gallery', tags=['Promotion Gallery'])
service = PromotionGallery(collection, db['promotion_gallery_views'])


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


@router.get('/items/{key}/media/{kind}')
def media(key: str, kind: str, user=Depends(viewer)):
    path = service.media_path(service.entry(key), kind)
    if not path:
        raise HTTPException(404, 'Stored media unavailable.')
    return FileResponse(path, media_type='image/png' if kind == 'image' else 'audio/mpeg',
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
