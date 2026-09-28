"""Explicit authenticated animation requests; all GETs retrieve stored state only."""
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import FileResponse, JSONResponse

from newsmuncher.api.entries import collection
from newsmuncher.api.promotion_gallery import viewer
from newsmuncher.services.video import service, VideoError

router = APIRouter(prefix='/videos', tags=['Animation'])


def invoke(action, *args):
    try:
        return action(collection, *args)
    except VideoError as exc:
        raise HTTPException(exc.status, str(exc)) from None


def response(data, code=200):
    return JSONResponse(data, status_code=code, headers={'Cache-Control': 'private, no-store'})


@router.get('/{rewrite_id}')
def status(rewrite_id: str, user=Depends(viewer)):
    return response(invoke(service.status, rewrite_id, user['pet']))


@router.post('/{rewrite_id}')
def animate(rewrite_id: str, tasks: BackgroundTasks, user=Depends(viewer)):
    data, claimed = invoke(service.claim, rewrite_id, user['pet'])
    if claimed:
        tasks.add_task(service.run, collection, rewrite_id, user['pet'])
    return response(data, 202 if claimed else 200)


@router.get('/{rewrite_id}/media')
def media(rewrite_id: str, user=Depends(viewer)):
    data = invoke(service.status, rewrite_id, user['pet'])
    if not data.get('video_url'):
        raise HTTPException(404, 'Stored animation unavailable.')
    return FileResponse(service.path(rewrite_id), media_type='video/mp4',
                        headers={'Cache-Control': 'private, no-store'})
