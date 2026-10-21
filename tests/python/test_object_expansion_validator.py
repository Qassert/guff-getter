import csv
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest

from scripts.validate_object_expansion import (
    EXPECTED_COLUMNS,
    ValidationFailure,
    normalise,
    read_csv,
    render_text,
    validate,
)


def write_csv(path, rows, headers=EXPECTED_COLUMNS):
    with path.open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def candidate(word, **overrides):
    row = {
        "category": "object",
        "word": word,
        "domain": "industrial_machinery",
        "form": "hand_tool",
        "source_file": "curated_test",
        "review_status": "proposed",
    }
    row.update(overrides)
    return row


def live_file(tmp_path, *rows):
    path = tmp_path / "live.csv"
    write_csv(path, rows, ["category", "word"])
    return path


def kinds(report, word):
    return {(item["kind"], item["reason"]) for item in report["findings"] if item["word"] == word}


def test_batch_01_is_now_fully_recognised_in_live_vocabulary():
    report = validate(
        Path("docs/object-expansion-batch-01.csv"),
        batch_dir=Path("docs"),
    )
    assert report["candidate_count"] == 250
    assert report["proposed_count"] == 234
    assert report["accepted_count"] == 0
    assert report["needs_review_count"] == 0
    assert report["rejected_count"] == 250
    assert set(report["counts_by_domain"].values()) == {50}
    assert report["ready_for_human_review"] is False


def test_batches_02_to_09_are_balanced_unique_and_fully_imported():
    all_rows = []
    totals = Counter()
    for number in range(2, 10):
        path = Path(f"docs/object-expansion-batch-{number:02d}.csv")
        rows = read_csv(path, expected_columns=EXPECTED_COLUMNS)
        assert len(rows) == 100
        domain_counts = Counter(row["domain"] for row in rows)
        assert len(domain_counts) == 4
        assert set(domain_counts.values()) == {25}
        assert {row["source_file"] for row in rows} == {f"curated_batch_{number:02d}"}
        assert {row["review_status"] for row in rows} <= {"proposed", "needs_review"}
        totals.update(row["review_status"] for row in rows)
        all_rows.extend(rows)

    assert len(all_rows) == 800
    assert totals == {"proposed": 759, "needs_review": 41}
    normalised = [normalise(row["word"]) for row in all_rows]
    compacted = [value.replace(" ", "") for value in normalised]
    assert len(set(normalised)) == len(normalised)
    assert len(set(compacted)) == len(compacted)

    with Path("newsmuncher/static/data/object-generator-vocabulary.csv").open(
            encoding="utf-8", newline="") as source:
        live = {(row["category"], normalise(row["word"])) for row in csv.DictReader(source)}
    imported = {(row["category"], normalise(row["word"])) for row in all_rows}
    assert imported <= live

    for number in range(2, 10):
        report = validate(
            Path(f"docs/object-expansion-batch-{number:02d}.csv"),
            batch_dir=Path("docs"),
        )
        assert report["rejected_count"] == 100
        assert report["accepted_count"] == 0
        assert report["ready_for_human_review"] is False


def test_batches_10_to_19_are_staged_balanced_and_cross_batch_unique():
    all_rows = []
    totals = Counter()
    for number in range(10, 20):
        path = Path(f"docs/object-expansion-batch-{number:02d}.csv")
        rows = read_csv(path, expected_columns=EXPECTED_COLUMNS)
        assert len(rows) == 100
        domain_counts = Counter(row["domain"] for row in rows)
        assert len(domain_counts) == 4
        assert set(domain_counts.values()) == {25}
        assert {row["source_file"] for row in rows} == {f"curated_batch_{number:02d}"}
        assert {row["review_status"] for row in rows} <= {"proposed", "needs_review"}
        totals.update(row["review_status"] for row in rows)
        all_rows.extend(rows)

    assert len(all_rows) == 1000
    assert totals == {"proposed": 951, "needs_review": 49}
    normalised = [normalise(row["word"]) for row in all_rows]
    compacted = [value.replace(" ", "") for value in normalised]
    assert len(set(normalised)) == len(normalised)
    assert len(set(compacted)) == len(compacted)

    with Path("newsmuncher/static/data/object-generator-vocabulary.csv").open(
            encoding="utf-8", newline="") as source:
        live = [(row["category"], normalise(row["word"])) for row in csv.DictReader(source)]
    imported = [(row["category"], normalise(row["word"])) for row in all_rows]
    assert all(live.count(item) == 1 for item in imported)


