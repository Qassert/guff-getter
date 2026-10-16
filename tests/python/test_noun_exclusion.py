from datetime import datetime, timezone
from collections import Counter
import os
import threading
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
import pytest
from pymongo.errors import DuplicateKeyError

from newsmuncher.services.comedy_audit import build_audit_record
from newsmuncher.services.concept_selection import (
    ConceptRegistry, ConceptSelectionConfig, TARGET_QUOTAS,
)
from newsmuncher.services.comedy_concepts import normalised
from newsmuncher.services.noun_exclusion import (
    automatic_repetition_enabled,
    NounExclusionConfig, NounExclusionMemory, attribute_violations, blocked_entries,
    TRACKED_COMIC_IDENTITIES, extract_final_entries, filter_candidates,
    discover_recent_identities, discover_used_constructions, identity_entries,
    ingredient_texts, phrase_found, short_animal_mentions,
)
from test_name_selection import MemoryCollection


def test_species_history_is_soft_but_complete_animal_jokes_remain_hard():
    historical = {"noun_identity:pangolin", "phrase:pangolin"}
    assert blocked_entries("pangolin refusing the conservatory", historical) == []
    assert identity_entries("pangolin") == set()

    complete_joke = identity_entries("pangolin refusing the conservatory")
    assert "phrase:pangolin refusing conservatory" in complete_joke
    assert blocked_entries("a pangolin refusing the conservatory", complete_joke)


def test_final_animal_use_enters_soft_history_without_hard_species_entry():
    concept = {
        "phrase": "pangolin refusing the conservatory", "base": "pangolin",
        "animal_species": "pangolin", "premise_key": "refusal:conservatory",
    }
    entries = extract_final_entries(
        title="", body="A pangolin refusing the conservatory arrived.",
        source_text="", concepts=[concept])
    assert "phrase:pangolin" not in entries
    assert "noun_identity:pangolin" not in entries
    assert "phrase:pangolin refusing conservatory" in entries
    assert "premise:refusal:conservatory" in entries
    assert "pangolin" in discover_recent_identities(
        "Several pangolins' objections were recorded.")


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


class MongoUpsertConflictCollection(Collection):
    """Model Mongo's duplicate _id error for a conditional upsert miss."""

    def update_one(self, query, update, upsert=False):
        if upsert and "entries" in query:
            raise DuplicateKeyError("duplicate key: _id")
        return super().update_one(query, update, upsert)


class VanishingConflictCollection(Collection):
    def __init__(self):
        super().__init__()
        self.fail_conditional_once = True

    def update_one(self, query, update, upsert=False):
        if "entries" in query and self.fail_conditional_once:
            self.fail_conditional_once = False
            return SimpleNamespace(matched_count=0, upserted_id=None)
        return super().update_one(query, update, upsert)


class PersistentFilterMismatchCollection(Collection):
    def update_one(self, query, update, upsert=False):
        if "entries" in query:
            return SimpleNamespace(matched_count=0, upserted_id=None)
        return super().update_one(query, update, upsert)


def test_flag_is_default_off_and_validated():
    with patch.dict("os.environ", {}, clear=True):
        assert not NounExclusionConfig.from_environment().enabled
    assert NounExclusionConfig("evaluation").enabled


def test_automatic_repetition_control_is_default_on_and_reversible():
    with patch.dict("os.environ", {}, clear=True):
        assert automatic_repetition_enabled()
    with patch.dict("os.environ", {
            "NEWSMUNCHER_AUTOMATIC_REPETITION_CONTROL": "off"}):
        assert not automatic_repetition_enabled()


def test_plural_and_compound_exclusion_with_source_protection():
    entries = identity_entries("gravy boats")
    assert entries == {"phrase:gravy boat", "noun_identity:gravy"}
    assert blocked_entries("two municipal gravy pumps", entries) == ["noun_identity:gravy"]
    assert blocked_entries("gravy pumps", entries, "Gravy exports rise") == []


def test_phrase_identity_matching_uses_same_connector_normalisation_as_reservation():
    exclusions = identity_entries("beast of burden")
    assert "phrase:beast burden" in exclusions
    assert blocked_entries(
        "quasar radiation-powered beast of burden", exclusions
    ) == ["phrase:beast burden"]


def test_recurring_comic_identities_match_plurals_and_compounds_only():
    for identity in TRACKED_COMIC_IDENTITIES:
        exclusions = {"noun_identity:" + identity}
        assert blocked_entries(
            f"constitutional {identity}-powered lawn mower", exclusions
        ) == ["noun_identity:" + identity]
    assert blocked_entries("the allotmentarian arrived", {
        "noun_identity:allotment"}) == []


