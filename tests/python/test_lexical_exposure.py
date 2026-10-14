from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import random
from threading import Lock

from newsmuncher.services.lexical_exposure import (
    LexicalExposureConfig, LexicalExposureMemory, build_lexical_event,
    exposure_keys, exposure_weight, text_penalty, weighted_choice,
)
from newsmuncher.services.comedy_concepts import ComedyConceptGenerator
from scripts.diagnostics.evaluate_vocabulary_phase4m import evaluate


class AtomicCollection:
    def __init__(self):
        self.docs = {}
        self.lock = Lock()

    def find_one(self, query, projection=None):
        with self.lock:
            doc = self.docs.get(query.get("_id"))
            return deepcopy(doc) if doc else None

    def update_one(self, query, update, upsert=False):
        with self.lock:
            key = query["_id"]
            doc = self.docs.get(key)
            rewrite_id = query.get("events.rewrite_id", {}).get("$ne")
            if doc and rewrite_id in {x["rewrite_id"] for x in doc.get("events", [])}:
                return type("Result", (), {"matched_count": 0, "upserted_id": None})()
            inserted = doc is None
            if inserted:
                doc = {"_id": key, **deepcopy(update.get("$setOnInsert", {}))}
                self.docs[key] = doc
            spec = update["$push"]["events"]
            doc.setdefault("events", []).extend(deepcopy(spec["$each"]))
            doc["events"] = doc["events"][spec["$slice"]:]
            return type("Result", (), {
                "matched_count": 0 if inserted else 1,
                "upserted_id": key if inserted else None,
            })()


def event(number, word="gravy"):
    return build_lexical_event(
        f"rewrite-{number}", "Source needs harbour",
        first_body=f"A municipal {word} inspection began.",
        final_body=f"The {word} inspector returned.",
        concepts=[{"phrase": f"constitutional {word} service", "base": f"{word} boat"}],
    )


def test_default_off_and_invalid_configuration(monkeypatch):
    monkeypatch.delenv("NEWSMUNCHER_LEXICAL_DIVERSITY", raising=False)
    assert not LexicalExposureConfig.from_environment().enabled
    monkeypatch.setenv("NEWSMUNCHER_LEXICAL_DIVERSITY", "evaluation")
    assert LexicalExposureConfig.from_environment().enabled
    monkeypatch.setenv("NEWSMUNCHER_LEXICAL_DIVERSITY", "ban-it")
    try:
        LexicalExposureConfig.from_environment()
        assert False
    except ValueError:
        pass


def test_unique_phrases_share_word_penalty_and_source_words_are_exempt():
    memory = LexicalExposureMemory(AtomicCollection(), "pet-a",
                                   LexicalExposureConfig("evaluation", 10, 4))
    memory.events = [event(1)]
    penalties = memory.penalties("Harbour gravy report")
    assert penalties["word:gravy"] == 0
    penalties = memory.penalties("Harbour report")
    assert penalties["word:gravy"] > 0
    assert text_penalty("intergalactic gravy tribunal", penalties) > 0
    assert text_penalty("intergalactic marmalade tribunal", penalties) < text_penalty(
        "intergalactic gravy tribunal", penalties)


def test_penalties_decay_and_words_recover_after_bounded_window():
    memory = LexicalExposureMemory(AtomicCollection(), "pet-a",
                                   LexicalExposureConfig("evaluation", 3, 4))
    memory.events = [event(1), event(2, "custard"), event(3, "marmalade")]
    assert memory.penalties()["word:gravy"] < memory.penalties()["word:marmalade"]
    memory.events = memory.events[1:] + [event(4, "turnip")]
    assert memory.penalties()["word:gravy"] == 0
    rng = random.Random(44)
    draws = Counter(weighted_choice(rng, ["gravy", "turnip"], {"word:gravy": 50})
                    for _ in range(5000))
    assert draws["gravy"] > 0 and draws["turnip"] > draws["gravy"]
    assert exposure_weight(10_000) >= 0.08


def test_memory_is_bounded_persistent_concurrent_and_scope_isolated():
    collection = AtomicCollection()
    config = LexicalExposureConfig("evaluation", 5, 4)
    first = LexicalExposureMemory(collection, "pet-a", config)
    with ThreadPoolExecutor(max_workers=8) as pool:
        outcomes = list(pool.map(lambda number: first.record(event(number)), range(30)))
    assert sum(outcomes) == 30
    restarted = LexicalExposureMemory(collection, "pet-a", config)
    assert len(restarted.load()) == 5
    assert len({x["rewrite_id"] for x in restarted.events}) == 5
    other = LexicalExposureMemory(collection, "pet-b", config)
    assert other.record(event(100, "pudding"))
    assert len(other.load()) == 1 and len(restarted.load()) == 5
    assert other.record_id != restarted.record_id
    assert not restarted.record(event(29))


def test_event_and_guidance_distinguish_offers_first_and_final():
    item = build_lexical_event(
        "one", "The source requires marmalade.",
        first_body="A gravy pump met marmalade.",
        final_body="The gravy committee retained marmalade.",
        concepts=[{"phrase": "ceremonial gravy pump", "base": "gravy pump"}],
        raw_ingredients=[{"text": "milk float"}],
    )
    assert "word:gravy" in item["offered"] and "word:milk" in item["offered"]
    assert "word:gravy" in item["first_pass"] and "word:gravy" in item["final"]
    assert "word:marmalade" not in item["first_pass"] + item["final"]
    memory = LexicalExposureMemory(AtomicCollection(), "pet", LexicalExposureConfig("evaluation"))
    memory.events = [item, item]
    guidance = memory.guidance()
    assert "soft preference" in guidance and "gravy" in guidance
    assert "remain allowed" in guidance


def test_exposure_keys_ignore_grammar_and_keep_multiword_identity():
    keys = exposure_keys("the municipal gravy inspection")
    assert "word:the" not in keys
    assert "word:municipal" in keys and "word:gravy" in keys
    assert "identity:municipal-gravy-inspection" in keys


def test_empty_penalties_preserve_generator_baseline_exactly():
    baseline = ComedyConceptGenerator("same", vocabulary_mode="evaluation").generate(25)
    disabled = ComedyConceptGenerator(
        "same", vocabulary_mode="evaluation", lexical_penalties={}).generate(25)
    assert baseline == disabled


def test_offline_comparison_improves_breadth_and_short_window_repetition():
    result = evaluate(30, "phase4m-test")
    before, after = result["baseline"], result["phase4m"]
    assert after["unique_words"] >= before["unique_words"]
    assert after["rolling_5_word_repetitions"] < before["rolling_5_word_repetitions"]
    assert after["category_distribution"] == before["category_distribution"]
    assert after["mean_quality_score"] >= before["mean_quality_score"] - .05
    assert after["exhaustion_events"] == 0
