import random
import os
import sys
import csv
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock, patch

from newsmuncher.services.classic_munge import classic_physical_pool, prepare_classic_prompt
from newsmuncher.services.munge_engines import (
    MungeEngine, engine_plan, project_modern_variant,
)


def test_classic_uses_all_historical_csv_banks_offline():
    result = prepare_classic_prompt(
        {"title": "Source", "description": "Description", "extract": "Body"},
        random_source=random.Random(7),
    )
    assert set(result["contenders"]) == {
        "slang", "nouns", "adverbs", "animals", "names", "places"}
    assert all(len(values) == 10 for values in result["contenders"].values())
    assert "Text to Transform:" in result["full_prompt"]
    assert "Always add 1 rude swear word" in result["full_prompt"]


def _write_object_vocabulary(path, rows):
    with path.open("w", encoding="utf-8", newline="") as target:
        writer = csv.writer(target)
        writer.writerow(["category", "word"])
        writer.writerows(rows)


def test_classic_combines_legacy_objects_and_physical_object_categories(tmp_path):
    legacy = tmp_path / "animalsAndObjects.csv"
    legacy.write_text("legacy badger,Shared   Wrench,legacy kettle", encoding="utf-8")
    shared = tmp_path / "object-generator-vocabulary.csv"
    _write_object_vocabulary(shared, [
        ("object", "robotic gripper"),
        ("device", "signal generator"),
        ("adjective", "luminous"),
        ("surreal_descriptor", "bureaucratic"),
        ("object", " shared wrench "),
    ])

    pool = classic_physical_pool(legacy, shared)
    normalised = {" ".join(word.casefold().split()): word for word in pool}
    assert "legacy badger" in normalised
    assert "robotic gripper" in normalised
    assert "signal generator" in normalised
    assert "luminous" not in normalised
    assert "bureaucratic" not in normalised
    assert list(normalised).count("shared wrench") == 1
    assert normalised["shared wrench"] == "Shared   Wrench"


def test_classic_reads_future_object_additions_without_code_changes(tmp_path):
    shared = tmp_path / "object-generator-vocabulary.csv"
    _write_object_vocabulary(shared, [("object", "future clockwork turnip")])
    with patch("newsmuncher.services.classic_munge.random.sample",
               side_effect=lambda values, count: list(values)[-count:]):
        result = prepare_classic_prompt(
            {"title": "Source", "description": "Description", "extract": "Body"},
            object_vocabulary_path=shared,
        )
    assert len(result["contenders"]["animals"]) == 10
    assert "future clockwork turnip" in result["contenders"]["animals"]
    assert all(len(values) == 10 for values in result["contenders"].values())


def test_classic_falls_back_to_legacy_pool_for_missing_or_malformed_shared_csv(
        tmp_path, caplog):
    legacy = tmp_path / "animalsAndObjects.csv"
    legacy.write_text("badger,emu,wrench", encoding="utf-8")
    missing = tmp_path / "missing.csv"
    assert set(classic_physical_pool(legacy, missing)) == {"badger", "emu", "wrench"}

    malformed = tmp_path / "malformed.csv"
    malformed.write_text("wrong,columns\nobject,anvil\n", encoding="utf-8")
    assert set(classic_physical_pool(legacy, malformed)) == {"badger", "emu", "wrench"}
    assert "using legacy pool only" in caplog.text


def test_current_benchmark_is_independent_of_experimental_options():
    options = {"future_rule": "one"}
    experimental = engine_plan("experimental", options)
    options["future_rule"] = "changed"
    current = engine_plan("current")
    assert current.engine is MungeEngine.CURRENT
    assert current.experimental_options == ()
    assert experimental.experimental_options == (("future_rule", "one"),)
    assert engine_plan("classic").classic_csv is True


def test_projection_removes_hidden_generated_and_raw_animal_provenance():
    nouns = [{"phrase": f"object {index}", "target_bank": "nouns"}
             for index in range(14)]
    generated = [{"phrase": f"{animal} in a hat", "target_bank": "animals",
                  "score": 10-index}
                 for index, animal in enumerate(("tapir", "pangolin", "gibbon"))]
    raw_records = [{"text": animal, "target_bank": "animals"}
                   for animal in ("gorilla", "yak", "emu")]
    raw_prompt = [{"phrase": item["text"], "target_bank": "animals", "raw": True}
                  for item in raw_records]
    plan = {"prompt": nouns + generated + raw_prompt,
            "generated": list(nouns + generated), "raw": raw_records}
    projected, metrics = project_modern_variant(plan)
    assert len(projected["prompt"]) == 18
    assert metrics["presented_animals"] == 4
    assert len(projected["generated"]) + len(projected["raw"]) == 18
    assert not ({"yak", "emu"} & {item["text"] for item in projected["raw"]})


