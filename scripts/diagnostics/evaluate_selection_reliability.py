"""Offline Phase 3G endurance audit for all generated selection registries."""
from __future__ import annotations

from collections import Counter
import contextlib
from datetime import datetime, timezone
import io
import random
from statistics import mean
from time import monotonic

from scripts.diagnostics.evaluate_comedy_diversity import OfflineCollection
from newsmuncher.services.concept_selection import ConceptRegistry
from newsmuncher.services.descriptor_selection import DescriptorRegistry
from newsmuncher.services.name_selection import InventedNameRegistry


class CountingCollection(OfflineCollection):
    def __init__(self):
        super().__init__()
        self.operations = Counter()

    def find(self, *args, **kwargs):
        self.operations["find"] += 1
        return super().find(*args, **kwargs)

    def update_one(self, *args, **kwargs):
        self.operations["update_one"] += 1
        return super().update_one(*args, **kwargs)

    def update_many(self, *args, **kwargs):
        self.operations["update_many"] += 1
        return super().update_many(*args, **kwargs)


def run(rewrites=250, seed="phase3g-final"):
    rng = random.Random(seed)
    now = lambda: datetime(2026, 10, 10, tzinfo=timezone.utc)
    collections = {key: CountingCollection() for key in ("names", "concepts", "descriptors")}
    names = InventedNameRegistry(collections["names"], now=now)
    concepts = ConceptRegistry(collections["concepts"], now=now)
    descriptors = DescriptorRegistry(collections["descriptors"], now=now)
    offered_names, elapsed = [], []
    checkpoints, failures = {}, []
    log = io.StringIO()
    with contextlib.redirect_stdout(log):
        for number in range(rewrites):
            key = f"pet:rewrite-{number}"
            started = monotonic()
            try:
                name_slate = names.offer(key)
                concept_slate = concepts.offer(key)
                descriptor_slate = descriptors.offer(key)
                # A genuine retry of the active attempt must be stable.
                if number in (0, 9, 24, 49, 99, 249):
                    assert names.offer(key) == name_slate
                offered_names.extend(name_slate)
                used_names = rng.sample(name_slate, rng.randint(2, 4))
                used_concepts = rng.sample(concept_slate, rng.randint(2, 4))
                used_descriptors = rng.sample(descriptor_slate, rng.randint(2, 4))
                names.accept(key, f"rewrite-{number}", name_slate,
                             used_names[0], " | ".join(used_names[1:]))
                concepts.accept(key, f"rewrite-{number}", concept_slate,
                                "", " | ".join(item["phrase"] for item in used_concepts))
                descriptors.accept(key, f"rewrite-{number}", descriptor_slate,
                                   "", " | ".join(item["phrase"] for item in used_descriptors))
            except Exception as exc:  # diagnostic records the exact bounded failure
                failures.append((number + 1, type(exc).__name__, str(exc)))
                break
            elapsed.append((monotonic() - started) * 1000)
            if number + 1 in (10, 25, 50, 100, 250):
                counts = Counter(offered_names)
                checkpoints[number + 1] = {
                    "successful": number + 1,
                    "unique_names": len(counts),
                    "repeated_name_occurrences": len(offered_names) - len(counts),
                    "average_selection_ms": round(mean(elapsed), 2),
                    "maximum_selection_ms": round(max(elapsed), 2),
                }
    return {
        "seed": seed,
        "requested_rewrites": rewrites,
        "successful_rewrites": len(elapsed),
        "controlled_or_unexpected_failures": failures,
        "checkpoints": checkpoints,
        "operations": {key: dict(value.operations) for key, value in collections.items()},
        "cooldown_relaxations": {
            "concepts": log.getvalue().count("relaxing saturated base/premise"),
            "descriptors": log.getvalue().count("relaxing saturated subject"),
            "names": 0,
        },
    }


if __name__ == "__main__":
    from pprint import pprint
    pprint(run(), sort_dicts=False)
