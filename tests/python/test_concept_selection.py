from datetime import datetime, timedelta, timezone
from collections import Counter
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from test_name_selection import MemoryCollection
from newsmuncher.services.concept_selection import (
    CONCEPT_GUIDANCE, ConceptRegistry, ConceptSelectionConfig,
    ConceptSelectionExhausted, PHYSICAL_CATEGORIES,
)
from newsmuncher.services.comedy_concepts import normalised
from newsmuncher.services.comedy_concepts import animal_mentions
from newsmuncher.services.lexical_exposure import meaningful_words
from newsmuncher.services.munge_engines import modern_prompt_concepts


def registry(collection=None, now=None):
    return ConceptRegistry(collection or MemoryCollection(), now=now or (
        lambda: datetime(2026, 10, 9, tzinfo=timezone.utc)))


def test_default_and_legacy_configuration(monkeypatch):
    monkeypatch.delenv("NEWSMUNCHER_CONCEPT_MODE", raising=False)
    monkeypatch.delenv("NEWSMUNCHER_EXPANDED_VOCABULARY", raising=False)
    monkeypatch.delenv("NEWSMUNCHER_NEW_VOCABULARY", raising=False)
    config = ConceptSelectionConfig.from_environment()
    assert config.mode == "generated"
    assert config.vocabulary_mode == "off"
    assert config.new_vocabulary is True
    monkeypatch.setenv("NEWSMUNCHER_CONCEPT_MODE", "legacy")
    assert ConceptSelectionConfig.from_environment().mode == "legacy"


def test_lexical_recency_penalty_changes_final_candidate_order():
    baseline_service = ConceptRegistry(MemoryCollection())
    candidates = baseline_service._candidates("final-order")
    repeated, _ = next(
        pair for pair in candidates
        if pair[1] == "nouns" and pair[0].category == "everyday_british")
    identity = meaningful_words(repeated.phrase)[0]

    baseline_service.candidates = lambda key, lexical_penalties=None: candidates
    baseline = baseline_service.offer("baseline-final-order")
    assert repeated.phrase in {item["phrase"] for item in baseline}

    penalised_service = ConceptRegistry(MemoryCollection())
    penalised_service.candidates = lambda key, lexical_penalties=None: candidates
    penalised = penalised_service.offer(
        "penalised-final-order", lexical_penalties={"word:" + identity: 100})
    assert repeated.phrase not in {item["phrase"] for item in penalised}
    assert len(penalised) == 20
    assert sum(item["target_bank"] == "animals" for item in penalised) == 6


def test_short_animal_recency_penalty_changes_final_candidate_order():
    short_animals = {"emu", "yak", "pig", "bee", "olm", "cow", "eel"}
    for suffix in range(20):
        candidate_service = ConceptRegistry(MemoryCollection())
        candidates = candidate_service._candidates(f"short-animal-order:{suffix}")
        baseline_service = ConceptRegistry(MemoryCollection())
        baseline_service.candidates = lambda key, lexical_penalties=None: candidates
        baseline = baseline_service.offer(f"short-animal-baseline:{suffix}")
        repeated = next((item["animal_species"] for item in baseline
                         if item.get("animal_species") in short_animals), None)
        if repeated:
            break
    assert repeated is not None

    penalised_service = ConceptRegistry(MemoryCollection())
    penalised_service.candidates = lambda key, lexical_penalties=None: candidates
    penalised = penalised_service.offer(
        f"short-animal-penalised:{suffix}",
        lexical_penalties={"word:" + repeated: 100},
    )
    assert repeated not in {item.get("animal_species") for item in penalised}
    assert len(penalised) == 20
    assert sum(item["target_bank"] == "animals" for item in penalised) == 6


