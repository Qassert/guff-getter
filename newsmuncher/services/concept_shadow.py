"""Offline-only concept slate and prompt previews; never used by live rewriting."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import csv
from pathlib import Path
import random
import re

from newsmuncher.config import PROMPT_FILE, WORDS_DIR
from newsmuncher.services.comedy_concepts import (
    CATEGORIES, DEFAULT_CATEGORY_WEIGHTS, ComedyConceptGenerator, GeneratedConcept,
    normalised,
)
from newsmuncher.services.comedy_names import ComedyNameGenerator


SHADOW_CONCEPT_GUIDANCE = """SHADOW CONCEPT PREVIEW (NOT ACTIVE):
- Treat generated concepts as optional comic ingredients, not mandatory replacements.
- Prefer two to four strong concepts that fit the source naturally.
- Preserve each selected multiword concept as a coherent phrase.
- Do not splice several concepts together or force every concept into the story."""


@dataclass(frozen=True)
class ShadowSlate:
    strategy: str
    nouns: tuple[str, ...]
    animals: tuple[str, ...]
    concepts: tuple[GeneratedConcept, ...]
    prompt_preview: str
    approximate_tokens: int
    baseline_tokens: int
    guidance_tokens: int

    @property
    def token_difference(self):
        return self.approximate_tokens - self.baseline_tokens

    @property
    def candidate_token_difference(self):
        return self.token_difference - self.guidance_tokens


def _read_csv(name: str) -> list[str]:
    with (WORDS_DIR / name).open(encoding="utf-8", newline="") as source:
        return list(dict.fromkeys(value.strip() for row in csv.reader(source)
                                  for value in row if value.strip()))


def _sample(values: list[str], count: int, rng: random.Random) -> list[str]:
    return rng.sample(values, count)


def _allocation(count: int, seed: str) -> dict[str, int]:
    raw = {key: count * value / sum(DEFAULT_CATEGORY_WEIGHTS.values())
           for key, value in DEFAULT_CATEGORY_WEIGHTS.items()}
    result = {key: int(value) for key, value in raw.items()}
    remaining = count - sum(result.values())
    order = list(CATEGORIES)
    random.Random(f"{seed}:quota-ties").shuffle(order)
    order.sort(key=lambda key: -(raw[key] - result[key]))
    for key in order[:remaining]:
        result[key] += 1
    return result


def concept_slate(seed: str, count: int) -> list[GeneratedConcept]:
    """Generate an exact weighted slate while preferring distinct visible bases."""
    chosen = []
    used_bases = set()
    for category, needed in _allocation(count, seed).items():
        if not needed:
            continue
        candidates = ComedyConceptGenerator(f"{seed}:{category}").generate(
            max(needed * 5, 20), category=category
        )
        for candidate in candidates:
            base = normalised(candidate.base)
            if base in used_bases:
                continue
            chosen.append(candidate)
            used_bases.add(base)
            if sum(item.category == category for item in chosen) == needed:
                break
    if len(chosen) != count:
        raise RuntimeError("Could not assemble a base-diverse shadow concept slate")
    random.Random(seed).shuffle(chosen)
    return chosen


def _parts(values):
    return [values[index::3] for index in range(3)]


def _format_prompt(banks: dict[str, list[str]], include_guidance: bool) -> str:
    values = {}
    for key in ("noun", "adverb", "animal", "slang", "place", "name"):
        for index, part in enumerate(_parts(banks[key]), 1):
            values[f"{key}_words{index}"] = ", ".join(part)
    prompt = PROMPT_FILE.read_text(encoding="utf-8").format(**values)
    return f"{prompt}\n\n{SHADOW_CONCEPT_GUIDANCE}" if include_guidance else prompt


def approximate_tokens(text: str) -> int:
    """Conservative provider-free estimate; English prompts average ~4 chars/token."""
    return round(len(text.encode("utf-8")) / 4)


def build_shadow_slate(seed: str, strategy: str) -> ShadowSlate:
    if strategy not in {"A", "B", "C"}:
        raise ValueError("Shadow strategy must be A, B or C")
    rng = random.Random(seed)
    legacy_nouns = _sample(_read_csv("nouns.csv"), 10, rng)
    legacy_animals = _sample(_read_csv("animalsAndObjects.csv"), 10, rng)
    banks = {
        "noun": legacy_nouns,
        "animal": legacy_animals,
        "adverb": _sample(_read_csv("adverbs.csv"), 10, rng),
        "slang": _sample(_read_csv("slang.csv"), 10, rng),
        "place": _sample(_read_csv("places.csv"), 10, rng),
        "name": [item.name for item in ComedyNameGenerator(f"{seed}:names").generate(10)],
    }
    baseline = _format_prompt(banks, False)
    generated_count = {"A": 10, "B": 20, "C": 6}[strategy]
    concepts = concept_slate(f"{seed}:{strategy}", generated_count)
    phrases = [item.phrase for item in concepts]
    if strategy == "A":
        banks["noun"] = phrases
    elif strategy == "B":
        banks["noun"], banks["animal"] = phrases[:10], phrases[10:]
    else:
        banks["noun"] = legacy_nouns[:7] + phrases[:3]
        banks["animal"] = legacy_animals[:7] + phrases[3:]
    preview = _format_prompt(banks, True)
    return ShadowSlate(
        strategy, tuple(banks["noun"]), tuple(banks["animal"]), tuple(concepts),
        preview, approximate_tokens(preview), approximate_tokens(baseline),
        approximate_tokens("\n\n" + SHADOW_CONCEPT_GUIDANCE),
    )


class InMemoryConceptRegistry:
    """Offline lease/cooldown model for retries and concurrency evaluation."""

    def __init__(self, cooldown_days=30, offer_minutes=15, now=None):
        self.cooldown = timedelta(days=cooldown_days)
        self.offer_lifetime = timedelta(minutes=offer_minutes)
        self.now = now or (lambda: datetime.now(timezone.utc))
        self.records = {}
        self.offers = {}

    def offer(self, selection_key: str, count=6) -> list[GeneratedConcept]:
        if selection_key in self.offers:
            return self.offers[selection_key]
        now = self.now()
        queue = concept_slate(selection_key, max(count * 8, 48))
        selected = []
        selected_bases = set()
        active_bases = {
            normalised(record["base"])
            for record in self.records.values()
            if record.get("offered_by") not in (None, selection_key)
            and record.get("offer_until", now) > now
        }
        for item in queue:
            key = normalised(item.phrase)
            record = self.records.get(key, {})
            leased = record.get("offered_by") not in (None, selection_key)
            lease_live = record.get("offer_until", now) > now
            cooling = record.get("last_used_at", now - self.cooldown) > now - self.cooldown
            if ((leased and lease_live) or cooling or
                    normalised(item.base) in selected_bases or
                    normalised(item.base) in active_bases):
                continue
            record.update(offered_by=selection_key, offer_until=now + self.offer_lifetime,
                          base=item.base, version=item.generator_version)
            self.records[key] = record
            selected.append(item)
            selected_bases.add(normalised(item.base))
            if len(selected) == count:
                self.offers[selection_key] = selected
                return selected
        self.release(selection_key)
        raise RuntimeError("Insufficient shadow concepts outside cooldown")

    def accept(self, selection_key: str, title: str, body: str) -> list[str]:
        text = f"{title}\n{body}"
        used = []
        for item in self.offers.pop(selection_key, []):
            key = normalised(item.phrase)
            record = self.records[key]
            if re.search(rf"(?<!\w){re.escape(item.phrase)}(?!\w)", text, re.I):
                record.update(last_used_at=self.now(), use_count=record.get("use_count", 0) + 1)
                used.append(item.phrase)
            record.pop("offered_by", None)
            record.pop("offer_until", None)
        return used

    def release(self, selection_key: str):
        self.offers.pop(selection_key, None)
        for record in self.records.values():
            if record.get("offered_by") == selection_key:
                record.pop("offered_by", None)
                record.pop("offer_until", None)


def slate_metrics(slate: ShadowSlate) -> dict:
    return {
        "categories": dict(Counter(item.category for item in slate.concepts)),
        "intensities": dict(Counter(item.intensity for item in slate.concepts)),
        "repeated_bases": len(slate.concepts) - len({normalised(item.base) for item in slate.concepts}),
        "token_difference": slate.token_difference,
        "candidate_token_difference": slate.candidate_token_difference,
    }
