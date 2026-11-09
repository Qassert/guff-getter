from scripts.diagnostics.evaluate_thematic_ingredients_phase4p import evaluate


def test_four_way_provider_free_comparison_preserves_baseline_and_broadens_space():
    result = evaluate(20, "phase4p-test")
    baseline, phase4n = result["baseline"], result["phase4n"]
    phase4p, combined = result["phase4p"], result["combined"]
    assert baseline["unique_ingredients"] == phase4n["unique_ingredients"]
    assert baseline["unique_vocabulary"] == phase4n["unique_vocabulary"]
    assert phase4p["conceptual_domains_represented"] >= 25
    assert phase4p["cross_domain_ingredients"] > 0
    assert set(phase4p["seed_kind_distribution"]) == {
        "entity", "process", "property", "relationship"}
    assert phase4p["category_distribution"] == baseline["category_distribution"]
    assert phase4p["unique_vocabulary"] > baseline["unique_vocabulary"]
    assert phase4p["stored_ingredient_events"] == 20
    assert combined["unique_ingredients"] == phase4p["unique_ingredients"]
