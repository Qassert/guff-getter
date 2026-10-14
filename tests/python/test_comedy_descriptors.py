import json
from pathlib import Path

import pytest

from newsmuncher.services.comedy_descriptors import (
    CATEGORIES, ROLES, ComedyDescriptorGenerator, DescriptorGeneratorConfig, normalised,
)


def signature(items):
    return [(item.phrase, item.category, item.grammatical_role, item.intensity) for item in items]


def test_phase4e_descriptor_expansion_is_opt_in_and_adds_mechanisms():
    baseline = ComedyDescriptorGenerator("phase4e").generate(200)
    expanded = ComedyDescriptorGenerator("phase4e", expansion_mode="evaluation").generate(200)
    added = {"peculiar_habit", "romantic_complication", "questionable_condition",
             "bizarre_qualification", "workplace_incompetence", "irrational_fear",
             "peculiar_ambition", "personal_scandal", "unusual_hobby", "social_rivalry",
             "personal_legal_restriction", "unlikely_achievement"}
    assert not ({x.comic_mechanism for x in baseline} & added)
    assert {x.comic_mechanism for x in expanded} & added
    assert len({x.grammatical_role for x in expanded}) == 6


def test_seeded_generation_is_deterministic_and_varies_by_seed():
    assert signature(ComedyDescriptorGenerator("same").generate(200)) == signature(ComedyDescriptorGenerator("same").generate(200))
    assert signature(ComedyDescriptorGenerator("same").generate(200)) != signature(ComedyDescriptorGenerator("other").generate(200))


def test_default_category_and_intensity_mix_is_exact():
    items = ComedyDescriptorGenerator(1).generate(100)
    assert {key: sum(item.category == key for item in items) for key in CATEGORIES} == {
        "cheeky_british": 70, "broader_absurdity": 30,
    }
    assert {key: sum(item.intensity == key for item in items) for key in (1, 2, 3)} == {1:30, 2:45, 3:25}


def test_configuration_controls_category_and_intensity():
    config = DescriptorGeneratorConfig(category_weights={"broader_absurdity": 1}, intensity_weights={3: 1})
    items = ComedyDescriptorGenerator(2, config).generate(50)
    assert {item.category for item in items} == {"broader_absurdity"}
    assert {item.intensity for item in items} == {3}


def test_metadata_roles_safety_and_uniqueness():
    generator = ComedyDescriptorGenerator("metadata")
    items = generator.generate(500)
    assert len({normalised(item.phrase) for item in items}) == 500
    assert len({item.grammatical_role for item in items}) >= 5
    assert all(item.grammatical_role in ROLES and item.comic_mechanism for item in items)
    assert all(item.generator_version == "comedy-descriptors-v3-diversity" for item in items)
    assert all(2 <= item.word_count <= 16 and item.quality_score >= 6 for item in items)
    assert all(item.insertion_rule and item.usage_example.endswith(".") for item in items)
    assert all(item.semantic_theme and item.premise_key.startswith(item.semantic_theme + ":")
               for item in items)
    assert all(generator.rejection_reason(item) is None for item in items)


def test_grammar_roles_keep_context_dependent_phrases_out_of_pre_noun_slot():
    items = ComedyDescriptorGenerator("grammar").generate(1000)
    pre_noun = [item.phrase for item in items if item.grammatical_role == "pre_noun"]
    assert pre_noun and all(not phrase.startswith(("furious about", "legally required", "medically advised", "banned from")) for phrase in pre_noun)
    assert all(item.grammatical_role != "pre_noun" for item in items if " about " in item.phrase)


def test_role_examples_use_the_required_grammatical_placement():
    items = ComedyDescriptorGenerator("role-examples").generate(1500)
    by_role = {role: next(item for item in items if item.grammatical_role == role) for role in ROLES}
    assert by_role["pre_noun"].usage_example.startswith("The " + by_role["pre_noun"].phrase)
    assert f" is {by_role['predicate'].phrase}." in by_role["predicate"].usage_example
    for role in ("post_noun", "behavioural"):
        assert f", {by_role[role].phrase}," in by_role[role].usage_example
    assert by_role["adverbial"].usage_example.endswith(by_role["adverbial"].phrase + ".")
    assert by_role["short_clause"].phrase.casefold() in by_role["short_clause"].usage_example.casefold()
    assert all(item.usage_example[:1].isupper() for item in items)


def test_pre_noun_comic_contradictions_remain_attributive_phrases():
    items = ComedyDescriptorGenerator("pre-noun-grammar").generate(1200)
    contradictions = [item for item in items if item.template == "incompetence_manner"]
    assert contradictions
    assert all(len(item.phrase.split()) == 2 for item in contradictions)
    assert all(item.usage_example.startswith("The ") for item in contradictions)


def test_weak_phase3a_premises_are_no_longer_generated():
    phrases = {item.phrase for item in ComedyDescriptorGenerator("editorial-floor").generate(3000)}
    assert "chronically underqualified" not in phrases
    assert "furious about a badly chaired meeting" not in phrases
    assert "certain they could inspect a nuclear submarine" not in phrases


def test_blocked_and_awkward_candidates_are_rejected():
    generator = ComedyDescriptorGenerator(3)
    good = generator.generate(1)[0]
    blocked = good.__class__(**{**good.__dict__, "phrase":"racial slur clerk"})
    awkward = good.__class__(**{**good.__dict__, "phrase":"required to to whisper"})
    assert generator.rejection_reason(blocked) == "blocked_term"
    assert generator.rejection_reason(awkward) == "awkward_join"


def test_large_audit_is_unique_balanced_diverse_and_bounded():
    generator = ComedyDescriptorGenerator("five-thousand")
    items = generator.generate(5000)
    report = generator.last_diagnostics
    assert len({normalised(item.phrase) for item in items}) == 5000
    assert report.accepted == 5000 and not report.exhausted
    assert report.categories == {"cheeky_british":3500, "broader_absurdity":1500}
    assert report.intensities == {1:1500, 2:2250, 3:1250}
    assert set(report.roles) == set(ROLES)
    assert len(report.templates) == 24 and report.rejected_total > 0
    assert report.proposed == report.rejected_total + report.eligible
    assert report.eligible == report.accepted + report.unselected


def test_tiny_component_space_exhausts_cleanly(tmp_path):
    data = json.loads(Path("newsmuncher/resources/descriptors/comedy_descriptor_components.json").read_text())
    data["banks"]["comic_domain"] = ["emotionally"]
    data["banks"]["comic_state"] = ["double-parked"]
    data["templates"] = [data["templates"][0]]
    path = tmp_path / "tiny.json"; path.write_text(json.dumps(data))
    config = DescriptorGeneratorConfig(category_weights={"cheeky_british":1}, intensity_weights={1:1}, candidates_per_descriptor=2)
    generator = ComedyDescriptorGenerator(1, config, path)
    with pytest.raises(ValueError, match="exhausted"):
        generator.generate(2)
    assert generator.last_diagnostics.exhausted


def test_generator_is_not_wired_into_live_rewrite():
    from newsmuncher.utils import clean_data
    assert "comedy_descriptors" not in Path(clean_data.__file__).read_text()


def test_phase4f_slate_sampling_broadens_quality_filtered_evaluation_output():
    from newsmuncher.services.comedy_descriptors import descriptor_slate
    old, improved = [], []
    for number in range(20):
        seed = f"phase4f-regression:{number}"
        old.extend(x.phrase for x in descriptor_slate(seed, expansion_mode="phase4e"))
        improved.extend(x.phrase for x in descriptor_slate(seed, expansion_mode="evaluation"))
    assert len(set(improved)) > len(set(old))
