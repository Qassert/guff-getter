"""Generated comedy-descriptor leases and accepted-use cooldowns."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import os
import re
from time import monotonic

from pymongo.errors import DuplicateKeyError

from newsmuncher.services.comedy_descriptors import (
    assemble_descriptor_slate, descriptor_candidate_pool, normalised,
)
from newsmuncher.services.semantic_memory import (
    descriptor_premise_family, descriptor_subject_anchor, family_record,
    recency_penalty, record_family_use, semantic_memory_enabled,
)
from newsmuncher.services.noun_exclusion import blocked_entries


DESCRIPTOR_GUIDANCE = """GENERATED-DESCRIPTOR RULES:
- These are optional: use roughly two to four where they fit naturally; never force all ten.
- Respect role tags: PRE before a noun or after a linking verb; PRED after a linking verb; POST after a noun; ADV after an action; BEHAV as an ongoing comma-delimited behaviour; CLAUSE as a clause.
- Rewrite surrounding grammar to fit one selected descriptor. Never stack several descriptors or obscure the source event."""

ROLE_TAGS = {
    "pre_noun": "PRE", "predicate": "PRED", "post_noun": "POST",
    "adverbial": "ADV", "behavioural": "BEHAV", "short_clause": "CLAUSE",
}


class DescriptorSelectionExhausted(RuntimeError):
    """The bounded local search could not atomically lease a complete slate."""


@dataclass(frozen=True)
class DescriptorSelectionConfig:
    mode: str = "generated"
    cooldown_days: int = 30
    offer_minutes: int = 15
    slate_size: int = 10
    candidate_slates: int = 50
    vocabulary_mode: str = "off"
    semantic_memory_mode: str = "off"

    @classmethod
    def from_environment(cls):
        return cls(
            mode=os.getenv("NEWSMUNCHER_DESCRIPTOR_MODE", "generated").strip().lower(),
            cooldown_days=int(os.getenv("NEWSMUNCHER_DESCRIPTOR_COOLDOWN_DAYS", "30")),
            offer_minutes=int(os.getenv("NEWSMUNCHER_DESCRIPTOR_OFFER_MINUTES", "15")),
            vocabulary_mode=os.getenv("NEWSMUNCHER_EXPANDED_DESCRIPTORS", "off").strip().lower(),
            semantic_memory_mode=os.getenv("NEWSMUNCHER_COMEDY_SEMANTIC_MEMORY", "off").strip().lower(),
        )

    def __post_init__(self):
        if self.mode not in {"generated", "legacy"}:
            raise ValueError("NEWSMUNCHER_DESCRIPTOR_MODE must be 'generated' or 'legacy'")
        if self.cooldown_days < 0 or self.offer_minutes < 1 or self.slate_size != 10:
            raise ValueError("Invalid descriptor-selection limits")
        if self.candidate_slates < 1:
            raise ValueError("Descriptor candidate search must be positive")
        if self.vocabulary_mode not in {"off", "reviewed", "evaluation"}:
            raise ValueError("NEWSMUNCHER_EXPANDED_DESCRIPTORS must be off, reviewed or evaluation")
        semantic_memory_enabled(self.semantic_memory_mode)


def prompt_descriptor(item: dict) -> str:
    """Compact role annotation for the existing ten prompt slots."""
    return f"{item['phrase']} [{ROLE_TAGS[item['grammatical_role']]}]"


def _utc_datetime(value):
    """Return a Mongo datetime in comparable aware UTC form.

    PyMongo decodes BSON datetimes as naive UTC unless the client explicitly
    enables timezone-aware decoding.  Registry clocks are aware UTC, so the
    availability prefilter must normalize persisted values before comparing
    them in Python.
    """
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class DescriptorRegistry:
    """Lease both phrase and joke subject, rolling back partial acquisition."""

    def __init__(self, collection, config=None, now=None):
        self.collection = collection
        self.config = config or DescriptorSelectionConfig()
        self.now = now or (lambda: datetime.now(timezone.utc))
        self.last_metrics = {}

    def candidate_pool(self, selection_key, lexical_penalties=None):
        return descriptor_candidate_pool(
            f"{selection_key}:pool", self.config.slate_size, self.config.vocabulary_mode,
            lexical_penalties=lexical_penalties)

    def _acquire(self, record_id, selection_key, now, until, fields, enforce_cooldown=True):
        cutoff = now - timedelta(days=self.config.cooldown_days)
        clauses = [{"$or": [{"offered_by": selection_key}, {"offer_until": {"$exists": False}},
                              {"offer_until": {"$lte": now}}]}]
        if enforce_cooldown:
            clauses.insert(0, {"$or": [{"last_used_at": {"$exists": False}},
                                         {"last_used_at": {"$lte": cutoff}}]})
        query = {"_id": record_id, "$and": clauses}
        update = {"$setOnInsert": {"version": 1}, "$set": {
            **fields, "offered_by": selection_key, "offer_until": until,
        }}
        try:
            result = self.collection.update_one(query, update, upsert=True)
        except DuplicateKeyError:
            return False
        return bool(result.matched_count or result.upserted_id is not None)

    def offer(self, selection_key, avoid_themes=(), recent_offers=None,
              lexical_penalties=None, noun_exclusions=(), source_text=""):
        started = monotonic()
        now = self.now(); until = now + timedelta(minutes=self.config.offer_minutes)
        self.last_metrics = {"candidate_ms": 0.0, "filter_ms": 0.0,
                             "lease_ms": 0.0, "availability_reads": 0,
                             "lease_writes": 0, "relaxed": False,
                             "lexical_penalty_terms": len(lexical_penalties or {})}
        try:
            stage = monotonic()
            generated_pool = (self.candidate_pool(selection_key, lexical_penalties)
                              if lexical_penalties else self.candidate_pool(selection_key))
            before_exclusion = len(generated_pool)
            generated_pool = [item for item in generated_pool
                              if not blocked_entries(item.phrase, noun_exclusions, source_text)
                              and "premise:" + item.premise_key not in noun_exclusions]
            self.last_metrics["noun_exclusion_rejected"] = (
                before_exclusion - len(generated_pool))
            self.last_metrics["candidate_ms"] = round((monotonic() - stage) * 1000, 2)
            candidate_ids = list({key for item in generated_pool for key in (
                "phrase:" + normalised(item.phrase), "subject:" + normalised(item.subject),
                "premise:" + normalised(item.premise_key),
                family_record("descriptor", item.comic_mechanism),
                family_record("descriptor-premise", descriptor_premise_family(item)),
            )})
            stage = monotonic()
            existing = {doc["_id"]: doc for doc in self.collection.find(
                {"_id": {"$in": candidate_ids}},
                {"_id": 1, "last_used_at": 1, "offered_by": 1, "offer_until": 1},
            )}
            self.last_metrics["availability_reads"] = 1
            cutoff = now - timedelta(days=self.config.cooldown_days)
            memory_enabled = semantic_memory_enabled(self.config.semantic_memory_mode)
            family_penalties = {
                item.comic_mechanism: recency_penalty(existing.get(family_record(
                    "descriptor", item.comic_mechanism)), now, self.config.cooldown_days)
                for item in generated_pool
            } if memory_enabled else {}
            family_penalties.update(recent_offers or {})
            if memory_enabled:
                family_penalties.update({
                    "premise:" + item.premise_key: recency_penalty(existing.get(
                        family_record("descriptor-premise", descriptor_premise_family(item))),
                        now, self.config.cooldown_days)
                    for item in generated_pool
                })

            def available(record_id, enforce_cooldown=True):
                doc = existing.get(record_id)
                if not doc:
                    return True
                last_used_at = _utc_datetime(doc.get("last_used_at"))
                offer_until = _utc_datetime(doc.get("offer_until"))
                cooled = (enforce_cooldown and last_used_at
                          and last_used_at > cutoff)
                leased = (doc.get("offered_by") != selection_key and
                          offer_until and offer_until > now)
                return not cooled and not leased

            strict_pool = [item for item in generated_pool
                           if available("phrase:" + normalised(item.phrase))
                           and available("subject:" + normalised(item.subject))
                           and available("premise:" + normalised(item.premise_key))]
            subject_cooldown = True
            try:
                assemble_descriptor_slate(
                    strict_pool, f"{selection_key}:viability", self.config.slate_size,
                    avoid_themes=avoid_themes,
                    diversify=self.config.vocabulary_mode == "evaluation",
                    family_penalties=family_penalties,
                )
                pool = strict_pool
            except RuntimeError:
                # Phrase cooldown remains strict. Subject cooldown is a diversity
                # preference and may relax only after the bounded pool proves
                # that all six grammar roles cannot otherwise be supplied.
                subject_cooldown = False
                self.last_metrics["relaxed"] = True
                pool = [item for item in generated_pool
                        if available("phrase:" + normalised(item.phrase))
                        and available("subject:" + normalised(item.subject), False)
                        and available("premise:" + normalised(item.premise_key), False)]
                print(f"[descriptors] {selection_key} relaxing saturated subject cooldown")
            self.last_metrics["filter_ms"] = round((monotonic() - stage) * 1000, 2)
            stage = monotonic()
            for attempt in range(self.config.candidate_slates):
                slate = assemble_descriptor_slate(
                    pool, f"{selection_key}:assembled:{attempt}", self.config.slate_size,
                    avoid_themes=avoid_themes,
                    diversify=self.config.vocabulary_mode == "evaluation",
                    family_penalties=family_penalties,
                )
                selected = []
                for position, item in enumerate(slate):
                    data = asdict(item)
                    phrase_key = "phrase:" + normalised(item.phrase)
                    subject_key = "subject:" + normalised(item.subject)
                    premise_key = "premise:" + normalised(item.premise_key)
                    common = {"phrase": item.phrase, "normalized_phrase": normalised(item.phrase),
                              "subject": item.subject, "normalized_subject": normalised(item.subject),
                              "semantic_theme": item.semantic_theme, "premise_key": item.premise_key,
                              "generator_version": item.generator_version, "position": position}
                    self.last_metrics["lease_writes"] += 1
                    if not self._acquire(phrase_key, selection_key, now, until,
                                         {**common, "record_type": "phrase", "metadata": data}):
                        self.release(selection_key); break
                    self.last_metrics["lease_writes"] += 1
                    if not self._acquire(subject_key, selection_key, now, until,
                                         {**common, "record_type": "subject"},
                                         enforce_cooldown=subject_cooldown):
                        self.release(selection_key); break
                    self.last_metrics["lease_writes"] += 1
                    if not self._acquire(premise_key, selection_key, now, until,
                                         {**common, "record_type": "premise"},
                                         enforce_cooldown=subject_cooldown):
                        self.release(selection_key); break
                    selected.append(data)
                if len(selected) == self.config.slate_size:
                    self.last_metrics["lease_ms"] = round((monotonic() - stage) * 1000, 2)
                    self.last_metrics["total_ms"] = round((monotonic() - started) * 1000, 2)
                    print("[descriptors] offered " + "; ".join(
                        f"{item['phrase']} [{ROLE_TAGS[item['grammatical_role']]}]" for item in selected))
                    return selected
        except (RuntimeError, ValueError) as exc:
            # Generator/search exhaustion is a controlled pre-provider failure,
            # never an unhandled 500 and never a reason to retain partial leases.
            self.release(selection_key)
            print(f"[descriptors] bounded candidate search failed for {selection_key}: {type(exc).__name__}")
            raise DescriptorSelectionExhausted(
                "Not enough generated descriptors are currently available. Please try MUNGE IT again."
            ) from exc
        self.release(selection_key)
        print(f"[descriptors] selection exhausted for {selection_key}; released partial leases")
        raise DescriptorSelectionExhausted(
            "Not enough generated descriptors are currently available. Please try MUNGE IT again."
        )

    @staticmethod
    def _used(item, text):
        # Deliberately conservative: punctuation outside the phrase and case are
        # ignored, while inflection and paraphrase are not guessed.
        return bool(re.search(rf"(?<!\w){re.escape(item['phrase'])}(?!\w)", text, re.I))

    def accept(self, selection_key, rewrite_id, descriptors, title, body, source_text=""):
        started = monotonic()
        text = f"{title}\n{body}"; now = self.now(); used = []
        decisions = []
        for item in descriptors:
            anchor = descriptor_subject_anchor(item["subject"])
            anchor_used = (len(anchor) >= 4 and bool(re.search(
                rf"(?<!\w){re.escape(anchor)}(?:s|es)?(?!\w)", text, re.I
            )) and not bool(re.search(
                rf"(?<!\w){re.escape(anchor)}(?:s|es)?(?!\w)", source_text, re.I
            )))
            decisions.append((item, self._used(item, text), bool(re.search(
                rf"(?<!\w){re.escape(item['subject'])}(?!\w)", text, re.I
            )) and not bool(re.search(
                rf"(?<!\w){re.escape(item['subject'])}(?!\w)", source_text, re.I
            )), anchor_used))
        matching_ms = round((monotonic() - started) * 1000, 2)
        update_started = monotonic()
        family_uses = set()
        premise_family_uses = set()
        for item, exact, subject_used, anchor_used in decisions:
            ids = ["phrase:" + normalised(item["phrase"]),
                   "subject:" + normalised(item["subject"]),
                   "premise:" + normalised(item["premise_key"])]
            used_ids = ids if exact else ids[1:] if subject_used else []
            if used_ids:
                self.collection.update_many(
                    {"_id": {"$in": used_ids}, "offered_by": selection_key},
                    {"$set": {"last_used_at": now, "last_rewrite_id": rewrite_id},
                     "$inc": {"use_count": 1},
                     "$unset": {"offered_by": "", "offer_until": ""}},
                )
                if exact:
                    used.append(item["phrase"])
                if semantic_memory_enabled(self.config.semantic_memory_mode):
                    family_uses.add((family_record("descriptor", item["comic_mechanism"]),
                                     item["comic_mechanism"], item["semantic_theme"]))
            if semantic_memory_enabled(self.config.semantic_memory_mode) and (
                    exact or subject_used or anchor_used):
                family = descriptor_premise_family(item)
                premise_family_uses.add((family_record("descriptor-premise", family), family))
        for record_id, mechanism, theme in family_uses:
            record_family_use(self.collection, record_id, now, rewrite_id,
                              comic_mechanism=mechanism, semantic_theme=theme)
        for record_id, family in premise_family_uses:
            record_family_use(self.collection, record_id, now, rewrite_id,
                              semantic_family=family)
        self.release(selection_key)
        self.last_accept_metrics = {
            "matching_ms": matching_ms,
            "cooldown_and_release_ms": round((monotonic() - update_started) * 1000, 2),
        }
        print(f"[descriptors] used={used}; released={len(descriptors) - len(used)}")
        return used

    def release(self, selection_key):
        return self.collection.update_many(
            {"offered_by": selection_key},
            {"$unset": {"offered_by": "", "offer_until": ""}},
        )
