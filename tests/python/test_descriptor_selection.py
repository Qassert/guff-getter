from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from test_name_selection import MemoryCollection
from newsmuncher.services.comedy_descriptors import (
    assemble_descriptor_slate, descriptor_candidate_pool, descriptor_slate, normalised,
)
from newsmuncher.services.descriptor_selection import (
    DESCRIPTOR_GUIDANCE, DescriptorRegistry, DescriptorSelectionConfig,
    DescriptorSelectionExhausted, prompt_descriptor,
)


def registry(collection=None, now=None, **config):
    return DescriptorRegistry(
        collection or MemoryCollection(), DescriptorSelectionConfig(**config),
        now=now or (lambda: datetime(2026, 10, 9, tzinfo=timezone.utc)),
    )


def test_default_and_legacy_configuration(monkeypatch):
    monkeypatch.delenv("NEWSMUNCHER_DESCRIPTOR_MODE", raising=False)
    monkeypatch.delenv("NEWSMUNCHER_EXPANDED_DESCRIPTORS", raising=False)
    assert DescriptorSelectionConfig.from_environment().mode == "generated"
    assert DescriptorSelectionConfig.from_environment().vocabulary_mode == "off"
    monkeypatch.setenv("NEWSMUNCHER_EXPANDED_DESCRIPTORS", "evaluation")
    assert DescriptorSelectionConfig.from_environment().vocabulary_mode == "evaluation"
    monkeypatch.setenv("NEWSMUNCHER_DESCRIPTOR_MODE", "legacy")
    assert DescriptorSelectionConfig.from_environment().mode == "legacy"
    monkeypatch.setenv("NEWSMUNCHER_DESCRIPTOR_MODE", "mixed")
    with pytest.raises(ValueError):
        DescriptorSelectionConfig.from_environment()


def test_offer_is_stable_ten_way_balanced_and_role_complete():
    service = registry(); first = service.offer("pet:rewrite")
    assert [x["phrase"] for x in service.offer("pet:rewrite")] == [x["phrase"] for x in first]
    assert len(first) == len({normalised(x["phrase"]) for x in first}) == 10
    assert Counter(x["category"] for x in first) == {"cheeky_british": 7, "broader_absurdity": 3}
    assert Counter(x["intensity"] for x in first) == {1: 3, 2: 5, 3: 2}
    assert len({x["grammatical_role"] for x in first}) == 6
    assert len({normalised(x["subject"]) for x in first}) == 10
    assert sum(x["word_count"] <= 8 for x in first) >= 4
    assert service.last_metrics["availability_reads"] == 1
    assert service.last_metrics["lease_writes"] == 30


def test_evaluation_registry_uses_phase4f_diversified_assembly(monkeypatch):
    import newsmuncher.services.descriptor_selection as module
    calls = []
    original = module.assemble_descriptor_slate
    def recording(*args, **kwargs):
        calls.append(kwargs.get("diversify", False))
        return original(*args, **kwargs)
    monkeypatch.setattr(module, "assemble_descriptor_slate", recording)
    registry(vocabulary_mode="evaluation").offer("pet:phase4f")
    assert calls and all(calls)


def test_cross_generator_theme_preference_reduces_avoidable_overlap():
    pool = descriptor_candidate_pool("cross-generator")
    ordinary = assemble_descriptor_slate(pool, "cross-choice")
    avoided = {"institutional_control", "medical_restriction"}
    balanced = assemble_descriptor_slate(pool, "cross-choice", avoid_themes=avoided)
    assert sum(item.semantic_theme in avoided for item in balanced) < sum(
        item.semantic_theme in avoided for item in ordinary
    )


def test_concurrent_sessions_have_disjoint_phrase_and_subject_leases():
    service = registry()
    with ThreadPoolExecutor(max_workers=2) as pool:
        first, second = list(pool.map(service.offer, ("pet:a", "pet:b")))
    assert not ({normalised(x["phrase"]) for x in first} & {normalised(x["phrase"]) for x in second})
    assert not ({normalised(x["subject"]) for x in first} & {normalised(x["subject"]) for x in second})


