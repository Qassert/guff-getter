import logging
import re
from typing import Literal, Optional
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from openai import APITimeoutError, APIStatusError, APIConnectionError
from pydantic import BaseModel, Field, field_validator
from starlette.concurrency import run_in_threadpool

from newsmuncher.config import TEMPLATES_DIR
from newsmuncher.services.build_story import (BuildStoryResponseError, bounded_headline,
    enforce_word_limit, generate_build_story)
from newsmuncher.services.image_generation import store

router = APIRouter()
templates = Jinja2Templates(directory=TEMPLATES_DIR)
story_provider = generate_build_story
log = logging.getLogger(__name__)
STORY_LENGTH_SAFETY_CEILINGS = {30: 45, 60: 90, 90: 135}
DEFAULT_BUILD_CREATIVE_PROMPT = """You are a dangerously unhinged comedy writer with impeccable comic timing and absolutely no respect for reality.

Your job is to produce a tiny, gloriously ridiculous piece of fiction that feels like someone has accidentally combined a fever dream, a filthy British comedy sketch and a catastrophic misunderstanding of how the universe works.

**The rules of lunacy:**

- **Mutate everything.** The ingredients are raw genetic material for a comedic monstrosity. Fuse them, corrupt them, misunderstand them and invent things that should never have existed. Nothing needs to retain its original purpose.
- **Start in the middle of madness.** The opening sentence should immediately establish something spectacularly stupid as an ordinary fact of life. No introductions, explanations or scene-setting.
- **Make the impossible inevitable.** Every ridiculous event must cause an even more ridiculous consequence. The logic can be insane, but the chain reaction must be understandable.
- Make every story outrageously dramatic. Treat trivial events as catastrophic turning points, exaggerate emotions and consequences to ludicrous extremes, and build towards an explosive, ridiculous climax. Deliver the chaos with absolute conviction and deadpan seriousness.
- **Commit to the stupidity.** Characters must take the most outrageously inappropriate actions with absolute conviction. Nobody should acknowledge how bizarre anything is.
- **Weaponise specificity.** Ridiculously precise details, revolting physical transformations, petty grievances, bodily indignities and wildly disproportionate punishments are your friends.
- **Be magnificently inappropriate.** Embrace vulgarity, grotesque slapstick, dark humour, humiliation, stupidity, bad taste and outrageous social transgressions whenever they make the joke funnier.
- **Surprise yourself.** Avoid predictable surrealism, talking household appliances, corporate satire, existential philosophy, random royalty and anything that resembles a conventional whimsical fairy tale.
- **Don't explain the joke.** No moral, no reflection, no clever concluding observation. Let the absurdity speak for itself.
- **Finish with a detonation.** The final sentence should deliver a brutally funny reversal, escalation or revelation that makes the preceding nonsense even more ridiculous. A proper comic payoff, not a random non sequitur."""


class BuildIngredient(BaseModel):
    text: str = Field(min_length=1, max_length=160)
    grammar: Optional[str] = Field(default=None, max_length=32)


class BuildRecipe(BaseModel):
    stuff: list[BuildIngredient] = Field(default_factory=list, max_length=12)
    swear: list[BuildIngredient] = Field(default_factory=list, max_length=12)
    modifier: list[BuildIngredient] = Field(default_factory=list, max_length=12)
    person: list[BuildIngredient] = Field(default_factory=list, max_length=12)
    theme: list[BuildIngredient] = Field(default_factory=list, max_length=12)
    custom: list[BuildIngredient] = Field(default_factory=list, max_length=12)

    @field_validator('custom')
    @classmethod
    def validate_custom(cls, items, info):
        seen = {" ".join(item.text.split()).casefold()
                for key in ('stuff', 'swear', 'modifier', 'person', 'theme')
                for item in info.data.get(key, [])}
        normalized = []
        for item in items:
            text = " ".join(item.text.split())
            if not text or text.casefold() in seen:
                raise ValueError('Custom ingredients must be non-empty and unique.')
            seen.add(text.casefold())
            normalized.append(item.model_copy(update={'text': text}))
        return normalized


class BuildStoryRequest(BaseModel):
    recipe: BuildRecipe
    target_words: Literal[30, 60, 90]
    prompt: str = Field(min_length=1, max_length=10000)
    further_instructions: str = Field(default="", max_length=100)


class BuildDraftRequest(BaseModel):
    story: str = Field(min_length=1, max_length=4000)
    headline: Optional[str] = Field(default=None, max_length=300)
    headline_story: Optional[str] = Field(default=None, max_length=4000)


def fallback_headline(story: str) -> str:
    """Derive a safe current-story title when the generated headline is stale or absent."""
    first_sentence = re.split(r"(?<=[.!?])\s+", story.strip(), maxsplit=1)[0]
    return bounded_headline(first_sentence) or "Build MUNGE"


