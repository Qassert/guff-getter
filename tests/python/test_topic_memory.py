from copy import deepcopy
from types import SimpleNamespace

import pytest

from newsmuncher.services.comedy_descriptors import GeneratedDescriptor, assemble_descriptor_slate, normalised
from newsmuncher.services.topic_memory import (
    TopicMemory, TopicMemoryConfig, build_topic_event, detect_topics, name_topic_family,
)


class MemoryCollection:
    def __init__(self):
        self.document = None
        self.reads = 0
        self.writes = 0

    def find_one(self, query, projection=None):
        self.reads += 1
        return deepcopy(self.document)

    def update_one(self, query, update, upsert=False):
        self.writes += 1
        rewrite = update["$push"]["events"]["$each"][0]["rewrite_id"]
        if self.document and any(event["rewrite_id"] == rewrite
                                 for event in self.document["events"]):
            return SimpleNamespace(matched_count=0, upserted_id=None)
        inserted = self.document is None
        self.document = self.document or {"_id": "recent", "version": 1, "events": []}
        event_update = update["$push"]["events"]
        self.document["events"].extend(deepcopy(event_update["$each"]))
        self.document["events"] = self.document["events"][event_update["$slice"]:]
        return SimpleNamespace(matched_count=not inserted, upserted_id="recent" if inserted else None)


def keys(text, source=""):
    return {item["key"] for item in detect_topics(text, source)}


def test_topic_flag_defaults_off_and_requires_explicit_evaluation(monkeypatch):
    monkeypatch.delenv("NEWSMUNCHER_COMEDY_TOPIC_MEMORY", raising=False)
    assert not TopicMemoryConfig.from_environment().enabled
    monkeypatch.setenv("NEWSMUNCHER_COMEDY_TOPIC_MEMORY", "evaluation")
    assert TopicMemoryConfig.from_environment().enabled
    monkeypatch.setenv("NEWSMUNCHER_COMEDY_TOPIC_MEMORY", "yes")
    with pytest.raises(ValueError):
        TopicMemoryConfig.from_environment()


def test_audited_construction_variants_are_recognised_without_broad_false_matches():
    assert "construction:illegal-raffle" in keys("The stoat ran an illegal raffle.")
    assert "construction:tribunal" in keys("A kettle represented itself at the tribunal.")
    assert "construction:tribunal" in keys("A kettle is representing itself at a tribunal.")
    assert "construction:floorboards-framed-it" in keys("It insisted the floorboards framed him.")
    assert "construction:unauthorised-swelling" in keys("Capable of unauthorised swelling!")
    assert "construction:neighbour-started-it" in keys("It insists that the neighbour started it.")
    assert "construction:powered" in keys("A hamster-powered milk float arrived.")
    assert "construction:illegal-raffle" not in keys("They bought a legal raffle ticket.")


def test_subjects_are_specific_and_source_driven_mentions_are_exempt():
    detected = keys("Municipal gravy reached the tea urn beside an allotment.")
    assert {"subject:municipal-authority", "subject:gravy", "subject:tea",
            "subject:allotment"} <= detected
    assert keys("The gravy inquiry continued.", "A report about gravy.") == set()


def test_completed_offer_event_keeps_offers_and_final_detections_separate():
    event = build_topic_event(
        "rewrite", {"crazyReplacement1Title": "Tea trouble",
                    "crazyReplacement1Extract": "A kettle ran an illegal raffle."},
        {"title": "Sport", "description": "", "extract": "A match."},
        ["Lady Verity Yaffle-Cholmondeley"],
        {"Lady Verity Yaffle-Cholmondeley": "cheeky:cvcvc"},
        [{"phrase": "milk float with diplomatic immunity", "base": "milk float",
          "premise_key": "institutional:immunity"}],
        [{"phrase": "banned from speed topiary", "premise_key": "secret:speedtopiary"}],
    )
    assert event["descriptor_phrases"] == [normalised("banned from speed topiary")]
    assert event["name_families"] == ["yaffle"]
    assert {item["key"] for item in event["final_topics"]} == {
        "subject:tea", "construction:illegal-raffle"
    }


def test_memory_loads_once_penalises_recent_offers_and_deduplicates_rewrite():
    collection = MemoryCollection()
    service = TopicMemory(collection, TopicMemoryConfig("evaluation", window=3))
    event = {"rewrite_id": "one", "descriptor_phrases": ["speedtopiary"],
             "name_families": ["yaffle"],
             "final_topics": [{"key": "subject:gravy", "label": "gravy", "kind": "subject"}]}
    assert service.record(event)
    assert not service.record(event)
    service.load()
    assert collection.reads == 1 and collection.writes == 2
    assert service.penalties("descriptor_phrases", "offered:")["offered:speedtopiary"] > 0
    assert service.recent_name_families()["yaffle"] > 0
    assert service.guidance() == ""
    second = {**event, "rewrite_id": "two"}
    assert service.record(second)
    service.load()
    assert "gravy" in service.guidance()


def test_descriptor_recent_offer_penalty_is_soft_and_preserves_quality_floor():
    def item(phrase, score, role, category, intensity):
        return GeneratedDescriptor(
            phrase=phrase, grammatical_role=role, comic_mechanism="secret_history",
            semantic_theme="secret_history", premise_key=phrase, category=category,
            intensity=intensity, template="test", generator_version="test", word_count=4,
            quality_score=score, editorial_warnings=(), subject=phrase,
            insertion_rule="predicate", usage_example="Example",
        )
    # Directly compare the ordering signal using a six-role compatible pool.
    pool = []
    assignments = zip(
        ("pre_noun", "adverbial", "predicate", "post_noun", "behavioural", "short_clause"),
        ("cheeky_british",) * 4 + ("broader_absurdity",) * 2,
        (1, 1, 2, 2, 2, 3),
    )
    for role, category, intensity in assignments:
        for suffix in ("old", "fresh"):
            pool.append(item(f"{role} {suffix}", 8.0 if suffix == "old" else 7.9,
                             role, category, intensity))
    penalties = {"offered:" + normalised(item.phrase): 10 for item in pool if item.phrase.endswith("old")}
    selected = assemble_descriptor_slate(pool, "topic-test", 6, diversify=True,
                                         family_penalties=penalties)
    assert all(item.phrase.endswith("fresh") for item in selected)
    assert min(item.quality_score for item in selected) == 7.9


def test_name_topic_family_targets_yaffle_without_banning_other_names():
    assert name_topic_family("Lady Verity Yaffle-Cholmondeley", "cheeky:cvc") == "yaffle"
    assert name_topic_family("Barry Bustleton", "cheeky:cvc") == "cheeky:cvc"


def test_phase4j_audit_is_deterministic_and_improves_each_target_dimension():
    from scripts.diagnostics.evaluate_vocabulary_phase4j import run

    first=run(250); second=run(250)
    for label in ("phase4i", "phase4j"):
        first[label]["selection_latency_ms"]={}; second[label]["selection_latency_ms"]={}
    assert first == second
    before, after = first["phase4i"], first["phase4j"]
    for metric in ("exact_offered_phrases", "semantic_premises", "final_subjects",
                   "final_constructions"):
        assert after[metric]["rolling_10"] < before[metric]["rolling_10"]
    assert after["object_identities"]["unique"] >= before["object_identities"]["unique"]
    assert after["name_sound_families"]["unique"] >= before["name_sound_families"]["unique"]
    assert after["humour_quality_proxy"] >= before["humour_quality_proxy"] - .15
    assert after["exhaustion_events"] == 0
