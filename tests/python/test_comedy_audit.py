from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import csv
import json

import pytest

from newsmuncher.services.comedy_audit import (
    ComedyAuditConfig, ComedyAuditLogger, build_audit_record,
)
from scripts.diagnostics.export_comedy_audit import export, load_records


def sample_record(rewrite_id="rewrite-1", environment=None):
    return build_audit_record(
        rewrite_id=rewrite_id,
        timestamp=datetime(2026, 10, 12, 12, 30, tzinfo=timezone.utc),
        source={"title": "Café inquiry", "description": "Résumé", "extract": "Original — text."},
        result={"crazyReplacement1Title": "Pudding's début!",
                "crazyReplacement1Extract": "Sir Gravy met Moon Badger and a wonky milk float."},
        names=["Sir Gravy"],
        concepts=[{"phrase": "wonky milk float", "target_bank": "nouns", "base": "milk float",
                   "premise_key": "behaviour:wonky", "semantic_theme": "unexpected_behaviour"}],
        descriptors=[{"phrase": "ceremonially damp", "subject": "damp",
                      "premise_key": "ritual:damp", "comic_mechanism": "invented_ritual"}],
        contenders={"slang": ["Moon Badger", "Flange Wizard"], "places": ["Pudding End"]},
        timings={"prompt_characters": 1234, "provider": {"elapsed_ms": 12.5},
                 "unsafe_text": "must be removed"},
        environment=environment or {"NEWSMUNCHER_FINAL_JOKE_MEMORY": "evaluation"},
    )


def test_config_defaults_off_and_supports_configured_relative_path(monkeypatch):
    monkeypatch.delenv("NEWSMUNCHER_COMEDY_AUDIT_LOG", raising=False)
    assert not ComedyAuditConfig.from_environment().enabled
    monkeypatch.setenv("NEWSMUNCHER_COMEDY_AUDIT_LOG", "on")
    monkeypatch.setenv("NEWSMUNCHER_COMEDY_AUDIT_PATH", "local_audits/custom.jsonl")
    config = ComedyAuditConfig.from_environment()
    assert config.enabled and config.path.name == "custom.jsonl" and config.path.is_absolute()
    monkeypatch.setenv("NEWSMUNCHER_COMEDY_AUDIT_LOG", "maybe")
    with pytest.raises(ValueError):
        ComedyAuditConfig.from_environment()


def test_disabled_logger_performs_no_write(tmp_path):
    path = tmp_path / "audit.jsonl"
    assert not ComedyAuditLogger(ComedyAuditConfig(False, path)).append(sample_record())
    assert not path.exists()


def test_enabled_logging_preserves_unicode_punctuation_and_optional_metadata(tmp_path):
    path = tmp_path / "audit.jsonl"
    logger = ComedyAuditLogger(ComedyAuditConfig(True, path))
    assert logger.append(sample_record())
    record = load_records(path)[0]
    assert record["source"]["headline"] == "Café inquiry"
    assert record["final"]["headline"] == "Pudding's début!"
    assert record["ingredients"]["found_exactly_in_final"]["names"] == [{"name": "Sir Gravy"}]
    assert record["ingredients"]["found_exactly_in_final"]["legacy"]["slang"] == ["Moon Badger"]
    assert record["semantic"]["found_exact_premise_ids"] == ["behaviour:wonky"]
    assert any(item["evidence"] == "milk float"
               for item in record["semantic"]["topic_memory_detections"])
    minimal = build_audit_record(
        rewrite_id="minimal", source={}, result={}, environment={}, timestamp=datetime.now(timezone.utc))
    assert logger.append(minimal)
    assert load_records(path)[1]["ingredients"]["offered"]["generated_concepts"] == []


