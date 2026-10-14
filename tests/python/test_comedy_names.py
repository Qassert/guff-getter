import json
from pathlib import Path

import pytest

from newsmuncher.services.comedy_names import (
    ComedyNameGenerator, NameGeneratorConfig, normalized,
)


def pairs(names):
    return [(item.category, item.name, item.recipe) for item in names]


def test_phase4e_name_expansion_is_opt_in_deterministic_and_preserves_mix():
    baseline = ComedyNameGenerator("phase4e").generate(100)
    first = ComedyNameGenerator("phase4e", expansion_mode="evaluation").generate(100)
    again = ComedyNameGenerator("phase4e", expansion_mode="evaluation").generate(100)
    assert [x.name for x in first] == [x.name for x in again]
    assert [x.category for x in first].count("cheeky") == 70
    assert [x.category for x in first].count("absurd") == 30
    assert any(token in x.surname_component for x in first
               for token in ("Quibble", "Thistle", "Crumple", "Nudge", "Pucker"))
    assert [x.name for x in first] != [x.name for x in baseline]


def test_seed_is_reproducible_and_different_seeds_vary():
    first = pairs(ComedyNameGenerator(seed="same").generate(80))
    second = pairs(ComedyNameGenerator(seed="same").generate(80))
    other = pairs(ComedyNameGenerator(seed="other").generate(80))
    assert first == second
    assert first != other


def test_default_batch_is_exactly_seventy_thirty_and_configurable():
    default = ComedyNameGenerator(seed=7).generate(100)
    assert [item.category for item in default].count("cheeky") == 70
    assert [item.category for item in default].count("absurd") == 30
    custom = ComedyNameGenerator(seed=7, config=NameGeneratorConfig(.25, .75)).generate(100)
    assert [item.category for item in custom].count("cheeky") == 25
    assert [item.category for item in custom].count("absurd") == 75


@pytest.mark.parametrize("style,count", [("cheeky", 100), ("absurd", 50), ("phonetic", 50)])
def test_requested_review_sets_are_unique_filtered_and_labelled(style, count):
    generator = ComedyNameGenerator(seed="review")
    names = generator.generate(count, style)
    fingerprints = [normalized(item.name) for item in names]
    assert len(fingerprints) == len(set(fingerprints)) == count
    assert all(item.category == style and generator.acceptable(item.name) for item in names)


def test_filter_rejects_known_names_slurs_and_unpronounceable_text(tmp_path):
    data = json.loads(Path("newsmuncher/resources/names/comedy_name_components.json").read_text())
    data["blocked_terms"] = ["blockedword"]
    path = tmp_path / "components.json"
    path.write_text(json.dumps(data))
    generator = ComedyNameGenerator(seed=1, components_path=path, known_names={"Existing Person"})
    assert not generator.acceptable("Existing Person")
    assert not generator.acceptable("Barry Blockedword")
    assert not generator.acceptable("Brrr Xqzzt")
    assert generator.acceptable("Percy Piddleworth")


def test_phonetic_construction_space_fails_instead_of_padding_weak_names():
    generator = ComedyNameGenerator(seed=1)
    available = len(generator._phonetic_candidates())
    with pytest.raises(ValueError, match="editorially approved phonetic constructions"):
        generator.generate(available + 1, "phonetic")


def test_phonetic_names_are_constructed_and_explain_the_spoken_joke():
    generator = ComedyNameGenerator(seed=1)
    names = generator.generate(50, "phonetic")
    assert all(item.generated for item in names)
    assert all(item.meaning and item.technique for item in names)
    assert len({item.meaning for item in names}) == 50


def test_familiar_internet_joke_names_are_explicitly_excluded():
    generator = ComedyNameGenerator(seed=1)
    for familiar in ("Ben Dover", "Phil McCracken", "Drew Peacock", "Justin Time",
                     "Hugh Jass", "Bill Board", "Cole Slaw", "Cliff Hanger"):
        assert generator.rejection_reason(familiar) == "familiar_joke"
    assert not ({normalized(item.name) for item in generator.generate(50, "phonetic")}
                & generator.familiar_jokes)


def test_phonetic_family_data_has_no_mislabelled_spoonerisms_or_fixed_name_list():
    generator = ComedyNameGenerator(seed=1)
    bank = generator.data["phonetic_generator"]
    assert "phonetic" not in generator.data
    assert len(bank["families"]) >= 12
    assert all("spoonerism" not in family["technique"] for family in bank["families"])


def test_future_real_name_mixture_is_configuration_only():
    config = NameGeneratorConfig(future_category_weights={
        "invented": .5, "celebrity": .25, "historical": .25,
    })
    assert config.future_category_weights["celebrity"] == .25
    assert set(config.future_category_weights) == {"invented", "celebrity", "historical"}


def test_gendered_honorifics_do_not_form_unsuitable_combinations():
    generator = ComedyNameGenerator(seed="honorific-audit")
    names = [item.name for item in generator.generate(500, "absurd")]
    feminine = set(generator.data["absurd"]["feminine_given_names"])
    masculine = set(generator.data["absurd"]["masculine_given_names"])
    assert not any(name.startswith(("Sir ", "Lord ")) and name.split()[1] in feminine for name in names)
    assert not any(name.startswith(("Lady ", "Dame ")) and name.split()[1] in masculine for name in names)
    assert not any(name.split()[0] in feminine and any(title in name for title in
                   ("Third Earl", "Baron of", "Viscount of", "Chairman of", "Master of"))
                   for name in names)
    assert not any(name.split()[0] in masculine and "Duchess of" in name for name in names)


def test_large_audit_is_unique_varied_and_reports_quality_rejections():
    generator = ComedyNameGenerator(seed="five-thousand")
    names = generator.generate(5000)
    report = generator.last_diagnostics
    assert len({normalized(item.name) for item in names}) == 5000
    assert report.accepted == 5000 and not report.exhausted
    assert report.rejected_total > 0
    assert len(report.templates) >= 10
    assert max(report.first_components.values()) <= 200  # Four-percent cap.
    assert max(report.surname_components.values()) <= 50  # One-percent cap.
    assert report.templates["given+constructed"] > 0
    assert report.templates["elaborate"] > 0


def test_legacy_bank_and_live_claim_categories_remain_unchanged():
    from newsmuncher.services.word_shuffle import BANK_FILES
    from newsmuncher.utils.clean_data import CSV_FILES
    assert CSV_FILES["names"] == "names.csv"
    assert "names" not in BANK_FILES
