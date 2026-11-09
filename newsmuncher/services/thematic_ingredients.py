"""Default-off typed thematic seeds and bounded cross-domain ingredients."""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from dataclasses import dataclass
from functools import lru_cache
import hashlib
import json
import os
from pathlib import Path
import random
import re

from pymongo.errors import DuplicateKeyError

from newsmuncher.services.lexical_exposure import exposure_weight, text_penalty
from newsmuncher.services.noun_exclusion import blocked_entries, NounExclusionExhausted


THEME_INGREDIENT_ENV = "NEWSMUNCHER_THEME_INGREDIENTS"
THEME_SPARK_ENV = "NEWSMUNCHER_THEME_SPARKS"
SEED_PATH = Path(__file__).parents[1] / "resources/vocabulary/thematic_ingredient_seeds.json"
KINDS = ("entities", "processes", "properties", "relationships")


@dataclass(frozen=True)
class ThemeIngredientConfig:
    mode: str = "off"
    concept_count: int = 2
    descriptor_count: int = 1
    window: int = 20

    @classmethod
    def from_environment(cls):
        return cls(
            os.getenv(THEME_INGREDIENT_ENV, "off").strip().lower(),
            int(os.getenv("NEWSMUNCHER_THEME_CONCEPT_COUNT", "2")),
            int(os.getenv("NEWSMUNCHER_THEME_DESCRIPTOR_COUNT", "1")),
            int(os.getenv("NEWSMUNCHER_THEME_INGREDIENT_WINDOW", "20")),
        )

    def __post_init__(self):
        if self.mode not in {"off", "evaluation"}:
            raise ValueError(f"{THEME_INGREDIENT_ENV} must be off or evaluation")
        if not 0 <= self.concept_count <= 2 or not 0 <= self.descriptor_count <= 1:
            raise ValueError("Theme ingredient replacement limits are invalid")
        if not 10 <= self.window <= 50:
            raise ValueError("Theme ingredient memory window must be 10..50")

    @property
    def enabled(self):
        return self.mode == "evaluation"


@dataclass(frozen=True)
class ThemeSparkConfig:
    """Presentation-only switch for already selected Phase 4P ingredients."""

    mode: str = "off"

    @classmethod
    def from_environment(cls):
        return cls(os.getenv(THEME_SPARK_ENV, "off").strip().lower())

    def __post_init__(self):
        if self.mode not in {"off", "evaluation"}:
            raise ValueError(f"{THEME_SPARK_ENV} must be off or evaluation")

    @property
    def enabled(self):
        return self.mode == "evaluation"


def partition_theme_sparks(concepts, descriptors, enabled=False):
    """Move selected thematic values out of ordinary banks without reselecting them."""
    concept_banks = {bank: [] for bank in ("nouns", "animals")}
    sparks = []
    for item in concepts or ():
        phrase = str(item.get("phrase", ""))
        if enabled and item.get("thematic"):
            sparks.append({"kind": "concept", "text": phrase})
        else:
            concept_banks[item["target_bank"]].append(phrase)
    descriptor_values = []
    for item in descriptors or ():
        phrase = str(item.get("phrase", ""))
        if enabled and item.get("source") == "thematic_seed_catalogue":
            sparks.append({"kind": "descriptor", "text": phrase})
        else:
            descriptor_values.append(phrase)
    return concept_banks, descriptor_values, sparks


@lru_cache(maxsize=1)
def load_thematic_seeds():
    payload = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    records = tuple(payload.get("domains", ()))
    domain_ids, seed_ids = [], []
    for record in records:
        domain_ids.append(record.get("domain_id"))
        if set(record.get("seeds", {})) != set(KINDS):
            raise ValueError("Every thematic domain requires all four typed seed groups")
        for kind in KINDS:
            values = record["seeds"][kind]
            if len(values) < 4:
                raise ValueError("Every thematic seed group requires four entries")
            for item in values:
                required = {"id", "text", "grammar", "provenance", "licence_id",
                            "approval_status", "safety_status"}
                if not required <= item.keys():
                    raise ValueError("Malformed thematic ingredient seed")
                if len(re.findall(r"[A-Za-z]+", item["text"])) > 4:
                    raise ValueError("Thematic seeds must remain compact")
                seed_ids.append(item["id"])
    if len(records) != 100 or len(set(domain_ids)) != 100 or len(set(seed_ids)) != len(seed_ids):
        raise ValueError("The thematic seed catalogue must cover 100 unique domains and seeds")
    return records


def _stable_random(seed):
    digest = hashlib.sha256(str(seed).encode("utf-8")).digest()
    return random.Random(int.from_bytes(digest[:8], "big"))


def _words(text):
    return re.findall(r"[A-Za-z]+(?:-[A-Za-z]+)?", str(text))


def _normalised(text):
    return re.sub(r"[^a-z0-9]+", "", str(text).casefold())