def test_hybrid_audit_distinguishes_offered_raw_from_found_raw():
    record = build_audit_record(
        rewrite_id="hybrid", source={},
        result={"crazyReplacement1Title": "A badger inquiry",
                "crazyReplacement1Extract": "The kettle remained innocent."},
        raw_ingredients=[{"text": "badger", "source": "expanded_catalogue"},
                         {"text": "teapot", "source": "legacy_csv"}],
        comparison_variant="D", environment={},
    )
    assert record["comparison_variant"] == "D"
    assert len(record["ingredients"]["offered"]["raw_hybrid_ingredients"]) == 2
    assert record["ingredients"]["found_exactly_in_final"]["raw_hybrid_ingredients"] == [
        {"text": "badger", "source": "expanded_catalogue"}
    ]


def test_audit_distinguishes_first_pass_and_lexical_selection_context():
    record = build_audit_record(
        rewrite_id="lexical", source={},
        result={"crazyReplacement1Title": "Final gravy",
                "crazyReplacement1Extract": "The final custard arrived."},
        first_pass={"crazyReplacement1Title": "Draft gravy",
                    "crazyReplacement1Extract": "The first marmalade arrived."},
        lexical_context={
            "recent_events": 4,
            "penalties": {"word:gravy": 12, "word:custard": 4},
            "selected_with_penalty": [
                {"kind": "concept", "text": "gravy tribunal", "penalty": 12}],
        },
        environment={"NEWSMUNCHER_LEXICAL_DIVERSITY": "evaluation"},
    )
    assert record["first_pass"]["article_text"] == "The first marmalade arrived."
    assert record["final"]["article_text"] == "The final custard arrived."
    assert record["lexical_exposure"]["selection_penalties"]["word:gravy"] == 12
    assert record["lexical_exposure"]["selected_with_penalty"][0]["text"] == "gravy tribunal"
    assert record["feature_flags"]["NEWSMUNCHER_LEXICAL_DIVERSITY"] == "evaluation"


def test_audit_records_selected_and_observed_thematic_influence():
    record = build_audit_record(
        rewrite_id="thematic", source={}, result={},
        thematic_context={
            "recent_events": 6,
            "selection_penalties": {"mycology": 8.4},
            "selected_domains": [{"id": "mycology", "family": "living_systems",
                                  "label": "mycology", "inspiration": "fungal networks",
                                  "keywords": ["fungus", "spore", "mycelium"]}],
            "influenced_domains": [{"id": "mycology", "family": "living_systems",
                                    "matched_keywords": ["spore"]}],
        },
        environment={"NEWSMUNCHER_THEMATIC_DIVERSITY": "evaluation"},
    )
    thematic = record["thematic_diversity"]
    assert thematic["selection_penalties"] == {"mycology": 8.4}
    assert thematic["selected_domains"][0]["id"] == "mycology"
    assert thematic["influenced_domains"][0]["matched_keywords"] == ["spore"]
    assert record["feature_flags"]["NEWSMUNCHER_THEMATIC_DIVERSITY"] == "evaluation"


def test_audit_records_theme_ingredient_provenance_and_metrics():
    record = build_audit_record(
        rewrite_id="theme-ingredients", source={},
        first_pass={"crazyReplacement1Title": "A luminous kettle using spore dispersal",
                    "crazyReplacement1Extract": "First pass."},
        result={"crazyReplacement1Title": "Final",
                "crazyReplacement1Extract": "A luminous kettle using spore dispersal remained."},
        environment={"NEWSMUNCHER_THEME_INGREDIENTS": "evaluation",
                     "NEWSMUNCHER_THEME_SPARKS": "evaluation"},
        theme_ingredient_context={
            "recent_events": 3,
            "selection_penalties": {"seed:mycelium": 4.5},
            "selection_metrics": {"selected": 2, "rejected": {"word_count": 1}},
            "theme_sparks_enabled": True,
            "prompt_placement": "adjacent_before_source",
            "selected": [{"text": "luminous kettle using spore dispersal",
                          "domain_ids": ["mycology", "optics"],
                          "seed_ids": ["mycelium", "refraction"],
                          "construction_id": "property_base_process",
                          "cross_domain": True,
                          "provenance": "curated local catalogue"}],
        },
    )
    context = record["theme_ingredients"]
    assert context["recent_events"] == 3
    assert context["selection_penalties"]["seed:mycelium"] == 4.5
    assert context["selected"][0]["cross_domain"] is True
    assert context["selection_metrics"]["selected"] == 2
    assert context["theme_sparks_enabled"] is True
    assert context["prompt_placement"] == "adjacent_before_source"
    assert context["found_exactly_in_first_pass"][0]["construction_id"] == \
        "property_base_process"
    assert context["found_exactly_in_final"][0]["text"] == \
        "luminous kettle using spore dispersal"
    assert record["feature_flags"]["NEWSMUNCHER_THEME_INGREDIENTS"] == "evaluation"
    assert record["feature_flags"]["NEWSMUNCHER_THEME_SPARKS"] == "evaluation"


