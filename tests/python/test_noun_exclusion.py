from datetime import datetime, timezone
from collections import Counter
import os
import threading
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from newsmuncher.services.comedy_audit import build_audit_record
from newsmuncher.services.concept_selection import ConceptRegistry, ConceptSelectionConfig
from newsmuncher.services.comedy_concepts import normalised
from newsmuncher.services.noun_exclusion import (
    NounExclusionConfig, NounExclusionMemory, attribute_violations, blocked_entries,
    extract_final_entries, filter_candidates, identity_entries, phrase_found,
)
from test_name_selection import MemoryCollection


class Collection:
    def __init__(self):
        self.doc = None
        self.lock = threading.Lock()

    def find_one(self, query, projection=None):
        with self.lock:
            return None if self.doc is None else {
                key: (list(value) if isinstance(value, list) else value)
                for key, value in self.doc.items()
            }

    def update_one(self, query, update, upsert=False):
        with self.lock:
            if self.doc is None:
                if not upsert:
                    return SimpleNamespace(matched_count=0, upserted_id=None)
                self.doc = {"_id": query["_id"], "entries": [], "reservations": []}
                inserted = query["_id"]
            else:
                inserted = None
            if "entries" in query:
                forbidden = set(query["entries"].get("$nin", ()))
                reserved = {entry for item in self.doc.get("reservations", [])
                            for entry in item.get("entries", ())}
                if forbidden & (set(self.doc.get("entries", ())) | reserved):
                    return SimpleNamespace(matched_count=0, upserted_id=None)
            revision = query.get("revision")
            if revision is not None and self.doc.get("revision", 0) != revision:
                return SimpleNamespace(matched_count=0, upserted_id=None)
            if "$or" in query and self.doc.get("revision", 0) != 0:
                return SimpleNamespace(matched_count=0, upserted_id=None)
            if "$pull" in update:
                condition = update["$pull"]["reservations"]
                if "generation_id" in condition:
                    self.doc["reservations"] = [x for x in self.doc["reservations"]
                        if x.get("generation_id") != condition["generation_id"]]
            if "$push" in update:
                self.doc.setdefault("reservations", []).append(
                    update["$push"]["reservations"])
            if "$set" in update:
                self.doc.update(update["$set"])
            return SimpleNamespace(matched_count=1, upserted_id=inserted)


def test_flag_is_default_off_and_validated():
    with patch.dict("os.environ", {}, clear=True):
        assert not NounExclusionConfig.from_environment().enabled
    assert NounExclusionConfig("evaluation").enabled


def test_plural_and_compound_exclusion_with_source_protection():
    entries = identity_entries("gravy boats")
    assert entries == {"phrase:gravy boat", "noun_identity:gravy"}
    assert blocked_entries("two municipal gravy pumps", entries) == ["noun_identity:gravy"]
    assert blocked_entries("gravy pumps", entries, "Gravy exports rise") == []


def test_complete_phrase_filtering_catches_all_manual_gravy_examples():
    exclusions = {"noun_identity:gravy"}
    examples = (
        "traffic cone of constitutional gravy service",
        "royal directorate for gravy procurement",
        "gravy-powered lawn mower",
        "spiritually gravy-invested",
    )
    assert all(blocked_entries(value, exclusions) == ["noun_identity:gravy"]
               for value in examples)


def test_template_grammar_is_not_persisted_or_enforced_as_a_noun():
    entries = identity_entries(
        "gravy-powered mower automatically buttering and insisting on an inquiry")
    assert "noun_identity:gravy" in entries and "noun_identity:mower" in entries
    assert "noun_identity:powered" not in entries and "noun_identity:insisting" not in entries
    assert "noun_identity:automatically" not in entries and "noun_identity:buttering" not in entries
    assert blocked_entries(
        "otter-powered toaster automatically buttering and insisting on terms",
        {"noun_identity:powered", "noun_identity:automatically", "noun_identity:buttering", "noun_identity:insisting"},
    ) == []


