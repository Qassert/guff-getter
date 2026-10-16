"""Adapter for the CSV-based rewrite preserved at git commit 42a86b9."""
from pathlib import Path
import random

from newsmuncher.config import WORDS_DIR
from newsmuncher.utils.clean_data import CSV_FILES, clean_data, extract_unique_words


CLASSIC_PROMPT = Path(__file__).parents[1] / "resources" / "prompts" / "rewrite_classic.txt"


def prepare_classic_prompt(entry, count=10, random_source=None):
    """Reproduce the original six-bank random prompt without modern selectors."""
    random_source = random_source or random
    words = {
        category: extract_unique_words(str(WORDS_DIR / filename), count)
        for category, filename in CSV_FILES.items()
    }
    def thirds(values):
        values = list(values)
        random_source.shuffle(values)
        return [values[index::3] for index in range(3)]
    parts = {category: thirds(values) for category, values in words.items()}
    prompt_stems = {
        "slang": "slang", "nouns": "noun", "adverbs": "adverb",
        "animals": "animal", "names": "name", "places": "place",
    }
    prompt = CLASSIC_PROMPT.read_text(encoding="utf-8").format(**{
        f"{prompt_stems[category]}_words{index + 1}": ", ".join(chunks[index])
        for category, chunks in parts.items() for index in range(3)
    })
    cleaned = clean_data(entry)
    title = (cleaned.get("title", "No title provided").strip() + " - " +
             cleaned.get("description", "No description provided").strip())
    extract = cleaned.get("extract", "No extract provided").strip()
    return {
        "full_prompt": f"{prompt}\n\nText to Transform:\nTitle: {title}\nExtract: {extract}",
        "contenders": words,
    }
