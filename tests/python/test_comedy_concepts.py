import json
from pathlib import Path

import pytest

from newsmuncher.services.comedy_concepts import (
    CATEGORIES,
    ComedyConceptGenerator,
    ConceptGeneratorConfig,
    normalised,
)


def signature(items):
    return [(item.phrase, item.category, item.template, item.intensity) for item in items]


def test_seeded_generation_is_deterministic_and_other_seeds_vary():
    first = signature(ComedyConceptGenerator("same").generate(200))
    second = signature(ComedyConceptGenerator("same").generate(200))
    other = signature(ComedyConceptGenerator("different").generate(200))
    assert first == second
    assert first != other


def test_new_vocabulary_softly_blends_accessibility_tiers():
    from collections import Counter
    from newsmuncher.services.experimental_vocabulary import vocabulary_tiers

    tiers = vocabulary_tiers()
    generator = ComedyConceptGenerator("accessible-blend", new_vocabulary=True)
    ordinary = [generator._pick("domestic_objects") for _ in range(500)]
    counts = Counter(tiers.get(value.casefold(), "production") for value in ordinary)
    assert counts["production"] > counts["specialist"] > 0
    assert counts["familiar"] > counts["unusual"] > 0

    specialist_averse = [generator._pick(
        "domestic_objects", avoid_specialist=True) for _ in range(500)]
    avoided_count = sum(tiers.get(value.casefold()) == "specialist"
                        for value in specialist_averse)
    assert 0 < avoided_count < counts["specialist"]


def test_default_category_weights_are_exact_for_a_hundred():
    concepts = ComedyConceptGenerator(7).generate(100)
    counts = {category: sum(item.category == category for item in concepts)
              for category in CATEGORIES}
    assert counts == {
        "everyday_british": 15,
        "cheeky_object": 20,
        "absurd_invention": 20,
        "ridiculous_creature": 20,
        "bureaucratic_nonsense": 15,
        "emergency_equipment": 5,
        "ceremonial_object": 5,
    }


def test_categories_and_intensities_are_configurable():
    config = ConceptGeneratorConfig(
        category_weights={"ridiculous_creature": 1},
        intensity_weights={3: 1},
        maximum_theme_share=.20,
    )
    concepts = ComedyConceptGenerator(2, config=config).generate(60)
    assert {item.category for item in concepts} == {"ridiculous_creature"}
    assert {item.intensity for item in concepts} == {3}


@pytest.mark.parametrize("category,count", [
    ("everyday_british", 20), ("cheeky_object", 25),
    ("absurd_invention", 25), ("ridiculous_creature", 25),
    ("bureaucratic_nonsense", 20), ("emergency_equipment", 10),
    ("ceremonial_object", 10),
])
def test_editorial_samples_are_unique_grammatical_and_compatible(category, count):
    generator = ComedyConceptGenerator(f"sample:{category}")
    concepts = generator.generate(count, category=category)
    assert len({normalised(item.phrase) for item in concepts}) == count
    assert all(item.category == category for item in concepts)
    assert all(item.article in {"a", "an"} for item in concepts)
    assert all(item.grammatical_number == "singular" for item in concepts)
    assert all(item.countability == "countable" for item in concepts)
    assert all(2 <= len(item.phrase.split()) <= 8 for item in concepts)
    templates = {item["id"] for item in generator.data["templates"][category]}
    assert all(item.template in templates for item in concepts)
    assert all(normalised(item.base) in normalised(item.phrase) for item in concepts)


def test_safety_filter_rejects_blocked_repetition_and_invisible_base(tmp_path):
    source = Path("newsmuncher/resources/concepts/comedy_concept_components.json")
    data = json.loads(source.read_text())
    data["blocked_terms"].append("blockedword")
    path = tmp_path / "components.json"
    path.write_text(json.dumps(data))
    generator = ComedyConceptGenerator(1, components_path=path)
    good = generator.generate(1, category="everyday_british")[0]
    assert generator.rejection_reason(good) is None
    bad = good.__class__(**{**good.__dict__, "phrase": "blockedword kettle"})
    assert generator.rejection_reason(bad) == "blocked_term"
    bad = good.__class__(**{**good.__dict__, "phrase": "wobbly wobbly kettle", "base": "kettle"})
    assert generator.rejection_reason(bad) == "repeated_word"
    bad = good.__class__(**{**good.__dict__, "phrase": "polite hat", "base": "kettle"})
    assert generator.rejection_reason(bad) == "base_not_visible"


def test_large_audit_is_unique_balanced_and_does_not_exhaust():
    generator = ComedyConceptGenerator("five-thousand")
    concepts = generator.generate(5000)
    report = generator.last_diagnostics
    assert len({normalised(item.phrase) for item in concepts}) == 5000
    assert report.accepted == 5000 and not report.exhausted
    assert report.categories == {
        "everyday_british": 750, "cheeky_object": 1000,
        "absurd_invention": 1000, "ridiculous_creature": 1000,
        "bureaucratic_nonsense": 750, "emergency_equipment": 250,
        "ceremonial_object": 250,
    }
    assert report.intensities == {1: 1500, 2: 2250, 3: 1250}
    assert report.rejected_total > 0
    assert len(report.templates) >= 22
    assert max(report.bases.values()) <= 125
    assert len({item.base for item in concepts}) >= 850
    assert len({item.premise_key for item in concepts}) >= 875
    assert len({item.comic_mechanism for item in concepts}) >= 21
    assert len({item.semantic_theme for item in concepts}) >= 15


