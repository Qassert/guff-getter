from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from pymongo.errors import DuplicateKeyError

from newsmuncher.services.radical_comedy import (
    RADICAL_CONTROLLING_PREMISE_ENV,
    RADICAL_CONTROLLING_PREMISE_EXCLUDED_BANKS,
    RadicalControllingPremiseConfig,
    RadicalPlaceholderError, RadicalPremiseConfig, RadicalPremiseMemory,
    detect_radical_premises, eligible_radical_controlling_premises,
    prepare_radical_prompt,
    radical_controlling_premises, radical_inspirations,
    restore_radical_placeholders, select_radical_controlling_premise,
)


class MemoryCollection:
    def __init__(self):
        self.docs = {}

    def find_one(self, query):
        return deepcopy(self.docs.get(query["_id"]))

    def update_one(self, query, update, upsert=False):
        key = query["_id"]
        doc = self.docs.get(key)
        rewrite = query.get("events.rewrite_id", {}).get("$ne")
        if doc and rewrite and any(
                event.get("rewrite_id") == rewrite for event in doc.get("events", ())):
            return SimpleNamespace(matched_count=0, upserted_id=None)
        inserted = doc is None
        if inserted:
            doc = {"_id": key, **deepcopy(update.get("$setOnInsert", {}))}
            self.docs[key] = doc
        push = update.get("$push", {}).get("events")
        if push:
            events = list(doc.get("events", ())) + deepcopy(push["$each"])
            doc["events"] = events[push["$slice"]:]
        return SimpleNamespace(
            matched_count=not inserted, upserted_id=key if inserted else None)


def premise_keys(text, source=""):
    return {item["key"] for item in detect_radical_premises(text, source)}


def test_semantic_premises_keep_mechanism_and_distinctive_target_together():
    assert premise_keys("The mayor refuses to recognise linear time.") == {
        "refusal_target:linear time"}
    assert premise_keys("The mayor rejects linear time.") == {
        "refusal_target:linear time"}
    assert premise_keys("The mayor refuses to recognise fishing tackle.") == {
        "refusal_target:fishing tackle"}
    assert premise_keys("The mayor refuses to recognise carpet.") == {
        "refusal_target:carpet"}


def test_premise_detection_covers_relationships_and_exempts_source_ideas():
    text = ("The gazebo became a municipal sponge and was mistaken for the deputy moon. "
            "It was married to a wheelie bin made of nervous custard.")
    keys = premise_keys(text)
    assert "transformation:municipal sponge" in keys
    assert "mistaken_identity:deputy moon" in keys
    assert "invented_relationship:wheelie bin" in keys
    assert premise_keys("The gazebo became a sponge.",
                        "The gazebo became a sponge.") == set()


def test_memory_is_per_pet_bounded_soft_and_retry_safe():
    collection = MemoryCollection()
    first = RadicalPremiseMemory(
        collection, "pet-a", RadicalPremiseConfig(history_articles=3, guidance_items=2),
        now=lambda: datetime(2026, 10, 17, tzinfo=timezone.utc))
    second = RadicalPremiseMemory(collection, "pet-b")
    for index, body in enumerate((
        "The chair became a municipal sponge.",
        "The table was mistaken for a deputy moon.",
        "The lamp married a wheelie bin.",
        "The wardrobe was made of nervous custard.",
    )):
        first.accept(f"rewrite-{index}", "Title", body)
    assert len(first.events) == 3
    guidance = first.guidance()
    assert guidance.count("\n-") == 2
    assert "physical property involving nervous custard" in guidance
    assert second.load() == []
    assert first.accept("rewrite-3", "Title", "The wardrobe became fog.") == []
    assert len(first.events) == 3


def test_concurrent_scope_creation_retries_atomic_event_push():
    class RacingCollection(MemoryCollection):
        raced = False
        def update_one(self, query, update, upsert=False):
            if upsert and not self.raced:
                self.raced = True
                self.docs[query["_id"]] = {
                    "_id": query["_id"], "version": 1,
                    "record_type": "radical_premise_memory", "events": []}
                raise DuplicateKeyError("concurrent creator")
            return super().update_one(query, update, upsert)

    collection = RacingCollection()
    memory = RadicalPremiseMemory(collection, "pet")
    accepted = memory.accept(
        "rewrite", "Title", "The gazebo became a municipal sponge.")
    assert accepted == ["transformation:municipal sponge"]
    assert collection.docs[memory.record_id]["events"][0]["rewrite_id"] == "rewrite"