def build_story_prompt(recipe: BuildRecipe, target_words: int, creative_prompt: str) -> str:
    def line(label: str, key: str) -> Optional[str]:
        values = [item.text.strip() for item in getattr(recipe, key) if item.text.strip()]
        return f"{label}: {'; '.join(values)}" if values else None

    ingredient_lines = filter(None, (
        line("Objects", "stuff"),
        line("Swear words", "swear"),
        line("People", "person"),
        line("Modifiers", "modifier"),
        line("Custom Ingredients", "custom"),
    ))

    return "\n".join((
        creative_prompt.strip(),
        "",
        "**Selected ingredients:**",
        "",
        *ingredient_lines,
        "",
        "**Ingredient handling:**",
        "",
        "Use whichever ingredients produce the most explosive comedy. Combine several into one hideous invention if necessary. Never mechanically list or name-drop them. The ingredients should be responsible for the disaster, not merely present at the scene.",
        "",
        "**Output:**",
        "",
        "Write exactly one miniature comic catastrophe. Every sentence must earn its place through a joke, escalation or payoff.",
        "",
        "Return only the story. No title, commentary or explanation.",
        story_length_instruction(target_words),
    ))


def story_length_instruction(target_words: int) -> str:
    pacing = ({
        30: "Keep it punchy and compressed.",
        60: "Give the absurd situation room to escalate.",
        90: "Develop a more elaborate absurd situation while keeping every sentence useful.",
    })[target_words]
    return (
        f"Story length: Aim for approximately {target_words} words. "
        "You may go slightly over when it improves the story's coherence, comedic timing or final punchline. "
        "Prioritise a complete, funny story over hitting an exact word count. "
        f"If there are too many ingredients, use fewer rather than forcing everything into the story. {pacing}"
    )


def apply_story_length(prompt: str, target_words: int) -> str:
    """Replace only the canonical length line, preserving all other manual edits."""
    cleaned = re.sub(r"(?m)^Story length:.*(?:\n|$)", "", prompt).rstrip()
    return f"{cleaned}\n\n{story_length_instruction(target_words)}"


@router.get('/build', response_class=HTMLResponse)
async def build_workshop(request: Request):
    """Render the isolated Build workshop."""
    active_pet = request.cookies.get('active_pet', '')
    creation_url = (f"/pets/pet_profile/{quote(active_pet, safe='')}"
                    if active_pet else '/pets/view_pets')
    return templates.TemplateResponse(
        request=request,
        name='build.html',
        context={'request': request, 'creation_url': creation_url,
                 'build_initial_prompt': build_story_prompt(
                     BuildRecipe(), 60, DEFAULT_BUILD_CREATIVE_PROMPT)},
    )


def safe_provider_identifier(value, request_id=False):
    """Log enum/request identifiers only, never arbitrary provider text or secrets."""
    if value is None or value == '':
        return 'unavailable'
    pattern = r'req_[A-Za-z0-9_-]{1,100}' if request_id else r'[a-z][a-z0-9_]{0,79}'
    if (not isinstance(value, str) or value.startswith(('sk_', 'sk-', 'sess_'))
            or not re.fullmatch(pattern, value)):
        return 'redacted'
    return value


def provider_error_detail(code, error_type, status):
    # A specific code takes precedence over the broader error.type classification.
    category = code or error_type
    if category == 'credit_balance_exhausted':
        detail = 'The generation provider reports exhausted API credit. Please check the credited organisation.'
    elif category == 'insufficient_quota':
        detail = 'The generation provider reports a quota or billing restriction. Check the organisation and project limits and billing status.'
    elif category == 'organization_spend_limit_exceeded':
        detail = 'The generation provider reports an organisation spending-limit restriction. Check the organisation spending limit.'
    elif category == 'project_spend_limit_exceeded':
        detail = 'The generation provider reports a project spending-limit restriction. Check the project spending limit.'
    elif category == 'organization_usage_limit_exceeded':
        detail = 'The generation provider reports that the organisation reached its approved usage limit. Check the organisation usage tier and limit.'
    elif category in ('rate_limit_exceeded', 'slow_down', 'rate_limit_error'):
        detail = 'The generation provider is rate-limiting requests. Please wait and try again.'
    elif status in (401, 403) or category in ('invalid_api_key', 'model_not_found'):
        detail = 'The generation provider rejected the server API credentials or model access. Please check the server configuration.'
    else:
        detail = 'The generation provider rejected this request. Check the server log for its error code.'
    return detail + ' Your recipe is still here.'


