"""Generated-concept leases and accepted-use cooldowns."""
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from collections import Counter
import os, re
from time import monotonic
from pymongo.errors import DuplicateKeyError
from newsmuncher.services.comedy_concepts import (
    ComedyConceptGenerator, animal_mentions, normalised,
)
from newsmuncher.services.semantic_memory import (
    family_record, record_family_use, semantic_memory_enabled,
)
from newsmuncher.services.noun_exclusion import (
    blocked_entries, compile_exclusion_index, phrase_found,
)

CONCEPT_GUIDANCE = """GENERATED-CONCEPT RULES:
- Generated concepts are optional; use roughly two to four only where natural.
- Preserve the source story's central meaning and recognisable structure.
- Keep each concept coherent; never splice several concepts into one phrase.
- Give creatures and objects appropriate roles and avoid repeating one joke."""
PHYSICAL_CATEGORIES = {"everyday_british", "cheeky_object", "absurd_invention",
                       "emergency_equipment", "ceremonial_object"}
TARGET_QUOTAS = {
    "nouns": {"everyday_british": 1, "cheeky_object": 2, "absurd_invention": 2,
              "bureaucratic_nonsense": 3, "emergency_equipment": 1,
              "ceremonial_object": 1},
    "animals": {"everyday_british": 2, "cheeky_object": 2,
                "absurd_invention": 2, "ridiculous_creature": 4},
}


class ConceptSelectionExhausted(RuntimeError):
    """The bounded local search could not assemble a complete leased slate."""

@dataclass(frozen=True)
class ConceptSelectionConfig:
    mode: str = "generated"
    cooldown_days: int = 30
    offer_minutes: int = 15
    vocabulary_mode: str = "off"
    semantic_memory_mode: str = "off"
    @classmethod
    def from_environment(cls):
        mode = os.getenv("NEWSMUNCHER_CONCEPT_MODE", "generated").strip().lower()
        return cls(mode, int(os.getenv("NEWSMUNCHER_CONCEPT_COOLDOWN_DAYS", "30")),
                   int(os.getenv("NEWSMUNCHER_CONCEPT_OFFER_MINUTES", "15")),
                   os.getenv("NEWSMUNCHER_EXPANDED_VOCABULARY", "off").strip().lower(),
                   os.getenv("NEWSMUNCHER_COMEDY_SEMANTIC_MEMORY", "off").strip().lower())
    def __post_init__(self):
        if self.mode not in {"generated", "legacy"}:
            raise ValueError("NEWSMUNCHER_CONCEPT_MODE must be 'generated' or 'legacy'")
        if self.cooldown_days < 0 or self.offer_minutes < 1:
            raise ValueError("Invalid concept-selection limits")
        if self.vocabulary_mode not in {"off", "reviewed", "evaluation"}:
            raise ValueError(
                "NEWSMUNCHER_EXPANDED_VOCABULARY must be off, reviewed or evaluation"
            )
        semantic_memory_enabled(self.semantic_memory_mode)