def test_radical_prompt_is_seeded_source_led_and_uses_only_optional_sparks():
    source = {"title": "Mayor opens bridge", "description": "Today",
              "extract": "The mayor opened the bridge after lunch."}
    first = prepare_radical_prompt(source, "rewrite-1", "Avoid the sponge premise.")
    second = prepare_radical_prompt(source, "rewrite-1", "Avoid the sponge premise.")
    assert first["full_prompt"] == second["full_prompt"]
    assert first["contenders"] == {}
    assert len(first["radical_inspirations"]) == 6
    assert "not a checklist" in first["full_prompt"]
    assert "Create fresh comic premises" in first["full_prompt"]
    assert "stable aliases" in first["full_prompt"]
    assert "Replace most significant unprotected ordinary nouns" in first["full_prompt"]
    assert "Transform the\ncentral generic subject itself" in first["full_prompt"]
    assert "there is no sentence-by-\nsentence correspondence requirement" in first["full_prompt"]
    assert "Preserve event-level progression, not original wording" in first["full_prompt"]
    assert "Do not append detached one-liners" in first["full_prompt"]
    assert "Keep the source's principal subjects" not in first["full_prompt"]
    assert "Each rewritten sentence should do the narrative work" not in first["full_prompt"]
    assert "The mayor opened the bridge after lunch." in first["full_prompt"]
    assert first["preprocessing"] is not None


def test_controlling_premise_catalogue_filters_modifier_banks_without_mutation():
    premises = radical_controlling_premises()
    eligible = eligible_radical_controlling_premises()
    assert len(premises) == 118
    assert len(eligible) == 88
    assert len({item.identifier for item in premises}) == 118
    assert len({item.mechanism_family for item in premises}) == 11
    assert len({item.mechanism_family for item in eligible}) == 8
    assert all(item.text and item.bank and item.mechanism_family for item in premises)
    excluded = [item for item in premises
                if item.bank in RADICAL_CONTROLLING_PREMISE_EXCLUDED_BANKS]
    assert len(excluded) == 30
    assert not ({item.identifier for item in excluded}
                & {item.identifier for item in eligible})

    # Filtering is a selector view only. Every entry remains in its original
    # intensity-specific production bank.
    data = json.loads(Path(
        "newsmuncher/resources/concepts/comedy_concept_components.json"
    ).read_text(encoding="utf-8"))
    for item in excluded:
        bank = data["banks"][item.bank]
        values = bank[str(item.intensity)] if isinstance(bank, dict) else bank
        assert item.text in values


def test_controlling_premise_selection_is_deterministic_and_reaches_every_family():
    eligible_families = {
        item.mechanism_family for item in eligible_radical_controlling_premises()}
    assert (select_radical_controlling_premise("rewrite-1") ==
            select_radical_controlling_premise("rewrite-1"))
    selected_families = {
        select_radical_controlling_premise(f"family-coverage-{index}").mechanism_family
        for index in range(500)
    }
    assert selected_families == eligible_families


def test_empty_controlling_premise_pool_degrades_to_baseline_prompt(monkeypatch):
    monkeypatch.setenv(RADICAL_CONTROLLING_PREMISE_ENV, "evaluation")
    monkeypatch.setattr(
        "newsmuncher.services.radical_comedy.radical_controlling_premises",
        lambda: (),
    )
    prepared = prepare_radical_prompt(
        {"title": "Mayor", "description": "", "extract": "The mayor opened a bridge."},
        "empty-pool",
    )
    assert prepared["radical_controlling_premise_enabled"] is True
    assert prepared["radical_controlling_premise"] is None
    assert "CONTROLLED PREMISE EXPERIMENT" not in prepared["full_prompt"]


