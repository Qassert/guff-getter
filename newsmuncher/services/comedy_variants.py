"""Opt-in Phase 4K prompt experiments; variant A preserves the live baseline."""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import hashlib
import os
from pathlib import Path
import random
import re

from newsmuncher.config import WORDS_DIR
from newsmuncher.services.vocabulary_catalogue import eligible_concept_entries
from newsmuncher.services.word_shuffle import read_bank
from newsmuncher.services.lexical_exposure import exposure_weight, text_penalty
from newsmuncher.services.noun_exclusion import blocked_entries, NounExclusionExhausted


VARIANT_ENV = "NEWSMUNCHER_COMEDY_VARIANT"
VARIANT_COUNTS = {
    "A": (10, 0),   # generated per bank, raw per bank
    "B": (5, 5),
    "C": (5, 0),
    "D": (3, 5),
}
HYBRID_GUIDANCE = """HYBRID-SURPRISE RULES:
- Raw identities are optional creative sparks, not phrases to concatenate.
- Build at most one clear, source-relevant relationship around any chosen raw identity.
- Prefer an unexpected but understandable collision; do not merely list ingredients.
- Preserve the source story, readable prose, cheeky British voice and coherent jokes."""


@dataclass(frozen=True)
class ComedyVariantConfig:
    label: str = "A"

    @classmethod
    def from_environment(cls):
        label = os.getenv(VARIANT_ENV, "A").strip().upper()
        if label not in VARIANT_COUNTS:
            raise ValueError(f"{VARIANT_ENV} must be A, B, C or D")
        return cls(label)

    @property
    def experimental(self):
        return self.label != "A"


def _stable_random(seed):
    digest = hashlib.sha256(str(seed).encode("utf-8")).digest()
    return random.Random(int.from_bytes(digest[:8], "big"))


def _safe_legacy(value):
    value = re.sub(r"\s+", " ", str(value)).strip()
    return (value if 1 <= len(value.split()) <= 4 and len(value) <= 48
            and re.search(r"[A-Za-z]", value) else None)


def _balanced_generated(items, count, seed, lexical_penalties=None):
    """Sample the already quality-gated slate while spreading mechanisms."""
    rng = _stable_random(seed)
    shuffled = list(items)
    if lexical_penalties:
        reordered = []
        while shuffled:
            weights = [exposure_weight(text_penalty(
                item.get("phrase", ""), lexical_penalties)) for item in shuffled]
            value = rng.choices(shuffled, weights=weights, k=1)[0]
            reordered.append(value); shuffled.remove(value)
        shuffled = reordered
    else:
        rng.shuffle(shuffled)
    chosen, mechanisms = [], set()
    for prefer_new in (True, False):
        for item in shuffled:
            if item in chosen or (prefer_new and item.get("comic_mechanism") in mechanisms):
                continue
            chosen.append(item)
            mechanisms.add(item.get("comic_mechanism"))
            if len(chosen) == count:
                return chosen
    return chosen


@lru_cache(maxsize=4)
def _raw_pool(bank, catalogue_mode):
    if bank == "nouns":
        legacy_file, catalogue_family = "nouns.csv", "objects"
    else:
        legacy_file, catalogue_family = "animalsAndObjects.csv", "animals"
    legacy = []
    for text in read_bank(Path(WORDS_DIR) / legacy_file):
        if cleaned := _safe_legacy(text):
            legacy.append({
                "text": cleaned, "target_bank": bank,
                "source": "legacy_csv", "source_file": legacy_file,
                "family": "legacy_noun" if bank == "nouns" else "legacy_mixed_identity",
                "provenance": "existing NewsMuncher CSV; review before redistribution",
            })
    catalogue = [{
        "text": item["text"], "target_bank": bank,
        "source": "expanded_catalogue", "ingredient_id": item["id"],
        "family": item["family"], "semantic_domain": item["semantic_class"],
        "source_id": item["source_id"], "licence_id": item["licence_id"],
        "approval_status": item["approval_status"],
    } for item in eligible_concept_entries(catalogue_family, catalogue_mode)]
    return tuple(legacy), tuple(catalogue)


def _raw_selection(bank, count, seed, catalogue_mode, lexical_penalties=None,
                   noun_exclusions=(), source_text=""):
    cached_legacy, cached_catalogue = _raw_pool(bank, catalogue_mode)
    legacy, catalogue = list(cached_legacy), list(cached_catalogue)
    legacy = [item for item in legacy if not blocked_entries(
        item["text"], noun_exclusions, source_text)]
    catalogue = [item for item in catalogue if not blocked_entries(
        item["text"], noun_exclusions, source_text)]
    rng = _stable_random(f"{seed}:{bank}:raw")
    def reorder(values):
        if not lexical_penalties:
            rng.shuffle(values); return values
        ordered = []
        while values:
            weights = [exposure_weight(text_penalty(
                item["text"], lexical_penalties)) for item in values]
            selected = rng.choices(values, weights=weights, k=1)[0]
            ordered.append(selected); values.remove(selected)
        return ordered
    legacy, catalogue = reorder(legacy), reorder(catalogue)
    result = []
    # Alternate the two broad sources so the experiment actually tests both.
    queues = (legacy, catalogue) if rng.randrange(2) == 0 else (catalogue, legacy)
    while len(result) < count:
        progressed = False
        for queue in queues:
            while queue and any(x["text"].casefold() == queue[0]["text"].casefold()
                                for x in result):
                queue.pop(0)
            if queue and len(result) < count:
                result.append(queue.pop(0)); progressed = True
        if not progressed:
            raise NounExclusionExhausted(
                f"Not enough eligible raw {bank} ingredients. Please try MUNGE IT again.")
    return result


def build_variant(label, offered_concepts, seed, vocabulary_mode="off",
                  lexical_penalties=None, noun_exclusions=(), source_text=""):
    """Return prompt concepts, generated tracking subset and raw provenance."""
    label = label.upper()
    generated_count, raw_count = VARIANT_COUNTS[label]
    if label == "A":
        return {
            "label": label, "prompt": list(offered_concepts),
            "generated": list(offered_concepts), "raw": [],
            "guidance": "", "counts": {"generated": 20, "raw": 0},
        }
    catalogue_mode = "evaluation" if vocabulary_mode == "evaluation" else "reviewed"
    generated, raw = [], []
    for bank in ("nouns", "animals"):
        candidates = [item for item in offered_concepts if item.get("target_bank") == bank]
        generated.extend(_balanced_generated(
            candidates, generated_count, f"{seed}:{bank}", lexical_penalties))
        if raw_count:
            raw.extend(_raw_selection(
                bank, raw_count, seed, catalogue_mode, lexical_penalties,
                noun_exclusions, source_text))
    prompt = list(generated) + [
        {"phrase": item["text"], "target_bank": item["target_bank"], "raw": True}
        for item in raw
    ]
    return {
        "label": label, "prompt": prompt, "generated": generated, "raw": raw,
        "guidance": HYBRID_GUIDANCE if raw else "",
        "counts": {"generated": len(generated), "raw": len(raw)},
    }