def test_hidden_prompt_animals_release_with_selection_and_do_not_gain_cooldowns():
    collection = MemoryCollection()
    service = registry(collection)
    selected = service.offer("animal-projection-release")
    presented, metrics = modern_prompt_concepts(selected)
    hidden = [item for item in selected if item not in presented]
    assert metrics["selected_animals"] == 6
    assert metrics["presented_animals"] == 4
    assert len(hidden) == 2

    service.accept("animal-projection-release", "rewrite", presented,
                   "A quiet title", "No selected creature appeared.")

    assert not any(doc.get("offered_by") == "animal-projection-release"
                   for doc in collection.docs.values())
    for item in hidden:
        assert collection.docs["phrase:" + normalised(item["phrase"])].get(
            "last_rewrite_id") is None


def test_new_vocabulary_switch_is_explicit(monkeypatch):
    monkeypatch.delenv("NEWSMUNCHER_NEW_VOCABULARY", raising=False)
    assert ConceptSelectionConfig.from_environment().new_vocabulary is True
    monkeypatch.setenv("NEWSMUNCHER_NEW_VOCABULARY", "on")
    assert ConceptSelectionConfig.from_environment().new_vocabulary is True
    monkeypatch.setenv("NEWSMUNCHER_NEW_VOCABULARY", "off")
    assert ConceptSelectionConfig.from_environment().new_vocabulary is False


def test_new_vocabulary_is_blended_and_default_path_is_unchanged():
    baseline = ConceptRegistry(MemoryCollection()).offer("new-vocab:fixed")
    experimental = ConceptRegistry(
        MemoryCollection(), ConceptSelectionConfig(new_vocabulary=True)
    ).offer("new-vocab:fixed")
    assert len(baseline) == len(experimental) == 20
    assert [item["phrase"] for item in baseline] != [
        item["phrase"] for item in experimental]
    from newsmuncher.services.experimental_vocabulary import concept_banks
    new_bases = set(concept_banks()["domestic_objects"])
    selected_new = sum(item["base"] in new_bases for item in experimental)
    assert 2 <= selected_new <= 8
    assert any(item["base"] not in new_bases for item in experimental)


def test_new_vocabulary_respects_exclusions_and_falls_back_by_category(monkeypatch):
    from newsmuncher.services.comedy_concepts import ComedyConceptGenerator
    from newsmuncher.services.experimental_vocabulary import concept_banks
    banks = concept_banks()
    blocked = banks["domestic_objects"][0]
    monkeypatch.setenv("NEWSMUNCHER_NEW_VOCABULARY", "on")
    excluded = {"noun_identity:" + blocked}
    generator = ComedyConceptGenerator(
        "new-vocab:filter", new_vocabulary=True,
        noun_exclusions=excluded, target_bank="nouns")
    assert blocked not in generator._bank("domestic_objects")
    service = ConceptRegistry(
        MemoryCollection(), ConceptSelectionConfig(new_vocabulary=True))
    offered = service.offer("new-vocab:excluded", noun_exclusions=excluded)
    assert len(offered) == 20
    assert blocked not in {item["base"] for item in offered}
    assert [item["target_bank"] for item in offered].count("animals") == 6
    assert [item["target_bank"] for item in offered].count("nouns") == 14


def test_expanded_vocabulary_modes_are_explicit_and_machine_review_is_local(monkeypatch):
    from newsmuncher.services.vocabulary_catalogue import eligible_concept_entries
    reviewed = eligible_concept_entries("animals", "reviewed")
    evaluation = eligible_concept_entries("animals", "evaluation")
    assert reviewed and all(x["approval_status"] == "editorially_reviewed" for x in reviewed)
    assert {x["text"] for x in evaluation} - {x["text"] for x in reviewed} == {
        "daw", "kea", "olm"}
    assert all(x["approval_status"] == "editorially_reviewed" or
               x["text"] in {"daw", "kea", "olm"} for x in evaluation)
    assert all(x["familiarity"] != "obscure" for x in evaluation)
    monkeypatch.setenv("NEWSMUNCHER_EXPANDED_VOCABULARY", "evaluation")
    assert ConceptSelectionConfig.from_environment().vocabulary_mode == "evaluation"