def test_controlling_premise_flag_is_default_off_and_preserves_prompt(monkeypatch):
    monkeypatch.delenv(RADICAL_CONTROLLING_PREMISE_ENV, raising=False)
    source = {"title": "Mayor opens bridge", "description": "Today",
              "extract": "The mayor opened the bridge after lunch."}
    prepared = prepare_radical_prompt(source, "rewrite-off")
    assert prepared["radical_controlling_premise_enabled"] is False
    assert prepared["radical_controlling_premise"] is None
    assert "CONTROLLED PREMISE EXPERIMENT" not in prepared["full_prompt"]
    assert RadicalControllingPremiseConfig().enabled is False


def test_enabled_controlling_premise_is_primary_but_sparks_stay_secondary(monkeypatch):
    monkeypatch.setenv(RADICAL_CONTROLLING_PREMISE_ENV, "evaluation")
    source = {"title": "Mayor opens bridge", "description": "Today",
              "extract": "The mayor opened the bridge after lunch."}
    first = prepare_radical_prompt(source, "rewrite-enabled")
    second = prepare_radical_prompt(source, "rewrite-enabled")
    premise = first["radical_controlling_premise"]
    assert first["full_prompt"] == second["full_prompt"]
    assert premise == second["radical_controlling_premise"]
    assert first["radical_controlling_premise_enabled"] is True
    assert premise.identifier.startswith("codex-session-2026-10-18:premise:")
    assert f"Mechanism seed: {premise.text}" in first["full_prompt"]
    assert "transform the central generic subject or function" in first["full_prompt"]
    assert "through at least two existing narrative beats" in first["full_prompt"]
    assert "do not merely insert or quote the wording" in first["full_prompt"]
    assert "optional sparks remain secondary inspiration" in first["full_prompt"]
    assert len(first["radical_inspirations"]) == 6


def test_controlling_premise_flag_rejects_unknown_mode():
    with pytest.raises(ValueError, match=RADICAL_CONTROLLING_PREMISE_ENV):
        RadicalControllingPremiseConfig("on")


def test_radical_prompt_keeps_ordinary_nouns_visible_for_transformation():
    source = {
        "title": "Alice Smith opens London museum",
        "description": "A public ceremony",
        "extract": (
            "Alice Smith opened the dusty museum cupboard in London on 12 March 2020. "
            "Smith carried an ancient brass telescope angrily."
        ),
    }
    prepared = prepare_radical_prompt(source, "rewrite-visible-nouns")
    prompt = prepared["full_prompt"]
    assert prompt.count("[PERSON_1]") >= 2
    assert "[PLACE_1]" in prompt
    assert "[FACT_" in prompt
    for visible in ("dusty museum cupboard", "ancient brass telescope", "angrily"):
        assert visible in prompt
    for protected in ("Alice Smith", "London", "12 March 2020"):
        assert protected not in prompt


def test_radical_fact_placeholders_restore_and_unknown_ones_are_rejected():
    preprocessing = {
        "records": [
            {"placeholder": "[PERSON_1]", "literal": "Alice Smith"},
            {"placeholder": "[FACT_1]", "literal": "12 March 2020"},
        ],
    }
    restored, count = restore_radical_placeholders({
        "crazyReplacement1Title": "[PERSON_1]",
        "crazyReplacement1Extract": "[PERSON_1] arrived on [FACT_1].",
    }, preprocessing)
    assert count == 3
    assert restored["crazyReplacement1Extract"] == "Alice Smith arrived on 12 March 2020."
    with pytest.raises(RadicalPlaceholderError, match=r"\[FACT_9\]"):
        restore_radical_placeholders({
            "crazyReplacement1Title": "Title",
            "crazyReplacement1Extract": "It happened on [FACT_9].",
        }, preprocessing)


