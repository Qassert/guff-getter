from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from threading import Lock
from types import SimpleNamespace

from newsmuncher.services.lexical_exposure import LexicalExposureConfig
from newsmuncher.services.thematic_diversity import load_domains
from newsmuncher.services.thematic_ingredients import (
    ThemeIngredientConfig, ThemeIngredientMemory, ThemeSparkConfig,
    ThematicIngredientBuilder, load_thematic_seeds, partition_theme_sparks,
    theme_ingredient_event,
)
from scripts.diagnostics.build_thematic_seed_catalogue import build


class Collection:
    def __init__(self): self.docs = {}; self.lock = Lock()
    def find_one(self, query, projection=None):
        with self.lock: return deepcopy(self.docs.get(query["_id"]))
    def update_one(self, query, update, upsert=False):
        with self.lock:
            key = query["_id"]; doc = self.docs.get(key)
            rewrite = query.get("events.rewrite_id", {}).get("$ne")
            if doc and rewrite in {x["rewrite_id"] for x in doc.get("events", [])}:
                return SimpleNamespace(matched_count=0, upserted_id=None)
            inserted = doc is None
            if inserted:
                if not upsert: return SimpleNamespace(matched_count=0, upserted_id=None)
                doc = {"_id": key, **deepcopy(update.get("$setOnInsert", {}))}
                self.docs[key] = doc
            spec = update["$push"]["events"]
            doc.setdefault("events", []).extend(deepcopy(spec["$each"]))
            doc["events"] = doc["events"][spec["$slice"]:]
            return SimpleNamespace(matched_count=not inserted,
                                   upserted_id=key if inserted else None)


def domains():
    return list(load_domains())[:4]


def concept_plan():
    generated = []
    for target in ("nouns", "animals"):
        for index in range(10):
            generated.append({"phrase": f"premise {target} {index}", "base": f"base {target} {index}",
                              "target_bank": target, "comic_mechanism": "baseline",
                              "semantic_theme": "baseline", "score": 7.0})
    return {"label": "A", "prompt": list(generated), "generated": list(generated),
            "raw": [], "guidance": "", "counts": {"generated": 20, "raw": 0}}


def descriptors():
    roles = ("pre_noun", "adverbial", "predicate", "post_noun", "behavioural", "short_clause")
    return [{"phrase": f"descriptor {i}", "subject": f"subject {i}",
             "grammatical_role": roles[i % len(roles)], "category": "cheeky_british",
             "comic_mechanism": "baseline", "semantic_theme": "baseline",
             "premise_key": f"baseline:{i}", "generator_version": "test"}
            for i in range(10)]


def test_seed_catalogue_covers_every_domain_and_type():
    records = load_thematic_seeds()
    assert len(records) == 100
    assert {x["domain_id"] for x in records} == {x["id"] for x in load_domains()}
    assert all(set(x["seeds"]) == {"entities", "processes", "properties", "relationships"}
               for x in records)
    assert sum(len(values) for record in records for values in record["seeds"].values()) == 1600
    assert build()["domains"] == list(records)


def test_default_off_is_exact_noop_and_does_not_touch_memory(monkeypatch):
    monkeypatch.delenv("NEWSMUNCHER_THEME_INGREDIENTS", raising=False)
    config = ThemeIngredientConfig.from_environment(); original = concept_plan()
    builder = ThematicIngredientBuilder(domains(), "seed", config)
    assert builder.apply_concepts(original) is original
    prompt, tracked = builder.apply_descriptors(descriptors())
    assert prompt == tracked == descriptors()
    collection = Collection(); memory = ThemeIngredientMemory(collection, "pet", config)
    assert memory.load() == [] and not memory.record(theme_ingredient_event("r", []))
    assert collection.docs == {}


def test_cross_domain_concepts_preserve_counts_and_descriptor_roles():
    config = ThemeIngredientConfig("evaluation")
    builder = ThematicIngredientBuilder(domains(), "stable", config)
    plan = builder.apply_concepts(concept_plan())
    assert len(plan["prompt"]) == 20 and len(plan["generated"]) == 18
    assert len(plan["raw"]) == 2
    assert {x["target_bank"] for x in plan["raw"]} == {"nouns", "animals"}
    assert all(x["cross_domain"] and len(x["domain_ids"]) == 2 for x in plan["raw"])
    original = descriptors(); prompt, tracked = builder.apply_descriptors(original)
    assert len(prompt) == 10 and len(tracked) == 9
    assert sorted(x["grammatical_role"] for x in prompt) == sorted(
        x["grammatical_role"] for x in original)
    assert len(builder.selected) == 3


def test_unfamiliar_valid_combinations_bypass_subjective_baseline_ranking():
    builder = ThematicIngredientBuilder(domains(), "ranking", ThemeIngredientConfig("evaluation"))
    plan = builder.apply_concepts(concept_plan())
    assert builder.last_metrics["valid"] > builder.last_metrics["selected"]
    assert builder.last_metrics["ranking_losses"] > 0
    assert all(2 <= len(x["text"].split()) <= 8 for x in plan["raw"])


