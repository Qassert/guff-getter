"""Offline integration checks for the in-session editorial catalogue batch."""
from collections import Counter
import json
from pathlib import Path

from newsmuncher.services.comedy_concepts import ComedyConceptGenerator, SEMANTIC_THEMES
from newsmuncher.services.concept_selection import ConceptRegistry, ConceptSelectionConfig
from newsmuncher.services.munge_engines import modern_prompt_concepts
from newsmuncher.services.noun_exclusion import (
    NounExclusionConfig, NounExclusionMemory, blocked_entries, identity_entries,
)
from newsmuncher.services.vocabulary_catalogue import VocabularyCatalogue, eligible_concept_entries
from test_name_selection import MemoryCollection
from test_noun_exclusion import Collection


REVIEW = Path("docs/candidates/codex-catalogue-expansion-2026-10-18.json")


def accepted(kind):
    return [r for r in json.loads(REVIEW.read_text())["candidates"]
            if r["kind"] == kind and r["review"]["status"] == "accepted"]


def test_catalogue_additions_are_reviewed_traceable_and_selectable():
    catalogue = VocabularyCatalogue.load()
    assert not [issue for issue in catalogue.validate() if issue.level == "error"]
    additions = accepted("vocabulary")
    ids = {r["integrated_id"] for r in additions}
    eligible = {r["id"]: r for r in eligible_concept_entries("objects", "reviewed")}
    assert len(ids) == 299 and ids <= eligible.keys()
    for row in additions:
        entry = eligible[row["integrated_id"]]
        assert entry["text"] == row["text"]
        assert entry["familiarity"] in {"common", "unusual"}
        assert entry["editorial_review"]["human_reviewed"] is False
        assert ("intentional_fiction" in entry["editorial_flags"]) == row["fictional"]
    generator = ComedyConceptGenerator("catalogue-integration", vocabulary_mode="reviewed")
    banks = set().union(*(generator._bank(name) for name in (
        "domestic_objects", "cheeky_objects", "devices", "emergency_devices", "ceremonial_objects")))
    assert {r["text"] for r in additions} <= banks


def test_every_new_premise_works_in_its_existing_template_and_hard_filter():
    generator = ComedyConceptGenerator("premise-grammar")
    additions = accepted("premise")
    assert len(additions) == 118
    for row in additions:
        category, template = next(
            (category, template)
            for category, templates in generator.data["templates"].items()
            for template in templates if template.get("modifier_bank") == row["bank"])
        assert row["text"] in generator._bank(row["bank"], row["intensity"])
        base = "guinea pig" if category == "ridiculous_creature" else "trouser press"
        original_templates, original_pick = generator._templates_for, generator._pick
        try:
            generator._templates_for = lambda *args: [template]
            generator._pick = lambda bank, *args: (
                row["text"] if bank == row["bank"] else base)
            concept, _ = generator._candidate(category, row["intensity"])
        finally:
            generator._templates_for, generator._pick = original_templates, original_pick
        assert generator.rejection_reason(concept) is None, concept.phrase
        exclusion = "premise:" + concept.premise_key
        filtered = ComedyConceptGenerator("blocked", noun_exclusions={exclusion})
        assert row["text"] not in filtered._bank(
            row["bank"], row["intensity"], SEMANTIC_THEMES[template["mechanism"]])


def test_consecutive_current_slates_use_active_window_and_release_all_leases():
    collection, registry_collection = Collection(), MemoryCollection()
    memory = NounExclusionMemory(collection, "synthetic-pet", NounExclusionConfig("evaluation"))
    old = [f"phrase:archived {i:04d}" for i in range(2000)]
    active = [f"phrase:synthetic {i:04d}" for i in range(1495)]
    active += ["noun_identity:gravy", "noun_identity:queue", "phrase:beast burden",
               "premise:principled_refusal:recogniselineartime",
               "premise:impossible_measurement:weighceremonialdignity"]
    collection.doc = {"_id": memory.record_id, "entries": old + active,
                      "reservations": [], "revision": 1}
    service = ConceptRegistry(registry_collection,
                              ConceptSelectionConfig(new_vocabulary=True))
    for index in range(3):
        key = f"catalogue-review-{index}"
        memory.load()
        exclusions = memory.exclusions()
        selected = service.offer(key, noun_exclusions=exclusions)
        assert Counter(r["target_bank"] for r in selected) == {"nouns": 14, "animals": 6}
        assert all(not blocked_entries(r["phrase"], exclusions) for r in selected)
        shown, _ = modern_prompt_concepts(selected)
        assert Counter(r["target_bank"] for r in shown) == {"nouns": 14, "animals": 4}
        requested = set().union(*(identity_entries(r["phrase"]) | {
            "premise:" + r["premise_key"]} for r in shown))
        assert memory.reserve(key, requested)
        # Synthetic success: only two offered phrases survive in final prose.
        used = shown[:2]
        service.accept(key, key, shown, "", ". ".join(r["phrase"] for r in used))
        final_entries = set().union(*(identity_entries(r["phrase"]) | {
            "premise:" + r["premise_key"]} for r in used))
        assert memory.complete(key, final_entries)
        assert collection.doc["reservations"] == []
        assert not any(r.get("offered_by") for r in registry_collection.docs.values())
        assert len(memory.entries) == 1500
