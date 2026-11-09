"""Offline production-shaped diversity audit; never imports provider or database clients."""
from __future__ import annotations

import argparse
import contextlib
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import io
import random
from types import SimpleNamespace

from pymongo.errors import DuplicateKeyError

from newsmuncher.services.concept_selection import ConceptRegistry
from newsmuncher.services.descriptor_selection import DescriptorRegistry


class OfflineCollection:
    """Small Mongo update subset for deterministic simulations only."""
    def __init__(self): self.docs = {}
    @staticmethod
    def _apply(doc, update, inserted=False):
        if inserted: doc.update(deepcopy(update.get("$setOnInsert", {})))
        doc.update(deepcopy(update.get("$set", {})))
        for key, value in update.get("$inc", {}).items(): doc[key] = doc.get(key, 0) + value
        for key in update.get("$unset", {}): doc.pop(key, None)
    @staticmethod
    def _eligible(doc, query):
        if doc is None: return True
        clauses = query.get("$and")
        if not clauses: return doc.get("offered_by") == query.get("offered_by")
        for clause in clauses:
            alternatives = clause["$or"]
            if "last_used_at" in alternatives[-1]:
                cutoff = alternatives[-1]["last_used_at"]["$lte"]
                if doc.get("last_used_at") and doc["last_used_at"] > cutoff: return False
            elif "offer_until" in alternatives[-1]:
                now = alternatives[-1]["offer_until"]["$lte"]
                owner = alternatives[0]["offered_by"]
                if (doc.get("offered_by") != owner and doc.get("offer_until")
                        and doc["offer_until"] > now): return False
        return True
    def update_one(self, query, update, upsert=False):
        key = query["_id"]; doc = self.docs.get(key)
        if not self._eligible(doc, query):
            if upsert: raise DuplicateKeyError("busy")
            return SimpleNamespace(matched_count=0, upserted_id=None)
        inserted = doc is None; doc = self.docs.setdefault(key, {"_id": key})
        self._apply(doc, update, inserted)
        return SimpleNamespace(matched_count=0 if inserted else 1,
                               upserted_id=key if inserted else None)
    def update_many(self, query, update):
        ids = query.get("_id", {}).get("$in")
        count = 0
        for key, doc in self.docs.items():
            if ids is not None and key not in ids: continue
            if query.get("offered_by") is not None and doc.get("offered_by") != query["offered_by"]: continue
            self._apply(doc, update); count += 1
        return SimpleNamespace(modified_count=count)
    def find(self, query, projection=None):
        ids = set(query.get("_id", {}).get("$in", self.docs))
        return [deepcopy(doc) for key, doc in self.docs.items() if key in ids]


def _metric(items, field):
    counts = Counter(item[field] for item in items)
    return {
        "unique": len(counts), "repeated_occurrences": len(items) - len(counts),
        "top": counts.most_common(5),
    }


def _rolling_repetition(slates, field, width=10):
    values = []
    for start in range(max(1, len(slates) - width + 1)):
        window = [item[field] for slate in slates[start:start + width] for item in slate]
        values.append(len(window) - len(set(window)))
    return {"maximum": max(values, default=0), "average": round(sum(values) / len(values), 2) if values else 0}


