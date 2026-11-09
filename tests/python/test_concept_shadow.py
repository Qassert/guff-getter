from datetime import datetime, timedelta, timezone

from newsmuncher.services.concept_shadow import (
    InMemoryConceptRegistry, build_shadow_slate, concept_slate, slate_metrics,
)
from newsmuncher.services.comedy_concepts import normalised


def test_three_strategies_preserve_slots_and_do_not_change_live_code():
    a = build_shadow_slate("same", "A")
    b = build_shadow_slate("same", "B")
    c = build_shadow_slate("same", "C")
    assert (len(a.concepts), len(b.concepts), len(c.concepts)) == (10, 20, 6)
    assert all(len(slate.nouns) == len(slate.animals) == 10 for slate in (a, b, c))
    assert "SHADOW CONCEPT PREVIEW (NOT ACTIVE)" in c.prompt_preview


def test_shadow_slates_are_reproducible_weighted_and_base_diverse():
    first = build_shadow_slate("stable", "C")
    second = build_shadow_slate("stable", "C")
    assert first == second
    assert slate_metrics(first)["repeated_bases"] == 0
    assert sum(slate_metrics(first)["categories"].values()) == 6


def test_prompt_estimate_shows_elaborate_strategies_cost_more():
    a = build_shadow_slate("tokens", "A")
    b = build_shadow_slate("tokens", "B")
    c = build_shadow_slate("tokens", "C")
    assert b.token_difference > c.token_difference
    assert a.token_difference > 0 and c.token_difference > 0


def test_retry_returns_same_lease_and_concurrent_sessions_do_not_overlap():
    registry = InMemoryConceptRegistry()
    first = registry.offer("session-a")
    assert registry.offer("session-a") == first
    second = registry.offer("session-b")
    assert not ({item.phrase for item in first} & {item.phrase for item in second})
    assert not ({item.base for item in first} & {item.base for item in second})


def test_failed_rewrite_release_and_exact_accepted_use_cooldown():
    clock = [datetime(2026, 1, 1, tzinfo=timezone.utc)]
    registry = InMemoryConceptRegistry(now=lambda: clock[0])
    failed = registry.offer("failed")
    registry.release("failed")
    assert "offered_by" not in registry.records[next(iter(registry.records))]
    offered = registry.offer("accepted")
    used = offered[0]
    assert registry.accept("accepted", "Title", f"A story about {used.phrase}.") == [used.phrase]
    assert registry.records[normalised(used.phrase)]["use_count"] == 1
    clock[0] += timedelta(days=31)
    assert registry.offer("after-cooldown")


def test_concept_shadow_is_not_imported_by_live_prompt_path():
    from pathlib import Path
    live = Path("newsmuncher/api/previews.py").read_text()
    cleaner = Path("newsmuncher/utils/clean_data.py").read_text()
    assert "concept_shadow" not in live
    assert "concept_shadow" not in cleaner
