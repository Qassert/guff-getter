"""Adapter for the CSV-based rewrite preserved at git commit 42a86b9."""
import csv
import logging
from pathlib import Path
import random
import re

from newsmuncher.config import STATIC_DIR, WORDS_DIR
from newsmuncher.utils.clean_data import CSV_FILES, clean_data, extract_unique_words


CLASSIC_PROMPT = Path(__file__).parents[1] / "resources" / "prompts" / "rewrite_classic.txt"
OBJECT_VOCABULARY = STATIC_DIR / "data" / "object-generator-vocabulary.csv"
LOGGER = logging.getLogger(__name__)


def _classic_words(path):
    """Read a complete legacy bank using Classic's original comma parser."""
    with Path(path).open("r") as source:
        content = source.read()
    return [word.strip() for word in list(set(content.split(','))) if word.strip()]


def _pool_key(word):
    return re.sub(r"\s+", " ", word).strip().casefold()


def classic_physical_pool(legacy_path=None, object_vocabulary_path=None):
    """Return legacy animals/objects plus current OBJECT physical vocabulary.

    A malformed or unavailable shared file is non-fatal: Classic retains its complete
    historical pool and emits a diagnostic for operators.
    """
    legacy_path = Path(legacy_path or WORDS_DIR / CSV_FILES["animals"])
    object_vocabulary_path = Path(object_vocabulary_path or OBJECT_VOCABULARY)
    legacy = _classic_words(legacy_path)
    combined = {_pool_key(word): word for word in legacy}
    try:
        shared_words = []
        with object_vocabulary_path.open(encoding="utf-8-sig", newline="") as source:
            reader = csv.DictReader(source, strict=True)
            if reader.fieldnames != ["category", "word"]:
                raise ValueError(
                    f"expected category,word columns; received {reader.fieldnames}")
            for line_number, row in enumerate(reader, 2):
                if None in row or row.get("category") is None or row.get("word") is None:
                    raise ValueError(f"malformed row {line_number}")
                if row["category"].strip() not in {"object", "device"}:
                    continue
                word = row["word"].strip()
                if word:
                    shared_words.append(word)
        for word in shared_words:
            combined.setdefault(_pool_key(word), word)
    except (OSError, UnicodeError, csv.Error, ValueError) as exc:
        LOGGER.warning(
            "Classic shared OBJECT vocabulary unavailable; using legacy pool only: %s",
            exc,
        )
    return list(combined.values())


def _sample(values, count):
    if len(values) < count:
        LOGGER.warning("Classic bank has only %d values for a %d-word draw", len(values), count)
        return list(values)
    return random.sample(values, count)


def prepare_classic_prompt(entry, count=10, random_source=None, object_vocabulary_path=None):
    """Reproduce the original six-bank random prompt without modern selectors."""
    random_source = random_source or random
    words = {
        category: (_sample(classic_physical_pool(
            WORDS_DIR / filename, object_vocabulary_path), count)
            if category == "animals" else
            extract_unique_words(str(WORDS_DIR / filename), count))
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