def test_expanded_concepts_preserve_quota_determinism_and_multiword_identities():
    config = ConceptSelectionConfig(vocabulary_mode="evaluation")
    first = ConceptRegistry(MemoryCollection(), config=config).offer("expanded:fixed")
    second = ConceptRegistry(MemoryCollection(), config=config).offer("expanded:fixed")
    assert [x["phrase"] for x in first] == [x["phrase"] for x in second]
    assert Counter(x["category"] for x in first) == {
        "everyday_british": 3, "cheeky_object": 3, "absurd_invention": 4,
        "ridiculous_creature": 4, "bureaucratic_nonsense": 3,
        "emergency_equipment": 2, "ceremonial_object": 1,
    }
    assert any(" " in x["base"] for x in first)


def test_expanded_retries_are_stable_and_concurrent_leases_remain_disjoint():
    collection = MemoryCollection()
    config = ConceptSelectionConfig(vocabulary_mode="evaluation")
    service = ConceptRegistry(collection, config=config)
    first = service.offer("expanded:retry")
    retry = service.offer("expanded:retry")
    concurrent = service.offer("expanded:other")
    assert [x["phrase"] for x in retry] == [x["phrase"] for x in first]
    assert not ({x["phrase"] for x in first} & {x["phrase"] for x in concurrent})
    assert not ({x["base"] for x in first} & {x["base"] for x in concurrent})


def test_expanded_offered_animal_is_cooled_without_static_species_bank():
    collection = MemoryCollection()
    service = ConceptRegistry(collection, config=ConceptSelectionConfig(
        vocabulary_mode="evaluation"))
    offered = service.offer("expanded:animal-use")
    creature = next(x for x in offered if x["animal_species"] and x["animal_species"] not in {
        "badger", "ferret", "pigeon", "alpaca", "goose", "duck", "otter",
    })
    service.accept("expanded:animal-use", "rewrite", offered, "",
                   f"The {creature['animal_species']} caused a scene.")
    assert collection.docs[
        "animal:" + normalised(creature["animal_species"])
    ]["use_count"] == 1


def test_catalogue_failure_becomes_typed_exhaustion_and_releases(monkeypatch):
    collection = MemoryCollection()
    service = ConceptRegistry(collection, config=ConceptSelectionConfig(
        vocabulary_mode="evaluation"))
    monkeypatch.setattr(service, "candidates", MagicMock(side_effect=ValueError("bad catalogue")))
    try:
        service.offer("expanded:broken")
    except ConceptSelectionExhausted:
        pass
    else:
        raise AssertionError("Expected controlled selection failure")
    assert all(doc.get("offered_by") != "expanded:broken" for doc in collection.docs.values())


def test_offer_is_stable_twenty_way_balanced_and_semantically_targeted():
    service = registry()
    first = service.offer("pet:session")
    second = service.offer("pet:session")
    assert [item["phrase"] for item in first] == [item["phrase"] for item in second]
    assert [item["target_bank"] for item in first].count("nouns") == 14
    assert [item["target_bank"] for item in first].count("animals") == 6
    assert all(item["category"] != "ridiculous_creature" for item in first
               if item["target_bank"] == "nouns")
    assert all(item["category"] == "ridiculous_creature" or item["category"] in PHYSICAL_CATEGORIES
               for item in first if item["target_bank"] == "animals")
    assert Counter(item["category"] for item in first) == {
        "everyday_british": 3, "cheeky_object": 3, "absurd_invention": 4,
        "ridiculous_creature": 4, "bureaucratic_nonsense": 3,
        "emergency_equipment": 2, "ceremonial_object": 1,
    }
    assert service.last_metrics["availability_reads"] == 1
    assert service.last_metrics["lease_writes"] <= 68


