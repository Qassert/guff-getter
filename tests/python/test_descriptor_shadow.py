from datetime import datetime, timedelta, timezone
from pathlib import Path

from newsmuncher.services.comedy_descriptors import normalised
from newsmuncher.services.descriptor_shadow import (
    InMemoryDescriptorRegistry, build_shadow_slate, descriptor_slate, slate_metrics,
)


def test_strategies_preserve_ten_slots_and_leave_live_prompt_untouched():
    a, b, c = (build_shadow_slate("slots", key) for key in "ABC")
    assert [(len(x.generated), len(x.legacy), len(x.prompt_values)) for x in (a, b, c)] == [
        (10, 0, 10), (7, 3, 10), (6, 4, 10),
    ]
    assert "SHADOW DESCRIPTOR PREVIEW (NOT ACTIVE)" in a.prompt_preview
    assert "SHADOW DESCRIPTOR PREVIEW" not in Path("newsmuncher/resources/prompts/rewrite.txt").read_text()


def test_full_replacement_is_deterministic_balanced_and_subject_diverse():
    first = build_shadow_slate("stable", "A")
    assert first == build_shadow_slate("stable", "A")
    metrics = slate_metrics(first)
    assert metrics["categories"] == {"cheeky_british": 7, "broader_absurdity": 3}
    assert metrics["intensities"] == {1: 3, 2: 5, 3: 2}
    assert metrics["repeated_subjects"] == 0
    assert len(metrics["roles"]) >= 5 and len(metrics["mechanisms"]) >= 7
    assert metrics["short_descriptors"] >= 4


def test_prompt_preview_preserves_role_and_insertion_guidance():
    slate = build_shadow_slate("grammar", "A")
    for item in slate.generated:
        assert item.phrase in slate.prompt_preview
        assert f"role: {item.grammatical_role}" in slate.prompt_preview
        assert item.insertion_rule in slate.prompt_preview
    assert "use roughly two to four" in slate.prompt_preview


def test_strategy_cost_and_legacy_compatibility():
    a, b, c = (build_shadow_slate("tokens", key) for key in "ABC")
    assert a.token_difference > b.token_difference > c.token_difference > 0
    assert b.legacy and c.legacy
    assert all(value for value in (*b.legacy, *c.legacy))


def test_retry_is_stable_and_concurrent_offers_do_not_overlap():
    registry = InMemoryDescriptorRegistry()
    first = registry.offer("rewrite-a")
    assert registry.offer("rewrite-a") == first
    second = registry.offer("rewrite-b")
    assert not ({normalised(x.phrase) for x in first} & {normalised(x.phrase) for x in second})
    assert not ({normalised(x.subject) for x in first} & {normalised(x.subject) for x in second})


def test_failure_release_expiry_and_exact_use_cooldown():
    clock = [datetime(2026, 1, 1, tzinfo=timezone.utc)]
    registry = InMemoryDescriptorRegistry(now=lambda: clock[0])
    failed = registry.offer("failed")
    registry.release("failed")
    assert all(record.get("offered_by") != "failed" for record in registry.records.values())
    offered = registry.offer("accepted"); used = offered[0]
    assert registry.accept("accepted", "Title", f"The mayor is {used.phrase}.") == [used.phrase]
    assert registry.records[normalised(used.phrase)]["use_count"] == 1
    clock[0] += timedelta(days=31)
    assert registry.offer("after-cooldown")


def test_inflected_or_paraphrased_use_is_not_falsely_cooled_down():
    registry = InMemoryDescriptorRegistry()
    offered = registry.offer("paraphrase"); item = offered[0]
    assert registry.accept("paraphrase", "Title", "The wording was substantially paraphrased.") == []
    assert "last_used_at" not in registry.records[normalised(item.phrase)]


def test_saturated_cooldown_uses_rewrite_specific_expanded_space():
    registry = InMemoryDescriptorRegistry()
    for index in range(8):
        key = f"rewrite-{index}"
        offered = registry.offer(key)
        registry.accept(key, "Title", " ".join(item.phrase for item in offered))
    ninth = registry.offer("rewrite-8")
    assert len(ninth) == 10


def test_invalid_strategy_and_no_live_or_provider_dependency():
    import pytest
    with pytest.raises(ValueError):
        build_shadow_slate("bad", "D")
    live = Path("newsmuncher/api/previews.py").read_text() + Path("newsmuncher/utils/clean_data.py").read_text()
    assert "descriptor_shadow" not in live
    module = Path("newsmuncher/services/descriptor_shadow.py").read_text()
    assert "OpenAI(" not in module and "pymongo" not in module