def test_audit_records_exact_repetition_replacement_evidence():
    record = build_audit_record(
        rewrite_id="replacement", source={}, result={},
        environment={"NEWSMUNCHER_REPETITION_REPLACEMENT": "evaluation"},
        repetition_replacement_context={
            "enabled": True,
            "eligible_targets": [{"text": "gravy", "kind": "concept",
                                  "recent_exposure": 18,
                                  "first_pass_occurrences": 2}],
            "rejected_targets": [{"text": "working", "kind": "concept",
                                  "recent_exposure": 30,
                                  "first_pass_occurrences": 1,
                                  "reason": "narrative_or_ordinary_language"}],
            "recent_exposure_signals": {"word:gravy": 18},
            "alternatives": [{"text": "spore dispersal", "kind": "concept",
                              "recent_exposure": 0,
                              "construction_id": "property_base_process"}],
            "exact_target_changes": [{"text": "gravy", "first_pass_occurrences": 2,
                                      "final_occurrences": 0, "exactly_removed": True}],
            "exact_alternative_additions": [
                {"text": "spore dispersal", "first_pass_occurrences": 0,
                 "final_occurrences": 1, "exactly_added": True}],
            "new_recently_overused_terms": [], "maximum_substitutions": 2,
            "copy_edit_fell_back": False,
        })
    context = record["repetition_replacement"]
    assert context["eligible_targets"][0]["text"] == "gravy"
    assert context["rejected_targets"][0]["reason"] == \
        "narrative_or_ordinary_language"
    assert context["exact_target_changes"][0]["exactly_removed"] is True
    assert context["exact_alternative_additions"][0]["exactly_added"] is True
    assert record["feature_flags"]["NEWSMUNCHER_REPETITION_REPLACEMENT"] == "evaluation"


def test_audit_records_phrase_overlap_provenance_and_unmatched_removal():
    record = build_audit_record(
        rewrite_id="phrase-replacement", source={}, result={},
        environment={"NEWSMUNCHER_PHRASE_REPLACEMENT": "evaluation"},
        repetition_replacement_context={
            "enabled": True, "phrase_replacement_enabled": True,
            "eligible_targets": [{"text": "trouser press", "kind": "concept",
                                  "role": "animals", "recent_exposure": 75,
                                  "first_pass_occurrences": 1,
                                  "provenance": "concept-v3",
                                  "ingredient_phrase": "shed-inflating trouser press"}],
            "overlap_exclusions": [{"text": "press",
                                    "reason": "component_of_selected_phrase",
                                    "overlapping_target": "trouser press",
                                    "recent_exposure": 75}],
            "alternatives": [{"text": "megaphone", "kind": "concept",
                              "role": "animals", "recent_exposure": 0,
                              "source_phrase": "megaphone in counterweight balance",
                              "domain_ids": ["bridge-engineering"],
                              "seed_kinds": ["relationship", "entity"],
                              "role_compatible": True, "length_distance": 1}],
            "exact_target_changes": [{"text": "trouser press",
                                      "first_pass_occurrences": 1,
                                      "final_occurrences": 0, "exactly_removed": True}],
            "exact_alternative_additions": [{"text": "megaphone",
                                              "first_pass_occurrences": 0,
                                              "final_occurrences": 0,
                                              "exactly_added": False}],
            "targets_removed_without_supplied_alternative": ["trouser press"],
            "inventive_fallback": False, "fallback_domain_cues": [],
        })
    context = record["repetition_replacement"]
    assert context["phrase_replacement_enabled"] is True
    assert context["eligible_targets"][0]["provenance"] == "concept-v3"
    assert context["overlap_exclusions"][0]["overlapping_target"] == "trouser press"
    assert context["offered_alternatives"][0]["domain_ids"] == ["bridge-engineering"]
    assert context["targets_removed_without_supplied_alternative"] == ["trouser press"]
    assert record["feature_flags"]["NEWSMUNCHER_PHRASE_REPLACEMENT"] == "evaluation"