def test_concurrent_leases_are_phrase_and_base_disjoint():
    service = registry()
    first, second = service.offer("pet:a"), service.offer("pet:b")
    assert not ({x["phrase"] for x in first} & {x["phrase"] for x in second})
    assert not ({x["base"] for x in first} & {x["base"] for x in second})
    assert not ({x["premise_key"] for x in first} & {x["premise_key"] for x in second})
    assert not ({x["animal_species"] for x in first if x["animal_species"]} &
                {x["animal_species"] for x in second if x["animal_species"]})


def test_animal_detection_normalizes_singular_plural_and_multiword_species():
    assert animal_mentions("Hamsters met geese and two guinea pigs.") == {
        "hamster", "goose", "guinea pig",
    }


def test_recent_species_records_do_not_force_hard_cooldown_relaxation():
    now = datetime(2026, 10, 15, tzinfo=timezone.utc)
    collection = MemoryCollection()
    service = ConceptRegistry(collection, now=lambda: now)
    for item, target in service._candidates("soft-species"):
        if target != "animals" or not item.animal_species:
            continue
        for prefix, value in (("base:", item.base),
                              ("animal:", item.animal_species)):
            key = prefix + normalised(value)
            collection.docs[key] = {"_id": key, "last_used_at": now,
                                    "use_count": 1}
    offered = service.offer("soft-species")
    assert len(offered) == 20
    assert Counter(item["target_bank"] for item in offered) == {
        "nouns": 14, "animals": 6}
    assert service.last_metrics["relaxed"] is False


def test_accept_tracks_exact_use_only_and_release_allows_reuse():
    collection = MemoryCollection(); service = registry(collection)
    offered = service.offer("pet:first")
    used = service.accept("pet:first", "rewrite", offered, "title", offered[0]["phrase"])
    assert used == [offered[0]["phrase"]]
    assert collection.docs["base:" + normalised(offered[0]["base"])]["use_count"] == 1
    assert collection.docs["phrase:" + normalised(offered[0]["phrase"])]["use_count"] == 1
    assert collection.docs["premise:" + normalised(offered[0]["premise_key"])]["use_count"] == 1
    assert all("offered_by" not in doc for doc in collection.docs.values())
    failed = service.offer("pet:failed")
    service.release("pet:failed")
    assert all("offered_by" not in doc for doc in collection.docs.values())


def test_semantic_memory_records_used_mechanism_but_never_blocks_saturated_family():
    collection = MemoryCollection()
    service = ConceptRegistry(collection, config=ConceptSelectionConfig(
        vocabulary_mode="evaluation", semantic_memory_mode="evaluation"))
    offered = service.offer("semantic:first")
    item = offered[0]
    service.accept("semantic:first", "rewrite", offered, "", item["base"])
    family_docs = [doc for key, doc in collection.docs.items()
                   if key.startswith("semantic:concept:")]
    assert family_docs and family_docs[0]["last_rewrite_id"] == "rewrite"
    # A family record is a ranking signal, not a lease or hard cooldown.
    assert len(service.offer("semantic:second")) == 20
    service.release("semantic:second")
    assert all("offered_by" not in doc for doc in collection.docs.values())


def test_paraphrased_and_independently_introduced_animals_are_remembered():
    collection = MemoryCollection(); service = registry(collection)
    offered = service.offer("pet:animals")
    creature = next(item for item in offered if item["animal_species"])
    service.accept("pet:animals", "rewrite", offered, "title",
                   f"A {creature['animal_species']} caused trouble beside several hamsters.")
    for animal in (creature["animal_species"], "hamster"):
        record = collection.docs["animal:" + normalised(animal)]
        assert record["use_count"] == 1
        assert record["last_rewrite_id"] == "rewrite"


