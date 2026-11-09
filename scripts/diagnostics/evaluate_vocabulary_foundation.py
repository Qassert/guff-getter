"""Phase 4B offline catalogue/selector audit; never imported by live code."""
from __future__ import annotations

from collections import Counter, deque
from statistics import mean
from time import monotonic
import tracemalloc

from newsmuncher.services.vocabulary_catalogue import OfflineVocabularySelector, VocabularyCatalogue
from scripts.diagnostics.evaluate_vocabulary_expansion import _simulate, catalogues

QUOTAS = {"animals": 4, "objects": 16, "descriptors": 10,
          "names": 10, "slang": 10, "places": 10}
PHASE4A_KEYS = {"animals": "animals", "objects": "objects", "descriptors": "descriptors",
                "names": "name_components", "slang": "slang", "places": "places"}


def _phase4b(catalogue, family, seed, rewrites):
    recent = deque(maxlen=QUOTAS[family] * 10)
    slates = []
    for index in range(rewrites):
        selector = OfflineVocabularySelector(catalogue, f"{seed}:{family}:{index}", recent)
        slate = selector.select(family, QUOTAS[family])
        ids = [item["id"] for item in slate]
        slates.append(slate)
        recent.extend(ids)
    flat = [item for slate in slates for item in slate]
    windows = []
    for index in range(len(slates)):
        values = [item["id"] for slate in slates[max(0, index - 9):index + 1] for item in slate]
        windows.append(len(values) - len(set(values)))
    return {
        "offers": len(flat), "unique": len({item["id"] for item in flat}),
        "repeated_occurrences": len(flat) - len({item["id"] for item in flat}),
        "rolling_ten_average_reuse": round(mean(windows), 2),
        "rolling_ten_maximum_reuse": max(windows),
        "semantic_classes": len({item["semantic_class"] for item in flat}),
        "construction_types": len({item["subtype"] for item in flat}),
    }


def examples(catalogue, seed="phase4b", per_family=17):
    output = []
    recent = ()
    for family in sorted(QUOTAS):
        selected = OfflineVocabularySelector(catalogue, f"{seed}:examples:{family}", recent).select(
            family, min(per_family, len(catalogue.by_family[family])))
        for item in selected:
            label = "WEAK/REVIEW" if item["approval_status"] == "machine_checked" else "reviewed"
            text = item["text"]
            if family == "animals": rendered = f"{text} working as a relief parking warden"
            elif family == "objects": rendered = f"{text} with temporary powers of arrest"
            elif family == "names": rendered = f"name ingredient: {text}"
            elif family == "places": rendered = f"fictional place ingredient: {text}"
            elif family == "slang": rendered = f"colloquial ingredient: {text}"
            else: rendered = f"descriptor ingredient: {text}"
            output.append({"family": family, "example": rendered, "status": label,
                           "semantic_class": item["semantic_class"]})
    return output[:100]


def run(seed="phase4b", rewrites=250):
    tracemalloc.start(); started = monotonic()
    catalogue = VocabularyCatalogue.load()
    old = catalogues()
    comparison = {}
    for family, quota in QUOTAS.items():
        phase4a_pool = old[PHASE4A_KEYS[family]][1]
        comparison[family] = {
            "phase4a": _simulate(phase4a_pool, f"{seed}:{family}:phase4a", quota, rewrites),
            "phase4b": _phase4b(catalogue, family, seed, rewrites),
        }
    _, peak = tracemalloc.get_traced_memory(); tracemalloc.stop()
    validation = catalogue.validate()
    return {
        "seed": seed, "rewrites": rewrites,
        "counts": {family: len(catalogue.by_family[family]) for family in sorted(QUOTAS)},
        "approval": dict(Counter(item["approval_status"] for item in catalogue.entries)),
        "validation": dict(Counter(f"{issue.level}:{issue.code}" for issue in validation)),
        "comparison": comparison, "examples": examples(catalogue, seed),
        "local_ms": round((monotonic() - started) * 1000, 2),
        "peak_memory_bytes": peak, "database_operations": 0,
        "network_operations": 0, "provider_operations": 0,
    }


if __name__ == "__main__":
    from pprint import pprint
    pprint(run(), sort_dicts=False)