def test_partial_phrase_subject_acquisition_is_rolled_back(monkeypatch):
    collection = MemoryCollection(); service = registry(collection, candidate_slates=1)
    original = service._acquire
    monkeypatch.setattr(service, "_acquire", lambda record_id, *args, **kwargs:
                        False if record_id.startswith("subject:") else original(record_id, *args, **kwargs))
    with pytest.raises(DescriptorSelectionExhausted):
        service.offer("pet:partial")
    assert all(doc.get("offered_by") != "pet:partial" for doc in collection.docs.values())


def test_generator_exhaustion_is_typed_and_releases_partial_leases(monkeypatch):
    collection = MemoryCollection(); service = registry(collection)
    collection.docs["phrase:partial"] = {
        "_id": "phrase:partial", "offered_by": "pet:failed",
        "offer_until": datetime(2026, 10, 9, 1, tzinfo=timezone.utc),
    }
    monkeypatch.setattr(service, "candidate_pool", lambda key: (_ for _ in ()).throw(
        RuntimeError("bounded generator exhausted")
    ))
    with pytest.raises(DescriptorSelectionExhausted):
        service.offer("pet:failed")
    assert "offered_by" not in collection.docs["phrase:partial"]


def test_exact_use_cools_phrase_and_subject_and_releases_unused():
    collection = MemoryCollection(); service = registry(collection)
    offered = service.offer("pet:first"); item = offered[0]
    used = service.accept("pet:first", "rewrite", offered, "Title", f"It was {item['phrase']}!")
    assert used == [item["phrase"]]
    for key in ("phrase:" + normalised(item["phrase"]), "subject:" + normalised(item["subject"])):
        assert collection.docs[key]["use_count"] == 1
        assert collection.docs[key]["last_rewrite_id"] == "rewrite"
    assert all("offered_by" not in doc for doc in collection.docs.values())


def test_semantic_memory_records_paraphrased_subject_family_and_stays_soft():
    collection = MemoryCollection()
    service = registry(collection, vocabulary_mode="evaluation",
                       semantic_memory_mode="evaluation")
    offered = service.offer("semantic:first"); item = offered[0]
    service.accept("semantic:first", "rewrite", offered, "", item["subject"])
    family_docs = [doc for key, doc in collection.docs.items()
                   if key.startswith("semantic:descriptor:")]
    assert family_docs and family_docs[0]["last_rewrite_id"] == "rewrite"
    assert len(service.offer("semantic:second")) == 10


def test_semantic_memory_recognises_different_queueing_wording():
    collection = MemoryCollection()
    service = registry(collection, semantic_memory_mode="evaluation")
    offered = service.offer("semantic:queueing")
    item = {**offered[0], "subject": "competitive queueing",
            "semantic_theme": "secret_history",
            "premise_key": "secret_history:competitive queueing"}
    service.accept("semantic:queueing", "rewrite", [item], "",
                   "He was suspended from professional queueing.")
    record = collection.docs["semantic:descriptor-premise:secret-history-queueing"]
    assert record["use_count"] == 1


def test_case_and_outer_punctuation_match_but_paraphrase_does_not():
    service = registry(); offered = service.offer("pet:match"); item = offered[0]
    assert service._used(item, f"({item['phrase'].upper()}), yes")
    assert not service._used(item, "A vaguely similar but paraphrased description")


def test_descriptor_subject_memory_tracks_reliable_use_but_not_source_fact():
    collection = MemoryCollection(); service = registry(collection)
    offered = service.offer("pet:subject-memory")
    item = offered[0]
    service.accept("pet:subject-memory", "rewrite", offered, "title",
                   f"The witness kept {item['subject']} throughout.")
    assert collection.docs["subject:" + normalised(item["subject"])]["use_count"] == 1
    assert collection.docs["premise:" + normalised(item["premise_key"])]["use_count"] == 1

    second = service.offer("pet:subject-source")
    second_item = second[0]
    source = f"The source already says {second_item['subject']}."
    service.accept("pet:subject-source", "rewrite-2", second, "title", source, source)
    assert collection.docs["subject:" + normalised(second_item["subject"])].get(
        "last_rewrite_id"
    ) != "rewrite-2"


