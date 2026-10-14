from datetime import datetime, timedelta, timezone

import pytest

from newsmuncher.services.semantic_memory import (
    descriptor_premise_family, descriptor_subject_anchor, family_record,
    name_sound_family, recency_penalty, semantic_memory_enabled,
)


def test_feature_flag_defaults_off_and_requires_explicit_evaluation(monkeypatch):
    monkeypatch.delenv("NEWSMUNCHER_COMEDY_SEMANTIC_MEMORY", raising=False)
    assert not semantic_memory_enabled()
    monkeypatch.setenv("NEWSMUNCHER_COMEDY_SEMANTIC_MEMORY", "evaluation")
    assert semantic_memory_enabled()
    monkeypatch.setenv("NEWSMUNCHER_COMEDY_SEMANTIC_MEMORY", "yes")
    with pytest.raises(ValueError):
        semantic_memory_enabled()


def test_family_keys_collapse_wording_and_name_punctuation_variants():
    assert family_record("descriptor", "secret history") == family_record(
        "descriptor", "Secret-History"
    )
    assert name_sound_family("Wibble-bottom") == name_sound_family("Wibblebottom")
    assert descriptor_subject_anchor("competitive queueing") == "queueing"
    assert descriptor_subject_anchor("professional queueing") == "queueing"
    assert descriptor_premise_family({
        "semantic_theme": "secret_history", "subject": "competitive queueing",
    }) == "secret_history:queueing"


def test_recency_penalty_is_soft_bounded_and_decays():
    now = datetime(2026, 10, 11, tzinfo=timezone.utc)
    recent = {"last_used_at": now, "use_count": 100}
    old = {"last_used_at": now - timedelta(days=31), "use_count": 100}
    assert recency_penalty(recent, now) == 2.0
    assert recency_penalty(old, now) == 0.0
