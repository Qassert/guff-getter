"""Bounded OpenAI story generation for the isolated Build workshop."""

from __future__ import annotations

import json
import re

from dotenv import load_dotenv
from openai import APITimeoutError, OpenAI

from newsmuncher.config import ENV_FILE

BUILD_STORY_MODEL = "gpt-6-sol"
BUILD_STORY_TIMEOUT_SECONDS = 30.0
BUILD_STORY_MAX_WORDS = 99
BUILD_STORY_MAX_OUTPUT_TOKENS = 750
BUILD_HEADLINE_MAX_WORDS = 18
BUILD_HEADLINE_MAX_CHARACTERS = 180
BUILD_STORY_FORMAT = {
    "type": "json_schema",
    "name": "build_story_with_headline",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "story": {"type": "string"},
            "headline": {"type": "string"},
        },
        "required": ["story", "headline"],
        "additionalProperties": False,
    },
}


def enforce_word_limit(text: str, maximum: int = BUILD_STORY_MAX_WORDS) -> str:
    """Return provider prose containing no more than the requested word count."""
    if not isinstance(text, str):
        return ""
    words = re.findall(r"\S+", text.strip())
    return " ".join(words[:maximum])


def bounded_headline(text: str) -> str:
    """Normalise a sung headline without changing the saved story."""
    if not isinstance(text, str):
        return ""
    clean = " ".join(text.split()).strip('"“” ')
    clean = " ".join(clean.split()[:BUILD_HEADLINE_MAX_WORDS])
    return clean[:BUILD_HEADLINE_MAX_CHARACTERS].rstrip(" ,.;:!?")


class BuildStoryResponseError(ValueError):
    """A safe response failure that can be shown without leaking provider text."""
    def __init__(self, code, detail, status_code=502):
        super().__init__(detail)
        self.code = code
        self.detail = detail
        self.status_code = status_code


def generate_build_story(prompt: str, maximum_words: int) -> dict[str, str]:
    """Generate one Build story and its jingle headline in a single provider call."""
    load_dotenv(dotenv_path=ENV_FILE, override=False)
    with OpenAI(max_retries=0, timeout=BUILD_STORY_TIMEOUT_SECONDS) as client:
        response = client.responses.create(
            model=BUILD_STORY_MODEL,
            input=[
                {
                    "role": "developer",
                    "content": (
                        "Write only the requested miniature story. Transform the supplied "
                        "ingredients into coherent absurd events rather than quoting them in "
                        "dialogue. Adult language supplied by the user is allowed. Keep the "
                        f"story at most {maximum_words} words. After completing the story, write "
                        "a separate 12–18-word headline that captures its funniest outrageous "
                        "event. Make the headline punchy, rhythmic, deranged and suitable for "
                        "singing or rapping, like an absurd tabloid hook. Prefer vivid characters, "
                        "bizarre actions, grotesque consequences and ridiculous specificity. "
                        "Keep it recognisably connected to the story; do not repeat its opening "
                        "sentence, invent an unrelated event, use introductory filler or add "
                        "unnecessary punctuation. Return only the requested structured fields."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            reasoning={"effort": "none"},
            text={"format": BUILD_STORY_FORMAT},
            max_output_tokens=BUILD_STORY_MAX_OUTPUT_TOKENS,
            store=False,
        )
    for item in getattr(response, 'output', []) or []:
        for part in getattr(item, 'content', []) or []:
            if getattr(part, 'type', None) == 'refusal':
                raise BuildStoryResponseError('refusal',
                    'The provider declined this prompt. Edit the prompt or ingredients and try again. Your recipe is still here.', 422)
    if getattr(response, 'status', 'completed') != 'completed':
        raise BuildStoryResponseError('incomplete',
            'Story generation returned an incomplete response. Your recipe is still here; please try again.')
    try:
        result = json.loads(response.output_text)
    except (json.JSONDecodeError, TypeError, AttributeError) as exc:
        raise BuildStoryResponseError('invalid_json',
            'Story generation returned an invalid response. Your recipe is still here; please try again.') from exc
    if not isinstance(result, dict):
        raise BuildStoryResponseError("invalid_shape", "Story generation returned an invalid response. Your recipe is still here; please try again.")
    story = enforce_word_limit(result.get("story"), maximum_words)
    if not story:
        raise BuildStoryResponseError("empty_story", "Story generation returned no text. Your recipe is still here; please try again.")
    return {"story": story, "headline": bounded_headline(result.get("headline"))}