def test_small_component_space_reports_exhaustion(tmp_path):
    data = json.loads(Path(
        "newsmuncher/resources/concepts/comedy_concept_components.json"
    ).read_text())
    data["banks"]["domestic_objects"] = ["kettle"]
    for key in ("everyday_modifiers", "materials"):
        data["banks"][key] = {"1": ["wobbly"], "2": ["wobbly"], "3": ["wobbly"]}
    data["templates"]["everyday_british"] = [data["templates"]["everyday_british"][0]]
    path = tmp_path / "components.json"
    path.write_text(json.dumps(data))
    config = ConceptGeneratorConfig(
        category_weights={"everyday_british": 1},
        intensity_weights={1: 1},
        candidates_per_concept=3,
    )
    generator = ComedyConceptGenerator(1, config=config, components_path=path)
    with pytest.raises(ValueError, match="exhausted"):
        generator.generate(2)
    assert generator.last_diagnostics.exhausted

    partial_generator = ComedyConceptGenerator(
        1, config=config, components_path=path)
    partial = partial_generator.generate(2, allow_partial=True)
    assert len(partial) == 1
    assert partial_generator.last_diagnostics.exhausted


def test_existing_word_banks_and_live_claim_categories_are_not_part_of_generator():
    from newsmuncher.services.word_shuffle import BANK_FILES
    from newsmuncher.utils.clean_data import CSV_FILES
    assert CSV_FILES["nouns"] == "nouns.csv"
    assert BANK_FILES["nouns"] == "nouns.csv"
    assert "concepts" not in BANK_FILES


def test_known_bad_grammar_patterns_are_structurally_impossible():
    generator = ComedyConceptGenerator("grammar-regression")
    concepts = generator.generate(2000)
    phrases = [item.phrase.casefold() for item in concepts]
    assert not any("trained in close combat stepladder" in phrase for phrase in phrases)
    assert not any("capable of minor prophecy clipboard" in phrase for phrase in phrases)
    assert not any("operating beyond recommended thrust crumpet" in phrase for phrase in phrases)
    assert not any("response rapid-response" in phrase for phrase in phrases)
    assert not any("response portable" in phrase for phrase in phrases)
    assert not any("eating planets under diplomatic immunity crab" in phrase for phrase in phrases)
    assert not any("portable badger evacuation mobile toast rack" in phrase for phrase in phrases)
    assert not any("civic aggressive doormats commission" in phrase for phrase in phrases)
    assert not any("heavily unionised attack specialist newt" in phrase for phrase in phrases)
    assert not any("sacred royal emergency serving hatch" in phrase for phrase in phrases)


def test_creatures_and_ceremonial_objects_have_developed_premises():
    config = ConceptGeneratorConfig(maximum_theme_share=.10)
    generator = ComedyConceptGenerator("developed-premises", config=config)
    creatures = generator.generate(300, category="ridiculous_creature")
    ceremonial = ComedyConceptGenerator("ceremonial-premises", config=config).generate(
        300, category="ceremonial_object"
    )
    assert all(item.word_count >= 2 for item in creatures)
    assert all(item.word_count >= 3 for item in ceremonial)
    assert sum(item.word_count == 2 for item in creatures) / len(creatures) <= .20
    assert all(item.comic_mechanism for item in creatures + ceremonial)
    assert all(item.semantic_theme and item.premise_key.startswith(item.semantic_theme + ":")
               for item in creatures + ceremonial)


def test_animal_metadata_covers_creatures_and_animal_power_sources():
    concepts = ComedyConceptGenerator("animal-ingredients").generate(1000)
    creatures = [item for item in concepts if item.category == "ridiculous_creature"]
    powered = [item for item in concepts
               if item.animal_species and item.category == "absurd_invention"]
    assert creatures and all(item.animal_species == item.base for item in creatures)
    assert powered
    assert all(item.animal_species in item.phrase for item in powered)


def test_strong_two_word_creature_exception_remains_supported(tmp_path):
    source = Path("newsmuncher/resources/concepts/comedy_concept_components.json")
    data = json.loads(source.read_text())
    data["banks"]["compact_creature_actions"] = {
        "1": ["shoplifting"], "2": ["shoplifting"], "3": ["shoplifting"]
    }
    data["banks"]["creatures"] = ["badger"]
    data["templates"]["ridiculous_creature"] = [
        item for item in data["templates"]["ridiculous_creature"]
        if item["id"] == "strong_compact_creature"
    ]
    path = tmp_path / "components.json"
    path.write_text(json.dumps(data))
    generator = ComedyConceptGenerator(
        "short-exception",
        config=ConceptGeneratorConfig(maximum_theme_share=1),
        components_path=path,
    )
    concepts = generator.generate(1, category="ridiculous_creature")
    assert concepts[0].word_count == 2
    assert all(item.phrase.startswith("shoplifting ") for item in concepts)
