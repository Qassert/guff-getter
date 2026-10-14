import json

import pytest

from newsmuncher.services.comedy_variants import ComedyVariantConfig, build_variant
from scripts.diagnostics.export_comedy_comparison import export


def concepts():
    values = []
    for bank in ("nouns", "animals"):
        for index in range(10):
            values.append({"phrase": f"{bank} premise {index}", "target_bank": bank,
                           "comic_mechanism": f"mechanism-{index % 6}",
                           "semantic_theme": f"theme-{index % 5}", "score": 7.0})
    return values


def test_config_defaults_to_unchanged_a_and_rejects_unknown(monkeypatch):
    monkeypatch.delenv("NEWSMUNCHER_COMEDY_VARIANT", raising=False)
    assert ComedyVariantConfig.from_environment().label == "A"
    monkeypatch.setenv("NEWSMUNCHER_COMEDY_VARIANT", "d")
    assert ComedyVariantConfig.from_environment().label == "D"
    monkeypatch.setenv("NEWSMUNCHER_COMEDY_VARIANT", "surprise")
    with pytest.raises(ValueError):
        ComedyVariantConfig.from_environment()


def test_a_is_exact_baseline_and_variants_have_declared_counts():
    offered = concepts()
    baseline = build_variant("A", offered, "same")
    assert baseline["prompt"] == offered and baseline["generated"] == offered
    assert baseline["raw"] == [] and baseline["guidance"] == ""
    expected = {"B": (10, 10, 20), "C": (10, 0, 10), "D": (6, 10, 16)}
    for label, counts in expected.items():
        plan = build_variant(label, offered, "same")
        assert (len(plan["generated"]), len(plan["raw"]), len(plan["prompt"])) == counts
        assert {item["target_bank"] for item in plan["prompt"]} == {"nouns", "animals"}


def test_hybrid_is_deterministic_varied_and_does_not_mislabel_mixed_csv_as_species():
    first = build_variant("B", concepts(), "stable")
    second = build_variant("B", concepts(), "stable")
    assert first == second
    assert len({item["comic_mechanism"] for item in first["generated"]}) >= 5
    assert all("animal_species" not in item for item in first["raw"])
    mixed = [item for item in first["raw"]
             if item.get("source_file") == "animalsAndObjects.csv"]
    assert mixed and all(item["family"] == "legacy_mixed_identity" for item in mixed)
    assert all(item.get("source") and item.get("provenance") or item.get("source_id")
               for item in first["raw"])


def test_blind_export_preserves_complete_text_and_separates_key(tmp_path):
    source = tmp_path / "audit.jsonl"
    records = [{"rewrite_id": label, "comparison_variant": label,
                "source": {"headline": "Same source", "article_text": "Complete original."},
                "final": {"headline": f"Heading {label}",
                          "article_text": f"Complete rewrite {label}."}}
               for label in "ABCD"]
    source.write_text("\n".join(json.dumps(x) for x in records) + "\n")
    report, key = tmp_path / "blind.md", tmp_path / "key.csv"
    assert export(source, report, key) == 4
    text = report.read_text()
    assert "Complete original." in text and "Complete rewrite A." in text
    assert "variant" not in text.casefold()
    assert text.count("\n## Article 1\n") == 1 and text.count("### Article 1 — Version") == 4
    assert "variant" in key.read_text() and all(f",{x}," in key.read_text() for x in "ABCD")
