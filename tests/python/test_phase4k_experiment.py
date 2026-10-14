import json
from pathlib import Path

from scripts.diagnostics.run_comedy_phase4k_experiment import (
    BASE_FEATURES, MemoryCollection, SOURCES_PATH, metrics,
)


def test_source_manifest_has_seven_distinct_complete_categories():
    sources = json.loads(SOURCES_PATH.read_text())
    assert len(sources) == len({item["id"] for item in sources}) == 7
    assert len({item["category"] for item in sources}) == 7
    assert all(len(item["extract"].split()) >= 65 for item in sources)


def test_in_memory_collection_supports_isolated_memory_operations():
    collection = MemoryCollection()
    first = collection.update_one({"_id": "one"}, {"$set": {"value": 1}}, upsert=True)
    assert first.upserted_id == "one"
    collection.update_one({"_id": "one"}, {"$inc": {"value": 2}})
    assert collection.find_one({"_id": "one"})["value"] == 3
    collection.update_one(
        {"_id": "recent", "events.rewrite_id": {"$ne": "r1"}},
        {"$push": {"events": {"$each": [{"rewrite_id": "r1"}], "$slice": -10}}},
        upsert=True,
    )
    assert collection.find_one({"_id": "recent"})["events"][0]["rewrite_id"] == "r1"


def test_experiment_feature_manifest_is_explicit_and_metrics_count_motifs():
    assert BASE_FEATURES["NEWSMUNCHER_COMEDY_AUDIT_LOG"] == "on"
    assert BASE_FEATURES["NEWSMUNCHER_COMEDY_TOPIC_MEMORY"] == "evaluation"
    records = []
    for label in "ABCD":
        records.append({
            "comparison_variant": label,
            "final": {"headline": "Royal crumpet", "article_text": "A hamster-powered parliament."},
            "ingredients": {"offered": {"generated_concepts": [], "raw_hybrid_ingredients": []},
                            "found_exactly_in_final": {"concepts": [], "raw_hybrid_ingredients": []}},
            "semantic": {"canonical_joke_families": [], "topic_memory_detections": []},
        })
    result = metrics(records)
    assert result["A"]["motifs"] == {"powered": 1, "parliament": 1, "royal": 1, "crumpet": 1}