def test_final_extraction_tracks_independent_recurring_identity_and_source_exemption():
    entries = extract_final_entries(
        title="Unexpected pudding", body="The apocalypses formed queues beside the allotments.",
        source_text="Ordinary council report")
    assert {"noun_identity:apocalypse", "noun_identity:queue",
            "noun_identity:allotment"} <= entries
    protected = extract_final_entries(
        title="Queue report", body="The queue remained open.",
        source_text="Original report about the queue")
    assert "noun_identity:queue" not in protected


def test_recurring_identity_exclusion_filters_every_concept_bank():
    from newsmuncher.services.comedy_concepts import ComedyConceptGenerator
    generator = ComedyConceptGenerator(
        "cross-bank", noun_exclusions={"noun_identity:queue"})
    for bank in ("everyday_modifiers", "creature_roles", "bureaucratic_disputes"):
        for intensity in (1, 2, 3):
            assert all("queue" not in value.casefold()
                       for value in generator._bank(bank, intensity))


def test_recurring_identity_expires_through_existing_fifo_eviction():
    collection = Collection()
    memory = NounExclusionMemory(
        collection, "pet", NounExclusionConfig("evaluation", capacity=10))
    memory.load()
    initial = ["noun_identity:queue"] + [f"phrase:item {index}" for index in range(9)]
    assert memory.complete("first", initial)
    assert memory.complete("second", {"noun_identity:gravy"})
    assert "noun_identity:queue" not in memory.entries
    assert "noun_identity:gravy" in memory.entries


def test_recent_model_inventions_create_bounded_source_aware_guidance():
    collection = Collection()
    memory = NounExclusionMemory(collection, "pet", NounExclusionConfig("evaluation"))
    memory.load()
    for index in range(14):
        identities = {"gravy", "postmaster", f"identity{index}"}
        assert memory.complete(f"rewrite-{index}", set(), identities)
    assert len(memory.recent_identity_events) == 12
    guidance = memory.avoidance_guidance()
    assert "gravy" in guidance and "postmaster" in guidance
    assert len(guidance.split(",")) <= 9
    assert "gravy" not in memory.avoidance_guidance("Source report about gravy exports")


def test_recent_identity_discovery_is_conservative_and_normalised():
    identities = discover_recent_identities(
        "Two relief postmasters inspected gravy-powered kettles while the report was clear.")
    assert {"postmaster", "gravy", "kettle"} <= set(identities)
    assert "powered" not in identities and "report" not in identities
    assert "clear" not in identities


def test_short_animals_are_normalised_into_recent_history_and_guidance():
    assert short_animal_mentions("Emus, a yak's hat, bees' knees, olms and eels") == {
        "emu", "yak", "bee", "olm", "eel",
    }
    identities = discover_recent_identities(
        "Emus met pigs, bees, olms, cows and eels while the source remained dull.")
    assert {"emu", "pig", "bee", "olm", "cow", "eel"} <= set(identities)
    assert "and" not in identities and "the" not in identities

    memory = NounExclusionMemory(Collection(), "pet", NounExclusionConfig("evaluation"))
    memory.load()
    for index in range(2):
        assert memory.complete(f"animals-{index}", set(), {"emu", "bee"})
    guidance = memory.avoidance_guidance()
    assert "emu" in guidance and "bee" in guidance


def test_species_soft_recency_expires_after_twelve_other_articles():
    collection = Collection()
    memory = NounExclusionMemory(collection, "pet", NounExclusionConfig("evaluation"))
    memory.load()
    assert memory.complete("animal", set(), {"pangolin"})
    assert memory.identity_penalties()["word:pangolin"] > 0
    for index in range(12):
        assert memory.complete(f"later-{index}", set(), {f"identity{index}"})
    assert "word:pangolin" not in memory.identity_penalties()


def test_metadata_identity_discovery_covers_paraphrased_cross_bank_nouns():
    entries = extract_final_entries(
        title="The Parish Floorboard",
        body="A parish official blamed the floorboards before lunch.",
        source_text="A report about a flowering shrub",
    )
    # Metadata-derived identities feed recent-use guidance and soft penalties;
    # one prose appearance must not promote them into hard FIFO exclusions.
    assert "noun_identity:parish" not in entries
    assert "noun_identity:floorboard" not in entries
    assert {"parish", "floorboard"} <= set(discover_recent_identities(
        "A parish official blamed the floorboards before lunch."))
    assert not blocked_entries(
        "the floorboards framed it", {"noun_identity:floorboard"})
    assert not blocked_entries(
        "militant parish returning officer", {"noun_identity:parish"})