def test_legacy_component_entries_require_accepted_phrase_boundary_evidence():
    old = {
        "noun:gravy", "noun:powered", "noun:automatically",
        "phrase:gravy powered lawn mower automatically",
    }
    assert blocked_entries("another gravy pump", old) == ["noun:gravy"]
    assert blocked_entries("an automatically polished pump", old) == []
    assert blocked_entries("a powered toaster", old) == []


def test_optional_articles_do_not_hide_reused_constructions():
    assert phrase_found(
        "a cod working as a time-travelling constitutional lawyer",
        "cod working as time-travelling constitutional lawyer")
    assert phrase_found(
        "a corkscrew calibrated to weigh the ceremonial dignity of Penge",
        "corkscrew calibrated to weigh ceremonial dignity")


def test_candidate_filtering_refills_from_remaining_pool():
    candidates = [{"text": text} for text in ("gravy pump", "otters", "sextant")]
    eligible = filter_candidates(candidates, {"noun_identity:gravy"}, "text")
    assert [item["text"] for item in eligible[:2]] == ["otters", "sextant"]


def test_concept_selection_builds_bounded_refill_headroom_for_exact_cooldowns():
    service = ConceptRegistry(
        MemoryCollection(), ConceptSelectionConfig(vocabulary_mode="evaluation"))
    original = service._candidates
    calls = []

    def candidates(key, lexical_penalties=None, noun_exclusions=(), source_text="",
                   component_filter_cache=None):
        calls.append(key)
        if len(calls) == 1:
            return []  # model the exhausted first category-specific batch
        return original(key, lexical_penalties, noun_exclusions, source_text,
                        component_filter_cache)

    service._candidates = candidates
    selected = service.offer("noun-refill", noun_exclusions={"noun_identity:gravy"})
    assert len(selected) == 20
    assert calls == ["noun-refill"] + [
        f"noun-refill:noun-refill:{batch}" for batch in range(1, 5)]
    assert service.last_metrics["candidate_batches"] == 5
    assert all(not blocked_entries(item["phrase"], {"noun_identity:gravy"})
               for item in selected)


def test_exclusion_aware_concepts_prune_components_and_preserve_full_slate():
    exclusions = {
        "noun_identity:gravy",
        "premise:impossible_measurement:weighceremonialdignity",
    }
    service = ConceptRegistry(MemoryCollection())
    selected = service.offer("component-pruning", noun_exclusions=exclusions)
    assert len(selected) == 20
    assert len({item["base"] for item in selected}) == 20
    assert len({item["premise_key"] for item in selected}) == 20
    assert all(not blocked_entries(item["phrase"], exclusions) for item in selected)
    assert all("premise:" + item["premise_key"] not in exclusions for item in selected)
    assert all(item["animal_species"] for item in selected
               if item["target_bank"] == "animals")
    assert service.last_metrics["noun_exclusion_rejected"] == 0


def test_exclusion_aware_selection_handles_five_thousand_mixed_records():
    exclusions = {"noun_identity:gravy"}
    exclusions.update(f"phrase:unused historical comic identity {index}"
                      for index in range(4999))
    service = ConceptRegistry(MemoryCollection())
    selected = service.offer("bounded-five-thousand", noun_exclusions=exclusions)
    assert len(selected) == 20
    assert all(not blocked_entries(item["phrase"], exclusions) for item in selected)


