"""Offline Phase 3F diversity/performance audit; no provider or database clients."""
from __future__ import annotations

from collections import Counter
import contextlib
from datetime import datetime, timezone
from statistics import mean
from time import monotonic
import io

from scripts.diagnostics.evaluate_comedy_diversity import OfflineCollection
from newsmuncher.services.concept_selection import ConceptRegistry
from newsmuncher.services.concept_selection import ConceptSelectionExhausted
from newsmuncher.services.comedy_concepts import normalised
from datetime import timedelta
from newsmuncher.services.descriptor_selection import DescriptorRegistry


class CountingCollection(OfflineCollection):
    def __init__(self):
        super().__init__(); self.operations = Counter()
    def find(self, *args, **kwargs):
        self.operations["find"] += 1
        return super().find(*args, **kwargs)
    def update_one(self, *args, **kwargs):
        self.operations["update_one"] += 1
        return super().update_one(*args, **kwargs)
    def update_many(self, *args, **kwargs):
        self.operations["update_many"] += 1
        return super().update_many(*args, **kwargs)


class SequentialConceptRegistry(ConceptRegistry):
    """Phase 3E selection shape for offline round-trip comparison only."""
    @staticmethod
    def _record_ids(item):
        return ["phrase:" + normalised(item.phrase), "base:" + normalised(item.base),
                "premise:" + normalised(item.premise_key)]

    def offer(self, selection_key):
        now = self.now(); until = now + timedelta(minutes=self.config.offer_minutes)
        self.last_metrics = {"lease_writes": 0}
        candidates = self.candidates(selection_key)
        selected = self._offer(selection_key, candidates, now, until, True)
        if selected is None:
            selected = self._offer(selection_key, candidates, now, until, False)
        if selected is None:
            raise ConceptSelectionExhausted("legacy sequential audit exhausted")
        return selected


def _window_metrics(values, width=10):
    windows = [values[index:index + width] for index in range(len(values) - width + 1)]
    return {
        "average_unique_per_ten": round(mean(len(set(window)) for window in windows), 2),
        "least_unique_per_ten": min(len(set(window)) for window in windows),
        "most_repeated": Counter(values).most_common(5),
    }


def _identity_metrics(values):
    counts = Counter(values)
    return {"unique": len(counts), "repeated_occurrences": len(values) - len(counts),
            "most_repeated": counts.most_common(5)}


def run(rewrites=100):
    now = lambda: datetime(2026, 10, 9, tzinfo=timezone.utc)
    baseline_animals, remembered_animals = [], []
    baseline_objects, remembered_objects = [], []
    baseline_subjects, remembered_subjects = [], []
    baseline_premises, remembered_premises = [], []
    # Baseline approximates the old blind spot: each paraphrased species is
    # accepted but no persistent registry sees it.
    with contextlib.redirect_stdout(io.StringIO()):
        for number in range(rewrites):
            registry = ConceptRegistry(CountingCollection(), now=now)
            offered = registry.offer(f"baseline:{number}")
            baseline_animals.append(next(item["animal_species"] for item in offered
                                         if item["animal_species"]))
            object_item = next(item for item in offered if not item["animal_species"])
            baseline_objects.append(object_item["base"])
            baseline_premises.append(object_item["premise_key"])
            descriptor = DescriptorRegistry(CountingCollection(), now=now).offer(
                f"baseline-descriptor:{number}"
            )[0]
            baseline_subjects.append(descriptor["subject"])
            baseline_premises.append(descriptor["premise_key"])

    concepts_collection = CountingCollection()
    descriptors_collection = CountingCollection()
    local_times = []
    sequential_collection = CountingCollection()
    with contextlib.redirect_stdout(io.StringIO()):
        for number in range(rewrites):
            key = f"sequential:{number}"
            registry = SequentialConceptRegistry(sequential_collection, now=now)
            offered = registry.offer(key)
            registry.accept(key, f"rewrite-{number}", offered, "",
                            " | ".join(item["phrase"] for item in offered[:3]))
    with contextlib.redirect_stdout(io.StringIO()):
        for number in range(rewrites):
            key = f"remembered:{number}"
            concepts = ConceptRegistry(concepts_collection, now=now)
            descriptors = DescriptorRegistry(descriptors_collection, now=now)
            started = monotonic(); offered = concepts.offer(key)
            animal = next(item["animal_species"] for item in offered if item["animal_species"])
            remembered_animals.append(animal)
            # Species-only wording models a paraphrase; object and descriptor
            # subjects model structured ingredient preservation.
            object_item = next(item for item in offered if not item["animal_species"])
            descriptor_slate = descriptors.offer(key)
            descriptor = descriptor_slate[0]
            remembered_objects.append(object_item["base"])
            remembered_subjects.append(descriptor["subject"])
            remembered_premises.extend((object_item["premise_key"], descriptor["premise_key"]))
            concepts.accept(key, f"rewrite-{number}", offered, "",
                            f"A {animal} disputed the {object_item['base']}.")
            descriptors.accept(key, f"rewrite-{number}", descriptor_slate, "",
                               f"The witness remained {descriptor['subject']}.")
            local_times.append((monotonic() - started) * 1000)

    return {
        "rewrites": rewrites,
        "baseline_animals": _window_metrics(baseline_animals),
        "remembered_animals": _window_metrics(remembered_animals),
        "baseline_objects": _identity_metrics(baseline_objects),
        "remembered_objects": _identity_metrics(remembered_objects),
        "baseline_descriptor_subjects": _identity_metrics(baseline_subjects),
        "remembered_descriptor_subjects": _identity_metrics(remembered_subjects),
        "baseline_premises": _identity_metrics(baseline_premises),
        "remembered_premises": _identity_metrics(remembered_premises),
        "concept_operations": dict(concepts_collection.operations),
        "phase3e_sequential_concept_operations": dict(sequential_collection.operations),
        "descriptor_operations": dict(descriptors_collection.operations),
        "local_ms": {"average": round(mean(local_times), 2),
                     "maximum": round(max(local_times), 2)},
    }


if __name__ == "__main__":
    from pprint import pprint
    pprint(run(), sort_dicts=False)
