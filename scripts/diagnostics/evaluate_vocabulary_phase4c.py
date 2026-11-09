"""Compare the isolated Phase 4B and Phase 4C catalogues over simulated MUNGEs."""
from __future__ import annotations

from collections import Counter, deque
import random
from statistics import mean
from time import monotonic
import tracemalloc

from newsmuncher.services.vocabulary_catalogue import OfflineVocabularySelector, VocabularyCatalogue

QUOTAS = {"animals": 4, "objects": 16, "descriptors": 10,
          "names": 10, "slang": 10, "places": 10}
PHASE4B_SOURCES = {"newsmuncher-curated", "phase4a-editorial-seed", "legacy-local-filter"}
USED_RANGES = {"animals": (1, 2), "objects": (2, 4), "descriptors": (2, 4),
               "names": (1, 3), "slang": (0, 1), "places": (0, 1)}


def phase4b_catalogue(catalogue):
    payload = dict(catalogue.payload)
    payload["ingredients"] = [entry for entry in catalogue.entries
                              if entry["source_id"] in PHASE4B_SOURCES]
    payload["catalogue_version"] = "phase4b-reconstructed"
    return VocabularyCatalogue(payload)


def simulate(catalogue, seed, rewrites):
    result = {}
    for family, quota in QUOTAS.items():
        recent = deque(maxlen=quota * 10); slates = []; used = []
        for index in range(rewrites):
            slate = OfflineVocabularySelector(catalogue, f"{seed}:{family}:{index}", recent).select(family, quota)
            slates.append(slate); recent.extend(entry["id"] for entry in slate)
            rng = random.Random(f"{seed}:{family}:used:{index}")
            low, high = USED_RANGES[family]; amount = rng.randint(low, high)
            used.extend(rng.sample(slate, amount) if amount else [])
        flat = [entry for slate in slates for entry in slate]
        windows = []
        for index in range(len(slates)):
            ids = [entry["id"] for slate in slates[max(0,index-9):index+1] for entry in slate]
            windows.append(len(ids)-len(set(ids)))
        semantic = Counter(entry["semantic_class"] for entry in flat)
        result[family] = {
            "offers": len(flat), "unique_offered": len({entry["id"] for entry in flat}),
            "repeated_offers": len(flat)-len({entry["id"] for entry in flat}),
            "rolling_ten_average_reuse": round(mean(windows),2),
            "rolling_ten_maximum_reuse": max(windows),
            "semantic_classes": len(semantic),
            "dominant_semantic_share": round(max(semantic.values())/len(flat),3),
            "used": len(used), "unique_used": len({entry["id"] for entry in used}),
            "repeated_used": len(used)-len({entry["id"] for entry in used}),
        }
    return result


def examples(catalogue, seed="phase4c"):
    output=[]
    for family in QUOTAS:
        amount=17 if family in {"animals","objects","descriptors","names"} else 16
        selected=OfflineVocabularySelector(catalogue,f"{seed}:examples:{family}").select(family,amount)
        for item in selected:
            status="WEAK/REVIEW" if item["approval_status"]=="machine_checked" else "reviewed"
            if family=="animals": phrase=f"{item['text']} disputing a parking fine"
            elif family=="objects": phrase=f"{item['text']} with ceremonial immunity"
            elif family=="descriptors": phrase=f"descriptor ingredient: {item['text']}"
            elif family=="names": phrase=f"name component: {item['text']}"
            elif family=="slang": phrase=f"colloquial ingredient: {item['text']}"
            else: phrase=f"fictional-place ingredient: {item['text']}"
            output.append({"family":family,"phrase":phrase,"status":status,
                           "semantic_class":item["semantic_class"]})
    return output[:100]


def run(seed="phase4c", rewrites=250):
    tracemalloc.start(); started=monotonic(); current=VocabularyCatalogue.load()
    baseline=phase4b_catalogue(current)
    before=simulate(baseline,seed+":b",rewrites); split=monotonic()
    after=simulate(current,seed+":c",rewrites); finished=monotonic()
    _,peak=tracemalloc.get_traced_memory(); tracemalloc.stop()
    return {"seed":seed,"rewrites":rewrites,
            "counts":{"phase4b":{f:len(baseline.by_family[f]) for f in QUOTAS},
                      "phase4c":{f:len(current.by_family[f]) for f in QUOTAS}},
            "phase4b":before,"phase4c":after,"examples":examples(current,seed),
            "phase4b_ms":round((split-started)*1000,2),
            "phase4c_ms":round((finished-split)*1000,2),
            "peak_memory_bytes":peak,"database_operations":0,"provider_operations":0,
            "network_operations_during_audit":0}


if __name__ == "__main__":
    from pprint import pprint
    pprint(run(),sort_dicts=False)