def test_concept_selection_relaxes_only_category_quota_after_proven_shortage():
    collection = MemoryCollection()
    service = ConceptRegistry(
        collection, ConceptSelectionConfig(vocabulary_mode="evaluation"),
        now=lambda: datetime(2026, 10, 13, tzinfo=timezone.utc))
    keys = ["quota-shortage"] + [
        f"quota-shortage:noun-refill:{batch}" for batch in range(1, 5)]
    marker = {"noun:never-selected"}
    candidates = [item for key in keys for item, target in service._candidates(
        key, noun_exclusions=marker)
                  if target == "nouns" and item.category == "bureaucratic_nonsense"]
    for item in candidates:
        collection.docs["phrase:" + normalised(item.phrase)] = {
            "_id": "phrase:" + normalised(item.phrase),
            "last_used_at": datetime(2026, 10, 13, tzinfo=timezone.utc),
        }

    selected = service.offer(
        "quota-shortage", noun_exclusions=marker)
    counts = Counter((item["target_bank"], item["category"]) for item in selected)
    assert len(selected) == 20
    assert counts[("nouns", "bureaucratic_nonsense")] == 0
    assert service.last_metrics["category_quota_slack"] >= 1
    assert max(counts[("nouns", category)] - quota for category, quota in {
        "everyday_british": 1, "cheeky_object": 2, "absurd_invention": 2,
        "emergency_equipment": 1, "ceremonial_object": 1,
    }.items()) <= service.last_metrics["category_quota_slack"]
    assert all(not blocked_entries(item["phrase"], {"noun:never-selected"})
               for item in selected)


def test_persistent_fifo_is_bounded_and_isolated():
    first, second = Collection(), Collection()
    config = NounExclusionConfig("evaluation", capacity=10)
    a = NounExclusionMemory(first, "pet-a", config)
    b = NounExclusionMemory(second, "pet-b", config)
    a.load(); b.load()
    a.complete("one", {f"noun:item-{index}" for index in range(12)})
    assert len(a.entries) == 10 and not b.load()
    reopened = NounExclusionMemory(first, "pet-a", config)
    assert reopened.load() == a.entries


def test_concurrent_reservation_and_failure_release():
    collection = Collection()
    config = NounExclusionConfig("evaluation")
    first = NounExclusionMemory(collection, "pet", config)
    second = NounExclusionMemory(collection, "pet", config)
    first.load(); second.load()
    results = []
    threads = [threading.Thread(target=lambda memory, run: results.append(
        memory.reserve(run, {"noun_identity:gravy"})), args=(memory, run))
        for memory, run in ((first, "a"), (second, "b"))]
    [thread.start() for thread in threads]
    [thread.join() for thread in threads]
    assert sorted(results) == [False, True]
    first.release("a"); second.release("b")
    retry = NounExclusionMemory(collection, "pet", config); retry.load()
    assert retry.reserve("c", {"noun_identity:gravy"})


def test_final_extraction_and_model_violation_are_distinct():
    concepts = [{"base": "gravy boat"}, {"base": "badgers"}]
    entries = extract_final_entries(
        title="Badgers seize a gravy boat", body="The badger celebrates.",
        source_text="Council publishes report", concepts=concepts)
    assert entries == {"phrase:gravy boat", "phrase:badger", "noun_identity:gravy", "noun_identity:badger"}
    assert blocked_entries("The model invented gravy rockets", {"noun_identity:gravy"}) == ["noun_identity:gravy"]


def test_completed_construction_records_premise_for_cross_base_exclusion():
    concepts = [{
        "phrase": "cod working as time-travelling constitutional lawyer",
        "base": "cod", "premise_key": "absurd_occupation:timetravellingconstitutionallawyer",
    }]
    entries = extract_final_entries(
        title="Cod elected", body="A cod working as a time-travelling constitutional lawyer won.",
        source_text="Election result", concepts=concepts)
    assert "premise:absurd_occupation:timetravellingconstitutionallawyer" in entries


def test_completion_commits_only_finally_used_nouns_and_premises():
    collection = Collection()
    memory = NounExclusionMemory(
        collection, "pet", NounExclusionConfig("evaluation"))
    memory.load()
    used = {
        "phrase": "gravy-powered lawn mower", "base": "lawn mower",
        "premise_key": "impossible_technology:gravy",
    }
    unused = {
        "phrase": "custard-powered toaster", "base": "toaster",
        "premise_key": "impossible_technology:custard",
    }
    offered_entries = set()
    for item in (used, unused):
        offered_entries.update(identity_entries(item["phrase"]))
        offered_entries.update(identity_entries(item["base"]))
    assert memory.reserve("rewrite-1", offered_entries)

    final_entries = extract_final_entries(
        title="Gravy mower elected",
        body="The gravy-powered lawn mower addressed the council.",
        source_text="Council election result", concepts=(used, unused),
    )
    assert "premise:impossible_technology:gravy" in final_entries
    assert "premise:impossible_technology:custard" not in final_entries
    assert not any("custard" in entry for entry in final_entries)

    assert memory.complete("rewrite-1", final_entries)
    assert set(memory.entries) == final_entries
    assert memory.reservations == []
    # The unused offer was released rather than entering the FIFO.
    assert memory.reserve("rewrite-2", identity_entries(unused["phrase"]))