def test_batches_20_to_29_are_pending_balanced_and_cross_batch_unique():
    all_rows = []
    totals = Counter()
    for number in range(20, 30):
        path = Path(f"docs/object-expansion-batch-{number:02d}.csv")
        rows = read_csv(path, expected_columns=EXPECTED_COLUMNS)
        assert len(rows) == 50
        domain_counts = Counter(row["domain"] for row in rows)
        assert len(domain_counts) == 5
        assert set(domain_counts.values()) == {10}
        assert {row["source_file"] for row in rows} == {f"curated_batch_{number:02d}"}
        assert {row["review_status"] for row in rows} <= {"proposed", "needs_review"}
        totals.update(row["review_status"] for row in rows)
        all_rows.extend(rows)

    assert len(all_rows) == 500
    assert totals == {"proposed": 471, "needs_review": 29}
    normalised = [normalise(row["word"]) for row in all_rows]
    compacted = [value.replace(" ", "") for value in normalised]
    assert len(set(normalised)) == len(normalised)
    assert len(set(compacted)) == len(compacted)

    with Path("newsmuncher/static/data/object-generator-vocabulary.csv").open(
            encoding="utf-8", newline="") as source:
        live = {(row["category"], normalise(row["word"])) for row in csv.DictReader(source)}
    assert not live.intersection(
        (row["category"], normalise(row["word"])) for row in all_rows)


def test_exact_case_whitespace_and_punctuation_duplicates_are_rejected(tmp_path):
    live = live_file(tmp_path, {"category": "device", "word": "Hydraulic Press"})
    path = tmp_path / "candidate.csv"
    write_csv(path, [candidate(" hydraulic--press ")])
    report = validate(path, live_path=live)
    assert ("reject", "exact/format duplicate") in kinds(report, "hydraulic--press")

    write_csv(path, [candidate("hydraulicpress")])
    report = validate(path, live_path=live)
    assert ("reject", "whitespace-format duplicate") in kinds(report, "hydraulicpress")


def test_unambiguous_singular_plural_variants_are_rejected(tmp_path):
    live = live_file(tmp_path, {"category": "object", "word": "hydraulic press"})
    path = tmp_path / "candidate.csv"
    write_csv(path, [candidate("hydraulic presses")])
    report = validate(path, live_path=live)
    assert ("reject", "singular/plural duplicate") in kinds(report, "hydraulic presses")


def test_spelling_variants_and_synonyms_are_review_warnings(tmp_path):
    live = live_file(
        tmp_path,
        {"category": "object", "word": "plow"},
        {"category": "device", "word": "power drill"},
    )
    path = tmp_path / "candidate.csv"
    write_csv(path, [
        candidate("plough", domain="agriculture_and_farming"),
        candidate("electric drill"),
    ])
    report = validate(path, live_path=live)
    assert ("review", "British/American spelling variant") in kinds(report, "plough")
    assert ("review", "likely synonym") in kinds(report, "electric drill")
    assert report["rejected_count"] == 0


def test_distinct_objects_sharing_a_common_noun_are_retained(tmp_path):
    live = live_file(tmp_path, {"category": "device", "word": "printing press"})
    path = tmp_path / "candidate.csv"
    write_csv(path, [candidate("hydraulic press")])
    report = validate(path, live_path=live)
    assert report["findings"] == []
    assert report["ready_for_human_review"] is True


def test_classic_overlap_is_advisory_not_blocking(tmp_path):
    live = live_file(tmp_path)
    classic = tmp_path / "animalsAndObjects.csv"
    classic.write_text("anvil,horse trough", encoding="utf-8")
    path = tmp_path / "candidate.csv"
    write_csv(path, [candidate("Anvil")])

    report = validate(path, live_path=live, classic_path=classic)

    assert ("review", "Classic vocabulary overlap") in kinds(report, "Anvil")
    assert report["rejected_count"] == 0
    assert report["accepted_count"] == 1
    assert report["ready_for_human_review"] is True


