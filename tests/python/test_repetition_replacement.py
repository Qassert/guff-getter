from collections import Counter

import pytest

from newsmuncher.services.repetition_replacement import (
    PhraseReplacementConfig, RepetitionReplacementConfig, build_repetition_replacement,
    finish_repetition_diagnostic,
)


def _build(**overrides):
    values = dict(
        first_pass={"crazyReplacement1Title": "Gravy returns",
                    "crazyReplacement1Extract":
                    "The gravy tribunal raced past a fucking moon badger."},
        source_text="A council reviewed transport.",
        lexical_penalties=Counter({"word:gravy": 18, "word:raced": 40,
                                   "word:tribunal": 2}),
        concepts=[{"phrase": "municipal gravy tribunal", "base": "gravy tribunal",
                   "target_bank": "nouns"}],
        descriptors=[], raw_ingredients=[], names=[], places=[],
        thematic_ingredients=[
            {"text": "luminous kettle using spore dispersal", "target_bank": "nouns",
             "construction_id": "property_base_process"},
            {"text": "responsive to mycelium during erosion",
             "grammatical_role": "predicate", "construction_id": "role_predicate"},
            {"text": "bronze pony in contact with a scribe", "target_bank": "animals",
             "construction_id": "base_relationship_entity"},
        ],
        config=RepetitionReplacementConfig("evaluation"),
    )
    values.update(overrides)
    return build_repetition_replacement(**values)


def test_flag_defaults_off_and_validates(monkeypatch):
    monkeypatch.delenv("NEWSMUNCHER_REPETITION_REPLACEMENT", raising=False)
    assert not RepetitionReplacementConfig.from_environment().enabled
    monkeypatch.setenv("NEWSMUNCHER_REPETITION_REPLACEMENT", "evaluation")
    assert RepetitionReplacementConfig.from_environment().enabled
    monkeypatch.setenv("NEWSMUNCHER_REPETITION_REPLACEMENT", "yes")
    with pytest.raises(ValueError):
        RepetitionReplacementConfig.from_environment()
    monkeypatch.delenv("NEWSMUNCHER_PHRASE_REPLACEMENT", raising=False)
    assert not PhraseReplacementConfig.from_environment().enabled
    monkeypatch.setenv("NEWSMUNCHER_PHRASE_REPLACEMENT", "evaluation")
    assert PhraseReplacementConfig.from_environment().enabled
    monkeypatch.setenv("NEWSMUNCHER_PHRASE_REPLACEMENT", "yes")
    with pytest.raises(ValueError):
        PhraseReplacementConfig.from_environment()


def test_default_off_has_no_plan():
    plan, diagnostic = _build(config=RepetitionReplacementConfig())
    assert plan is None
    assert diagnostic["enabled"] is False


def test_selects_exposed_first_pass_ingredient_and_excludes_narrative_verbs():
    plan, diagnostic = _build(raw_ingredients=[{"text": "raced"}])
    assert [item["text"] for item in plan["targets"]] == ["gravy"]
    assert plan["maximum_substitutions"] == 2
    assert len(plan["alternatives"]) <= 2
    assert any(item["text"] == "raced" and
               item["reason"] == "narrative_or_ordinary_language"
               for item in diagnostic["rejected_targets"])


def test_source_and_proper_identity_are_protected():
    plan, diagnostic = _build(
        source_text="The original gravy inquiry concerned Lady Marmalade.",
        names=["Lady Marmalade"],
        concepts=[{"phrase": "gravy inquiry", "base": "gravy"},
                  {"phrase": "Lady Marmalade scandal", "base": "marmalade"}],
        lexical_penalties=Counter({"word:gravy": 20, "word:marmalade": 20}),
        first_pass={"crazyReplacement1Title": "Gravy and Marmalade",
                    "crazyReplacement1Extract": "Gravy met Lady Marmalade."},
    )
    assert plan is None
    reasons = {item["text"]: item["reason"] for item in diagnostic["rejected_targets"]}
    assert reasons["gravy"] == "required_by_source"
    assert reasons["marmalade"] == "protected_name_or_location"


def test_threshold_absence_caps_and_role_compatible_alternatives():
    concepts = [{"phrase": word, "base": word, "target_bank": "nouns"}
                for word in ("gravy", "custard", "crumpet", "marmalade", "absentthing")]
    penalties = Counter({"word:" + word: 20 - index
                         for index, word in enumerate(
                             ("gravy", "custard", "crumpet", "marmalade", "absentthing"))})
    first = {"crazyReplacement1Title": "Food",
             "crazyReplacement1Extract": "Gravy custard crumpet marmalade gathered."}
    plan, diagnostic = _build(concepts=concepts, lexical_penalties=penalties,
                              first_pass=first)
    assert len(plan["targets"]) == 3
    assert len(plan["alternatives"]) == 2
    assert any(item["text"] == "absentthing" and
               item["reason"] == "absent_from_first_pass"
               for item in diagnostic["rejected_targets"])


def test_zero_targets_and_zero_alternatives_do_nothing():
    plan, _ = _build(lexical_penalties=Counter())
    assert plan is None
    plan, diagnostic = _build(thematic_ingredients=[])
    assert plan is None and diagnostic["eligible_targets"]


