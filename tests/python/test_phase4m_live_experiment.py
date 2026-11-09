import json

from scripts.diagnostics.run_comedy_phase4m_live_experiment import (
    GROUPS, _experiment_sources, _schedule, execute, objective_metrics,
)


def test_schedule_has_36_balanced_counterordered_generations():
    sources = _experiment_sources()
    schedule = _schedule(sources)
    assert len(schedule) == 36
    assert all(sum(group == wanted for group, *_ in schedule) == 18 for wanted in GROUPS)
    for index in range(0, len(schedule), 2):
        assert {schedule[index][0], schedule[index + 1][0]} == set(GROUPS)
        assert schedule[index][1:] == schedule[index + 1][1:]
    assert schedule[0][0] != schedule[2][0]


def test_provider_free_dry_run_builds_complete_blind_artifacts(tmp_path):
    run_dir = tmp_path / "phase4m-dry"
    manifest = execute(run_dir, dry_run=True)
    assert manifest["provider_calls_planned"] == 0
    assert manifest["validation"]["successful_outputs"] == 36
    assert manifest["validation"]["errors"] == 0
    assert manifest["validation"]["group_counts"] == {"off": 18, "evaluation": 18}
    assert manifest["validation"]["lexical_documents"] == {"off": 0, "evaluation": 1}
    assert len((run_dir / "combined.jsonl").read_text().splitlines()) == 36
    assert (run_dir / "blind_comparison.md").read_text().count("### Source ") == 36
    assert len((run_dir / "answer_key.csv").read_text().splitlines()) == 37
    measurements = json.loads((run_dir / "vocabulary_measurements.json").read_text())
    assert set(measurements) == set(GROUPS)


def test_objective_metrics_distinguish_first_pass_copy_edit_and_source_words():
    records = []
    for group in GROUPS:
        records.append({
            "experiment_group": group,
            "source": {"headline": "Harbour survey", "article_text": "Workers counted boats."},
            "first_pass": {"headline": "Gravy telescope", "article_text": "Custard marched."},
            "final": {"headline": "Gravy telescope", "article_text": "Custard marmalade marched."},
            "ingredients": {"offered": {
                "generated_concepts": [{"phrase": "gravy telescope", "semantic_theme": "absurd"}],
                "generated_descriptors": [], "generated_names": [],
            }},
        })
    metrics = objective_metrics(records)
    assert metrics["evaluation"]["model_introduced_unique_words"] >= 2
    assert metrics["evaluation"]["copy_edit_added_unique_words"] == 1
    assert metrics["evaluation"]["source_required_unique_words_in_final"] == 0
    assert metrics["evaluation"]["watched_article_counts"] == {
        "gravy": 1, "custard": 1, "marmalade": 1,
    }