class ConceptRegistry:
    def __init__(self, collection, config=None, now=None):
        self.collection, self.config = collection, config or ConceptSelectionConfig()
        self.now = now or (lambda: datetime.now(timezone.utc))
        self.last_metrics = {}

    @staticmethod
    def _utc(value):
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @staticmethod
    def _record_ids(item):
        ids = ["phrase:" + normalised(item.phrase), "base:" + normalised(item.base),
               "premise:" + normalised(item.premise_key)]
        if item.animal_species:
            ids.append("animal:" + normalised(item.animal_species))
        return ids

    @staticmethod
    def _family_id(item):
        return family_record("concept", item.comic_mechanism)
    def candidates(self, key, lexical_penalties=None):
        return self._candidates(key, lexical_penalties)

    def _candidates(self, key, lexical_penalties=None,
                    noun_exclusions=(), source_text="", component_filter_cache=None):
        """Build a broad deterministic queue for every semantic quota.

        Category-specific pools avoid making a scarce 5% category depend on its
        handful of entries in one small mixed slate.  The search remains bounded,
        reproducible and local while providing ample cooldown/collision headroom.
        """
        component_filter_cache = (component_filter_cache
                                  if component_filter_cache is not None else {})
        exclusion_index = (compile_exclusion_index(noun_exclusions, source_text)
                           if noun_exclusions else None)
        result = []
        for target, quotas in TARGET_QUOTAS.items():
            for category, quota in quotas.items():
                # Once source components are exclusion-aware, generating thirty
                # doomed variations per quota is unnecessary. Keep deterministic
                # headroom proportional to the slots the category must fill.
                count = max(4, quota * 2) if noun_exclusions else 30
                generator = ComedyConceptGenerator(
                    f"{key}:{target}:{category}",
                    vocabulary_mode=self.config.vocabulary_mode,
                    lexical_penalties=lexical_penalties,
                    noun_exclusions=noun_exclusions,
                    source_text=source_text,
                    target_bank=(target if noun_exclusions else None),
                    component_filter_cache=component_filter_cache,
                    exclusion_index=exclusion_index,
                )
                result.extend((item, target) for item in generator.generate(
                    count, category=category))
        return result

    def _acquire(self, record_id, selection_key, now, until, fields, enforce_cooldown=True):
        clauses = [{"$or": [{"offered_by": selection_key}, {"offer_until": {"$exists": False}},
                              {"offer_until": {"$lte": now}}]}]
        if enforce_cooldown:
            cutoff = now - timedelta(days=self.config.cooldown_days)
            clauses.insert(0, {"$or": [{"last_used_at": {"$exists": False}},
                                         {"last_used_at": {"$lte": cutoff}}]})
        try:
            result = self.collection.update_one(
                {"_id": record_id, "$and": clauses},
                {"$setOnInsert": {"version": 1}, "$set": {
                    **fields, "offered_by": selection_key, "offer_until": until,
                }}, upsert=True,
            )
        except DuplicateKeyError:
            return False
        return bool(result.matched_count or result.upserted_id is not None)

    def _offer(self, selection_key, candidates, now, until, enforce_diversity_cooldown,
               category_quota_slack=0):
        selected = []
        target_counts = {"nouns": 0, "animals": 0}
        category_counts = {target: {category: 0 for category in quotas}
                           for target, quotas in TARGET_QUOTAS.items()}
        selected_bases = set()
        selected_premises = set()
        for item, target in candidates:
            quota = TARGET_QUOTAS[target][item.category]
            if (target_counts[target] == 10 or
                    category_counts[target][item.category] >= quota + category_quota_slack or
                    normalised(item.base) in selected_bases or
                    item.premise_key in selected_premises):
                continue
            ids = self._record_ids(item)
            common = {"phrase": item.phrase, "normalized_phrase": normalised(item.phrase),
                      "base": item.base, "premise_key": item.premise_key,
                      "semantic_theme": item.semantic_theme, "category": item.category,
                      "intensity": item.intensity, "generator_version": item.generator_version,
                      "target_bank": target, "position": len(selected)}
            acquired = []
            record_types = ("phrase", "base", "premise", "animal")
            for record_id, record_type in zip(ids, record_types):
                strict = record_type == "phrase" or enforce_diversity_cooldown
                self.last_metrics["lease_writes"] += 1
                if not self._acquire(record_id, selection_key, now, until,
                                     {**common, "record_type": record_type}, strict):
                    break
                acquired.append(record_id)
            if len(acquired) != len(ids):
                if acquired:
                    self.collection.update_many(
                        {"_id": {"$in": acquired}, "offered_by": selection_key},
                        {"$unset": {"offered_by": "", "offer_until": ""}},
                    )
                continue
            selected.append({**asdict(item), "target_bank": target})
            target_counts[target] += 1
            category_counts[target][item.category] += 1
            selected_bases.add(normalised(item.base)); selected_premises.add(item.premise_key)
            if target_counts == {"nouns": 10, "animals": 10}:
                return selected
        self.release(selection_key)
        return None

    @staticmethod
    def _can_fill(candidates):
        """Cheaply prove the deterministic queue can satisfy every hard quota."""
        target_counts = {"nouns": 0, "animals": 0}
        category_counts = {target: {category: 0 for category in quotas}
                           for target, quotas in TARGET_QUOTAS.items()}
        bases, premises = set(), set()
        for item, target in candidates:
            if (target_counts[target] == 10 or
                    category_counts[target][item.category] >= TARGET_QUOTAS[target][item.category] or
                    normalised(item.base) in bases or item.premise_key in premises):
                continue
            target_counts[target] += 1
            category_counts[target][item.category] += 1
            bases.add(normalised(item.base)); premises.add(item.premise_key)
        return target_counts == {"nouns": 10, "animals": 10}

    def offer(self, selection_key, recent_offers=None, lexical_penalties=None,
              noun_exclusions=(), source_text=""):
        started = monotonic()
        now = self.now(); until = now + timedelta(minutes=self.config.offer_minutes)
        self.last_metrics = {"candidate_ms": 0.0, "filter_ms": 0.0,
                             "lease_ms": 0.0, "availability_reads": 0,
                             "lease_writes": 0, "relaxed": False,
                             "category_quota_slack": 0,
                             "candidate_batches": 1,
                             "vocabulary_mode": self.config.vocabulary_mode,
                             "lexical_penalty_terms": len(lexical_penalties or {})}
        try:
            stage = monotonic()
            component_filter_cache = {}
            exclusion_index = (compile_exclusion_index(noun_exclusions, source_text)
                               if noun_exclusions else None)
            candidates = (self._candidates(
                selection_key, lexical_penalties, noun_exclusions, source_text,
                component_filter_cache)
                if noun_exclusions else
                (self.candidates(selection_key, lexical_penalties)
                 if lexical_penalties else self.candidates(selection_key)))

            excluded_count = 0
            rejection_reasons = Counter()
            batch_diagnostics = []

            def eligible(values, label):
                nonlocal excluded_count
                result = []
                rejected = Counter()
                for item, target in values:
                    matches = blocked_entries(
                        item.phrase, noun_exclusions, source_text, exclusion_index)
                    if "premise:" + item.premise_key in noun_exclusions:
                        matches.append("premise:" + item.premise_key)
                    if matches:
                        excluded_count += 1
                        rejected.update(value.split(":", 1)[0] for value in matches)
                        rejection_reasons.update(
                            value.split(":", 1)[0] for value in matches)
                    else:
                        result.append((item, target))
                batch_diagnostics.append({
                    "batch": label, "generated": len(values),
                    "eligible": len(result), "rejected": dict(rejected),
                })
                return result

            candidates = eligible(candidates, "initial")
            # A single category-specific batch can appear viable before exact
            # phrase cooldowns are read, then lose a required slot afterwards.
            # Build bounded deterministic headroom whenever exclusions apply;
            # exclusions, exact cooldowns and quotas all stay hard.
            seen = {(target, normalised(item.phrase)) for item, target in candidates}
            for batch in range(1, 5):
                if not noun_exclusions:
                    break
                refill_key = f"{selection_key}:noun-refill:{batch}"
                refill = self._candidates(
                    refill_key, lexical_penalties, noun_exclusions, source_text,
                    component_filter_cache)
                for item, target in eligible(refill, f"refill_{batch}"):
                    fingerprint = (target, normalised(item.phrase))
                    if fingerprint not in seen:
                        seen.add(fingerprint)
                        candidates.append((item, target))
            self.last_metrics["candidate_batches"] = len(batch_diagnostics)
            self.last_metrics["noun_exclusion_rejected"] = excluded_count
            self.last_metrics["hard_rejection_reasons"] = dict(rejection_reasons)
            self.last_metrics["candidate_batch_diagnostics"] = batch_diagnostics
            self.last_metrics["hard_eligible_by_category"] = dict(Counter(
                f"{target}/{item.category}" for item, target in candidates))
            self.last_metrics["candidate_ms"] = round((monotonic() - stage) * 1000, 2)
        except ValueError as exc:
            self.release(selection_key)
            raise ConceptSelectionExhausted(
                "Not enough generated concepts are currently available. Please try MUNGE IT again."
            ) from exc
        stage = monotonic()
        candidate_ids = list({record_id for item, _target in candidates
                              for record_id in self._record_ids(item)})
        existing = {doc["_id"]: doc for doc in self.collection.find(
            {"_id": {"$in": candidate_ids}},
            {"_id": 1, "last_used_at": 1, "offered_by": 1,
             "offer_until": 1, "use_count": 1},
        )}
        self.last_metrics["availability_reads"] = 1
        cutoff = now - timedelta(days=self.config.cooldown_days)

        def available(record_id, enforce_cooldown=True):
            doc = existing.get(record_id)
            if not doc:
                return True
            last_used = self._utc(doc.get("last_used_at"))
            offer_until = self._utc(doc.get("offer_until"))
            cooled = enforce_cooldown and last_used and last_used > cutoff
            leased = (doc.get("offered_by") != selection_key and offer_until
                      and offer_until > now)
            return not cooled and not leased

        recent_offers = recent_offers or {}

        def recency(item):
            records = [existing.get(record_id, {}) for record_id in self._record_ids(item)]
            dates = [self._utc(doc.get("last_used_at")) for doc in records
                     if doc.get("last_used_at")]
            offer_penalty = max((recent_offers.get(record_id, 0)
                                 for record_id in self._record_ids(item)), default=0)
            return (offer_penalty,
                    max(dates) if dates else datetime.min.replace(tzinfo=timezone.utc),
                    sum(doc.get("use_count", 0) for doc in records))

        strict_candidates = [(item, target) for item, target in candidates
                             if all(available(record_id) for record_id in self._record_ids(item))]
        self.last_metrics["strict_cooldown_rejected"] = (
            len(candidates) - len(strict_candidates))
        strict_candidates.sort(key=lambda pair: recency(pair[0]))
        self.last_metrics["filter_ms"] = round((monotonic() - stage) * 1000, 2)
        stage = monotonic()
        selected = (self._offer(selection_key, strict_candidates, now, until, True)
                    if self._can_fill(strict_candidates) else None)
        if selected is None:
            print(f"[concepts] {selection_key} relaxing saturated base/premise cooldown")
            self.last_metrics["relaxed"] = True
            # Exact phrase cooldown and every active lease remain strict. Only
            # historical ingredient cooldown is relaxed, ordered oldest first.
            relaxed = [(item, target) for item, target in candidates
                       if available("phrase:" + normalised(item.phrase))
                       and all(available(record_id, False)
                               for record_id in self._record_ids(item)[1:])]
            relaxed.sort(key=lambda pair: recency(pair[0]))
            self.last_metrics["relaxed_eligible_by_category"] = dict(Counter(
                f"{target}/{item.category}" for item, target in relaxed))
            self.last_metrics["exact_or_active_rejected"] = len(candidates) - len(relaxed)
            selected = self._offer(selection_key, relaxed, now, until, False)
            if selected is None and noun_exclusions:
                print(f"[concepts] {selection_key} relaxing category quotas after "
                      "hard-exclusion shortage")
                for slack in range(1, 10):
                    selected = self._offer(
                        selection_key, relaxed, now, until, False,
                        category_quota_slack=slack,
                    )
                    if selected is not None:
                        self.last_metrics["category_quota_slack"] = slack
                        break
        self.last_metrics["lease_ms"] = round((monotonic() - stage) * 1000, 2)
        self.last_metrics["total_ms"] = round((monotonic() - started) * 1000, 2)
        if selected is None or len(selected) != 20:
            self.last_metrics["required_quotas"] = {
                f"{target}/{category}": quota
                for target, quotas in TARGET_QUOTAS.items()
                for category, quota in quotas.items()
            }
            self.last_metrics["active_candidate_leases"] = sum(
                1 for item, _target in candidates
                if any((existing.get(record_id, {}).get("offered_by") != selection_key
                        and self._utc(existing.get(record_id, {}).get("offer_until"))
                        and self._utc(existing.get(record_id, {}).get("offer_until")) > now)
                       for record_id in self._record_ids(item))
            )
            self.release(selection_key)
            print(f"[concepts] selection exhausted for {selection_key}; released partial slate")
            raise ConceptSelectionExhausted(
                "Not enough generated concepts are currently available. Please try MUNGE IT again."
            )
        print("[concepts] offered " + "; ".join(f"{x['target_bank']}:{x['phrase']} ({x['category']}, intensity {x['intensity']})" for x in selected))
        return selected
    @staticmethod
    def _contains(text, value):
        return phrase_found(text, value)

    def accept(self, selection_key, rewrite_id, concepts, title, body, source_text=""):
        started = monotonic()
        text, used, now = f"{title}\n{body}", [], self.now()
        source_animals = animal_mentions(source_text)
        accepted_animals = animal_mentions(text) - source_animals
        decisions = []
        for item in concepts:
            animal = item.get("animal_species")
            decisions.append((
                item,
                self._contains(text, item["phrase"]),
                self._contains(text, item["base"]),
                bool(animal and self._contains(text, animal)
                     and not self._contains(source_text, animal)),
            ))
        matching_ms = round((monotonic() - started) * 1000, 2)
        update_started = monotonic()
        touched = set()
        family_uses = set()
        for item, exact, base_used, offered_animal_used in decisions:
            phrase_id = "phrase:" + normalised(item["phrase"])
            base_id = "base:" + normalised(item["base"])
            premise_id = "premise:" + normalised(item["premise_key"])
            animal = item.get("animal_species")
            animal_id = "animal:" + normalised(animal) if animal else None
            ids = []
            if exact:
                ids.extend((phrase_id, premise_id))
                used.append(item["phrase"])
            if base_used and (not animal or animal not in source_animals):
                ids.append(base_id)
            if animal and (animal in accepted_animals or offered_animal_used):
                ids.append(animal_id)
            ids = list(dict.fromkeys(ids))
            if ids:
                self.collection.update_many({"_id": {"$in": ids}, "offered_by": selection_key},
                    {"$set": {"last_used_at": now, "last_rewrite_id": rewrite_id},
                     "$inc": {"use_count": 1}, "$unset": {"offered_by": "", "offer_until": ""}})
                touched.update(ids)
            if semantic_memory_enabled(self.config.semantic_memory_mode) and (exact or base_used):
                family_uses.add((family_record("concept", item["comic_mechanism"]),
                                 item["comic_mechanism"], item["semantic_theme"]))
        # A rewrite may independently introduce a known animal. Record it only
        # after persistence, and never count an animal required by the source.
        for animal in accepted_animals:
            record_id = "animal:" + normalised(animal)
            if record_id in touched:
                continue
            self.collection.update_one(
                {"_id": record_id},
                {"$setOnInsert": {"version": 1, "record_type": "animal",
                                  "animal_species": animal},
                 "$set": {"last_used_at": now, "last_rewrite_id": rewrite_id},
                 "$inc": {"use_count": 1}},
                upsert=True,
            )
        for record_id, mechanism, theme in family_uses:
            record_family_use(self.collection, record_id, now, rewrite_id,
                              comic_mechanism=mechanism, semantic_theme=theme)
        self.release(selection_key)
        self.last_accept_metrics = {
            "matching_ms": matching_ms,
            "cooldown_and_release_ms": round((monotonic() - update_started) * 1000, 2),
            "accepted_animals": len(accepted_animals),
        }
        print(f"[concepts] used={used}; animals={sorted(accepted_animals)}")
        return used
    def release(self, selection_key):
        return self.collection.update_many({"offered_by": selection_key},
                                           {"$unset": {"offered_by": "", "offer_until": ""}})