def test_current_presents_reserves_tracks_and_audits_four_of_six_animals():
    from test_image_generation import ImageTests

    fixture = ImageTests(); fixture.setUp()
    try:
        routes = fixture.previews()
        nouns = [{"phrase": f"object {index}", "target_bank": "nouns",
                  "score": 8, "base": f"object {index}",
                  "premise_key": f"object premise {index}"}
                 for index in range(14)]
        species = ("tapir", "pangolin", "gibbon", "gorilla", "yak", "emu")
        animals = [{"phrase": f"{animal} wearing a tabard",
                    "target_bank": "animals", "score": 12-index,
                    "base": animal, "animal_species": animal,
                    "premise_key": f"{animal} tabard"}
                   for index, animal in enumerate(species)]
        tracker = SimpleNamespace(
            offer=MagicMock(return_value=nouns + animals),
            accept=MagicMock(return_value=[]), release=MagicMock(),
            last_metrics={}, last_accept_metrics={},
        )
        routes.ConceptSelectionConfig.from_environment.return_value = SimpleNamespace(
            mode="generated", vocabulary_mode="off")
        routes.ConceptRegistry = MagicMock(return_value=tracker)
        routes.generated_concept_collection = MagicMock(return_value=object())
        memory = MagicMock()
        memory.exclusions.return_value = set()
        memory.identity_penalties.return_value = {}
        memory.avoidance_guidance.return_value = ""
        memory.recent_identity_events = []
        memory.reservations = []
        memory.reserve.return_value = True
        routes.NounExclusionMemory = MagicMock(return_value=memory)
        routes.comedy_noun_exclusion_collection = MagicMock(return_value=object())
        audit = MagicMock()
        routes.ComedyAuditConfig = MagicMock()
        routes.ComedyAuditConfig.from_environment.return_value = SimpleNamespace(enabled=True)
        routes.ComedyAuditLogger = MagicMock(return_value=audit)
        routes.prepare_prompt.return_value = {
            "full_prompt": "prompt", "preprocessing": None, "contenders": {}}
        routes.send_prompt.return_value = {"title": "one", "extract": "body"}
        routes.format_shizzalise_result.return_value = dict(fixture.result)
        routes.copy_edit_pass.return_value = None
        with patch.dict(os.environ, {"NEWSMUNCHER_NOUN_EXCLUSION": "evaluation"}):
            routes.shizzalise_data(routes.ShizzRequest(
                title="source", description="", extract="source", engine="current"),
                "alice", "alice")

        overrides = routes.prepare_prompt.call_args.kwargs["concept_overrides"]
        assert len(overrides["nouns"]) == 14
        assert len(overrides["animals"]) == 4
        tracked = tracker.accept.call_args.args[2]
        assert len(tracked) == 18
        assert sum(item["target_bank"] == "animals" for item in tracked) == 4
        reserved = memory.reserve.call_args.args[1]
        for animal in species[:4]:
            assert any(animal in entry for entry in reserved)
        for animal in species[4:]:
            assert all(animal not in entry for entry in reserved)
        record = audit.append.call_args.args[0]
        audited = record["ingredients"]["offered"]["generated_concepts"]
        assert len(audited) == 18
        assert sum(item.get("target_bank") == "animals" for item in audited) == 4
        memory.complete.assert_called_once()
    finally:
        fixture.tearDown(); fixture.doCleanups()


def test_classic_route_bypasses_modern_prompt_selection_and_records_engine():
    from test_image_generation import ImageTests

    fixture = ImageTests()
    fixture.setUp()
    try:
        routes = fixture.previews()
        classic = ModuleType("newsmuncher.services.classic_munge")
        classic.prepare_classic_prompt = MagicMock(return_value={
            "full_prompt": "classic CSV prompt", "contenders": {"animals": ["tapir"]},
        })
        routes.send_prompt.return_value = {"title": "Classic", "extract": "A tapir."}
        routes.format_shizzalise_result.return_value = dict(fixture.result)
        routes.copy_edit_pass.return_value = None
        with patch.dict(sys.modules, {"newsmuncher.services.classic_munge": classic}):
            result = routes.shizzalise_data(routes.ShizzRequest(
                title="source", description="", extract="body", engine="classic"),
                "alice", "alice")
        assert result["munge_engine"] == "classic"
        classic.prepare_classic_prompt.assert_called_once()
        routes.prepare_prompt.assert_not_called()
        routes.send_prompt.assert_called_once_with("classic CSV prompt")
        routes.claim_used_words.assert_not_called()
    finally:
        fixture.tearDown()
        fixture.doCleanups()


def test_classic_consecutive_rewrites_are_saved_without_vocabulary_claims():
    from test_image_generation import ImageTests

    fixture = ImageTests()
    fixture.setUp()
    try:
        routes = fixture.previews()
        classic = ModuleType("newsmuncher.services.classic_munge")
        classic.prepare_classic_prompt = MagicMock(return_value={
            "full_prompt": "classic CSV prompt", "contenders": {"animals": ["tapir"]},
        })
        routes.send_prompt.return_value = {"title": "Classic", "extract": "A tapir."}
        routes.format_shizzalise_result.side_effect = [
            {**fixture.result, "crazyReplacement1Title": "Classic one"},
            {**fixture.result, "crazyReplacement1Title": "Classic two"},
        ]
        routes.copy_edit_pass.return_value = None
        # This would reproduce the live WordClaimConflict if Classic still
        # attempted to enter the modern claim callback.
        routes.claim_used_words.side_effect = routes.WordClaimConflict("already claimed")
        with patch.dict(sys.modules, {"newsmuncher.services.classic_munge": classic}):
            results = [routes.shizzalise_data(routes.ShizzRequest(
                title="source", description="", extract="body", engine="classic",
                draft_session=f"classic-{index}"), "alice", "alice") for index in range(2)]

        assert [item["crazyReplacement1Title"] for item in results] == [
            "Classic one", "Classic two"]
        assert all(item["munge_engine"] == "classic" for item in results)
        routes.claim_used_words.assert_not_called()
        with fixture.store.transaction() as db:
            saved = [fixture.store.read(db, item["rewrite_id"], "alice") for item in results]
        assert [item["result"]["crazyReplacement1Title"] for item in saved] == [
            "Classic one", "Classic two"]
    finally:
        fixture.tearDown()
        fixture.doCleanups()