def test_expired_lease_and_cooldown_expiry_allow_reuse(monkeypatch):
    collection = MemoryCollection(); clock = [datetime(2026, 10, 9, tzinfo=timezone.utc)]
    service = registry(collection, now=lambda: clock[0], candidate_slates=1)
    fixed = descriptor_slate("fixed")
    monkeypatch.setattr(service, "candidate_pool", lambda key: fixed)
    first = service.offer("first")
    with pytest.raises(DescriptorSelectionExhausted): service.offer("second")
    clock[0] += timedelta(minutes=16)
    assert len(service.offer("second")) == 10
    service.accept("second", "rewrite", first, first[0]["phrase"], "")
    with pytest.raises(DescriptorSelectionExhausted): service.offer("third")
    clock[0] += timedelta(days=31)
    assert len(service.offer("third")) == 10


def test_five_consecutive_rewrites_and_fresh_attempt_ids_do_not_exhaust():
    collection = MemoryCollection(); slates = []
    for number in range(6):
        service = registry(collection)
        offered = service.offer(f"same-source:rewrite-{number}")
        slates.append({x["phrase"] for x in offered})
        service.accept(f"same-source:rewrite-{number}", f"rewrite-{number}", offered,
                       offered[0]["phrase"], offered[1]["phrase"])
    assert len(slates) == 6 and all(len(slate) == 10 for slate in slates)
    assert len({next(iter(slate)) for slate in slates}) > 1


def test_saturated_subject_cooldown_relaxes_but_phrase_cooldown_remains(monkeypatch):
    collection = MemoryCollection(); service = registry(collection)
    pool = service.candidate_pool("fixed-subjects")
    monkeypatch.setattr(service, "candidate_pool", lambda key: pool)
    for item in pool:
        key = "subject:" + normalised(item.subject)
        collection.docs[key] = {"_id": key, "last_used_at": service.now()}
    offered = service.offer("pet:subject-relaxed")
    assert len(offered) == 10
    assert len({item["phrase"] for item in offered}) == 10


def test_mongo_naive_utc_dates_are_safe_in_availability_prefilter():
    collection = MemoryCollection()
    now = datetime(2026, 10, 9, tzinfo=timezone.utc)
    service = registry(collection, now=lambda: now)
    pool = service.candidate_pool("naive-dates")
    cooled = pool[0]
    leased = pool[1]
    collection.docs["subject:" + normalised(cooled.subject)] = {
        "_id": "subject:" + normalised(cooled.subject),
        "last_used_at": datetime(2026, 10, 8),
    }
    collection.docs["subject:" + normalised(leased.subject)] = {
        "_id": "subject:" + normalised(leased.subject),
        "offered_by": "another-rewrite",
        "offer_until": datetime(2026, 10, 9, 0, 15),
    }

    offered = service.offer("naive-dates")

    assert len(offered) == 10
    assert cooled.subject not in {item["subject"] for item in offered}
    assert leased.subject not in {item["subject"] for item in offered}


def test_generated_prompt_has_ten_role_tags_and_no_legacy_adverb_claims(monkeypatch):
    from newsmuncher.utils import clean_data
    banks = {key: [f"{key}{i}" for i in range(10)] for key in
             ("nouns", "animals", "adverbs", "slang", "places", "names")}
    monkeypatch.setattr(clean_data, "load_random_words", lambda count, excluded=():
                        {key: ([] if key in excluded else list(values)) for key, values in banks.items()})
    monkeypatch.setattr(clean_data, "filter_word_banks", lambda prep, words: words)
    monkeypatch.setattr(clean_data, "preprocess_source", lambda entry: {"masked": entry})
    captured = {}
    monkeypatch.setattr(clean_data, "replacement_guidance", lambda prep, words:
                        captured.setdefault("assignment_adverbs", list(words["adverbs"])) or "guidance")
    slate = [x.__dict__ for x in descriptor_slate("prompt")]
    overrides = [prompt_descriptor(x) for x in slate]
    template = "|".join("{" + f"{bank}_words{i}" + "}" for bank in
                        ("noun", "adverb", "animal", "slang", "place", "name") for i in range(1, 4))
    result = clean_data.prepare_prompt(
        {"title":"t","description":"d","extract":"e"}, 10, template,
        descriptor_overrides=overrides, descriptor_guidance=DESCRIPTOR_GUIDANCE,
    )
    assert result["contenders"]["adverbs"] == []
    assert captured["assignment_adverbs"] == []
    assert all(value in result["full_prompt"] for value in overrides)
    assert all(f"[{tag}]" in result["full_prompt"] for tag in ("PRE","PRED","POST","ADV","BEHAV","CLAUSE"))
    assert "roughly two to four" in result["full_prompt"]


