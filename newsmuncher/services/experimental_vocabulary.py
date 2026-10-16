"""Load locally accepted Phase A/B vocabulary for the opt-in experiment."""
from __future__ import annotations

from functools import lru_cache
import json
from pathlib import Path


ROOT = Path(__file__).parents[2]
CANDIDATE_ROOT = ROOT / "docs" / "candidates"


@lru_cache(maxsize=1)
def vocabulary_records():
    """Return locally accepted candidate records without changing review data."""
    records = []
    for folder in ("phase-a-everyday", "phase-b-scaled"):
        for path in sorted((CANDIDATE_ROOT / folder).glob("batch-*.json")):
            records.extend(
                item for item in json.loads(path.read_text(encoding="utf-8"))["candidates"]
                if item.get("candidate_status") == "candidate_unreviewed"
            )

    pilot = json.loads(
        (CANDIDATE_ROOT / "thematic-vocabulary-phase-b-pilot.json").read_text(
            encoding="utf-8"))
    accepted_ids = set(json.loads(
        (CANDIDATE_ROOT / "phase-b-pilot-accepted.json").read_text(
            encoding="utf-8"))["candidate_ids"])
    records.extend(item for item in pilot["candidates"] if item["id"] in accepted_ids)

    return tuple(records)


@lru_cache(maxsize=1)
def vocabulary_tiers() -> dict[str, str]:
    """Map candidate text to its broad accessibility tier."""
    tiers = {}
    for item in vocabulary_records():
        familiarity = item.get("familiarity")
        tiers[item["text"].casefold()] = (
            "familiar" if familiarity == "familiar" else
            "unusual" if familiarity == "unusual_but_imaginable" else
            "specialist"
        )
    return tiers


@lru_cache(maxsize=1)
def concept_banks() -> dict[str, tuple[str, ...]]:
    """Return grammar-safe concept-bank additions; never changes review data."""
    records = vocabulary_records()
    entities = [item for item in records if item.get("kind") == "entity"]
    topics = [item for item in records if item.get("kind") in {
        "entity", "process", "relationship",
    }]
    def texts(items):
        return tuple(dict.fromkeys(item["text"] for item in items))

    entity_texts, topic_texts = texts(entities), texts(topics)
    return {
        # Too few passed entries are unambiguously whole animal species. Keep
        # the established reviewed creature bank for the hard animal quota.
        "creatures": (),
        "domestic_objects": entity_texts,
        "cheeky_objects": entity_texts,
        "devices": entity_texts,
        "emergency_devices": entity_texts,
        "ceremonial_objects": entity_texts,
        "bureau_topics": entity_texts,
        "bureaucratic_disputes": topic_texts,
        "emergency_purposes": topic_texts,
        "ceremonial_functions": topic_texts,
        "ceremonial_purposes": topic_texts,
        "ceremonial_failures": topic_texts,
    }
