from copy import deepcopy
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from newsmuncher.services.final_joke_memory import (
    FinalJokeMemory, FinalJokeMemoryConfig, detect_final_jokes,
)


class MemoryCollection:
    def __init__(self):
        self.docs = {}
        self.operations = {"find": 0, "find_one_and_update": 0, "update_one": 0}

    def find(self, query, projection=None):
        self.operations["find"] += 1
        allowed = set(query.get("record_type", {}).get("$in", ()))
        return [deepcopy(doc) for doc in self.docs.values()
                if not allowed or doc.get("record_type") in allowed]

    def find_one_and_update(self, query, update, upsert=False, return_document=None):
        self.operations["find_one_and_update"] += 1
        key = query["_id"]; inserted = key not in self.docs
        doc = self.docs.setdefault(key, {"_id": key})
        if inserted: doc.update(deepcopy(update.get("$setOnInsert", {})))
        for field, amount in update.get("$inc", {}).items():
            doc[field] = doc.get(field, 0) + amount
        return deepcopy(doc)

    def update_one(self, query, update, upsert=False):
        self.operations["update_one"] += 1
        key = query["_id"]; inserted = key not in self.docs
        doc = self.docs.setdefault(key, {"_id": key})
        if inserted: doc.update(deepcopy(update.get("$setOnInsert", {})))
        doc.update(deepcopy(update.get("$set", {})))
        for field, amount in update.get("$inc", {}).items():
            doc[field] = doc.get(field, 0) + amount
        return SimpleNamespace(matched_count=not inserted, upserted_id=key if inserted else None)


def memory(collection=None, **config):
    return FinalJokeMemory(
        collection or MemoryCollection(),
        FinalJokeMemoryConfig(mode="evaluation", **config),
        now=lambda: datetime(2026, 10, 12, tzinfo=timezone.utc),
    )


def keys(text, source=""):
    return {item["key"] for item in detect_final_jokes(text, source)}


def test_feature_flag_defaults_off_and_rejects_unknown_modes(monkeypatch):
    monkeypatch.delenv("NEWSMUNCHER_FINAL_JOKE_MEMORY", raising=False)
    assert not FinalJokeMemoryConfig.from_environment().enabled
    monkeypatch.setenv("NEWSMUNCHER_FINAL_JOKE_MEMORY", "evaluation")
    assert FinalJokeMemoryConfig.from_environment().enabled
    monkeypatch.setenv("NEWSMUNCHER_FINAL_JOKE_MEMORY", "yes")
    with pytest.raises(ValueError):
        FinalJokeMemoryConfig.from_environment()


def test_seventeen_accountants_exact_numeric_and_delegation_share_one_key():
    assert keys("Seventeen accountants arrived.") == {"numbered-group:17:accountant"}
    assert keys("A delegation of 17 accountants arrived.") == {
        "numbered-group:17:accountant"
    }


def test_queue_containment_variants_share_specific_scenario_without_banning_queue():
    expected = {"scenario:queue-containment"}
    assert keys("Emergency queue containment procedures began.") == expected
    assert keys("A specialist queue-containment unit arrived.") == expected
    assert keys("They waited in a queue outside accounts.") == set()


def test_source_facts_are_exempt_from_final_joke_memory():
    source = "A delegation of 17 accountants joined the queue-containment unit."
    assert keys("Seventeen accountants discussed queue containment.", source) == set()


def test_only_accepted_output_is_recorded_and_guidance_is_concise():
    collection = MemoryCollection(); service = memory(collection)
    used = service.accept("rewrite-1", "Seventeen accountants",
                          "Emergency queue containment procedures began.")
    assert set(used) == {"numbered-group:17:accountant", "scenario:queue-containment"}
    guidance = service.guidance()
    assert "17 accountants" in guidance and "queue-containment" in guidance
    assert len(guidance) < 500
    assert collection.operations == {"find": 1, "find_one_and_update": 1, "update_one": 2}


def test_cooldown_advances_on_successful_articles_without_jokes_and_then_expires():
    collection = MemoryCollection(); service = memory(collection, cooldown_articles=3)
    service.accept("one", "", "Seventeen accountants arrived.")
    assert "17 accountants" in service.guidance()
    service.accept("two", "", "A badger filed the minutes.")
    service.accept("three", "", "A teapot chaired proceedings.")
    assert "17 accountants" in service.guidance()
    service.accept("four", "", "The gazebo adjourned.")
    assert "17 accountants" not in service.guidance()


def test_disabled_mode_has_no_reads_writes_or_guidance():
    collection = MemoryCollection()
    service = FinalJokeMemory(collection, FinalJokeMemoryConfig())
    assert service.guidance() == ""
    assert service.accept("rewrite", "17 accountants", "queue containment") == []
    assert collection.operations == {"find": 0, "find_one_and_update": 0, "update_one": 0}


def test_phase4h_audit_is_equivalent_seeded_and_reduces_recurring_families():
    from scripts.diagnostics.evaluate_vocabulary_phase4h import run

    first = run(250)
    second = run(250)
    for label in ("phase4g", "phase4h"):
        first[label]["local_memory_latency_ms"] = {}
        second[label]["local_memory_latency_ms"] = {}
    assert first == second
    before, after = first["phase4g"], first["phase4h"]
    assert after["near_duplicate_final_jokes"]["repeated"] < before["near_duplicate_final_jokes"]["repeated"]
    assert after["near_duplicate_final_jokes"]["rolling_5"] < before["near_duplicate_final_jokes"]["rolling_5"]
    assert after["ingredient_unique"] == before["ingredient_unique"]
    assert after["semantic_premise_unique"] == before["semantic_premise_unique"]
    assert after["controlled_exhaustion_events"] == 0