def test_duplicate_detection_crosses_live_categories_and_current_batch(tmp_path):
    live = live_file(tmp_path, {"category": "device", "word": "microscope"})
    path = tmp_path / "candidate.csv"
    write_csv(path, [
        candidate("MICROSCOPE"),
        candidate("anvil"),
        candidate("Anvil", category="device", form="powered_device"),
    ])
    report = validate(path, live_path=live)
    assert ("reject", "exact/format duplicate") in kinds(report, "MICROSCOPE")
    assert ("reject", "duplicate within batch") in kinds(report, "Anvil")


def test_near_duplicate_names_within_a_batch_are_reviewed(tmp_path):
    live = live_file(tmp_path)
    path = tmp_path / "candidate.csv"
    write_csv(path, [candidate("laboratory incubator"), candidate("laboratory incubator unit")])
    report = validate(path, live_path=live)
    assert ("review", "near-duplicate name") in kinds(report, "laboratory incubator unit")


def test_approved_batches_block_and_pending_batches_only_warn(tmp_path):
    live = live_file(tmp_path)
    batch_dir = tmp_path / "batches"
    batch_dir.mkdir()
    write_csv(batch_dir / "object-expansion-batch-00.csv", [candidate("anvil", review_status="approved")])
    write_csv(batch_dir / "object-expansion-batch-02.csv", [candidate("lathe")])
    current = batch_dir / "object-expansion-batch-01.csv"
    write_csv(current, [candidate("ANVIL"), candidate("Lathe")])
    report = validate(current, live_path=live, batch_dir=batch_dir)
    assert ("reject", "approved duplicate") in kinds(report, "ANVIL")
    assert ("review", "pending-batch overlap") in kinds(report, "Lathe")


def test_validator_rereads_live_vocabulary_on_every_run(tmp_path):
    live = live_file(tmp_path)
    path = tmp_path / "candidate.csv"
    write_csv(path, [candidate("anvil")])
    assert validate(path, live_path=live)["rejected_count"] == 0
    write_csv(live, [{"category": "device", "word": "anvil"}], ["category", "word"])
    assert validate(path, live_path=live)["rejected_count"] == 1


@pytest.mark.parametrize("field,value", [
    ("category", "animal"),
    ("domain", "miscellaneous"),
    ("form", "contraption"),
    ("review_status", "maybe"),
])
def test_invalid_metadata_is_reported(tmp_path, field, value):
    live = live_file(tmp_path)
    path = tmp_path / "candidate.csv"
    write_csv(path, [candidate("anvil", **{field: value})])
    report = validate(path, live_path=live)
    assert any(f"invalid {field}" in error for error in report["metadata_errors"])
    assert report["ready_for_human_review"] is False


def test_malformed_csv_rows_are_rejected(tmp_path):
    path = tmp_path / "candidate.csv"
    path.write_text(
        ",".join(EXPECTED_COLUMNS) + "\nobject,anvil,industrial_machinery\n",
        encoding="utf-8",
    )
    with pytest.raises(ValidationFailure, match="malformed CSV row"):
        read_csv(path, expected_columns=EXPECTED_COLUMNS)


def test_unicode_and_multiword_entries_are_preserved(tmp_path):
    live = live_file(tmp_path)
    path = tmp_path / "candidate.csv"
    write_csv(path, [candidate("Müller–style gauge")])
    report = validate(path, live_path=live)
    assert report["candidate_count"] == 1
    assert report["findings"] == []
    assert normalise("Müller–style gauge") == "müller style gauge"


def test_rendered_and_json_results_are_deterministic(tmp_path):
    live = live_file(tmp_path, {"category": "device", "word": "power drill"})
    path = tmp_path / "candidate.csv"
    write_csv(path, [candidate("electric drill"), candidate("anvil")])
    first = validate(path, live_path=live)
    second = validate(path, live_path=live)
    assert render_text(first) == render_text(second)
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)


def test_cli_reports_an_imported_batch_as_live_duplicates():
    completed = subprocess.run(
        [sys.executable, "scripts/validate_object_expansion.py",
         "docs/object-expansion-batch-01.csv"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 1, completed.stderr + completed.stdout
    assert "Candidates: 250" in completed.stdout
    assert "Automatically rejected: 250" in completed.stdout
    assert "Ready for human review: no" in completed.stdout