def theme_ingredient_event(rewrite_id, ingredients):
    return {
        "rewrite_id": str(rewrite_id),
        "seed_ids": list(dict.fromkeys(
            seed for item in ingredients or () for seed in item.get("seed_ids", ()))),
        "construction_ids": list(dict.fromkeys(
            item.get("construction_id") for item in ingredients or ()
            if item.get("construction_id"))),
        "domain_ids": list(dict.fromkeys(
            domain for item in ingredients or () for domain in item.get("domain_ids", ()))),
    }


class ThemeIngredientMemory:
    """Bounded persistent seed/construction history isolated by anonymized pet."""

    def __init__(self, collection, scope, config=None):
        self.collection = collection
        self.config = config or ThemeIngredientConfig()
        self.record_id = "scope:" + hashlib.sha256(str(scope).encode()).hexdigest()[:24]
        self.events = []
        self.last_metrics = {}

    def load(self):
        if not self.config.enabled:
            return []
        document = self.collection.find_one({"_id": self.record_id}, {"events": 1}) or {}
        self.events = list(document.get("events", ()))[-self.config.window:]
        self.last_metrics = {"history_reads": 1, "events": len(self.events)}
        return self.events

    def penalties(self):
        values = Counter()
        for age, event in enumerate(reversed(self.events), 1):
            weight = max(1, self.config.window - age + 1)
            for seed_id in set(event.get("seed_ids", ())):
                values["seed:" + seed_id] += weight
            for construction in set(event.get("construction_ids", ())):
                values["construction:" + construction] += weight * 0.6
        return values

    def record(self, event):
        if not self.config.enabled:
            return False
        query = {"_id": self.record_id,
                 "events.rewrite_id": {"$ne": event["rewrite_id"]}}
        push = {"$push": {"events": {"$each": [event], "$slice": -self.config.window}}}
        try:
            result = self.collection.update_one(
                query, {"$setOnInsert": {"version": 1,
                                         "record_type": "theme_ingredients"}, **push},
                upsert=True)
        except DuplicateKeyError:
            result = self.collection.update_one(query, push, upsert=False)
        self.last_metrics = {"history_writes": 1,
                             "stored_events": min(self.config.window, len(self.events) + 1)}
        return bool(result.matched_count or result.upserted_id is not None)


