from typing import Optional
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from openai import APITimeoutError
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from newsmuncher.config import TEMPLATES_DIR
from newsmuncher.services.build_story import enforce_word_limit, generate_build_story

router = APIRouter()
templates = Jinja2Templates(directory=TEMPLATES_DIR)
story_provider = generate_build_story


class BuildIngredient(BaseModel):
    text: str = Field(min_length=1, max_length=160)
    grammar: Optional[str] = Field(default=None, max_length=32)


class BuildRecipe(BaseModel):
    stuff: list[BuildIngredient] = Field(default_factory=list, max_length=12)
    swear: list[BuildIngredient] = Field(default_factory=list, max_length=12)
    modifier: list[BuildIngredient] = Field(default_factory=list, max_length=12)
    person: list[BuildIngredient] = Field(default_factory=list, max_length=12)
    theme: list[BuildIngredient] = Field(default_factory=list, max_length=12)


class BuildStoryRequest(BaseModel):
    recipe: BuildRecipe


def build_story_prompt(recipe: BuildRecipe) -> str:
    def line(label: str, key: str) -> str:
        values = [item.text.strip() for item in getattr(recipe, key) if item.text.strip()]
        return f"{label}: {'; '.join(values) if values else 'None selected'}"

    return "\n".join((
        "Write a hilarious, absurdly surreal and ridiculous miniature story of no more than 80 words.",
        "",
        "Use the following selected ingredients:",
        "",
        line("Objects", "stuff"),
        line("Swear words", "swear"),
        line("People", "person"),
        line("Modifiers", "modifier"),
        line("Theme or setting", "theme"),
        "",
        "Integrate the supplied ingredients naturally into a coherent but wildly unexpected story. Prioritise originality, absurd humour and surprising combinations. Avoid unnecessary new characters or objects. Treat modifiers as optional guidance when forcing every one would damage the prose. Keep the finished story to 80 words or fewer.",
    ))


@router.get('/build', response_class=HTMLResponse)
async def build_workshop(request: Request):
    """Render the isolated Build workshop."""
    active_pet = request.cookies.get('active_pet', '')
    creation_url = (f"/pets/pet_profile/{quote(active_pet, safe='')}"
                    if active_pet else '/pets/view_pets')
    return templates.TemplateResponse(
        request=request,
        name='build.html',
        context={'request': request, 'creation_url': creation_url},
    )


@router.post('/build/generate')
async def generate_build_munge(payload: BuildStoryRequest):
    recipe = payload.recipe
    ingredients = [
        item for key in ('stuff', 'swear', 'modifier', 'person', 'theme')
        for item in getattr(recipe, key)
    ]
    if not ingredients:
        raise HTTPException(status_code=422, detail='Choose at least one recipe ingredient.')
    if sum(len(item.text) for item in ingredients) > 4000:
        raise HTTPException(status_code=422, detail='The selected recipe is too large.')

    prompt = build_story_prompt(recipe)
    try:
        story = await run_in_threadpool(story_provider, prompt)
    except (APITimeoutError, TimeoutError) as exc:
        raise HTTPException(status_code=504, detail='Story generation timed out. Please try again.') from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail='Story generation failed. Your recipe is still here.') from exc

    story = enforce_word_limit(story)
    if not story:
        raise HTTPException(status_code=502, detail='Story generation returned no text. Please try again.')
    return {'story': story}
