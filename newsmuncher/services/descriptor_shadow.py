"""Offline descriptor slates, prompt previews and lease simulations.

This module is deliberately absent from the live rewrite path.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import csv
from pathlib import Path
import random
import re

from newsmuncher.config import PROMPT_FILE, WORDS_DIR
from newsmuncher.services.comedy_descriptors import (
    ComedyDescriptorGenerator, GeneratedDescriptor, descriptor_slate, normalised,
)


SHADOW_DESCRIPTOR_GUIDANCE = """SHADOW DESCRIPTOR PREVIEW (NOT ACTIVE):
- Descriptors are optional comic ingredients; use roughly two to four where they fit naturally.
- Respect each descriptor's grammatical role and insertion guidance. Do not force predicate or clause forms before a noun.
- Prefer a mixture of short and developed descriptions, and avoid repeating the same comic mechanism.
- Do not combine several descriptors into one overloaded phrase or obscure the source event to accommodate them."""


@dataclass(frozen=True)
class DescriptorShadowSlate:
    strategy: str
    generated: tuple[GeneratedDescriptor, ...]
    legacy: tuple[str, ...]
    prompt_values: tuple[str, ...]
    prompt_preview: str
    descriptor_section: str
    approximate_tokens: int
    baseline_tokens: int
    guidance_tokens: int

    @property
    def token_difference(self):
        return self.approximate_tokens - self.baseline_tokens


def approximate_tokens(text: str) -> int:
    """Provider-free estimate used consistently with the concept shadow audit."""
    return round(len(text.encode("utf-8")) / 4)


def _legacy_descriptors(seed: str, count: int) -> list[str]:
    with (WORDS_DIR / "adverbs.csv").open(encoding="utf-8", newline="") as source:
        values = list(dict.fromkeys(value.strip() for row in csv.reader(source)
                                    for value in row if value.strip()))
    return random.Random(seed).sample(values, count)


def _parts(values):
    return [values[index::3] for index in range(3)]


def _annotated(item: GeneratedDescriptor) -> str:
    return f'{item.phrase} [role: {item.grammatical_role}; {item.insertion_rule}]'


def _format_prompt(descriptors: list[str], guidance: str = "") -> str:
    """Fill only the descriptor placeholders; mark every other bank for preview."""
    parts = _parts(descriptors)
    values = {
        **{f"adverb_words{index}": ", ".join(part) for index, part in enumerate(parts, 1)},
        **{f"{bank}_words{index}": f"<{bank.upper()}_{index}>"
           for bank in ("noun", "animal", "slang", "place", "name") for index in range(1, 4)},
    }
    prompt = PROMPT_FILE.read_text(encoding="utf-8").format(**values)
    return f"{prompt}\n\n{guidance}" if guidance else prompt


def build_shadow_slate(seed: str, strategy: str) -> DescriptorShadowSlate:
    """Preview A=10 generated, B=7 generated+3 legacy, C=6 generated+4 legacy."""
    generated_count = {"A": 10, "B": 7, "C": 6}.get(strategy)
    if generated_count is None:
        raise ValueError("Descriptor shadow strategy must be A, B or C")
    legacy_baseline = _legacy_descriptors(f"{seed}:baseline", 10)
    generated = descriptor_slate(f"{seed}:{strategy}", generated_count)
    legacy = _legacy_descriptors(f"{seed}:{strategy}:legacy", 10 - generated_count)
    prompt_values = [_annotated(item) for item in generated] + legacy
    random.Random(f"{seed}:{strategy}:order").shuffle(prompt_values)
    preview = _format_prompt(prompt_values, SHADOW_DESCRIPTOR_GUIDANCE)
    baseline = _format_prompt(legacy_baseline)
    section = "\n".join(
        f'- "{item.phrase}" — {item.grammatical_role}; {item.insertion_rule}; '
        f'{item.category}; intensity {item.intensity}; {item.comic_mechanism}; {item.word_count} words'
        for item in generated
    )
    return DescriptorShadowSlate(
        strategy, tuple(generated), tuple(legacy), tuple(prompt_values), preview, section,
        approximate_tokens(preview), approximate_tokens(baseline),
        approximate_tokens("\n\n" + SHADOW_DESCRIPTOR_GUIDANCE),
    )


class InMemoryDescriptorRegistry:
    """Offline model for a future phrase-level lease and accepted-use cooldown."""

    def __init__(self, cooldown_days=30, offer_minutes=15, now=None):
        self.cooldown = timedelta(days=cooldown_days)
        self.offer_lifetime = timedelta(minutes=offer_minutes)
        self.now = now or (lambda: datetime.now(timezone.utc))
        self.records = {}
        self.offers = {}

    def offer(self, rewrite_attempt_id: str, count=10) -> list[GeneratedDescriptor]:
        if rewrite_attempt_id in self.offers:
            return self.offers[rewrite_attempt_id]
        now = self.now()
        # Each rewrite identity expands its own deterministic generator space;
        # this is not a durable browser-session seed or a small shared pool.
        queue = ComedyDescriptorGenerator(f"{rewrite_attempt_id}:registry").generate(max(500, count * 50))
        selected, subjects = [], set()
        active_subjects = {
            normalised(record["subject"])
            for record in self.records.values()
            if record.get("offered_by") not in (None, rewrite_attempt_id)
            and record.get("offer_until", now) > now
        }
        for item in queue:
            key = normalised(item.phrase)
            record = self.records.get(key, {})
            other_live_lease = (record.get("offered_by") not in (None, rewrite_attempt_id)
                                and record.get("offer_until", now) > now)
            cooling = record.get("last_used_at", now - self.cooldown) > now - self.cooldown
            if (other_live_lease or cooling or normalised(item.subject) in subjects
                    or normalised(item.subject) in active_subjects):
                continue
            record.update(offered_by=rewrite_attempt_id, offer_until=now + self.offer_lifetime,
                          subject=item.subject, role=item.grammatical_role,
                          version=item.generator_version)
            self.records[key] = record
            selected.append(item); subjects.add(normalised(item.subject))
            if len(selected) == count:
                self.offers[rewrite_attempt_id] = selected
                return selected
        self.release(rewrite_attempt_id)
        raise RuntimeError("Insufficient shadow descriptors outside cooldown")

    def accept(self, rewrite_attempt_id: str, title: str, body: str) -> list[str]:
        text = f"{title}\n{body}"
        used = []
        for item in self.offers.pop(rewrite_attempt_id, []):
            key = normalised(item.phrase); record = self.records[key]
            # Exact phrase matching is intentionally conservative. Inflected or
            # paraphrased uses need future structured provider output or a local
            # grammatical matcher; guessing must not consume cooldown unfairly.
            if re.search(rf"(?<!\w){re.escape(item.phrase)}(?!\w)", text, re.I):
                record.update(last_used_at=self.now(), use_count=record.get("use_count", 0) + 1)
                used.append(item.phrase)
            record.pop("offered_by", None); record.pop("offer_until", None)
        return used

    def release(self, rewrite_attempt_id: str):
        self.offers.pop(rewrite_attempt_id, None)
        for record in self.records.values():
            if record.get("offered_by") == rewrite_attempt_id:
                record.pop("offered_by", None); record.pop("offer_until", None)


def slate_metrics(slate: DescriptorShadowSlate) -> dict:
    return {
        "categories": dict(Counter(item.category for item in slate.generated)),
        "intensities": dict(Counter(item.intensity for item in slate.generated)),
        "roles": dict(Counter(item.grammatical_role for item in slate.generated)),
        "mechanisms": dict(Counter(item.comic_mechanism for item in slate.generated)),
        "repeated_subjects": len(slate.generated) - len({normalised(item.subject) for item in slate.generated}),
        "short_descriptors": sum(item.word_count <= 8 for item in slate.generated),
        "token_difference": slate.token_difference,
    }