def test_structured_constructions_survive_conservative_editor_paraphrases():
    concepts = [
        {"phrase": "pad refusing to recognise linear time", "base": "pad",
         "semantic_theme": "principled_refusal",
         "premise_key": "principled_refusal:recogniselineartime"},
        {"phrase": "yak refusing to enter the conservatory", "base": "yak",
         "semantic_theme": "principled_refusal",
         "premise_key": "principled_refusal:entertheconservatory"},
        {"phrase": "stoat working as volunteer library warden", "base": "stoat",
         "semantic_theme": "absurd_occupation",
         "premise_key": "absurd_occupation:volunteerlibrarywarden"},
    ]
    found = discover_used_constructions(
        "A badger rejects linear time, refuses the conservatory and serves as "
        "volunteer library warden.", "A report about a station.", concepts)
    assert {item["key"] for item in found} == {
        "principled_refusal:recogniselineartime",
        "principled_refusal:entertheconservatory",
        "absurd_occupation:volunteerlibrarywarden",
    }
    assert {item["match"] for item in found} == {"exact", "paraphrased"}


def test_refusal_pattern_tracks_complete_target_not_reusable_grammar():
    concepts = [
        {"phrase": f"otter refusing to recognise {target}", "base": "otter",
         "semantic_theme": "principled_refusal",
         "premise_key": "principled_refusal:recognise" + target.replace(" ", "")}
        for target in ("linear time", "fishing tackle", "carpet")
    ]
    found = discover_used_constructions(
        "A badger rejects linear time, while another refuses to recognise carpet.",
        "", concepts)
    assert {item["key"] for item in found} == {
        "principled_refusal:recogniselineartime",
        "principled_refusal:recognisecarpet",
    }
    assert "principled_refusal:recognisefishingtackle" not in {
        item["key"] for item in found}


def test_complete_joke_penalty_does_not_penalise_different_refusal_targets():
    collection = Collection()
    memory = NounExclusionMemory(collection, "pet", NounExclusionConfig("evaluation"))
    memory.load()
    repeated = [{"key": "principled_refusal:recogniselineartime",
                 "label": "recognise linear time", "match": "paraphrased"}]
    assert memory.complete("one", set(), recent_constructions=repeated)
    assert memory.complete("two", set(), recent_constructions=repeated)
    penalties = memory.identity_penalties()
    assert penalties["premise:principled_refusal:recogniselineartime"] > 0
    assert penalties["identity:recognise-linear-time"] > 0
    assert penalties["premise:principled_refusal:recognisefishingtackle"] == 0
    assert penalties["premise:principled_refusal:recognisecarpet"] == 0
    guidance = memory.avoidance_guidance()
    assert "complete comic ideas: recognise linear time" in guidance
    assert "patterns remain available" in guidance
    assert "recognise fishing tackle" not in guidance
    assert "recognise carpet" not in guidance


def test_construction_matching_does_not_merge_different_related_jokes():
    concepts = [{
        "phrase": "pad refusing to recognise linear time", "base": "pad",
        "semantic_theme": "principled_refusal",
        "premise_key": "principled_refusal:recogniselineartime",
    }]
    assert discover_used_constructions(
        "A badger invoices the future and folds Tuesday in half.", "", concepts) == []


def test_construction_history_adds_soft_penalty_and_bounded_guidance():
    collection = Collection()
    memory = NounExclusionMemory(collection, "pet", NounExclusionConfig("evaluation"))
    memory.load()
    construction = [{"key": "absurd_occupation:volunteerlibrarywarden",
                     "label": "volunteer library warden", "match": "exact"}]
    assert memory.complete("one", set(), recent_constructions=construction)
    assert memory.complete("two", set(), recent_constructions=construction)
    penalties = memory.identity_penalties()
    assert penalties["premise:absurd_occupation:volunteerlibrarywarden"] > 0
    assert penalties["identity:volunteer-library-warden"] > 0
    guidance = memory.avoidance_guidance()
    assert "volunteer library warden" in guidance
    assert len(guidance.split(",")) <= 9
    assert memory.entries == []


