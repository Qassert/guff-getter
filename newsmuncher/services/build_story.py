"""Bounded OpenAI story generation for the isolated Build workshop."""

from __future__ import annotations

import re

from dotenv import load_dotenv
from openai import APITimeoutError, OpenAI

from newsmuncher.config import ENV_FILE

BUILD_STORY_MODEL = "gpt-6-sol"
BUILD_STORY_TIMEOUT_SECONDS = 30.0
BUILD_STORY_MAX_WORDS = 99


def enforce_word_limit(text: str, maximum: int = BUILD_STORY_MAX_WORDS) -> str:
    """Return provider prose containing no more than the requested word count."""
    words = re.findall(r"\S+", (text or "").strip())
    return " ".join(words[:maximum])


def generate_build_story(prompt: str, maximum_words: int) -> str:
    """Generate one Build story through the established Responses API client."""
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
                        f"story at most {maximum_words} words and add no heading or commentary."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        )
    story = enforce_word_limit(response.output_text, maximum_words)
    if not story:
        raise ValueError("The story provider returned no text.")
    return story
