import copy

from newsmuncher.services.vocabulary_catalogue import (
    OfflineVocabularySelector, VocabularyCatalogue, eligible_concept_entries,
)
from newsmuncher.services.comedy_concepts import animal_vocabulary
from scripts.diagnostics.evaluate_vocabulary_foundation import run
from scripts.diagnostics.evaluate_vocabulary_phase4c import phase4b_catalogue, run as run_phase4c
from scripts.diagnostics.evaluate_vocabulary_phase4d import run as run_phase4d


def test_catalogue_has_six_valid_offline_families():
    catalogue = VocabularyCatalogue.load()
    assert set(catalogue.by_family) == {"animals", "objects", "descriptors", "names", "slang", "places"}
    assert all(catalogue.by_family.values())
    assert not [issue for issue in catalogue.validate() if issue.level == "error"]


def test_animal_selection_policy_rejects_parts_and_roles_but_keeps_species():
    values = {item["text"] for item in
              eligible_concept_entries("animals", "evaluation")}
    assert not ({"ala", "pad", "paw", "dam", "egg", "pet",
                 "work animal", "roe"} & values)
    assert {"olm", "kea", "daw"} <= values
    assert {"tapir", "pangolin", "gibbon", "gorilla", "capybara",
            "wombat", "meerkat", "flamingo"} <= set(animal_vocabulary())


def test_selection_is_deterministic_grammar_compatible_and_avoids_recent_items():
    catalogue = VocabularyCatalogue.load()
    first = OfflineVocabularySelector(catalogue, "fixed").select("descriptors", 10, roles={"predicate"})
    again = OfflineVocabularySelector(catalogue, "fixed").select("descriptors", 10, roles={"predicate"})
    assert [item["id"] for item in first] == [item["id"] for item in again]
    assert all("predicate" in set(item["grammar"].get("roles", (item["grammar"].get("role"),))) for item in first)
    fresh = OfflineVocabularySelector(catalogue, "fixed", [item["id"] for item in first]).select(
        "descriptors", 10, roles={"predicate"})
    assert not ({item["id"] for item in first} & {item["id"] for item in fresh})


def test_validator_rejects_duplicate_unsupported_or_discriminatory_entries():
    catalogue = VocabularyCatalogue.load()
    payload = copy.deepcopy(catalogue.payload)
    bad = copy.deepcopy(payload["ingredients"][0])
    bad["id"] = "bad"
    bad["licence_id"] = "unknown"
    bad["text"] = "chinaman"
    payload["ingredients"].append(bad)
    codes = {issue.code for issue in VocabularyCatalogue(payload).validate() if issue.level == "error"}
    assert {"unsupported_licence", "discriminatory_content"} <= codes


def test_small_audit_is_offline_and_covers_all_families():
    result = run("test", 10)
    assert set(result["comparison"]) == {"animals", "objects", "descriptors", "names", "slang", "places"}
    assert result["database_operations"] == result["network_operations"] == result["provider_operations"] == 0


def test_phase4c_expands_every_family_without_relabelling_phase4b():
    catalogue = VocabularyCatalogue.load()
    baseline = phase4b_catalogue(catalogue)
    expected = {"animals": 134, "objects": 508, "descriptors": 705,
                "names": 492, "slang": 30, "places": 58}
    assert {family: len(baseline.by_family[family]) for family in expected} == expected
    assert all(len(catalogue.by_family[family]) > count for family, count in expected.items())
    assert len(catalogue.by_family["animals"]) >= 1000
    assert len(catalogue.by_family["objects"]) >= 2000
    assert len(catalogue.by_family["descriptors"]) >= 2000
    assert all(entry["approval_status"] == "machine_checked"
               for entry in catalogue.entries if entry["source_id"] in {"oewn-2025", "phase4c-original"})


def test_phase4c_audit_distinguishes_offered_from_used_and_is_offline():
    result = run_phase4c("test", 10)
    assert all(result["phase4c"][family]["offers"] > result["phase4c"][family]["used"]
               for family in result["phase4c"])
    assert result["database_operations"] == result["provider_operations"] == result["network_operations_during_audit"] == 0


def test_phase4d_audit_distinguishes_offer_prompt_and_mock_final():
    result = run_phase4d(rewrites=3)
    for mode in ("existing", "expanded_evaluation"):
        assert result[mode]["offered"]["total"] == 60
        assert result[mode]["passed_to_prompt"]["total"] == 60
        assert result[mode]["appeared_in_mock_final"]["total"] == 9