def test_reservation_reports_completed_history_conflict_after_stale_snapshot():
    collection = Collection()
    first = NounExclusionMemory(collection, "pet", NounExclusionConfig("evaluation"))
    stale = NounExclusionMemory(collection, "pet", NounExclusionConfig("evaluation"))
    first.load(); stale.load()
    assert first.complete("completed", {"noun_identity:otter"})
    assert not stale.reserve("later", {"noun_identity:otter", "phrase:fresh trumpet"})
    assert stale.last_reservation_conflict == {
        "reason": "completed_history",
        "completed_entries": ["noun_identity:otter"],
        "active_entries": [],
        "active_owner_count": 0,
    }
    assert stale.reservations == []


def test_reservation_filter_mismatch_avoids_duplicate_key_diagnostic_gap():
    collection = MongoUpsertConflictCollection()
    first = NounExclusionMemory(collection, "pet", NounExclusionConfig("evaluation"))
    stale = NounExclusionMemory(collection, "pet", NounExclusionConfig("evaluation"))
    first.load(); stale.load()
    assert first.complete("completed", {"noun_identity:otter"})
    assert not stale.reserve("later", {"noun_identity:otter", "phrase:fresh trumpet"})
    assert stale.last_reservation_conflict["reason"] == "completed_history"
    assert stale.last_reservation_conflict["completed_entries"] == ["noun_identity:otter"]


def test_reservation_retries_once_when_fresh_state_has_no_conflict():
    collection = VanishingConflictCollection()
    memory = NounExclusionMemory(collection, "pet", NounExclusionConfig("evaluation"))
    memory.load()
    assert memory.reserve("generation", {"noun_identity:otter"})
    assert memory.last_reservation_conflict == {}
    assert memory.reservations[0]["entries"] == ["noun_identity:otter"]


def test_unexplained_atomic_mismatch_has_specific_diagnostic_reason():
    collection = PersistentFilterMismatchCollection()
    memory = NounExclusionMemory(collection, "pet", NounExclusionConfig("evaluation"))
    memory.load()
    assert not memory.reserve("generation", {"noun_identity:otter"})
    assert memory.last_reservation_conflict == {
        "reason": "atomic_filter_mismatch_without_visible_conflict",
        "completed_entries": [], "active_entries": [], "active_owner_count": 0,
    }


def test_soft_identity_penalty_reduces_role_selection_without_banning_it():
    from newsmuncher.services.comedy_concepts import ComedyConceptGenerator
    baseline = 0
    penalised = 0
    for seed in range(500):
        baseline += (ComedyConceptGenerator(seed)._pick(
            "creature_roles", 1) == "relief postmaster")
        penalised += (ComedyConceptGenerator(
            seed, lexical_penalties={"word:postmaster": 100})._pick(
                "creature_roles", 1) == "relief postmaster")
    assert baseline > penalised
    assert any(ComedyConceptGenerator(
        seed, lexical_penalties={"word:postmaster": 100})._pick(
            "creature_roles", 1) == "relief postmaster" for seed in range(5000))


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


def test_beast_of_burden_exclusion_is_removed_before_final_reservation():
    exclusions = {"phrase:beast burden"}
    service = ConceptRegistry(MemoryCollection())
    selected = service.offer("beast-burden-regression", noun_exclusions=exclusions)
    assert len(selected) == 20
    assert Counter(item["target_bank"] for item in selected) == {
        "nouns": 14, "animals": 6,
    }
    assert all(not blocked_entries(item["phrase"], exclusions) for item in selected)


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
    assert max(counts[("nouns", category)] - quota
               for category, quota in TARGET_QUOTAS["nouns"].items()
               if category != "bureaucratic_nonsense") <= (
                   service.last_metrics["category_quota_slack"])
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
    assert entries == {"phrase:gravy boat", "noun_identity:gravy"}
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
            "recent_identities": ["floorboard", "parish"],
            "automatic_repetition": {
                "recent_events": 2,
                "recent_identity_history": [
                    {"rewrite_id": "one", "identities": ["floorboard"]}],
                "applied_penalties": {"word:floorboard": 12},
                "guidance": "Avoid floorboard.",
            },
        })
    assert record["noun_exclusion"] == {
        "enabled": True, "excluded_before": 40, "reserved_ingredients": 12,
        "prevented_ingredient_candidates": 3,
        "offered_ingredient_violations": ["noun_identity:gravy"],
        "model_introduced_violations": ["noun_identity:gravy"],
        "newly_extracted": ["noun:otter"],
        "recent_identities": ["floorboard", "parish"],
        "automatic_repetition": {
            "recent_events": 2,
            "recent_identity_history": [
                {"rewrite_id": "one", "identities": ["floorboard"]}],
            "applied_penalties": {"word:floorboard": 12.0},
            "guidance": "Avoid floorboard.",
        },
    }


