#!/usr/bin/env python3
"""Provider-free 500-generation audit for Phase 4N domain selection."""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import json
import random
from statistics import mean, pstdev
from types import SimpleNamespace

from pymongo.errors import DuplicateKeyError

from newsmuncher.services.thematic_diversity import (
    ThematicDiversityConfig, ThematicDiversityMemory, load_domains, thematic_event,
)


class MemoryCollection:
    def __init__(self): self.docs = {}

    def find_one(self, query, projection=None):
        value = self.docs.get(query.get("_id"))
        return deepcopy(value) if value else None

    def update_one(self, query, update, upsert=False):
        key = query["_id"]; document = self.docs.get(key)
        rewrite_id = query.get("events.rewrite_id", {}).get("$ne")
        if document and rewrite_id in {x["rewrite_id"] for x in document.get("events", [])}:
            return SimpleNamespace(matched_count=0, upserted_id=None)
        if document is None:
            if key in self.docs: raise DuplicateKeyError("collision")
            document = {"_id": key, **deepcopy(update.get("$setOnInsert", {}))}
            self.docs[key] = document; inserted = True
        else: inserted = False
        spec = update["$push"]["events"]
        document.setdefault("events", []).extend(deepcopy(spec["$each"]))
        document["events"] = document["events"][spec["$slice"]:]
        return SimpleNamespace(matched_count=0 if inserted else 1,
                               upserted_id=key if inserted else None)


def _rolling_repeat(sets, window):
    values = []
    for index, current in enumerate(sets):
        previous = set().union(*sets[max(0, index - window):index]) if index else set()
        values.append(len(current & previous))
    return round(mean(values), 3)


def evaluate(generations=500, seed="phase4n-final"):
    collection = MemoryCollection()
    config = ThematicDiversityConfig("evaluation", 4, 20)
    selected_sets, baseline_sets = [], []
    domain_counts, family_counts, family_sets = Counter(), Counter(), []
    catalogue = list(load_domains())
    for index in range(generations):
        memory = ThematicDiversityMemory(collection, "audit-pet", config)
        memory.load(); selected = memory.select(f"{seed}:{index}")
        selected_sets.append({item["id"] for item in selected})
        family_sets.append({item["family"] for item in selected})
        domain_counts.update(item["id"] for item in selected)
        family_counts.update(item["family"] for item in selected)
        memory.record(thematic_event(f"rewrite-{index}", selected))
        digest = hashlib.sha256(f"{seed}:{index}".encode()).digest()
        baseline_rng = random.Random(int.from_bytes(digest[:8], "big"))
        baseline_sets.append({item["id"] for item in baseline_rng.sample(catalogue, 4)})
    values = list(domain_counts.values())
    total = sum(values)
    return {
        "generations": generations,
        "domains_available": len(load_domains()),
        "domains_seen": len(domain_counts),
        "families_seen": len(family_counts),
        "selections": total,
        "domain_min": min(values), "domain_max": max(values),
        "domain_mean": round(mean(values), 3),
        "domain_coefficient_of_variation": round(pstdev(values) / mean(values), 4),
        "largest_domain_share": round(max(values) / total, 4),
        "largest_family_share": round(max(family_counts.values()) / total, 4),
        "rolling_five_domain_repeats": _rolling_repeat(selected_sets, 5),
        "rolling_ten_domain_repeats": _rolling_repeat(selected_sets, 10),
        "uniform_baseline_rolling_five_repeats": _rolling_repeat(baseline_sets, 5),
        "uniform_baseline_rolling_ten_repeats": _rolling_repeat(baseline_sets, 10),
        "mean_families_per_generation": round(mean(map(len, family_sets)), 3),
        "stored_events": len(next(iter(collection.docs.values()))["events"]),
        "family_distribution": dict(sorted(family_counts.items())),
        "domain_distribution": dict(sorted(domain_counts.items())),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--generations", type=int, default=500)
    parser.add_argument("--seed", default="phase4n-final")
    args = parser.parse_args()
    print(json.dumps(evaluate(args.generations, args.seed), indent=2))


if __name__ == "__main__":
    main()
