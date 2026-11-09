"""Opt-in short-window memory for completed offers and prominent final comedy."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import os
import re

from pymongo.errors import DuplicateKeyError

from newsmuncher.services.comedy_concepts import normalised as concept_normalised
from newsmuncher.services.comedy_descriptors import normalised as descriptor_normalised


TOPIC_MEMORY_ENV = "NEWSMUNCHER_COMEDY_TOPIC_MEMORY"


@dataclass(frozen=True)
class TopicMemoryConfig:
    mode: str = "off"
    window: int = 10
    guidance_items: int = 4

    @classmethod
    def from_environment(cls):
        return cls(
            os.getenv(TOPIC_MEMORY_ENV, "off").strip().lower(),
            int(os.getenv("NEWSMUNCHER_COMEDY_TOPIC_WINDOW", "10")),
            int(os.getenv("NEWSMUNCHER_COMEDY_TOPIC_GUIDANCE_ITEMS", "4")),
        )

    def __post_init__(self):
        if self.mode not in {"off", "evaluation"}:
            raise ValueError(f"{TOPIC_MEMORY_ENV} must be off or evaluation")
        if not 2 <= self.window <= 30 or not 1 <= self.guidance_items <= 8:
            raise ValueError("Invalid comedy topic-memory limits")

    @property
    def enabled(self):
        return self.mode == "evaluation"


SUBJECT_PATTERNS = (
    ("subject:gravy", "gravy", r"\bgravy\b"),
    ("subject:pudding-dessert", "puddings or desserts", r"\b(?:pudding|puddings|dessert|desserts|custard|trifle)\b"),
    ("subject:tea", "tea or tea equipment", r"\b(?:tea|teapot|tea[- ]?urn|kettle)\b"),
    ("subject:allotment", "allotments", r"\ballotments?\b"),
    ("subject:milk-float", "milk floats", r"\bmilk[- ]floats?\b"),
    ("subject:queue", "queueing", r"\b(?:queue|queues|queueing|queued)\b"),
    ("subject:municipal-authority", "municipal authority", r"\b(?:municipal|civic|council|inspectorate|ombudsman)\b"),
)
CONSTRUCTION_PATTERNS = (
    ("construction:powered", "another X-powered-Y construction", r"\b[a-z][a-z'-]*[- ]powered\s+[a-z]"),
    ("construction:tribunal", "representing itself at a tribunal", r"\brepresent(?:ing|ed|s)? (?:itself|himself|herself) at (?:a |the )?tribunal\b"),
    ("construction:illegal-raffle", "running an illegal raffle", r"\b(?:run|runs|running|ran) an illegal raffle\b"),
    ("construction:neighbour-started-it", "insisting the neighbour started it", r"\b(?:insist\w* )?(?:that )?the neighbour started it\b"),
    ("construction:unauthorised-swelling", "capable of unauthorised swelling", r"\bcapable of unauthori[sz]ed swelling\b"),
    ("construction:floorboards-framed-it", "claiming the floorboards framed it", r"\b(?:the )?floorboards? framed (?:it|them|him|her)\b"),
)


def detect_topics(text, source_text=""):
    """Return explainable high-confidence matches absent from the source."""
    output = []
    for kind, patterns in (("subject", SUBJECT_PATTERNS), ("construction", CONSTRUCTION_PATTERNS)):
        for key, label, pattern in patterns:
            match = re.search(pattern, text, re.I)
            if match and not re.search(pattern, source_text, re.I):
                output.append({"key": key, "label": label, "kind": kind,
                               "evidence": match.group(0)})
    return output


def name_topic_family(name, semantic_family=""):
    if "yaffle" in name.casefold():
        return "yaffle"
    return semantic_family or ""


def build_topic_event(rewrite_id, result, source, names=(), name_families=None,
                      concepts=(), descriptors=()):
    final_text = f"{result.get('crazyReplacement1Title', '')}\n{result.get('crazyReplacement1Extract', '')}"
    source_text = "\n".join(str(source.get(key, "")) for key in ("title", "description", "extract"))
    name_families = name_families or {}
    return {
        "rewrite_id": str(rewrite_id),
        "concept_phrases": [concept_normalised(item["phrase"]) for item in concepts],
        "concept_premises": [concept_normalised(item["premise_key"]) for item in concepts],
        "concept_bases": [concept_normalised(item["base"]) for item in concepts],
        "descriptor_phrases": [descriptor_normalised(item["phrase"]) for item in descriptors],
        "descriptor_premises": [descriptor_normalised(item["premise_key"]) for item in descriptors],
        "name_families": [family for name in names
                          if (family := name_topic_family(name, name_families.get(name, "")))],
        "final_topics": detect_topics(final_text, source_text),
    }


class TopicMemory:
    def __init__(self, collection, config=None):
        self.collection = collection
        self.config = config or TopicMemoryConfig()
        self.events = []
        self.last_metrics = {}

    def load(self):
        if not self.config.enabled:
            return []
        document = self.collection.find_one({"_id": "recent"}, {"events": 1}) or {}
        self.events = list(document.get("events", []))[-self.config.window:]
        self.last_metrics = {"history_reads": 1, "events": len(self.events)}
        return self.events

    def penalties(self, field, prefix=""):
        counter = Counter()
        for age, event in enumerate(reversed(self.events), 1):
            weight = max(1, self.config.window - age + 1)
            counter.update({prefix + value: weight for value in set(event.get(field, []))})
        return counter

    def recent_name_families(self):
        return self.penalties("name_families")

    def guidance(self):
        counts = Counter()
        labels = {}
        for event in self.events[-5:]:
            for item in event.get("final_topics", []):
                counts[item["key"]] += 1; labels[item["key"]] = item["label"]
        repeated = sorted((key for key in counts if counts[key] >= 2),
                          key=lambda key: (-counts[key], key))[:self.config.guidance_items]
        if not repeated:
            return ""
        bullets = "\n".join(f"- {labels[key]}" for key in repeated)
        return (
            "RECENT COMEDY VARIETY (soft preference):\n"
            "Where the source does not require it, prefer a different specific joke from these "
            "recently prominent subjects or constructions. Keep the same British absurdist tone.\n"
            f"{bullets}"
        )

    def record(self, event):
        if not self.config.enabled:
            return False
        try:
            result = self.collection.update_one(
                {"_id": "recent", "events.rewrite_id": {"$ne": event["rewrite_id"]}},
                {"$setOnInsert": {"version": 1},
                 "$push": {"events": {"$each": [event], "$slice": -self.config.window}}},
                upsert=True,
            )
        except DuplicateKeyError:
            return False
        self.last_metrics = {"history_writes": 1}
        return bool(result.matched_count or result.upserted_id is not None)
