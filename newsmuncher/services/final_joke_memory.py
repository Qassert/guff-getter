"""Opt-in, rule-based memory for specific jokes visible in accepted articles."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import os
import re
from pymongo import ReturnDocument


FINAL_JOKE_MEMORY_ENV = "NEWSMUNCHER_FINAL_JOKE_MEMORY"
NUMBER_WORDS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20,
}
NUMBER_PATTERN = "|".join((*NUMBER_WORDS, r"\d{1,3}"))
NUMBERED_GROUP = re.compile(
    rf"(?<!\w)(?P<number>{NUMBER_PATTERN})\s+(?P<noun>[a-z][a-z'-]{{3,}}s)(?!\w)", re.I
)
QUEUE_CONTAINMENT = re.compile(
    r"(?<!\w)queue(?:s|ing)?(?:[-\s]+[a-z]+){0,2}[-\s]+contain(?:ment|ed|ing)(?!\w)", re.I
)


@dataclass(frozen=True)
class FinalJokeMemoryConfig:
    mode: str = "off"
    cooldown_articles: int = 10
    max_guidance_items: int = 4

    @classmethod
    def from_environment(cls):
        return cls(
            mode=os.getenv(FINAL_JOKE_MEMORY_ENV, "off").strip().lower(),
            cooldown_articles=int(os.getenv(
                "NEWSMUNCHER_FINAL_JOKE_COOLDOWN_ARTICLES", "10")),
            max_guidance_items=int(os.getenv(
                "NEWSMUNCHER_FINAL_JOKE_MAX_GUIDANCE", "4")),
        )

    def __post_init__(self):
        if self.mode not in {"off", "evaluation"}:
            raise ValueError(f"{FINAL_JOKE_MEMORY_ENV} must be off or evaluation")
        if self.cooldown_articles < 1 or not 1 <= self.max_guidance_items <= 8:
            raise ValueError("Invalid final-joke memory limits")

    @property
    def enabled(self):
        return self.mode == "evaluation"


def _normal_number(value: str) -> str:
    folded = value.casefold()
    number = int(folded) if folded.isdigit() else NUMBER_WORDS[folded]
    return str(number)


def _singular(noun: str) -> str:
    folded = noun.casefold()
    if folded.endswith("ies"):
        return folded[:-3] + "y"
    if folded.endswith(("sses", "shes", "ches", "xes", "zes")):
        return folded[:-2]
    return folded[:-1] if folded.endswith("s") else folded


def detect_final_jokes(text: str, source_text: str = "") -> list[dict]:
    """Extract conservative, explainable constructions rather than broad topics."""
    source_keys = {item["key"] for item in detect_final_jokes(source_text) } if source_text else set()
    detected = {}
    for match in NUMBERED_GROUP.finditer(text):
        number = _normal_number(match.group("number"))
        noun = _singular(match.group("noun"))
        key = f"numbered-group:{number}:{noun}"
        if key not in source_keys:
            detected[key] = {
                "key": key,
                "label": f"the recurring '{number} {noun}s' group gag",
                "kind": "numbered_group",
            }
    if QUEUE_CONTAINMENT.search(text):
        key = "scenario:queue-containment"
        if key not in source_keys:
            detected[key] = {
                "key": key,
                "label": "the queue-containment emergency gag",
                "kind": "scenario",
            }
    return list(detected.values())


class FinalJokeMemory:
    """Read recent accepted constructions and record new ones after persistence."""

    def __init__(self, collection, config=None, now=None):
        self.collection = collection
        self.config = config or FinalJokeMemoryConfig()
        self.now = now or (lambda: datetime.now(timezone.utc))
        self.last_metrics = {}

    def recent(self) -> list[dict]:
        if not self.config.enabled:
            return []
        docs = list(self.collection.find({"record_type": {"$in": ["final_joke", "counter"]}}, {
            "_id": 1, "label": 1, "kind": 1, "last_used_at": 1,
            "last_article_sequence": 1, "use_count": 1, "record_type": 1, "value": 1,
        }))
        latest = max((int(doc.get("value", 0)) for doc in docs
                      if doc.get("record_type") == "counter"), default=0)
        floor = max(0, latest - self.config.cooldown_articles + 1)
        eligible = [doc for doc in docs if doc.get("record_type") == "final_joke"
                    if int(doc.get("last_article_sequence", 0)) >= floor]
        eligible.sort(key=lambda doc: (
            int(doc.get("last_article_sequence", 0)), int(doc.get("use_count", 0))
        ), reverse=True)
        self.last_metrics = {"availability_reads": 1, "recent_count": len(eligible)}
        return eligible[:self.config.max_guidance_items]

    def guidance(self) -> str:
        recent = self.recent()
        if not recent:
            return ""
        lines = "\n".join(f"- {item['label']}" for item in recent)
        return (
            "RECENT-JOKE VARIETY:\n"
            "Avoid repeating these specific recently used constructions; choose a fresh "
            "comic idea instead. Do not avoid their broad subjects when a different joke works.\n"
            f"{lines}"
        )

    def accept(self, rewrite_id: str, title: str, body: str, source_text: str = ""):
        if not self.config.enabled:
            return []
        counter = self.collection.find_one_and_update(
            {"_id": "_article_sequence"},
            {"$setOnInsert": {"version": 1, "record_type": "counter"},
             "$inc": {"value": 1}},
            upsert=True, return_document=ReturnDocument.AFTER,
        )
        sequence = int((counter or {}).get("value", 1))
        jokes = detect_final_jokes(f"{title}\n{body}", source_text)
        if not jokes:
            self.last_metrics = {"accepted": 0, "writes": 1}
            return []
        now = self.now()
        for joke in jokes:
            self.collection.update_one(
                {"_id": joke["key"]},
                {"$setOnInsert": {"version": 1, "record_type": "final_joke"},
                 "$set": {"label": joke["label"], "kind": joke["kind"],
                          "last_used_at": now, "last_rewrite_id": rewrite_id,
                          "last_article_sequence": sequence},
                 "$inc": {"use_count": 1}},
                upsert=True,
            )
        self.last_metrics = {"accepted": len(jokes), "writes": len(jokes) + 1}
        return [joke["key"] for joke in jokes]
