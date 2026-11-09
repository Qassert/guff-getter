"""Phase 4A prototype remains deterministic and disconnected from live code."""
from scripts.diagnostics.evaluate_vocabulary_expansion import run


def test_phase4a_diagnostic_is_deterministic_and_expands_every_catalogue():
    first = run(rewrites=10)
    second = run(rewrites=10)
    assert first["catalogue_counts"] == second["catalogue_counts"]
    assert first["comparison"] == second["comparison"]
    assert len(first["examples"]) == 50
    assert first["database_operations"] == 0
    assert all(values["prototype"] >= values["current"]
               for values in first["catalogue_counts"].values())
