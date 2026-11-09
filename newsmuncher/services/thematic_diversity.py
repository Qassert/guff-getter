"""Default-off rotating thematic inspiration with bounded persistent memory."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
import hashlib
import json
import os
from pathlib import Path
import random
import re

from pymongo.errors import DuplicateKeyError

from newsmuncher.services.lexical_exposure import exposure_weight


THEMATIC_DIVERSITY_ENV = "NEWSMUNCHER_THEMATIC_DIVERSITY"
CATALOGUE_PATH = Path(__file__).parents[1] / "resources/vocabulary/thematic_domains.json"


@dataclass(frozen=True)
class ThematicDiversityConfig:
    mode: str = "off"
    selection_count: int = 4
    window: int = 20

    @classmethod
    def from_environment(cls):
        return cls(
            os.getenv(THEMATIC_DIVERSITY_ENV, "off").strip().lower(),
            int(os.getenv("NEWSMUNCHER_THEMATIC_COUNT", "4")),
            int(os.getenv("NEWSMUNCHER_THEMATIC_WINDOW", "20")),
        )

    def __post_init__(self):
        if self.mode not in {"off", "evaluation"}:
            raise ValueError(f"{THEMATIC_DIVERSITY_ENV} must be off or evaluation")
        if not 3 <= self.selection_count <= 5 or not 10 <= self.window <= 50:
            raise ValueError("Invalid thematic-diversity limits")

    @property
    def enabled(self):
        return self.mode == "evaluation"


@lru_cache(maxsize=1)
def load_domains():
    payload = json.loads(CATALOGUE_PATH.read_text(encoding="utf-8"))
    domains = tuple(payload.get("domains", ()))
    ids = [item.get("id") for item in domains]
    families = {item.get("family") for item in domains}
    if len(domains) != 100 or len(set(ids)) != 100 or None in ids or len(families) < 8:
        raise ValueError("The thematic catalogue must contain 100 unique, broadly grouped domains")
    required = {"id", "family", "label", "inspiration", "keywords"}
    if any(not required <= item.keys() or len(item["keywords"]) < 3 for item in domains):
        raise ValueError("Malformed thematic domain")
    return domains


def _stable_random(seed):
    digest = hashlib.sha256(str(seed).encode("utf-8")).digest()
    return random.Random(int.from_bytes(digest[:8], "big"))


def detect_domain_influence(selected, final_text, source_text=""):
    final, source = str(final_text).casefold(), str(source_text).casefold()
    influenced = []
    for domain in selected or ():
        matches = []
        for keyword in domain.get("keywords", ()):
            pattern = re.compile(rf"(?<!\w){re.escape(keyword.casefold())}(?!\w)")
            if pattern.search(final) and not pattern.search(source):
                matches.append(keyword)
        if matches:
            influenced.append({"id": domain["id"], "family": domain["family"],
                               "matched_keywords": matches})
    return influenced


def thematic_event(rewrite_id, selected, final_text="", source_text=""):
    return {
        "rewrite_id": str(rewrite_id),
        "selected": [item["id"] for item in selected or ()],
        "families": [item["family"] for item in selected or ()],
        "influenced": detect_domain_influence(selected, final_text, source_text),
    }


class ThematicDiversityMemory:
    """One atomic, bounded domain-exposure stream per anonymized pet scope."""

    def __init__(self, collection, scope, config=None):
        self.collection = collection
        self.config = config or ThematicDiversityConfig()
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

    def penalties(self):
        domain_scores, family_scores = Counter(), Counter()
        for age, event in enumerate(reversed(self.events), 1):
            recency = max(1, self.config.window - age + 1)
            for domain_id in set(event.get("selected", ())):
                domain_scores[domain_id] += recency
            for family in set(event.get("families", ())):
                family_scores[family] += recency * 0.35
        return domain_scores, family_scores

    def select(self, seed):
        if not self.config.enabled:
            return []
        domain_scores, family_scores = self.penalties()
        available, chosen, chosen_families = list(load_domains()), [], Counter()
        rng = _stable_random(seed)
        while available and len(chosen) < self.config.selection_count:
            weights = []
            for domain in available:
                penalty = (domain_scores[domain["id"]] + family_scores[domain["family"]] +
                           chosen_families[domain["family"]] * 8)
                weights.append(exposure_weight(penalty, exploration_floor=0.12))
            item = rng.choices(available, weights=weights, k=1)[0]
            chosen.append(item); chosen_families[item["family"]] += 1; available.remove(item)
        self.last_metrics.update({"selected": len(chosen),
                                  "penalized_domains": len(domain_scores),
                                  "families": len(chosen_families),
                                  "selected_penalties": {
                                      item["id"]: round(
                                          domain_scores[item["id"]] +
                                          family_scores[item["family"]], 3)
                                      for item in chosen
                                  }})
        return chosen

    @staticmethod
    def guidance(selected):
        if not selected:
            return ""
        ideas = "; ".join(item["inspiration"] for item in selected)
        return (
            "OPTIONAL THEMATIC INSPIRATION:\n"
            f"Possible creative springboards: {ideas}. "
            "Ignore, combine, distort or reinterpret these freely. They are not subjects, "
            "requirements or a checklist; preserve the source and use them only when they "
            "spark an unexpected surreal connection."
        )

    def record(self, event):
        if not self.config.enabled:
            return False
        try:
            result = self.collection.update_one(
                {"_id": self.record_id, "events.rewrite_id": {"$ne": event["rewrite_id"]}},
                {"$setOnInsert": {"version": 1, "record_type": "thematic_diversity"},
                 "$push": {"events": {"$each": [event], "$slice": -self.config.window}}},
                upsert=True,
            )
        except DuplicateKeyError:
            # Two first writes for one pet can race on the unique _id. Retry
            # the losing event as a normal conditional append; a duplicate
            # rewrite UUID still matches nothing and remains idempotent.
            result = self.collection.update_one(
                {"_id": self.record_id,
                 "events.rewrite_id": {"$ne": event["rewrite_id"]}},
                {"$push": {"events": {"$each": [event],
                                        "$slice": -self.config.window}}},
                upsert=False,
            )
        self.last_metrics = {"history_writes": 1,
                             "stored_events": min(self.config.window, len(self.events) + 1)}
        return bool(result.matched_count or result.upserted_id is not None)
