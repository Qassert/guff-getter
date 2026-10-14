from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from types import SimpleNamespace

from newsmuncher.services.lexical_exposure import LexicalExposureConfig
from newsmuncher.services.thematic_diversity import (
    ThematicDiversityConfig, ThematicDiversityMemory, detect_domain_influence,
    load_domains, thematic_event,
)
from scripts.diagnostics.evaluate_thematic_diversity_phase4n import evaluate


class Collection:
    def __init__(self): self.docs = {}; self.lock = Lock()
    def find_one(self, query, projection=None):
        with self.lock: return deepcopy(self.docs.get(query["_id"]))
    def update_one(self, query, update, upsert=False):
        with self.lock:
            key = query["_id"]; doc = self.docs.get(key); rewrite = query["events.rewrite_id"]["$ne"]
            if doc and rewrite in {x["rewrite_id"] for x in doc.get("events", [])}:
                return SimpleNamespace(matched_count=0, upserted_id=None)
            inserted = doc is None
            if inserted:
                if not upsert: return SimpleNamespace(matched_count=0, upserted_id=None)
                doc = {"_id": key, **deepcopy(update.get("$setOnInsert", {}))}; self.docs[key] = doc
            spec = update["$push"]["events"]; doc.setdefault("events", []).extend(deepcopy(spec["$each"]))
            doc["events"] = doc["events"][spec["$slice"]:]
            return SimpleNamespace(matched_count=not inserted, upserted_id=key if inserted else None)


def test_catalogue_has_100_distinct_domains_and_broad_families():
    domains = load_domains()
    assert len(domains) == len({x["id"] for x in domains}) == 100
    assert len({x["family"] for x in domains}) == 11
    assert all(len(x["keywords"]) >= 3 for x in domains)


def test_default_off_does_not_read_select_or_write(monkeypatch):
    monkeypatch.delenv("NEWSMUNCHER_THEMATIC_DIVERSITY", raising=False)
    memory = ThematicDiversityMemory(Collection(), "pet", ThematicDiversityConfig.from_environment())
    assert memory.load() == [] and memory.select("seed") == []
    assert memory.record(thematic_event("r", [])) is False
    assert memory.collection.docs == {}


def test_selection_is_seeded_diverse_and_softly_avoids_recent_domains():
    memory = ThematicDiversityMemory(Collection(), "pet", ThematicDiversityConfig("evaluation", 4, 20))
    first = memory.select("one")
    assert len(first) == 4 and len({x["family"] for x in first}) >= 3
    memory.events = [thematic_event(str(i), first) for i in range(20)]
    second = memory.select("one")
    assert {x["id"] for x in second} != {x["id"] for x in first}
    assert set(memory.penalties()[0]) == {x["id"] for x in first}


def test_memory_is_bounded_persistent_isolated_and_duplicate_safe():
    collection = Collection(); config = ThematicDiversityConfig("evaluation", 4, 10)
    first = ThematicDiversityMemory(collection, "pet-a", config)
    selected = first.select("seed")
    for index in range(15): assert first.record(thematic_event(f"r{index}", selected))
    assert not first.record(thematic_event("r14", selected))
    restarted = ThematicDiversityMemory(collection, "pet-a", config); restarted.load()
    separate = ThematicDiversityMemory(collection, "pet-b", config); separate.load()
    assert len(restarted.events) == 10 and separate.events == []


def test_concurrent_unique_events_are_atomically_retained_and_bounded():
    collection = Collection(); config = ThematicDiversityConfig("evaluation", 4, 10)
    selected = ThematicDiversityMemory(collection, "pet", config).select("seed")
    def append(index):
        return ThematicDiversityMemory(collection, "pet", config).record(
            thematic_event(f"concurrent-{index}", selected))
    with ThreadPoolExecutor(max_workers=8) as pool:
        assert all(pool.map(append, range(20)))
    events = ThematicDiversityMemory(collection, "pet", config).load()
    assert len(events) == 10 and len({item["rewrite_id"] for item in events}) == 10


def test_guidance_is_optional_and_influence_is_source_exempt():
    selected = [next(x for x in load_domains() if x["id"] == "mycology")]
    guidance = ThematicDiversityMemory.guidance(selected)
    assert "Optional" in guidance or "OPTIONAL" in guidance
    assert "not subjects" in guidance and "Ignore, combine, distort" in guidance
    assert detect_domain_influence(selected, "A fungal spore joined the band", "")
    assert detect_domain_influence(selected, "A fungal spore joined the band", "fungal spore") == []


def test_500_generation_audit_covers_catalogue_without_concentration():
    result = evaluate(500, "phase4n-test")
    assert result["domains_seen"] == 100
    assert result["families_seen"] == 11
    assert result["largest_domain_share"] < 0.02
    assert result["largest_family_share"] < 0.13
    assert result["mean_families_per_generation"] >= 3.5
    assert result["stored_events"] == 20
    assert result["rolling_five_domain_repeats"] < result["uniform_baseline_rolling_five_repeats"]


def test_phase4m_configuration_is_independent():
    assert ThematicDiversityConfig("evaluation").enabled
    assert not LexicalExposureConfig("off").enabled
    assert ThematicDiversityConfig("off").mode == "off"
    assert LexicalExposureConfig("evaluation").enabled