def test_radical_placeholders_restore_consistently_from_actual_failure_pattern():
    preprocessing = {
        "records": [
            {"placeholder": "[PERSON_1]", "literal": "Ada Lovelace"},
            {"placeholder": "[PERSON_1]", "literal": "Lovelace"},
            {"placeholder": "[PLACE_1]", "literal": "London"},
            {"placeholder": "[ORGANIZATION_2]", "literal": "The Royal Society"},
            {"placeholder": "[OBJECT_1]", "literal": "analytical engine"},
            {"placeholder": "[PERSON_3]", "literal": "Charles Babbage"},
        ]}
    result = {
        "crazyReplacement1Title": "[PERSON_1] and [OBJECT_1]",
        "crazyReplacement1Extract": (
            "[PERSON_1] of [PLACE_1] is a [PERSON_1] within [ORGANIZATION_2], "
            "where punctuation sleeps standing up. [PERSON_3] inspects [OBJECT_1]."
        ),
    }
    restored, count = restore_radical_placeholders(result, preprocessing)
    assert count == 8
    assert "[" not in restored["crazyReplacement1Extract"]
    assert restored["crazyReplacement1Extract"].count("Ada Lovelace") == 2
    assert "London" in restored["crazyReplacement1Extract"]
    assert "The Royal Society" in restored["crazyReplacement1Extract"]
    assert "Charles Babbage inspects analytical engine" in restored["crazyReplacement1Extract"]


def test_radical_placeholder_guard_rejects_unknown_structural_alias():
    with pytest.raises(RadicalPlaceholderError, match=r"\[PERSON_9\]"):
        restore_radical_placeholders(
            {"crazyReplacement1Title": "Title",
             "crazyReplacement1Extract": "[PERSON_9] escaped."},
            {"records": []},
        )


def test_radical_sparks_respect_existing_hard_exclusions():
    baseline = radical_inspirations("fixed", count=40)
    blocked = baseline[0]
    filtered = radical_inspirations(
        "fixed", noun_exclusions={"phrase:" + blocked}, count=40)
    assert blocked not in filtered


def test_experimental_route_bypasses_modern_selectors_and_records_after_save():
    from test_image_generation import ImageTests

    fixture = ImageTests(); fixture.setUp()
    try:
        routes = fixture.previews()
        radical = MagicMock()
        radical.events = []
        radical.guidance.return_value = "avoid prior transformed gazebo"
        radical.accept.return_value = ["transformation:municipal sponge"]
        radical.last_metrics = {"accepted": 1}
        routes.RadicalPremiseMemory = MagicMock(return_value=radical)
        routes.ConceptRegistry = MagicMock()
        routes.DescriptorRegistry = MagicMock()
        routes.InventedNameRegistry = MagicMock()
        routes.comedy_noun_exclusion_collection = MagicMock(return_value=object())
        routes.prepare_radical_prompt = MagicMock(return_value={
            "full_prompt": "radical prompt", "preprocessing": None,
            "contenders": {}, "radical_inspirations": ["wheelie bin"],
        })
        routes.send_prompt.return_value = {
            "title": "Gazebo", "extract": "The gazebo became a municipal sponge."}
        routes.format_shizzalise_result.return_value = dict(fixture.result)
        routes.copy_edit_pass.return_value = None

        result = routes.shizzalise_data(routes.ShizzRequest(
            title="source", description="", extract="body", engine="experimental"),
            "alice", "alice")

        assert result["munge_engine"] == "experimental"
        routes.prepare_radical_prompt.assert_called_once()
        routes.prepare_prompt.assert_not_called()
        routes.ConceptRegistry.assert_not_called()
        routes.DescriptorRegistry.assert_not_called()
        routes.InventedNameRegistry.assert_not_called()
        routes.copy_edit_pass.assert_called_once_with(
            dict(fixture.result), radical_mode=True)
        routes.send_prompt.assert_called_once_with("radical prompt")
        routes.claim_used_words.assert_not_called()
        radical.accept.assert_called_once()
    finally:
        fixture.tearDown(); fixture.doCleanups()


def test_failed_experimental_generation_does_not_record_premise_history():
    from test_image_generation import ImageTests

    fixture = ImageTests(); fixture.setUp()
    try:
        routes = fixture.previews()
        radical = MagicMock(events=[], last_metrics={})
        radical.guidance.return_value = ""
        radical.accept.return_value = []
        routes.RadicalPremiseMemory = MagicMock(return_value=radical)
        routes.comedy_noun_exclusion_collection = MagicMock(return_value=object())
        routes.prepare_radical_prompt = MagicMock(return_value={
            "full_prompt": "radical prompt", "preprocessing": None,
            "contenders": {}, "radical_inspirations": [],
        })
        routes.send_prompt.side_effect = RuntimeError("provider failed")

        with pytest.raises(RuntimeError, match="provider failed"):
            routes.shizzalise_data(routes.ShizzRequest(
                title="source", description="", extract="body",
                engine="experimental"), "alice", "alice")

        radical.accept.assert_not_called()
        routes.claim_used_words.assert_not_called()
    finally:
        fixture.tearDown(); fixture.doCleanups()