def test_unused_offered_animal_is_not_counted_and_source_animal_is_exempt():
    collection = MemoryCollection(); service = registry(collection)
    offered = service.offer("pet:unused-animal")
    creature = next(item for item in offered if item["animal_species"])
    service.accept("pet:unused-animal", "rewrite", offered, "title", "No creature appeared.")
    assert "last_used_at" not in collection.docs[
        "animal:" + normalised(creature["animal_species"])
    ]

    second = service.offer("pet:source-animal")
    service.accept("pet:source-animal", "rewrite-2", second, "title",
                   "The hamster remained central.", "Original report about a hamster.")
    assert collection.docs.get("animal:hamster", {}).get("last_rewrite_id") != "rewrite-2"


def test_object_identity_is_remembered_even_when_full_concept_is_paraphrased():
    collection = MemoryCollection(); service = registry(collection)
    offered = service.offer("pet:object")
    item = next(value for value in offered if not value["animal_species"])
    service.accept("pet:object", "rewrite", offered, "title",
                   f"The {item['base']} survived, although its description changed.")
    assert collection.docs["base:" + normalised(item["base"])]["use_count"] == 1
    assert "use_count" not in collection.docs["phrase:" + normalised(item["phrase"])]


def test_used_concept_is_available_again_after_cooldown(monkeypatch):
    collection = MemoryCollection()
    clock = [datetime(2026, 10, 9, tzinfo=timezone.utc)]
    service = registry(collection, now=lambda: clock[0])
    offered = service.offer("pet:cooldown")
    service.accept("pet:cooldown", "rewrite", offered, offered[0]["phrase"], "body")
    fixed = service.candidates("pet:cooldown")
    selected = {(item["phrase"], item["target_bank"]) for item in offered}
    monkeypatch.setattr(service, "candidates", lambda key: [
        (item, target) for item, target in fixed if (item.phrase, target) in selected
    ])
    clock[0] += timedelta(days=31)
    later = service.offer("pet:cooldown")
    assert offered[0]["phrase"] in {item["phrase"] for item in later}


def test_five_consecutive_rewrites_can_cool_used_concepts_without_exhaustion():
    collection = MemoryCollection()
    for attempt in range(5):
        service = registry(collection)
        offered = service.offer(f"pet:rewrite-{attempt}")
        assert len(offered) == 20
        used_text = " ".join(item["phrase"] for item in offered[:4])
        service.accept(f"pet:rewrite-{attempt}", f"rewrite-{attempt}", offered, used_text, "")


def test_saturated_base_and_premise_cooldowns_relax_before_exhaustion(monkeypatch):
    collection = MemoryCollection(); service = registry(collection)
    candidates = service.candidates("fixed-diversity")
    monkeypatch.setattr(service, "candidates", lambda key: candidates)
    for item, _target in candidates:
        for key in ("base:" + normalised(item.base),
                    "premise:" + normalised(item.premise_key)):
            collection.docs[key] = {"_id": key, "last_used_at": service.now()}
    offered = service.offer("pet:relaxed")
    assert len(offered) == 20
    assert len({item["phrase"] for item in offered}) == 20
    # Viability is checked in memory, so the doomed strict slate performs no
    # sequential lease scan before the explicit relaxed attempt.
    assert service.last_metrics["availability_reads"] == 1
    assert service.last_metrics["lease_writes"] <= 68


def test_genuine_exhaustion_is_typed_and_releases_partial_offer(monkeypatch):
    collection = MemoryCollection(); service = registry(collection)
    monkeypatch.setattr(service, "candidates", lambda key: [])
    try:
        service.offer("pet:exhausted")
    except ConceptSelectionExhausted as exc:
        assert "try MUNGE IT again" in str(exc)
    else:
        raise AssertionError("Expected bounded selection exhaustion")
    assert all(doc.get("offered_by") != "pet:exhausted" for doc in collection.docs.values())