def test_exact_audit_evidence_does_not_claim_semantic_replacement():
    _, diagnostic = _build()
    diagnostic["recent_exposure_signals"] = {"word:gravy": 18, "word:custard": 12}
    final = {"crazyReplacement1Title": "Spore dispersal returns",
             "crazyReplacement1Extract":
             "A luminous kettle using spore dispersal met fresh custard."}
    finish_repetition_diagnostic(diagnostic, _build()[1] and {
        "crazyReplacement1Title": "Gravy returns",
        "crazyReplacement1Extract": "The gravy tribunal remained."}, final)
    assert diagnostic["exact_target_changes"][0]["exactly_removed"] is True
    assert any(item["text"] == "luminous kettle using spore dispersal" and
               item["exactly_added"] is True
               for item in diagnostic["exact_alternative_additions"])
    assert diagnostic["new_recently_overused_terms"] == ["custard"]


def test_absurd_profanity_is_only_data_and_never_locally_rewritten():
    first = {"crazyReplacement1Title": "Fucking gravy",
             "crazyReplacement1Extract":
             "The fucking gravy married a moon badger inside a sentient gusset."}
    plan, _ = _build(first_pass=first)
    assert plan and "fucking" in first["crazyReplacement1Extract"]


def test_phase4u_prefers_longest_provenance_phrase_and_suppresses_components():
    plan, diagnostic = _build(
        first_pass={"crazyReplacement1Title": "The Authority",
                    "crazyReplacement1Extract":
                    "A MUNICIPAL licensing authority, then a licensing authority, arrived."},
        concepts=[{"phrase": "municipal licensing authority for trifle standards",
                   "base": "licensing authority", "target_bank": "nouns",
                   "generator_version": "concept-v3"}],
        lexical_penalties=Counter({"identity:licensing-authority": 21,
                                   "word:licensing": 68, "word:authority": 68}),
        phrase_config=PhraseReplacementConfig("evaluation"),
        thematic_ingredients=[{"text": "backup cardigan in reciprocity with cavern",
                               "base": "backup cardigan", "target_bank": "nouns",
                               "domain_ids": ["divination", "caves"],
                               "seed_kinds": ["relationship", "entity"]}],
    )
    assert [item["text"] for item in plan["targets"]] == ["licensing authority"]
    assert plan["targets"][0]["first_pass_occurrences"] == 2
    assert {item["text"] for item in diagnostic["overlap_exclusions"]} == {
        "licensing", "authority"}
    assert plan["alternatives"][0]["text"] == "backup cardigan"
    assert plan["phrase_replacement"] is True


def test_phase4u_regression_jelly_mould_trouser_press_and_gravy_boat():
    concepts = [
        {"phrase": "jelly mould notorious for polishing", "base": "jelly mould",
         "target_bank": "nouns"},
        {"phrase": "shed-inflating trouser press", "base": "trouser press",
         "target_bank": "animals"},
        {"phrase": "gravy boat of municipal discipline", "base": "gravy boat",
         "target_bank": "nouns"},
    ]
    first = {"crazyReplacement1Title": "JELLY MOULD!",
             "crazyReplacement1Extract":
             "The jelly mould met a trouser press; the gravy boat objected."}
    penalties = Counter({"word:jelly": 10, "word:press": 75, "word:trouser": 30,
                         "word:gravy": 32})
    plan, diagnostic = _build(
        concepts=concepts, first_pass=first, lexical_penalties=penalties,
        phrase_config=PhraseReplacementConfig("evaluation"),
        thematic_ingredients=[
            {"text": "archival certificate using knucklebones", "base": "certificate",
             "target_bank": "nouns", "domain_ids": ["archives", "games"]},
            {"text": "megaphone in counterweight balance", "base": "megaphone",
             "target_bank": "animals", "domain_ids": ["bridges"]},
        ])
    assert [item["text"] for item in plan["targets"]] == [
        "trouser press", "gravy boat", "jelly mould"]
    excluded = {item["text"] for item in diagnostic["overlap_exclusions"]}
    assert {"press", "trouser", "gravy", "jelly"} <= excluded
    assert len(plan["targets"]) == 3 and len(plan["alternatives"]) == 2


def test_phase4u_prefers_low_exposure_role_match_and_can_audit_fallback():
    themes = [
        {"text": "bronze archival certificate", "base": "certificate",
         "target_bank": "nouns", "domain_ids": ["archives"]},
        {"text": "luminous backup cardigan", "base": "backup cardigan",
         "target_bank": "nouns", "domain_ids": ["optics"]},
    ]
    plan, _ = _build(
        phrase_config=PhraseReplacementConfig("evaluation"),
        thematic_ingredients=themes,
        lexical_penalties=Counter({"word:gravy": 18, "word:certificate": 20}))
    assert [item["text"] for item in plan["alternatives"]] == [
        "backup cardigan", "certificate"]

    plan, diagnostic = _build(
        phrase_config=PhraseReplacementConfig("evaluation"),
        thematic_ingredients=[{"text": "performing erosion with spores",
                               "subject": "spores", "grammatical_role": "predicate",
                               "domain_ids": ["mycology", "geology"]}])
    assert plan["inventive_fallback"] is True
    assert diagnostic["fallback_domain_cues"] == ["mycology", "geology"]


def test_phase4u_source_and_identity_protection_remain_hard():
    plan, diagnostic = _build(
        phrase_config=PhraseReplacementConfig("evaluation"),
        first_pass={"crazyReplacement1Title": "Gravy Boat",
                    "crazyReplacement1Extract": "Lady Gravy boarded the gravy boat."},
        source_text="The source required a gravy boat.", names=["Lady Gravy"],
        concepts=[{"phrase": "gravy boat", "base": "gravy boat",
                   "target_bank": "nouns"}],
        lexical_penalties=Counter({"word:gravy": 50, "word:boat": 50}))
    assert plan is None
    assert diagnostic["rejected_targets"][0]["reason"] == "protected_name_or_location"
