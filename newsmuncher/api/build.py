from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from newsmuncher.config import TEMPLATES_DIR

router = APIRouter()
templates = Jinja2Templates(directory=TEMPLATES_DIR)


@router.get('/build', response_class=HTMLResponse)
async def build_workshop(request: Request):
    """Render the isolated, client-side Build workshop."""
    return templates.TemplateResponse(
        request=request,
        name='build.html',
        context={'request': request},
    )