def test_large_history_does_not_promote_soft_identities_to_hard_exclusions():
    from newsmuncher.services.noun_exclusion import (
        blocked_entries, recent_comic_identity_anchors, verified_noun_anchors,
    )

    soft = sorted(set(recent_comic_identity_anchors(True)) -
                  set(verified_noun_anchors(True)))
    exclusions = {"noun_identity:" + word for word in soft}
    exclusions.update("phrase:historical filler %04d" % index
                      for index in range(2379 - len(exclusions)))

    service = registry(MemoryCollection())
    offered = service.offer("pet:large-history", noun_exclusions=exclusions)
    assert len(offered) == 20
    assert {item["target_bank"] for item in offered} == {"nouns", "animals"}
    assert all(not blocked_entries(item["phrase"], exclusions)
               for item in offered)


def test_historical_species_fifo_entries_do_not_exhaust_modern_slate():
    from newsmuncher.services.comedy_concepts import animal_vocabulary
    from newsmuncher.services.noun_exclusion import blocked_entries
    exclusions = set()
    for species in animal_vocabulary():
        exclusions.update({f"phrase:{species}", f"noun_identity:{species}"})
    index = 0
    while len(exclusions) < 2860:
        exclusions.add(f"phrase:unrelated historical premise {index}")
        index += 1
    collection = MemoryCollection()
    service = ConceptRegistry(collection)
    offered = service.offer("historical-species", noun_exclusions=exclusions)
    assert len(offered) == 20
    assert Counter(item["target_bank"] for item in offered) == {
        "nouns": 14, "animals": 6}
    assert all(not blocked_entries(item["phrase"], exclusions) for item in offered)
    service.release("historical-species")
    assert all(not doc.get("offered_by") for doc in collection.docs.values())


def test_fully_exhausted_optional_category_returns_partial_pool_for_fallback():
    from newsmuncher.services.comedy_concepts import ComedyConceptGenerator
    from newsmuncher.services.noun_exclusion import identity_words

    probe = ComedyConceptGenerator(
        "empty-bureaucratic-probe", target_bank="nouns", new_vocabulary=True)
    values = (*probe._bank("documents", 2, "institutional_control"),
              *probe._bank("bureau_bodies", 2, "institutional_control"))
    exclusions = {
        "phrase:" + " ".join(identity_words(value))
        for value in values if identity_words(value)
    }
    generator = ComedyConceptGenerator(
        "empty-bureaucratic", noun_exclusions=exclusions,
        target_bank="nouns", new_vocabulary=True)

    assert generator.generate(
        6, category="bureaucratic_nonsense", allow_partial=True) == []
    assert generator.last_diagnostics.exhausted
    assert generator.last_diagnostics.rejected["component_space"] == 1


def test_initial_generation_failure_records_stage_and_detail(monkeypatch):
    service = registry(MemoryCollection())
    monkeypatch.setattr(service, "_candidates",
                        lambda *args, **kwargs: (_ for _ in ()).throw(
                            ValueError("No bureaucratic_nonsense template supports intensity 3")))
    try:
        service.offer("pet:generation-failure", noun_exclusions={"phrase:x"})
    except ConceptSelectionExhausted:
        pass
    else:
        raise AssertionError("Expected initial candidate-generation failure")
    assert service.last_metrics["failure_stage"] == "candidate_generation"
    assert "bureaucratic_nonsense" in service.last_metrics["generation_error"]


def test_partial_bureaucratic_generation_uses_safe_category_fallback():
    from newsmuncher.services.comedy_concepts import ComedyConceptGenerator
    from newsmuncher.services.noun_exclusion import blocked_entries, identity_words

    probe = ComedyConceptGenerator(
        "bureaucratic-shortage-probe", target_bank="nouns", new_vocabulary=True)
    documents = probe._bank("documents", 2, "institutional_control")
    bodies = probe._bank("bureau_bodies", 2, "institutional_control")
    exclusions = {
        "phrase:" + " ".join(identity_words(value))
        for value in (*bodies, *documents[1:]) if identity_words(value)
    }
    exclusions.update(
        f"phrase:unrelated historical identity {index}" for index in range(3062 - len(exclusions))
    )

    collection = MemoryCollection()
    service = ConceptRegistry(
        collection, ConceptSelectionConfig(new_vocabulary=True))
    selected = service.offer(
        "large-ledger-bureaucratic-shortage", noun_exclusions=exclusions)

    assert len(selected) == 20
    assert Counter(item["target_bank"] for item in selected) == {
        "nouns": 14, "animals": 6}
    assert service.last_metrics["category_quota_slack"] >= 1
    shortfalls = service.last_metrics["candidate_generation_shortfalls"]
    assert any(item["category"] == "bureaucratic_nonsense"
               and item["produced"] < item["requested"]
               and item["rejected"].get("base_overuse", 0) > 0
               for item in shortfalls)
    assert all(not blocked_entries(item["phrase"], exclusions)
               for item in selected)
    service.release("large-ledger-bureaucratic-shortage")
    assert all(not doc.get("offered_by") for doc in collection.docs.values())


