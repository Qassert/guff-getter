from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from urllib.parse import quote

from newsmuncher.config import TEMPLATES_DIR

router = APIRouter()
templates = Jinja2Templates(directory=TEMPLATES_DIR)


@router.get('/build', response_class=HTMLResponse)
async def build_workshop(request: Request):
    """Render the isolated, client-side Build workshop."""
    active_pet = request.cookies.get('active_pet', '')
    creation_url = (f"/pets/pet_profile/{quote(active_pet, safe='')}"
                    if active_pet else '/pets/view_pets')
    return templates.TemplateResponse(
        request=request,
        name='build.html',
        context={'request': request, 'creation_url': creation_url},
    )