def run(seed="phase3e", rewrites=100):
    rng = random.Random(seed)
    concepts = ConceptRegistry(OfflineCollection(), now=lambda: datetime(2026, 10, 9, tzinfo=timezone.utc))
    descriptors = DescriptorRegistry(OfflineCollection(), now=lambda: datetime(2026, 10, 9, tzinfo=timezone.utc))
    concept_slates, descriptor_slates = [], []
    exact_used = {"concepts": 0, "descriptors": 0}
    paraphrased = {"concepts": 0, "descriptors": 0}
    ignored = {"concepts": 0, "descriptors": 0}
    relaxed = {"concepts": 0, "descriptors": 0}
    checkpoints = {}
    log = io.StringIO()
    with contextlib.redirect_stdout(log):
        for number in range(rewrites):
            key = f"audit:{seed}:{number}"
            concept_slate = concepts.offer(key)
            dominant = [theme for theme, count in Counter(
                item["semantic_theme"] for item in concept_slate
            ).items() if count >= 3]
            descriptor_slate = descriptors.offer(key, dominant)
            concept_slates.append(concept_slate); descriptor_slates.append(descriptor_slate)

            # Realistic mixed outcome: 2–4 exact uses, one local paraphrase that
            # conservative tracking intentionally misses, and all others ignored.
            c_order = rng.sample(concept_slate, len(concept_slate)); d_order = rng.sample(descriptor_slate, len(descriptor_slate))
            c_exact = c_order[:rng.randint(2, 4)]; d_exact = d_order[:rng.randint(2, 4)]
            exact_used["concepts"] += len(c_exact); exact_used["descriptors"] += len(d_exact)
            paraphrased["concepts"] += 1; paraphrased["descriptors"] += 1
            ignored["concepts"] += len(concept_slate) - len(c_exact) - 1
            ignored["descriptors"] += len(descriptor_slate) - len(d_exact) - 1
            concepts.accept(key, f"rewrite-{number}", concept_slate,
                            " | ".join(item["phrase"] for item in c_exact), "paraphrased premise")
            descriptors.accept(key, f"rewrite-{number}", descriptor_slate,
                               " | ".join(item["phrase"] for item in d_exact), "paraphrased premise")
            if number + 1 in (10, 25, 50, 100):
                checkpoints[number + 1] = summarize(concept_slates, descriptor_slates)
    output = log.getvalue()
    relaxed["concepts"] = output.count("relaxing saturated base/premise")
    relaxed["descriptors"] = output.count("relaxing saturated subject")
    def editorial_examples(slates, count=15):
        all_items = [item for slate in slates for item in slate]
        selected, seen_phrases, seen_mechanisms = [], set(), set()
        for prefer_new_mechanism in (True, False):
            for item in all_items:
                if item["phrase"] in seen_phrases: continue
                if prefer_new_mechanism and item["comic_mechanism"] in seen_mechanisms: continue
                selected.append(item); seen_phrases.add(item["phrase"])
                seen_mechanisms.add(item["comic_mechanism"])
                if len(selected) == count: return selected
        return selected

    return {
        "seed": seed, "rewrites": rewrites, "checkpoints": checkpoints,
        "accepted_exact": exact_used, "paraphrased_untracked": paraphrased,
        "ignored": ignored, "cooldown_relaxations": relaxed,
        "examples": {
            "concepts": editorial_examples(concept_slates),
            "descriptors": editorial_examples(descriptor_slates),
        },
    }


def summarize(concept_slates, descriptor_slates):
    concepts = [item for slate in concept_slates for item in slate]
    descriptors = [item for slate in descriptor_slates for item in slate]
    return {
        "concepts": {field: _metric(concepts, field) for field in
                     ("phrase", "base", "template", "comic_mechanism", "semantic_theme", "premise_key")},
        "descriptors": {field: _metric(descriptors, field) for field in
                        ("phrase", "subject", "template", "comic_mechanism", "semantic_theme", "premise_key")},
        "rolling_ten": {
            "concept_phrases": _rolling_repetition(concept_slates, "phrase"),
            "concept_premises": _rolling_repetition(concept_slates, "premise_key"),
            "descriptor_phrases": _rolling_repetition(descriptor_slates, "phrase"),
            "descriptor_premises": _rolling_repetition(descriptor_slates, "premise_key"),
        },
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", default="phase3e")
    parser.add_argument("--rewrites", type=int, default=100)
    args = parser.parse_args()
    from pprint import pprint
    pprint(run(args.seed, args.rewrites), sort_dicts=False)


if __name__ == "__main__": main()