class ThematicIngredientBuilder:
    """Construct a few valid ingredients without applying subjective comedy ranking."""

    def __init__(self, selected_domains, seed, config=None, recent_penalties=None,
                 lexical_penalties=None, noun_exclusions=(), source_text=""):
        self.config = config or ThemeIngredientConfig()
        self.domains = list(selected_domains or ())
        records = {item["domain_id"]: item for item in load_thematic_seeds()}
        self.seed_domains = [records[item["id"]] for item in self.domains if item["id"] in records]
        self.random = _stable_random(seed)
        self.recent = recent_penalties or Counter()
        self.lexical = lexical_penalties or Counter()
        self.noun_exclusions = set(noun_exclusions or ())
        self.source_text = source_text
        self.last_metrics = {"proposed": 0, "valid": 0, "selected": 0,
                             "rejected": Counter(), "ranking_losses": 0}
        self.selected = []

    def _seed(self, domain, kind):
        choices = domain["seeds"][kind]
        weights = []
        for item in choices:
            penalty = self.recent.get("seed:" + item["id"], 0)
            penalty += text_penalty(item["text"], self.lexical)
            weights.append(exposure_weight(penalty, exploration_floor=0.12))
        return self.random.choices(choices, weights=weights, k=1)[0]

    def _domain_pair(self, offset=0):
        if not self.seed_domains:
            raise ValueError("Theme ingredient mode requires selected thematic domains")
        first = self.seed_domains[offset % len(self.seed_domains)]
        others = [item for item in self.seed_domains if item["domain_id"] != first["domain_id"]]
        second = self.random.choice(others) if others else first
        return first, second

    def _valid(self, phrase, base=None, maximum=8):
        words = _words(phrase)
        if not 2 <= len(words) <= maximum:
            return "word_count"
        if len([word.casefold() for word in words]) != len(set(word.casefold() for word in words)):
            return "repeated_word"
        if base and _normalised(base) not in _normalised(phrase):
            return "base_not_visible"
        return None

    def _concept_candidate(self, base, target, offset):
        first, second = self._domain_pair(offset)
        form = offset % 3
        if form == 0:
            left, right = self._seed(first, "properties"), self._seed(second, "processes")
            construction = "property_base_process"
            phrase = f"{left['text']} {base} using {right['text']}"
            kinds = ["property", "process"]
        elif form == 1:
            left, right = self._seed(first, "processes"), self._seed(second, "properties")
            construction = "process_adapted_base"
            phrase = f"{left['text']}-adapted {right['text']} {base}"
            kinds = ["process", "property"]
        else:
            left, right = self._seed(first, "relationships"), self._seed(second, "entities")
            construction = "base_relationship_entity"
            phrase = f"{base} in {left['text']} with {right['text']}"
            kinds = ["relationship", "entity"]
        item = {
            "text": phrase, "phrase": phrase, "base": base, "target_bank": target,
            "source": "thematic_seed_catalogue", "family": "thematic_cross_domain",
            "semantic_domain": "cross_domain", "semantic_theme": "thematic_cross_domain",
            "comic_mechanism": construction,
            "premise_key": "thematic:" + ":".join(
                (first["domain_id"], second["domain_id"], construction)),
            "domain_ids": [first["domain_id"], second["domain_id"]],
            "seed_ids": [left["id"], right["id"]], "seed_kinds": kinds,
            "construction_id": construction, "cross_domain": first["domain_id"] != second["domain_id"],
            "provenance": "curated local Phase 4P thematic seed catalogue",
        }
        return item, self._valid(phrase, base)

    def apply_concepts(self, variant_plan):
        if not self.config.enabled or not self.seed_domains or not self.config.concept_count:
            return variant_plan
        plan = deepcopy(variant_plan)
        replacements = min(self.config.concept_count, 2)
        for offset, target in enumerate(("nouns", "animals")[:replacements]):
            positions = [index for index, item in enumerate(plan["prompt"])
                         if item.get("target_bank") == target]
            if not positions:
                continue
            position = self.random.choice(positions)
            displaced = plan["prompt"][position]
            candidates = []
            for attempt in range(12):
                self.last_metrics["proposed"] += 1
                candidate, reason = self._concept_candidate(
                    displaced.get("base") or displaced.get("phrase") or displaced.get("text"),
                    target, offset + attempt)
                if reason:
                    self.last_metrics["rejected"][reason] += 1
                elif blocked_entries(candidate["text"], self.noun_exclusions,
                                     self.source_text):
                    self.last_metrics["rejected"]["noun_exclusion"] += 1
                else:
                    candidates.append(candidate); self.last_metrics["valid"] += 1
            if not candidates:
                raise NounExclusionExhausted(
                    "Not enough eligible thematic concepts. Please try MUNGE IT again.")
            weights = [exposure_weight(
                self.recent.get("construction:" + item["construction_id"], 0),
                exploration_floor=0.12) for item in candidates]
            chosen = self.random.choices(candidates, weights=weights, k=1)[0]
            self.last_metrics["ranking_losses"] += len(candidates) - 1
            plan["prompt"][position] = {"phrase": chosen["text"], "target_bank": target,
                                        "raw": True, "thematic": True}
            if displaced in plan["generated"]:
                plan["generated"].remove(displaced)
            elif displaced in plan["raw"]:
                plan["raw"].remove(displaced)
            plan["raw"].append(chosen); self.selected.append(chosen)
        plan["counts"] = {**plan["counts"], "thematic": len(self.selected)}
        self.last_metrics["selected"] = len(self.selected)
        return plan

    def apply_descriptors(self, descriptors):
        if (not self.config.enabled or not self.seed_domains or
                not self.config.descriptor_count or not descriptors):
            return list(descriptors or ()), list(descriptors or ())
        prompt = deepcopy(list(descriptors)); tracked = list(descriptors)
        position = self.random.randrange(len(prompt)); displaced = descriptors[position]
        role = displaced["grammatical_role"]
        chosen = None
        for attempt in range(12):
            first, second = self._domain_pair(7 + attempt)
            entity, process = self._seed(first, "entities"), self._seed(second, "processes")
            compound = "-".join((entity["text"], process["text"], "adapted")).replace(" ", "-")
            patterns = {
                "pre_noun": compound,
                "adverbial": f"through {process['text']} with {entity['text']}",
                "predicate": f"responsive to {entity['text']} during {process['text']}",
                "post_noun": f"in contact with {entity['text']} during {process['text']}",
                "behavioural": f"performing {process['text']} with {entity['text']}",
                "short_clause": f"{entity['text']} triggers {process['text']}",
            }
            phrase = patterns[role]
            self.last_metrics["proposed"] += 1
            reason = self._valid(phrase, maximum=10)
            if reason:
                self.last_metrics["rejected"][reason] += 1
            elif blocked_entries(phrase, self.noun_exclusions, self.source_text):
                self.last_metrics["rejected"]["noun_exclusion"] += 1
            else:
                chosen = (first, second, entity, process, phrase)
                break
        if not chosen:
            raise NounExclusionExhausted(
                "Not enough eligible thematic descriptors. Please try MUNGE IT again.")
        first, second, entity, process, phrase = chosen
        item = {
            "text": phrase, "phrase": phrase, "subject": entity["text"],
            "grammatical_role": role, "category": displaced["category"],
            "comic_mechanism": "thematic_cross_domain",
            "semantic_theme": "thematic_cross_domain",
            "premise_key": "thematic:" + ":".join((first["domain_id"], second["domain_id"])),
            "generator_version": "thematic-ingredients-v1",
            "source": "thematic_seed_catalogue", "family": "thematic_cross_domain",
            "domain_ids": [first["domain_id"], second["domain_id"]],
            "seed_ids": [entity["id"], process["id"]], "seed_kinds": ["entity", "process"],
            "construction_id": "role_" + role,
            "cross_domain": first["domain_id"] != second["domain_id"],
            "provenance": "curated local Phase 4P thematic seed catalogue",
        }
        prompt[position] = item; tracked.remove(displaced)
        self.selected.append(item); self.last_metrics["valid"] += 1
        self.last_metrics["selected"] = len(self.selected)
        return prompt, tracked
