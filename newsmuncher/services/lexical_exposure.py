"""Opt-in, bounded lexical exposure memory for comedy vocabulary variety."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import hashlib
import os
import re

from pymongo.errors import DuplicateKeyError


LEXICAL_DIVERSITY_ENV = "NEWSMUNCHER_LEXICAL_DIVERSITY"
STOPWORDS = frozenset("""
a an and are as at be been being but by did do does for from had has have he her
hers him his i if in into is it its me my no nor not of on or our ours she so
that the their theirs them they this those through to too up us was we were what
when where which while who will with would you your yours after before during
each more most next once only other over same some than then there these under
until very
""".split())
WORD_RE = re.compile(r"[a-z]+(?:[-'][a-z]+)*", re.I)


@dataclass(frozen=True)
class LexicalExposureConfig:
    mode: str = "off"
    window: int = 10
    guidance_items: int = 4

    @classmethod
    def from_environment(cls):
        return cls(
            os.getenv(LEXICAL_DIVERSITY_ENV, "off").strip().lower(),
            int(os.getenv("NEWSMUNCHER_LEXICAL_WINDOW", "10")),
            int(os.getenv("NEWSMUNCHER_LEXICAL_GUIDANCE_ITEMS", "4")),
        )

    def __post_init__(self):
        if self.mode not in {"off", "evaluation"}:
            raise ValueError(f"{LEXICAL_DIVERSITY_ENV} must be off or evaluation")
        if not 2 <= self.window <= 30 or not 1 <= self.guidance_items <= 8:
            raise ValueError("Invalid lexical-exposure limits")

    @property
    def enabled(self):
        return self.mode == "evaluation"


def normal_word(value: str) -> str:
    return re.sub(r"[-']+", "-", value.casefold()).strip("-")


def meaningful_words(text: str) -> tuple[str, ...]:
    """Extract stable lexical anchors, excluding grammar and very short words."""
    return tuple(dict.fromkeys(
        word for raw in WORD_RE.findall(str(text or ""))
        if len(word := normal_word(raw)) >= 4 and word not in STOPWORDS
    ))


def normal_identity(text: str) -> str:
    words = meaningful_words(text)
    return "-".join(words) if 2 <= len(words) <= 4 else ""


def exposure_keys(text: str, include_identity=True) -> tuple[str, ...]:
    keys = ["word:" + word for word in meaningful_words(text)]
    identity = normal_identity(text) if include_identity else ""
    if identity:
        keys.append("identity:" + identity)
    return tuple(dict.fromkeys(keys))


def text_penalty(text: str, penalties) -> float:
    """Return a bounded additive exposure score; zero preserves baseline choice."""
    if not penalties:
        return 0.0
    keys = exposure_keys(text)
    return round(sum(float(penalties.get(key, 0.0)) for key in keys), 6)


def exposure_weight(penalty: float, exploration_floor: float = 0.08) -> float:
    """Retain enough exploration to prevent a finite candidate pool collapsing."""
    return exploration_floor + (1.0 - exploration_floor) / ((1.0 + penalty) ** 2)


def weighted_choice(random_source, values, penalties=None):
    """Choose from the full pool; exposure reduces but never removes probability."""
    values = list(values)
    if not values:
        raise IndexError("Cannot choose from an empty vocabulary bank")
    if not penalties:
        return random_source.choice(values)
    weights = [exposure_weight(text_penalty(value, penalties)) for value in values]
    return random_source.choices(values, weights=weights, k=1)[0]


def _ingredient_texts(concepts=(), descriptors=(), raw_ingredients=()):
    for item in concepts or ():
        for field in ("phrase", "base"):
            if item.get(field):
                yield str(item[field])
    for item in descriptors or ():
        for field in ("phrase", "subject"):
            if item.get(field):
                yield str(item[field])
    for item in raw_ingredients or ():
        if item.get("text"):
            yield str(item["text"])


def build_lexical_event(rewrite_id, source_text, first_title="", first_body="",
                        final_title="", final_body="", concepts=(), descriptors=(),
                        raw_ingredients=()):
    source_keys = set(exposure_keys(source_text))

    def keys_for(texts):
        keys = []
        for text in texts:
            keys.extend(key for key in exposure_keys(text) if key not in source_keys)
        return list(dict.fromkeys(keys))

    return {
        "rewrite_id": str(rewrite_id),
        "offered": keys_for(_ingredient_texts(concepts, descriptors, raw_ingredients)),
        "first_pass": keys_for((first_title, first_body)),
        "final": keys_for((final_title, final_body)),
    }


class LexicalExposureMemory:
    """One bounded persistent event stream per anonymized pet scope."""

    def __init__(self, collection, scope, config=None):
        self.collection = collection
        self.config = config or LexicalExposureConfig()
        digest = hashlib.sha256(str(scope).encode("utf-8")).hexdigest()[:24]
        self.record_id = "scope:" + digest
        self.events = []
        self.last_metrics = {}

    def load(self):
        if not self.config.enabled:
            return []
        document = self.collection.find_one({"_id": self.record_id}, {"events": 1}) or {}
        self.events = list(document.get("events", []))[-self.config.window:]
        self.last_metrics = {"history_reads": 1, "events": len(self.events)}
        return self.events

    def penalties(self, source_text=""):
        if not self.config.enabled:
            return Counter()
        source_keys = set(exposure_keys(source_text))
        output = Counter()
        for age, event in enumerate(reversed(self.events), 1):
            recency = max(1, self.config.window - age + 1)
            # A visible final use matters most; an offer still represents exposure.
            for field, multiplier in (("offered", 1), ("first_pass", 1), ("final", 3)):
                for key in set(event.get(field, [])) - source_keys:
                    output[key] += recency * multiplier
        return output

    def guidance(self, source_text=""):
        penalties = self.penalties(source_text)
        words = [(key[5:], value) for key, value in penalties.items()
                 if key.startswith("word:") and value >= 6]
        words.sort(key=lambda item: (-item[1], item[0]))
        selected = [word.replace("-", " ") for word, _ in words[:self.config.guidance_items]]
        if not selected:
            return ""
        return (
            "RECENT WORD VARIETY (soft preference):\n"
            "Where the source does not require them, favour fresh vocabulary instead of "
            "leaning again on these recently prominent words: " + ", ".join(selected) + ". "
            "They remain allowed when they inspire the best surreal joke."
        )

    def record(self, event):
        if not self.config.enabled:
            return False
        try:
            result = self.collection.update_one(
                {"_id": self.record_id, "events.rewrite_id": {"$ne": event["rewrite_id"]}},
                {"$setOnInsert": {"version": 1, "record_type": "lexical_exposure"},
                 "$push": {"events": {"$each": [event], "$slice": -self.config.window}}},
                upsert=True,
            )
        except DuplicateKeyError:
            return False
        self.last_metrics = {"history_writes": 1, "stored_events": min(
            self.config.window, len(self.events) + 1)}
        return bool(result.matched_count or result.upserted_id is not None)