def test_hyphenated_final_violation_is_attributed_to_offered_ingredient():
    result = attribute_violations(
        "Starting with a gravy-powered lawn mower, the toast rack raced.",
        {"noun_identity:gravy"}, ["gravy-powered lawn mower"])
    assert result == {
        "offered_ingredient_violations": ["noun_identity:gravy"],
        "model_introduced_violations": [],
    }


def test_audit_reports_prevention_violations_and_new_entries_separately():
    record = build_audit_record(
        rewrite_id="r", source={}, result={}, environment={},
        noun_exclusion_context={
            "enabled": True, "excluded_before": 40, "reserved_ingredients": 12,
            "prevented_ingredient_candidates": 3,
            "offered_ingredient_violations": ["noun_identity:gravy"],
            "model_introduced_violations": ["noun_identity:gravy"],
            "newly_extracted": ["noun:otter"],
        })
    assert record["noun_exclusion"] == {
        "enabled": True, "excluded_before": 40, "reserved_ingredients": 12,
        "prevented_ingredient_candidates": 3,
        "offered_ingredient_violations": ["noun_identity:gravy"],
        "model_introduced_violations": ["noun_identity:gravy"],
        "newly_extracted": ["noun:otter"],
    }


def test_route_reserves_then_commits_only_after_successful_persistence():
    import test_image_generation as fixtures
    fixture = fixtures.ImageTests(); fixture.setUp()
    try:
        routes = fixture.previews()
        memory = MagicMock()
        memory.exclusions.return_value = {"noun_identity:gravy"}
        memory.reserve.return_value = True
        routes.NounExclusionMemory = MagicMock(return_value=memory)
        routes.comedy_noun_exclusion_collection = MagicMock(return_value=object())
        routes.prepare_prompt.return_value = {
            "full_prompt": "masked", "preprocessing": None,
            "contenders": {"nouns": ["otter"], "animals": ["sextant"]},
        }
        routes.send_prompt.return_value = {"title": "new", "extract": "new"}
        routes.format_shizzalise_result.return_value = dict(fixture.result)
        routes.copy_edit_pass.return_value = None
        with patch.dict(os.environ, {"NEWSMUNCHER_NOUN_EXCLUSION": "evaluation"}):
            routes.shizzalise_data(
                routes.ShizzRequest(title="source", description="", extract="source"),
                "alice", "alice")
        memory.reserve.assert_called_once()
        memory.complete.assert_called_once()
    finally:
        fixture.tearDown(); fixture.doCleanups()


def test_route_releases_reservation_when_provider_fails():
    import test_image_generation as fixtures
    fixture = fixtures.ImageTests(); fixture.setUp()
    try:
        routes = fixture.previews()
        memory = MagicMock()
        memory.exclusions.return_value = set()
        memory.reserve.return_value = True
        routes.NounExclusionMemory = MagicMock(return_value=memory)
        routes.comedy_noun_exclusion_collection = MagicMock(return_value=object())
        routes.prepare_prompt.return_value = {
            "full_prompt": "masked", "preprocessing": None, "contenders": {}}
        routes.send_prompt.return_value = None
        with patch.dict(os.environ, {"NEWSMUNCHER_NOUN_EXCLUSION": "evaluation"}):
            try:
                routes.shizzalise_data(
                    routes.ShizzRequest(title="source", description="", extract="source"),
                    "alice", "alice")
            except routes.HTTPException:
                pass
        memory.release.assert_called_once()
        memory.complete.assert_not_called()
    finally:
        fixture.tearDown(); fixture.doCleanups()