def test_experimental_route_restores_placeholders_before_editing_and_saving():
    from test_image_generation import ImageTests

    fixture = ImageTests(); fixture.setUp()
    try:
        routes = fixture.previews()
        radical = MagicMock(events=[], last_metrics={})
        radical.guidance.return_value = ""
        radical.accept.return_value = []
        routes.RadicalPremiseMemory = MagicMock(return_value=radical)
        routes.comedy_noun_exclusion_collection = MagicMock(return_value=object())
        preprocessing = {"records": [
            {"placeholder": "[PERSON_1]", "literal": "Ada Lovelace"},
            {"placeholder": "[PLACE_1]", "literal": "London"},
            {"placeholder": "[ORGANIZATION_2]", "literal": "The Royal Society"},
        ]}
        routes.prepare_radical_prompt = MagicMock(return_value={
            "full_prompt": "radical prompt", "preprocessing": preprocessing,
            "contenders": {}, "radical_inspirations": [],
        })
        routes.send_prompt.return_value = {
            "title": "[PERSON_1] in [PLACE_1]",
            "extract": ("[PERSON_1] of [PLACE_1] is a [PERSON_1] within "
                        "[ORGANIZATION_2], where punctuation sleeps standing up."),
        }
        routes.format_shizzalise_result.side_effect = lambda response: {
            "crazyReplacement1Title": response["title"],
            "crazyReplacement1Extract": response["extract"],
            "crazyReplacement1done": True,
        }
        routes.copy_edit_pass.return_value = None
        routes.store.complete_draft = MagicMock(
            side_effect=lambda rewrite_id, pet, result: result)

        routes.shizzalise_data(routes.ShizzRequest(
            title="source", description="", extract="body", engine="experimental"),
            "alice", "alice")

        editor_input = routes.copy_edit_pass.call_args.args[0]
        assert "[PERSON_1]" not in editor_input["crazyReplacement1Extract"]
        assert editor_input["crazyReplacement1Extract"].count("Ada Lovelace") == 2
        saved = routes.store.complete_draft.call_args.args[2]
        assert "[" not in saved["crazyReplacement1Title"]
        assert "[" not in saved["crazyReplacement1Extract"]
        assert "The Royal Society" in saved["crazyReplacement1Extract"]
    finally:
        fixture.tearDown(); fixture.doCleanups()


def test_experimental_route_rejects_unknown_placeholder_before_save():
    from fastapi import HTTPException
    from test_image_generation import ImageTests

    fixture = ImageTests(); fixture.setUp()
    try:
        routes = fixture.previews()
        radical = MagicMock(events=[], last_metrics={})
        radical.guidance.return_value = ""
        routes.RadicalPremiseMemory = MagicMock(return_value=radical)
        routes.comedy_noun_exclusion_collection = MagicMock(return_value=object())
        routes.prepare_radical_prompt = MagicMock(return_value={
            "full_prompt": "radical prompt", "preprocessing": {"records": []},
            "contenders": {}, "radical_inspirations": [],
        })
        routes.send_prompt.return_value = {
            "title": "Broken", "extract": "[PERSON_1] remained unresolved."}
        routes.format_shizzalise_result.return_value = {
            "crazyReplacement1Title": "Broken",
            "crazyReplacement1Extract": "[PERSON_1] remained unresolved.",
            "crazyReplacement1done": True,
        }
        routes.store.complete_draft = MagicMock()

        with pytest.raises(HTTPException) as caught:
            routes.shizzalise_data(routes.ShizzRequest(
                title="source", description="", extract="body",
                engine="experimental"), "alice", "alice")

        assert caught.value.status_code == 502
        assert "[PERSON_1]" in caught.value.detail
        routes.store.complete_draft.assert_not_called()
        routes.copy_edit_pass.assert_not_called()
        radical.accept.assert_not_called()
    finally:
        fixture.tearDown(); fixture.doCleanups()