def test_expired_leases_can_be_acquired_by_another_session(monkeypatch):
    collection = MemoryCollection()
    clock = [datetime(2026, 10, 9, tzinfo=timezone.utc)]
    service = registry(collection, now=lambda: clock[0])
    candidates = service.candidates("fixed-candidates")
    monkeypatch.setattr(service, "candidates", lambda key: candidates)
    first = service.offer("pet:first")
    assert len(first) == 20
    selected = {(normalised(item["base"]), item["target_bank"]) for item in first}
    fixed_slate = [(item, target) for item, target in candidates
                   if (normalised(item.base), target) in selected]
    monkeypatch.setattr(service, "candidates", lambda key: fixed_slate)
    try:
        service.offer("pet:second")
    except ConceptSelectionExhausted:
        pass
    else:
        raise AssertionError("A live lease should exclude the identical fixed slate")
    clock[0] += timedelta(minutes=16)
    assert len(service.offer("pet:second")) == 20


def test_prompt_override_is_exact_ten_plus_ten_and_claims_legacy_only(monkeypatch):
    from newsmuncher.utils import clean_data
    banks = {key: [f"{key}{i}" for i in range(10)] for key in
             ("nouns", "animals", "adverbs", "slang", "places", "names")}
    def load(count, excluded=()):
        return {key: ([] if key in excluded else list(values)) for key, values in banks.items()}
    monkeypatch.setattr(clean_data, "load_random_words", load)
    monkeypatch.setattr(clean_data, "filter_word_banks", lambda prep, words: words)
    monkeypatch.setattr(clean_data, "preprocess_source", lambda entry: {"masked": entry})
    monkeypatch.setattr(clean_data, "replacement_guidance", lambda prep, words: "")
    template = "{noun_words1}|{noun_words2}|{noun_words3}|{animal_words1}|{animal_words2}|{animal_words3}|{adverb_words1}|{adverb_words2}|{adverb_words3}|{slang_words1}|{slang_words2}|{slang_words3}|{place_words1}|{place_words2}|{place_words3}|{name_words1}|{name_words2}|{name_words3}"
    result = clean_data.prepare_prompt(
        {"title":"t","description":"d","extract":"e"}, 10, template,
        concept_overrides={"nouns":[f"n{i}" for i in range(10)],
                           "animals":[f"a{i}" for i in range(10)]},
        concept_guidance=CONCEPT_GUIDANCE,
    )
    assert result["contenders"]["nouns"] == []
    assert result["contenders"]["animals"] == []
    assert all(value in result["full_prompt"] for value in ("n1","n9","a1","a9"))
    assert CONCEPT_GUIDANCE in result["full_prompt"]
    assert "Animal and non-animal concepts are alternatives, not a checklist" in result["full_prompt"]
    assert "readily imaginable situations" in result["full_prompt"]
    assert "zero, one or two" not in result["full_prompt"]

    legacy = clean_data.prepare_prompt(
        {"title":"t","description":"d","extract":"e"}, 10, template,
    )
    assert legacy["contenders"]["nouns"] == banks["nouns"]
    assert legacy["contenders"]["animals"] == banks["animals"]