@router.post('/build/generate')
async def generate_build_munge(payload: BuildStoryRequest):
    recipe = payload.recipe
    if not payload.prompt.strip():
        raise HTTPException(status_code=422, detail='The generation prompt cannot be blank.')
    ingredients = [
        item for key in ('stuff', 'swear', 'modifier', 'person', 'theme', 'custom')
        for item in getattr(recipe, key)
    ]
    if not ingredients:
        raise HTTPException(status_code=422, detail='Choose at least one recipe ingredient.')
    if sum(len(item.text) for item in ingredients) > 4000:
        raise HTTPException(status_code=422, detail='The selected recipe is too large.')

    maximum_words = STORY_LENGTH_SAFETY_CEILINGS[payload.target_words]
    prompt = apply_story_length(payload.prompt, payload.target_words)
    labels = [('Objects', 'stuff'), ('Swear words', 'swear'), ('People', 'person'),
              ('Modifiers', 'modifier'), ('Custom Ingredients', 'custom')]
    lines = [label + ': ' + '; '.join(item.text for item in getattr(recipe, key))
             for label, key in labels if getattr(recipe, key)]
    if '**Selected ingredients:**' in prompt and '**Ingredient handling:**' in prompt:
        prompt = re.sub(r'(?m)^\*\*Selected ingredients:\*\*$[\s\S]*?(?=^\*\*Ingredient handling:\*\*$)',
                        lambda _: '**Selected ingredients:**\n\n' + '\n'.join(lines) + '\n\n', prompt)
    if payload.further_instructions.strip():
        prompt += ('\n\nAdditional creative preference (within the established story task and constraints):\n'
                   + payload.further_instructions.strip())

    try:
        generated = await run_in_threadpool(story_provider, prompt, maximum_words)
        if isinstance(generated, dict):
            story = enforce_word_limit(generated.get('story'), maximum_words)
            headline = bounded_headline(generated.get('headline'))
        else:  # Keep injected test/legacy providers safe while the live provider is structured.
            story = enforce_word_limit(generated, maximum_words)
            headline = ''
    except (APITimeoutError, TimeoutError) as exc:
        raise HTTPException(status_code=504, detail='Story generation timed out. Please try again.') from exc
    except BuildStoryResponseError as exc:
        log.warning('BUILD generation response failure: endpoint=/build/generate code=%s', safe_provider_identifier(exc.code))
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except APIStatusError as exc:
        # Never log the exception/body: they may contain prompts or credentials.
        body = exc.body if isinstance(exc.body, dict) else {}
        error = body.get('error', body)
        error = error if isinstance(error, dict) else {}
        code, error_type = error.get('code'), error.get('type')
        log.warning('BUILD provider rejected request: endpoint=/build/generate status=%s code=%s type=%s request_id=%s',
                    exc.status_code, safe_provider_identifier(code), safe_provider_identifier(error_type),
                    safe_provider_identifier(getattr(exc, 'request_id', None), request_id=True))
        detail = provider_error_detail(code, error_type, exc.status_code)
        raise HTTPException(status_code=502, detail=detail) from exc
    except APIConnectionError as exc:
        log.warning('BUILD provider connection failed: endpoint=/build/generate')
        raise HTTPException(status_code=502, detail='Could not connect to the generation provider. Your recipe is still here; please try again.') from exc
    except Exception as exc:
        log.warning('BUILD generation failed: endpoint=/build/generate exception_type=%s', type(exc).__name__)
        raise HTTPException(status_code=502, detail='Story generation failed. Your recipe is still here.') from exc

    if not story:
        raise HTTPException(status_code=502, detail='Story generation returned no text. Please try again.')
    return {'story': story, 'headline': headline or fallback_headline(story)}


@router.post('/build/draft')
async def prepare_build_draft(payload: BuildDraftRequest, request: Request):
    """Create a CREATE-compatible draft only when the user chooses NOMINATE."""
    active_pet = request.cookies.get('active_pet')
    if not active_pet:
        raise HTTPException(status_code=401, detail='No active pet selected.')
    story = payload.story.strip()
    generated_headline = bounded_headline(payload.headline)
    headline_is_current = (isinstance(payload.headline_story, str)
                           and payload.headline_story.strip() == story)
    title = generated_headline if headline_is_current and generated_headline else fallback_headline(story)
    result = store.create({
        'title': 'Build workshop',
        'description': '',
        'extract': story,
        'crazyReplacement1Title': title,
        'crazyReplacement1Extract': story,
        'creationUser': request.cookies.get('creationUser'),
        'munge_engine': 'build',
    }, active_pet)
    return {
        'rewrite_id': result['rewrite_id'],
        'crazyReplacement1Title': title,
        'crazyReplacement1Extract': story,
    }