def test_auxiliary_bank_is_included_in_violation_attribution():
    selected = list(ingredient_texts(contenders={"slang": ["ball gravy"],
                                                 "names": ["Gravy"]}))
    result = attribute_violations(
        "A ball-gravy trumpet appeared.", {"noun_identity:gravy"}, selected)
    assert result["offered_ingredient_violations"] == ["noun_identity:gravy"]
    assert result["model_introduced_violations"] == []


def test_prompt_filters_hard_exclusions_from_auxiliary_banks():
    from newsmuncher.config import PROMPT_FILE
    from newsmuncher.utils.clean_data import prepare_prompt
    banks = {
        key: [f"{key} safe value {index}" for index in range(10)]
        for key in ("nouns", "animals", "adverbs", "places", "names")
    }
    banks["slang"] = ["ball gravy"] + [f"safe slang {index}" for index in range(10)]
    result = prepare_prompt(
        {"title": "Plant", "description": "Species", "extract": "A shrub."},
        10, PROMPT_FILE.read_text(encoding="utf-8"),
        word_banks_override=banks,
        noun_exclusions={"noun_identity:gravy"},
    )
    assert "ball gravy" not in result["contenders"]["slang"]
    assert len(result["contenders"]["slang"]) == 10


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


def test_route_reservation_conflict_reports_entry_and_releases_leases(capsys):
    import test_image_generation as fixtures
    fixture = fixtures.ImageTests(); fixture.setUp()
    try:
        routes = fixture.previews()
        memory = MagicMock()
        memory.exclusions.return_value = {"noun_identity:otter"}
        memory.reserve.return_value = False
        memory.last_reservation_conflict = {
            "reason": "completed_history",
            "completed_entries": ["noun_identity:otter"],
            "active_entries": [], "active_owner_count": 0,
        }
        routes.NounExclusionMemory = MagicMock(return_value=memory)
        routes.comedy_noun_exclusion_collection = MagicMock(return_value=object())
        routes.prepare_prompt.return_value = {
            "full_prompt": "masked", "preprocessing": None,
            "contenders": {"nouns": ["otter"]},
        }
        with patch.dict(os.environ, {"NEWSMUNCHER_NOUN_EXCLUSION": "evaluation"}):
            with pytest.raises(routes.HTTPException) as failure:
                routes.shizzalise_data(
                    routes.ShizzRequest(title="source", description="", extract="source"),
                    "alice", "alice")
        assert failure.value.status_code == 409
        assert not routes.send_prompt.called
        memory.release.assert_called_once()
        output = capsys.readouterr().out
        assert '"completed_entries": ["noun_identity:otter"]' in output
        assert '"reason": "completed_history"' in output
        assert '"origin": "already_excluded_at_selection"' in output
        assert '"selection_snapshot_entries": ["noun_identity:otter"]' in output
        assert '"stage": "noun_reservation"' in output
    finally:
        fixture.tearDown(); fixture.doCleanups()


def test_prompt_validation_409_reports_stage_before_provider(capsys):
    import test_image_generation as fixtures
    fixture = fixtures.ImageTests(); fixture.setUp()
    try:
        routes = fixture.previews()
        memory = MagicMock()
        memory.exclusions.return_value = set()
        routes.NounExclusionMemory = MagicMock(return_value=memory)
        routes.comedy_noun_exclusion_collection = MagicMock(return_value=object())
        routes.prepare_prompt.side_effect = routes.NounExclusionExhausted(
            "local prompt ingredient collision")
        with patch.dict(os.environ, {"NEWSMUNCHER_NOUN_EXCLUSION": "evaluation"}):
            with pytest.raises(routes.HTTPException) as failure:
                routes.shizzalise_data(
                    routes.ShizzRequest(title="source", description="", extract="source"),
                    "alice", "alice")
        assert failure.value.status_code == 409
        assert not routes.send_prompt.called
        output = capsys.readouterr().out
        assert '"stage": "prompt_construction"' in output
        assert '"provider_entered": false' in output
        assert '"exception": "NounExclusionExhausted"' in output
    finally:
        fixture.tearDown(); fixture.doCleanups()
