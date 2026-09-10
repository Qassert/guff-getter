"""Jingle endpoints verify permanent nomination and pet ownership server-side."""
from fastapi import APIRouter, Cookie, HTTPException
from fastapi.responses import JSONResponse
from newsmuncher.api.entries import collection
from newsmuncher.services.jingles import service, JingleError

router = APIRouter(prefix="/jingles", tags=["Jingles"])


def invoke(action, rewrite_id, owner):
    try:
        result = action(collection, rewrite_id, owner)
        return JSONResponse(result, headers={"Cache-Control": "no-store"})
    except JingleError as exc:
        raise HTTPException(exc.status, detail=str(exc)) from exc


@router.get("/{rewrite_id}")
def jingle_status(rewrite_id: str, active_pet: str = Cookie(None)):
    return invoke(service.status, rewrite_id, active_pet)


@router.post("/{rewrite_id}")
def make_jingle(rewrite_id: str, active_pet: str = Cookie(None)):
    return invoke(service.generate, rewrite_id, active_pet)