def test_seed_and_construction_penalties_decay_and_never_ban():
    config = ThemeIngredientConfig("evaluation", window=10)
    memory = ThemeIngredientMemory(Collection(), "pet", config)
    item = {"seed_ids": ["one"], "construction_id": "join", "domain_ids": ["d"]}
    memory.events = [theme_ingredient_event(str(i), [item]) for i in range(10)]
    first = memory.penalties(); memory.events = memory.events[-1:]; second = memory.penalties()
    assert first["seed:one"] > second["seed:one"] > 0
    builder = ThematicIngredientBuilder(domains(), "seed", config, first)
    assert builder.apply_concepts(concept_plan())["raw"]


def test_memory_is_persistent_isolated_bounded_duplicate_safe_and_concurrent():
    collection = Collection(); config = ThemeIngredientConfig("evaluation", window=10)
    item = {"seed_ids": ["one"], "construction_id": "join", "domain_ids": ["d"]}
    def append(index):
        return ThemeIngredientMemory(collection, "pet-a", config).record(
            theme_ingredient_event(f"r{index}", [item]))
    with ThreadPoolExecutor(max_workers=8) as pool:
        assert all(pool.map(append, range(20)))
    assert not append(19)
    restarted = ThemeIngredientMemory(collection, "pet-a", config); restarted.load()
    separate = ThemeIngredientMemory(collection, "pet-b", config); separate.load()
    assert len(restarted.events) == 10 and separate.events == []


def test_phase4m_and_phase4n_configuration_independence():
    assert ThemeIngredientConfig("evaluation").enabled
    assert not LexicalExposureConfig("off").enabled
    assert ThemeIngredientConfig("off").mode == "off"


def test_theme_sparks_are_default_off_and_require_phase4p_material(monkeypatch):
    monkeypatch.delenv("NEWSMUNCHER_THEME_SPARKS", raising=False)
    assert not ThemeSparkConfig.from_environment().enabled
    ordinary = concept_plan()["prompt"]
    concept_banks, descriptor_values, sparks = partition_theme_sparks(
        ordinary, descriptors(), enabled=True)
    assert not sparks
    assert sum(map(len, concept_banks.values())) == 20
    assert len(descriptor_values) == 10


def test_theme_sparks_change_presentation_without_changing_selection():
    config = ThemeIngredientConfig("evaluation")
    builder = ThematicIngredientBuilder(domains(), "same-selection", config)
    plan = builder.apply_concepts(concept_plan())
    offered, _ = builder.apply_descriptors(descriptors())
    selected_before = deepcopy(builder.selected)

    ordinary_banks, ordinary_descriptors, ordinary_sparks = partition_theme_sparks(
        plan["prompt"], offered, enabled=False)
    spark_banks, spark_descriptors, sparks = partition_theme_sparks(
        plan["prompt"], offered, enabled=True)

    assert builder.selected == selected_before
    assert ordinary_sparks == [] and len(sparks) == 3
    assert sum(map(len, ordinary_banks.values())) == 20
    assert sum(map(len, spark_banks.values())) == 18
    assert len(ordinary_descriptors) == 10 and len(spark_descriptors) == 9
    ordinary_text = set(sum(ordinary_banks.values(), []) + ordinary_descriptors)
    spark_text = set(sum(spark_banks.values(), []) + spark_descriptors +
                     [item["text"] for item in sparks])
    assert ordinary_text == spark_text


def test_compact_spark_block_is_adjacent_unique_and_preserves_counts(monkeypatch):
    from newsmuncher.utils import clean_data

    banks = {key: [f"{key}{i}" for i in range(10)] for key in
             ("nouns", "animals", "adverbs", "slang", "places", "names")}
    monkeypatch.setattr(clean_data, "load_random_words",
                        lambda count, excluded=(): {
                            key: ([] if key in excluded else list(values))
                            for key, values in banks.items()})
    monkeypatch.setattr(clean_data, "filter_word_banks", lambda prep, words: words)
    monkeypatch.setattr(clean_data, "preprocess_source", lambda entry: {"masked": entry})
    monkeypatch.setattr(clean_data, "replacement_guidance", lambda prep, words: "")
    template = "|".join("{" + bank + "_words" + str(part) + "}"
                        for bank in ("noun", "animal", "adverb", "slang", "place", "name")
                        for part in (1, 2, 3))
    concepts = {"nouns": [f"noun premise {i}" for i in range(9)],
                "animals": [f"animal premise {i}" for i in range(9)]}
    descriptors_without_spark = [f"descriptor {i}" for i in range(9)]
    sparks = [
        {"kind": "concept", "text": "fungal kettle using refraction"},
        {"kind": "concept", "text": "spore-adapted lunar badger"},
        {"kind": "descriptor", "text": "responsive to mycelium during erosion"},
    ]
    result = clean_data.prepare_prompt(
        {"title": "Source", "description": "", "extract": "Body"}, 10, template,
        concept_overrides=concepts, descriptor_overrides=descriptors_without_spark,
        theme_sparks=sparks)
    prompt = result["full_prompt"]
    assert prompt.index("Optional thematic sparks:") < prompt.index("Text to Transform:")
    assert "reinterpret them.\n\nText to Transform:" in prompt
    for item in sparks:
        assert prompt.count(item["text"]) == 1
    assert len(concepts["nouns"]) + 1 == 10
    assert len(concepts["animals"]) + 1 == 10
    assert len(descriptors_without_spark) + 1 == 10
