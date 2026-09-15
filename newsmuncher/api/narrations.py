"""Authenticated narration generation, retrieval and range-capable playback."""
from fastapi import APIRouter, Cookie, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from newsmuncher.api.entries import collection
from newsmuncher.services.narration import service, NarrationError

router = APIRouter(prefix='/narrations', tags=['Narration'])


class NarrationText(BaseModel):
    title: str = Field(min_length=1, max_length=1000)
    body: str = Field(min_length=1, max_length=3500)


def invoke(action, *args):
    try:
        return JSONResponse(action(collection, *args), headers={'Cache-Control': 'no-store'})
    except NarrationError as exc:
        raise HTTPException(exc.status, str(exc)) from exc


@router.get('/')
def saved_narrations(active_pet: str = Cookie(None)):
    return invoke(service.discover, active_pet)


@router.get('/for-rewrite/{rewrite_id}')
def resolve_narration(rewrite_id: str, active_pet: str = Cookie(None)):
    return invoke(service.resolve, rewrite_id, active_pet)


@router.get('/{entry_id}')
def narration_status(entry_id: str, active_pet: str = Cookie(None)):
    return invoke(service.status, entry_id, active_pet)


@router.post('/{entry_id}')
def create_narration(entry_id: str, text: NarrationText, active_pet: str = Cookie(None)):
    return invoke(service.generate, entry_id, active_pet, text.model_dump())


@router.get('/{entry_id}/audio')
def narration_audio(entry_id: str, active_pet: str = Cookie(None)):
    try:
        state = service.status(collection, entry_id, active_pet)
        if not state.get('narration_url'):
            raise NarrationError(404, 'Narration audio unavailable.')
        return FileResponse(service.path(entry_id), media_type='audio/mpeg',
                            headers={'Cache-Control': 'private, no-store'})
    except NarrationError as exc:
        raise HTTPException(exc.status, str(exc)) from exc