def test_legacy_prompt_retains_csv_adverb_contenders(monkeypatch):
    from newsmuncher.utils import clean_data
    banks = {key: [f"{key}{i}" for i in range(10)] for key in
             ("nouns", "animals", "adverbs", "slang", "places", "names")}
    monkeypatch.setattr(clean_data, "load_random_words", lambda count, excluded=():
                        {key:list(values) for key,values in banks.items()})
    monkeypatch.setattr(clean_data, "filter_word_banks", lambda prep, words: words)
    monkeypatch.setattr(clean_data, "preprocess_source", lambda entry: {"masked": entry})
    monkeypatch.setattr(clean_data, "replacement_guidance", lambda prep, words: "")
    template = "|".join("{" + f"{bank}_words{i}" + "}" for bank in
                        ("noun", "adverb", "animal", "slang", "place", "name") for i in range(1, 4))
    result = clean_data.prepare_prompt({"title":"t","description":"d","extract":"e"}, 10, template)
    assert result["contenders"]["adverbs"] == banks["adverbs"]


def test_route_exhaustion_is_409_before_provider_and_releases_other_offers():
    from test_image_generation import ImageTests
    fixture = ImageTests(); fixture.setUp()
    try:
        routes = fixture.previews()
        names = SimpleNamespace(release=MagicMock())
        concepts = SimpleNamespace(offer=MagicMock(return_value=[]), release=MagicMock())
        descriptors = SimpleNamespace(
            offer=MagicMock(side_effect=DescriptorSelectionExhausted("Descriptors busy; try again.")),
            release=MagicMock(),
        )
        routes.NameSelectionConfig.from_environment.return_value = SimpleNamespace(mode="legacy", slate_size=10)
        routes.ConceptSelectionConfig.from_environment.return_value = SimpleNamespace(mode="legacy")
        routes.DescriptorSelectionConfig.from_environment.return_value = SimpleNamespace(mode="generated")
        routes.DescriptorRegistry = MagicMock(return_value=descriptors)
        routes.generated_descriptor_collection = MagicMock(return_value=object())
        with pytest.raises(routes.HTTPException) as error:
            routes.shizzalise_data(routes.ShizzRequest(title="s",description="",extract="s"), "alice", "alice")
        assert error.value.status_code == 409 and "Descriptors busy" in error.value.detail
        routes.send_prompt.assert_not_called(); descriptors.release.assert_called()
    finally:
        fixture.tearDown(); fixture.doCleanups()


def test_route_uses_rewrite_uuid_accepts_after_copy_edit_and_adds_no_provider_call():
    from test_image_generation import ImageTests
    fixture = ImageTests(); fixture.setUp()
    try:
        routes = fixture.previews(); items = [x.__dict__ for x in descriptor_slate("route")]
        tracker = SimpleNamespace(offer=MagicMock(return_value=items), accept=MagicMock(return_value=[]),
                                  release=MagicMock())
        routes.DescriptorSelectionConfig.from_environment.return_value = SimpleNamespace(mode="generated")
        routes.DescriptorRegistry = MagicMock(return_value=tracker)
        routes.generated_descriptor_collection = MagicMock(return_value=object())
        routes.prepare_prompt.return_value = {"full_prompt":"prompt", "preprocessing":None, "contenders":{}}
        routes.send_prompt.return_value = {"title":"pass one", "extract":"pass one"}
        routes.format_shizzalise_result.return_value = dict(fixture.result)
        routes.copy_edit_pass.return_value = dict(fixture.result)
        request = routes.ShizzRequest(title="s", description="", extract="s", draft_session="same")
        routes.shizzalise_data(request, "alice", "alice")
        routes.shizzalise_data(request, "alice", "alice")
        keys = [call.args[0] for call in tracker.offer.call_args_list]
        assert len(keys) == 2 and keys[0] != keys[1] and all(key.startswith("alice:") for key in keys)
        assert routes.send_prompt.call_count == 2 and routes.copy_edit_pass.call_count == 2
        assert tracker.accept.call_count == 2
        kwargs = routes.prepare_prompt.call_args.kwargs
        assert len(kwargs["descriptor_overrides"]) == 10 and kwargs["descriptor_guidance"] == DESCRIPTOR_GUIDANCE
    finally:
        fixture.tearDown(); fixture.doCleanups()