def test_audit_records_bounded_radical_controlling_premise_diagnostics():
    record = build_audit_record(
        rewrite_id="radical-premise", source={}, result={},
        radical_context={
            "controlling_premise_enabled": True,
            "controlling_premise_id": "codex-session-2026-10-18:premise:017",
            "mechanism_family": "mistaken_identity",
            "sparks": [f"spark-{index}" for index in range(9)],
        })
    diagnostic = record["radical_experiment"]
    assert diagnostic == {
        "controlling_premise_enabled": True,
        "controlling_premise_id": "codex-session-2026-10-18:premise:017",
        "mechanism_family": "mistaken_identity",
        "sparks": [f"spark-{index}" for index in range(6)],
    }


def test_duplicate_and_concurrent_rewrite_ids_are_written_once(tmp_path):
    path = tmp_path / "audit.jsonl"
    logger = ComedyAuditLogger(ComedyAuditConfig(True, path))
    with ThreadPoolExecutor(max_workers=8) as pool:
        outcomes = list(pool.map(lambda _: logger.append(sample_record("same-id")), range(24)))
    assert sum(outcomes) == 1
    assert [record["rewrite_id"] for record in load_records(path)] == ["same-id"]


def test_concurrent_distinct_records_remain_valid_json_lines(tmp_path):
    path = tmp_path / "audit.jsonl"
    logger = ComedyAuditLogger(ComedyAuditConfig(True, path))
    with ThreadPoolExecutor(max_workers=8) as pool:
        assert all(pool.map(lambda number: logger.append(sample_record(f"id-{number}")), range(30)))
    assert {record["rewrite_id"] for record in load_records(path)} == {
        f"id-{number}" for number in range(30)
    }


def test_fixed_schema_does_not_leak_environment_secrets(tmp_path):
    secrets = {
        "OPENAI_API_KEY": "sk-secret-value", "MONGODB_URI": "mongodb://secret",
        "COOKIE": "session-secret", "NEWSMUNCHER_COMEDY_AUDIT_LOG": "on",
    }
    path = tmp_path / "audit.jsonl"
    ComedyAuditLogger(ComedyAuditConfig(True, path)).append(sample_record(environment=secrets))
    raw = path.read_text(encoding="utf-8")
    assert "sk-secret-value" not in raw and "mongodb://secret" not in raw
    assert "session-secret" not in raw and "OPENAI_API_KEY" not in raw


def test_markdown_and_csv_exports_preserve_complete_articles_and_provenance(tmp_path):
    source = tmp_path / "audit.jsonl"
    logger = ComedyAuditLogger(ComedyAuditConfig(True, source))
    logger.append(sample_record("one")); logger.append(sample_record("two"))
    markdown = tmp_path / "report.md"; spreadsheet = tmp_path / "report.csv"
    assert export(source, markdown) == 2
    text = markdown.read_text(encoding="utf-8")
    assert "Total MUNGEs: 2" in text and "Original — text." in text
    assert "Sir Gravy met Moon Badger and a wonky milk float." in text
    assert '"generated_concepts"' in text
    assert export(source, spreadsheet, "csv") == 2
    with spreadsheet.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["final_article"] == "Sir Gravy met Moon Badger and a wonky milk float."
    assert json.loads(rows[0]["ingredients"])["offered"]["generated_names"]