def test_route_adds_no_provider_call_and_tracking_failure_keeps_success():
    from test_image_generation import ImageTests
    fixture = ImageTests(); fixture.setUp()
    try:
        routes = fixture.previews()
        concepts = registry().offer("alice:legacy")
        tracker = SimpleNamespace(offer=MagicMock(return_value=concepts),
                                  accept=MagicMock(side_effect=RuntimeError("tracking")),
                                  release=MagicMock())
        routes.ConceptSelectionConfig.from_environment.return_value = SimpleNamespace(mode="generated")
        routes.ConceptRegistry = MagicMock(return_value=tracker)
        routes.generated_concept_collection = MagicMock(return_value=object())
        routes.prepare_prompt.return_value = {"full_prompt":"prompt", "preprocessing":None, "contenders":{}}
        routes.send_prompt.return_value = {"title":"one", "extract":"body"}
        routes.format_shizzalise_result.return_value = dict(fixture.result)
        routes.copy_edit_pass.return_value = None
        result = routes.shizzalise_data(routes.ShizzRequest(title="s",description="",extract="s"), "alice", "alice")
        routes.send_prompt.assert_called_once(); routes.copy_edit_pass.assert_called_once()
        assert result["crazyReplacement1Title"] == fixture.result["crazyReplacement1Title"]
        released_key = tracker.release.call_args.args[0]
        assert released_key.startswith("alice:") and released_key != "alice:legacy"
    finally:
        fixture.tearDown(); fixture.doCleanups()


def test_route_maps_selection_exhaustion_without_calling_provider():
    from test_image_generation import ImageTests
    fixture = ImageTests(); fixture.setUp()
    try:
        routes = fixture.previews()
        tracker = SimpleNamespace(
            offer=MagicMock(side_effect=ConceptSelectionExhausted("Concepts busy; try again.")),
            release=MagicMock(),
        )
        routes.ConceptSelectionConfig.from_environment.return_value = SimpleNamespace(mode="generated")
        routes.ConceptRegistry = MagicMock(return_value=tracker)
        routes.generated_concept_collection = MagicMock(return_value=object())
        try:
            routes.shizzalise_data(
                routes.ShizzRequest(title="s", description="", extract="s"), "alice", "alice"
            )
        except routes.HTTPException as exc:
            assert exc.status_code == 409
            assert exc.detail == "Concepts busy; try again."
        else:
            raise AssertionError("Expected controlled selection response")
        routes.send_prompt.assert_not_called()
    finally:
        fixture.tearDown(); fixture.doCleanups()


def test_same_browser_draft_session_gets_fresh_concept_attempt_identity():
    from test_image_generation import ImageTests
    fixture = ImageTests(); fixture.setUp()
    try:
        routes = fixture.previews()
        concepts = registry().offer("fixture")
        tracker = SimpleNamespace(
            offer=MagicMock(return_value=concepts), accept=MagicMock(return_value=[]),
            release=MagicMock(),
        )
        routes.ConceptSelectionConfig.from_environment.return_value = SimpleNamespace(mode="generated")
        routes.ConceptRegistry = MagicMock(return_value=tracker)
        routes.generated_concept_collection = MagicMock(return_value=object())
        routes.prepare_prompt.return_value = {"full_prompt":"prompt", "preprocessing":None, "contenders":{}}
        routes.send_prompt.return_value = {"title":"one", "extract":"body"}
        routes.format_shizzalise_result.return_value = dict(fixture.result)
        routes.copy_edit_pass.return_value = None
        request = routes.ShizzRequest(title="s", description="", extract="s", draft_session="same")
        routes.shizzalise_data(request, "alice", "alice")
        routes.shizzalise_data(request, "alice", "alice")
        keys = [call.args[0] for call in tracker.offer.call_args_list]
        assert len(keys) == 2 and keys[0] != keys[1]
        assert all(key.startswith("alice:") for key in keys)
    finally:
        fixture.tearDown(); fixture.doCleanups()
