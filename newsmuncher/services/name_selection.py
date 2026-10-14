"""Configurable rewrite-name slates with temporary offers and accepted-use cooldowns."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import os
import re
from time import monotonic

from pymongo.errors import DuplicateKeyError

from newsmuncher.services.comedy_names import ComedyNameGenerator, NameGeneratorConfig, normalized
from newsmuncher.services.semantic_memory import (
    family_record, name_sound_family, recency_penalty, record_family_use,
    semantic_memory_enabled,
)
from newsmuncher.services.topic_memory import name_topic_family


INVENTED_NAME_GUIDANCE = """INVENTED-NAME RULES:
- Replace real people with the supplied invented names wherever a replacement is appropriate.
- Favour the supplied names and keep each chosen character name exactly consistent throughout.
- Do not introduce real celebrities or historical figures as replacement characters.
- Use names naturally; do not force every supplied name into the story."""


class NameSelectionExhausted(RuntimeError):
    """The bounded local search could not atomically lease a complete slate."""


@dataclass(frozen=True)
class NameSelectionConfig:
    mode: str = "invented"
    slate_size: int = 10
    cheeky_weight: float = .70
    absurd_weight: float = .30
    cooldown_days: int = 30
    offer_minutes: int = 15
    candidates_per_style: int = 300
    vocabulary_mode: str = "off"
    semantic_memory_mode: str = "off"

    @classmethod
    def from_environment(cls):
        mode = os.getenv("NEWSMUNCHER_NAME_MODE", "invented").strip().lower()
        if mode not in {"invented", "legacy"}:
            raise ValueError("NEWSMUNCHER_NAME_MODE must be 'invented' or 'legacy'")
        return cls(
            mode=mode,
            cheeky_weight=float(os.getenv("NEWSMUNCHER_CHEEKY_NAME_WEIGHT", ".70")),
            absurd_weight=float(os.getenv("NEWSMUNCHER_ABSURD_NAME_WEIGHT", ".30")),
            cooldown_days=int(os.getenv("NEWSMUNCHER_NAME_COOLDOWN_DAYS", "30")),
            offer_minutes=int(os.getenv("NEWSMUNCHER_NAME_OFFER_MINUTES", "15")),
            vocabulary_mode=os.getenv("NEWSMUNCHER_EXPANDED_NAMES", "off").strip().lower(),
            semantic_memory_mode=os.getenv("NEWSMUNCHER_COMEDY_SEMANTIC_MEMORY", "off").strip().lower(),
        )

    def __post_init__(self):
        if self.mode not in {"invented", "legacy"}:
            raise ValueError("Unknown name-selection mode")
        if self.slate_size < 1 or self.cooldown_days < 0 or self.offer_minutes < 1:
            raise ValueError("Invalid name-selection limits")
        if self.candidates_per_style < self.slate_size:
            raise ValueError("Invented-name candidate search is too small")
        if self.cheeky_weight < 0 or self.absurd_weight < 0 or not (
                self.cheeky_weight + self.absurd_weight):
            raise ValueError("Invalid invented-name weights")
        if self.vocabulary_mode not in {"off", "reviewed", "evaluation"}:
            raise ValueError("NEWSMUNCHER_EXPANDED_NAMES must be off, reviewed or evaluation")
        semantic_memory_enabled(self.semantic_memory_mode)


class InventedNameRegistry:
    """Lease prompt candidates, then timestamp only names used by an accepted rewrite."""

    def __init__(self, collection, config=None, now=None):
        self.collection = collection
        self.config = config or NameSelectionConfig()
        self.now = now or (lambda: datetime.now(timezone.utc))
        self.last_metrics = {}
        self._offered_families = {}

    @staticmethod
    def _family(candidate):
        return f"{candidate.category}:{name_sound_family(candidate.surname_component)}"

    @staticmethod
    def _utc(value):
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def _acquire(self, candidate, selection_key, now, offer_until, cooldown_cutoff):
        key = normalized(candidate.name)
        query = {
            "_id": key,
            "$and": [
                {"$or": [
                    {"last_used_at": {"$exists": False}},
                    {"last_used_at": {"$lte": cooldown_cutoff}},
                ]},
                {"$or": [
                    {"offered_by": selection_key},
                    {"offer_until": {"$exists": False}},
                    {"offer_until": {"$lte": now}},
                ]},
            ],
        }
        update = {
            "$setOnInsert": {"display_name": candidate.name, "version": 1},
            "$set": {"offered_by": selection_key, "offer_until": offer_until,
                     "category": candidate.category, "recipe": candidate.recipe,
                     "semantic_family": self._family(candidate)},
        }
        try:
            self.last_metrics["lease_writes"] += 1
            result = self.collection.update_one(query, update, upsert=True)
        except DuplicateKeyError:
            return False
        return bool(result.matched_count or result.upserted_id is not None)

    def offer(self, selection_key: str, recent_families=None) -> list[str]:
        started = monotonic()
        self.last_metrics = {"candidate_ms": 0.0, "filter_ms": 0.0,
                             "lease_ms": 0.0, "availability_reads": 0,
                             "lease_writes": 0}
        now = self.now()
        cooldown_cutoff = now - timedelta(days=self.config.cooldown_days)
        offer_until = now + timedelta(minutes=self.config.offer_minutes)
        generator = ComedyNameGenerator(
            seed=selection_key,
            config=NameGeneratorConfig(
                cheeky_weight=self.config.cheeky_weight,
                absurd_weight=self.config.absurd_weight,
            ),
            expansion_mode=self.config.vocabulary_mode,
        )
        # A broad deterministic candidate queue makes cooldown avoidance practical
        # without permanently consuming the combinatorial generator.
        total_weight = self.config.cheeky_weight + self.config.absurd_weight
        cheeky_needed = round(self.config.slate_size * self.config.cheeky_weight / total_weight)
        needed = {"cheeky": cheeky_needed, "absurd": self.config.slate_size - cheeky_needed}
        pool_size = self.config.candidates_per_style
        stage = monotonic()
        try:
            candidates = {
                style: generator.generate(pool_size, style)
                for style in ("cheeky", "absurd")
            }
        except ValueError as exc:
            self.release(selection_key)
            raise NameSelectionExhausted(
                "Not enough invented names are currently available. Please try MUNGE IT again."
            ) from exc
        self.last_metrics["candidate_ms"] = round((monotonic() - stage) * 1000, 2)

        stage = monotonic()
        candidate_ids = [key for style in ("cheeky", "absurd")
                         for candidate in candidates[style]
                         for key in (normalized(candidate.name),
                                     family_record("name", self._family(candidate)))]
        existing = {doc["_id"]: doc for doc in self.collection.find(
            {"_id": {"$in": candidate_ids}},
            {"_id": 1, "last_used_at": 1, "offered_by": 1,
             "offer_until": 1, "use_count": 1},
        )}
        self.last_metrics["availability_reads"] = 1
        memory_enabled = semantic_memory_enabled(self.config.semantic_memory_mode)

        def available(candidate):
            doc = existing.get(normalized(candidate.name))
            if not doc:
                return True
            last_used = self._utc(doc.get("last_used_at"))
            leased_until = self._utc(doc.get("offer_until"))
            cooling = last_used and last_used > cooldown_cutoff
            leased = (doc.get("offered_by") != selection_key and leased_until
                      and leased_until > now)
            return not cooling and not leased

        recent_families = recent_families or {}

        def recency(candidate):
            doc = existing.get(normalized(candidate.name), {})
            family_penalty = (recency_penalty(
                existing.get(family_record("name", self._family(candidate))), now,
                self.config.cooldown_days,
            ) if memory_enabled else 0.0)
            topic_penalty = recent_families.get(
                name_topic_family(candidate.name, self._family(candidate)), 0)
            return (max(family_penalty, topic_penalty), self._utc(doc.get("last_used_at")) or
                    datetime.min.replace(tzinfo=timezone.utc),
                    doc.get("use_count", 0))

        eligible = {}
        for style in ("cheeky", "absurd"):
            eligible[style] = [candidate for candidate in candidates[style]
                               if available(candidate)]
            eligible[style].sort(key=recency)
            if len(eligible[style]) < needed[style]:
                self.release(selection_key)
                raise NameSelectionExhausted(
                    "Not enough invented names are currently available. Please try MUNGE IT again."
                )
        self.last_metrics["filter_ms"] = round((monotonic() - stage) * 1000, 2)
        stage = monotonic()
        selected = []
        for style in ("cheeky", "absurd"):
            acquired = 0
            for candidate in eligible[style]:
                if self._acquire(candidate, selection_key, now, offer_until, cooldown_cutoff):
                    selected.append(candidate.name)
                    acquired += 1
                if acquired == needed[style]:
                    break
            if acquired != needed[style]:
                break
        if len(selected) == self.config.slate_size:
            self._offered_families[selection_key] = {
                candidate.name: self._family(candidate)
                for style in ("cheeky", "absurd") for candidate in eligible[style]
                if candidate.name in selected
            }
            self.last_metrics["lease_ms"] = round((monotonic() - stage) * 1000, 2)
            self.last_metrics["total_ms"] = round((monotonic() - started) * 1000, 2)
            return selected
        self.release(selection_key)
        raise NameSelectionExhausted(
            "Not enough invented names are currently available. Please try MUNGE IT again."
        )

    def offered_family_map(self, selection_key):
        return dict(self._offered_families.get(selection_key, {}))

    def accept(self, selection_key: str, rewrite_id: str, names: list[str], title: str, body: str):
        text = f"{title}\n{body}"
        used = [name for name in names if re.search(
            rf"(?<!\w){re.escape(name)}(?!\w)", text, flags=re.IGNORECASE
        )]
        now = self.now()
        families = set()
        for name in used:
            self.collection.update_one(
                {"_id": normalized(name), "offered_by": selection_key},
                {"$set": {"last_used_at": now, "last_rewrite_id": rewrite_id,
                          "display_name": name},
                 "$inc": {"use_count": 1},
                 "$unset": {"offered_by": "", "offer_until": ""}},
            )
            family = self._offered_families.get(selection_key, {}).get(name)
            if semantic_memory_enabled(self.config.semantic_memory_mode) and family:
                families.add(family)
        unused = [normalized(name) for name in names if name not in used]
        if unused:
            self.collection.update_many(
                {"_id": {"$in": unused}, "offered_by": selection_key},
                {"$unset": {"offered_by": "", "offer_until": ""}},
            )
        for family in families:
            record_family_use(self.collection, family_record("name", family), now,
                              rewrite_id, semantic_family=family)
        self._offered_families.pop(selection_key, None)
        return used

    def release(self, selection_key: str):
        self._offered_families.pop(selection_key, None)
        self.collection.update_many(
            {"offered_by": selection_key},
            {"$unset": {"offered_by": "", "offer_until": ""}},
        )
