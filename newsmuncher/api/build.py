from typing import Literal, Optional
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
STORY_LENGTH_MAXIMUMS = {30: 33, 60: 66, 90: 99}


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
    target_words: Literal[30, 60, 90]


def build_story_prompt(recipe: BuildRecipe, target_words: int) -> str:
    def line(label: str, key: str) -> str:
        values = [item.text.strip() for item in getattr(recipe, key) if item.text.strip()]
        return f"{label}: {'; '.join(values) if values else 'None selected'}"

    minimum = round(target_words * 0.9)
    maximum = STORY_LENGTH_MAXIMUMS[target_words]
    pacing = ({30: "Keep it punchy and compressed.", 60: "Give the absurd situation room to escalate.", 90: "Develop a more elaborate absurd situation while keeping every sentence useful."})[target_words]

    return "\n".join((
        "You are an inventive, irreverent absurdist comedy writer. Write one coherent, genuinely funny miniature story using the selected ingredients as creative inspiration.",
        "",
        "Selected ingredients:",
        "",
        line("Objects", "stuff"),
        line("Swear words", "swear"),
        line("People", "person"),
        line("Modifiers", "modifier"),
        line("Theme or setting", "theme"),
        "",
        "Creative rules:",
        "- Transform, do not merely insert. Treat ingredients as creative seeds rather than mandatory phrases. Reinterpret, mutate and combine them so they become integral to the characters, objects, events or absurd logic.",
        "- Never satisfy the recipe by simply making a character say an insult, occupation or unusual phrase. Avoid lazy dialogue; build jokes from what the ingredients become and do.",
        "- Invent unexpected connections between ingredients. Begin with a peculiar situation, add a surprising complication, then escalate through a twisted but recognisable chain of cause and effect.",
        "- Prioritise comedy over completeness. Transform or omit an ingredient when literal inclusion would make the story weaker.",
        "- Be boldly irreverent: use deadpan narration, vivid specificity, dark humour, grotesque imagery, vulgarity, stupidity and wildly inappropriate consequences when funny.",
        "- Avoid tired surrealist clichés, especially generic existential dread, arbitrary promotions and sentient bureaucracy.",
        "- End with a surprising punchline that pays off or recontextualises an earlier detail instead of becoming random.",
        "",
        f"Aim for about {target_words} words (roughly {minimum} to {maximum}). {pacing} Coherence and the comic payoff matter more than an exact count, but never exceed {maximum} words.",
        "When the recipe is too crowded for the selected length, choose the funniest ingredients and combine, transform or omit the rest.",
        "Return only the story, with no title, introduction or explanation.",
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

    maximum_words = STORY_LENGTH_MAXIMUMS[payload.target_words]
    prompt = build_story_prompt(recipe, payload.target_words)
    try:
        story = await run_in_threadpool(story_provider, prompt, maximum_words)
    except (APITimeoutError, TimeoutError) as exc:
        raise HTTPException(status_code=504, detail='Story generation timed out. Please try again.') from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail='Story generation failed. Your recipe is still here.') from exc

    story = enforce_word_limit(story, maximum_words)
    if not story:
        raise HTTPException(status_code=502, detail='Story generation returned no text. Please try again.')
    return {'story': story}
