"""Experimental-only source-led comedy generation and recent-premise memory."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
import hashlib
import json
import os
from pathlib import Path
import random
import re

from pymongo.errors import DuplicateKeyError

from newsmuncher.services.noun_exclusion import blocked_entries
from newsmuncher.utils.source_preprocessing import (
    preserve_source_text, preprocess_radical_source,
)


RADICAL_PROMPT_PATH = (
    Path(__file__).parents[1] / "resources" / "prompts" / "rewrite_radical.txt"
)
RADICAL_HISTORY_WINDOW = 12
RADICAL_GUIDANCE_LIMIT = 5
RADICAL_CONTROLLING_PREMISE_ENV = "NEWSMUNCHER_RADICAL_CONTROLLING_PREMISE"
RADICAL_CONTROLLING_PREMISE_BATCH = "codex-session-2026-10-18"
RADICAL_CONTROLLING_PREMISE_EXCLUDED_BANKS = frozenset({
    "everyday_post_modifiers", "cheeky_post_modifiers",
})
STRUCTURAL_PLACEHOLDER_RE = re.compile(
    r"\[(?:PERSON|PLACE|ORGANIZATION|FACT|OBJECT|PHRASE|DESCRIPTION)_\d+\]",
    re.IGNORECASE,
)


class RadicalPlaceholderError(ValueError):
    """RADICAL output still contains a structural source placeholder."""


@dataclass(frozen=True)
class RadicalControllingPremiseConfig:
    """Default-off switch for the isolated controlling-premise experiment."""

    mode: str = "off"

    @classmethod
    def from_environment(cls):
        return cls(os.getenv(RADICAL_CONTROLLING_PREMISE_ENV, "off").strip().lower())

    def __post_init__(self):
        if self.mode not in {"off", "evaluation"}:
            raise ValueError(
                f"{RADICAL_CONTROLLING_PREMISE_ENV} must be off or evaluation")

    @property
    def enabled(self):
        return self.mode == "evaluation"


@dataclass(frozen=True)
class RadicalControllingPremise:
    identifier: str
    text: str
    mechanism_family: str
    bank: str
    intensity: int


def radical_placeholder_map(preprocessing):
    """Return one stable original reference for every masked source identity."""
    choices = {}
    for record in (preprocessing or {}).get("records", ()):
        placeholder = str(record.get("placeholder", "")).upper()
        literal = str(record.get("literal", "")).strip()
        if not placeholder or not literal:
            continue
        # Aliased surname references share a placeholder with the full name.
        # The longest source literal is the stable reference for every mention.
        if len(literal) > len(choices.get(placeholder, "")):
            choices[placeholder] = literal
    return choices


def restore_radical_placeholders(result, preprocessing):
    """Restore masked source identities and reject unknown structural tokens."""
    restored = dict(result)
    replacements = radical_placeholder_map(preprocessing)
    restored_count = 0
    unresolved = set()
    for key in ("title", "extract", "crazyReplacement1Title",
                "crazyReplacement1Extract"):
        value = restored.get(key)
        if not isinstance(value, str):
            continue

        def replace(match):
            nonlocal restored_count
            placeholder = match.group(0).upper()
            literal = replacements.get(placeholder)
            if literal is None:
                unresolved.add(placeholder)
                return match.group(0)
            restored_count += 1
            return literal

        restored[key] = STRUCTURAL_PLACEHOLDER_RE.sub(replace, value)
        unresolved.update(
            match.group(0).upper()
            for match in STRUCTURAL_PLACEHOLDER_RE.finditer(restored[key]))
    if unresolved:
        raise RadicalPlaceholderError(
            "RADICAL rewrite contained unresolved source placeholders: "
            + ", ".join(sorted(unresolved))
        )
    return restored, restored_count
WORD_RE = re.compile(r"[a-z]+(?:['-][a-z]+)?", re.I)
STOP_WORDS = frozenset({
    "a", "an", "and", "as", "at", "by", "for", "from", "in", "into", "of",
    "on", "or", "the", "their", "to", "under", "with", "without", "its",
})

# Each pattern retains the distinctive target of a relationship. Reusing a
# grammatical mechanism with a different target therefore remains available.
PREMISE_PATTERNS = (
    ("transformation", re.compile(
        r"\b(?:became|becomes|becoming|turned into|turning into|transformed into)\s+"
        r"(?P<target>[^,.;:!?]{2,70})", re.I)),
    ("mistaken_identity", re.compile(
        r"\b(?:mistaken for|confused with|masquerading as|disguised as)\s+"
        r"(?P<target>[^,.;:!?]{2,70})", re.I)),
    ("category_mistake", re.compile(
        r"\b(?:declared|classified|registered|treated)\s+(?:it |him |her |them )?as\s+"
        r"(?P<target>[^,.;:!?]{2,70})", re.I)),
    ("invented_relationship", re.compile(
        r"\b(?:married to|engaged to|adopted by|owned by|renting from|sharing custody with)\s+"
        r"(?P<target>[^,.;:!?]{2,70})", re.I)),
    ("physical_property", re.compile(
        r"\b(?:made of|filled with|containing|constructed from|coated in)\s+"
        r"(?P<target>[^,.;:!?]{2,70})", re.I)),
    ("refusal_target", re.compile(
        r"\b(?:refus\w*|reject\w*)\s+(?:to\s+)?(?:recognise|acknowledge|accept|obey)?\s*"
        r"(?P<target>[^,.;:!?]{2,70})", re.I)),
)


def _normal_target(value: str) -> str:
    value = re.split(
        r"\b(?:and|but)\s+(?:was|is|were|became|becomes|married|mistaken|turned|had)\b|"
        r"\b(?:made of|filled with|containing|constructed from|coated in)\b",
        value, maxsplit=1, flags=re.I)[0]
    words = [word.casefold().strip("-' ") for word in WORD_RE.findall(value)]
    words = [word for word in words if word not in STOP_WORDS]
    # A bounded content signature recognises light paraphrases without turning
    # a whole mechanism such as "refusal" into a prohibited joke family.
    return " ".join(words[:5])


def detect_radical_premises(text: str, source_text: str = "") -> list[dict]:
    """Extract conservative relationship-plus-target semantic joke identities."""
    source_keys = {item["key"] for item in detect_radical_premises(source_text)} \
        if source_text else set()
    found = {}
    for family, pattern in PREMISE_PATTERNS:
        for match in pattern.finditer(str(text or "")):
            target = _normal_target(match.group("target"))
            if not target or len(target) < 4:
                continue
            key = f"{family}:{target}"
            if key in source_keys:
                continue
            found[key] = {
                "key": key,
                "family": family,
                "target": target,
                "label": f"{family.replace('_', ' ')} involving {target}",
            }
    return list(found.values())


@dataclass(frozen=True)
class RadicalPremiseConfig:
    history_articles: int = RADICAL_HISTORY_WINDOW
    guidance_items: int = RADICAL_GUIDANCE_LIMIT

    def __post_init__(self):
        if self.history_articles < 1 or not 1 <= self.guidance_items <= 8:
            raise ValueError("Invalid RADICAL MODE premise-memory limits")


class RadicalPremiseMemory:
    """Per-pet bounded soft memory stored beside, but apart from, noun history."""

    def __init__(self, collection, scope, config=None, now=None):
        self.collection = collection
        self.config = config or RadicalPremiseConfig()
        self.now = now or (lambda: datetime.now(timezone.utc))
        digest = hashlib.sha256(str(scope).encode("utf-8")).hexdigest()[:24]
        self.record_id = "radical-premises:" + digest
        self.events = []
        self.last_metrics = {}

    def load(self):
        doc = self.collection.find_one({"_id": self.record_id}) or {}
        self.events = list(doc.get("events", ()))[-self.config.history_articles:]
        self.last_metrics = {"reads": 1, "recent_events": len(self.events)}
        return self.events

    def guidance(self, source_text=""):
        source_keys = {item["key"] for item in detect_radical_premises(source_text)}
        premises = []
        for event in reversed(self.events):
            for item in reversed(event.get("premises", ())):
                if item.get("key") not in source_keys and item.get("key") not in {
                        value.get("key") for value in premises}:
                    premises.append(item)
                if len(premises) >= self.config.guidance_items:
                    break
            if len(premises) >= self.config.guidance_items:
                break
        if not premises:
            return ""
        lines = "\n".join(f"- {item['label']}" for item in premises)
        return (
            "RECENT RADICAL PREMISES — avoid these specific idea-and-target pairs or "
            "close paraphrases. Their broad comic mechanisms remain available with genuinely "
            f"different targets:\n{lines}"
        )

    def accept(self, rewrite_id, title, body, source_text=""):
        premises = detect_radical_premises(f"{title}\n{body}", source_text)
        event = {"rewrite_id": str(rewrite_id), "premises": premises,
                 "recorded_at": self.now()}
        try:
            result = self.collection.update_one(
                {"_id": self.record_id,
                 "events.rewrite_id": {"$ne": str(rewrite_id)}},
                {"$setOnInsert": {"version": 1,
                                   "record_type": "radical_premise_memory"},
                 "$push": {"events": {"$each": [event],
                                       "$slice": -self.config.history_articles}}},
                upsert=True,
            )
        except DuplicateKeyError:
            # A concurrent first writer created the per-pet document. Retry the
            # same bounded atomic push without upsert; duplicate rewrite IDs
            # still fail the query and remain idempotent.
            result = self.collection.update_one(
                {"_id": self.record_id,
                 "events.rewrite_id": {"$ne": str(rewrite_id)}},
                {"$push": {"events": {"$each": [event],
                                       "$slice": -self.config.history_articles}}},
            )
        if not result or not (result.matched_count or result.upserted_id is not None):
            self.last_metrics = {"writes": 0, "accepted": 0, "duplicate": True}
            return []
        self.events = (self.events + [event])[-self.config.history_articles:]
        self.last_metrics = {"writes": 1, "accepted": len(premises), "duplicate": False}
        return [item["key"] for item in premises]


@lru_cache(maxsize=1)
def _inspiration_pool() -> tuple[str, ...]:
    """Small visual vocabulary pool; it never forms mandatory templates."""
    root = Path(__file__).parents[1] / "resources" / "concepts"
    data = json.loads((root / "comedy_concept_components.json").read_text(encoding="utf-8"))
    values = []
    for bank in ("domestic_objects", "devices", "cheeky_objects", "creatures",
                 "ceremonial_objects", "emergency_devices"):
        values.extend(data["banks"][bank])
    return tuple(dict.fromkeys(values))


def radical_inspirations(seed, noun_exclusions=(), source_text="", count=6):
    rng = random.Random(f"radical:{seed}")
    eligible = [value for value in _inspiration_pool()
                if not blocked_entries(value, noun_exclusions, source_text)]
    return rng.sample(eligible, min(count, len(eligible)))


@lru_cache(maxsize=1)
def radical_controlling_premises() -> tuple[RadicalControllingPremise, ...]:
    """Load the existing accepted premise batch with stable local identifiers."""
    root = Path(__file__).parents[1] / "resources" / "concepts"
    data = json.loads((root / "comedy_concept_components.json").read_text(
        encoding="utf-8"))
    batch = next(
        (item for item in data.get("editorial_batches", ())
         if item.get("id") == RADICAL_CONTROLLING_PREMISE_BATCH),
        None,
    )
    if batch is None:
        raise ValueError(
            f"Missing controlling-premise batch {RADICAL_CONTROLLING_PREMISE_BATCH}")
    premises = []
    for index, item in enumerate(batch.get("premises", ())):
        text = str(item.get("text", "")).strip()
        family = str(item.get("mechanism_family", "")).strip()
        bank = str(item.get("bank", "")).strip()
        if not text or not family or not bank:
            raise ValueError(f"Incomplete controlling premise at index {index}")
        premises.append(RadicalControllingPremise(
            identifier=f"{batch['id']}:premise:{index:03d}",
            text=text,
            mechanism_family=family,
            bank=bank,
            intensity=int(item.get("intensity", 1)),
        ))
    if len(premises) != 118:
        raise ValueError(
            f"Expected 118 controlling premises, found {len(premises)}")
    return tuple(premises)


def eligible_radical_controlling_premises() -> tuple[RadicalControllingPremise, ...]:
    """Return narrative-capable premise components without altering their catalogues."""
    return tuple(
        premise for premise in radical_controlling_premises()
        if premise.bank not in RADICAL_CONTROLLING_PREMISE_EXCLUDED_BANKS
    )


def select_radical_controlling_premise(seed) -> RadicalControllingPremise | None:
    """Choose a family, then a premise, reproducibly without family-size bias."""
    premises = eligible_radical_controlling_premises()
    by_family = {}
    for premise in premises:
        by_family.setdefault(premise.mechanism_family, []).append(premise)
    if not by_family:
        return None
    rng = random.Random(f"radical-controlling-premise:{seed}")
    family = rng.choice(sorted(by_family))
    return rng.choice(by_family[family])


def controlling_premise_guidance(premise: RadicalControllingPremise) -> str:
    return (
        "CONTROLLED PREMISE EXPERIMENT — PRIMARY CREATIVE DIRECTION\n"
        f"Mechanism seed: {premise.text}\n"
        "Silently adapt the underlying comic relationship to this source; do not merely "
        "insert or quote the wording. Make it transform the central generic subject or "
        "function and develop its consequences through at least two existing narrative "
        "beats. Preserve the source's event relationships and protected aliases, and do "
        "not invent unrelated events just to accommodate the premise. The optional sparks "
        "remain secondary inspiration."
    )


def load_noun_history_read_only(memory):
    """Load the hard-history snapshot without cleaning or mutating CURRENT state."""
    if not memory.config.enabled:
        return []
    doc = memory.collection.find_one({"_id": memory.record_id}) or {}
    memory.entries = list(doc.get("entries", ()))[-memory.config.capacity:]
    memory.reservations = list(doc.get("reservations", ()))
    memory.recent_identity_events = list(doc.get(
        "recent_identity_events", ()))[-RADICAL_HISTORY_WINDOW:]
    return memory.entries


def prepare_radical_prompt(source, rewrite_id, recent_premises="",
                           identity_guidance="", noun_exclusions=(),
                           controlling_premise_config=None):
    """Build the source-led prompt without modern concept or CSV assignments."""
    original = preserve_source_text(source)
    preprocessing = preprocess_radical_source(original)
    masked = preprocessing["masked"]
    source_text = "\n".join(str(original.get(key, ""))
                              for key in ("title", "description", "extract"))
    inspirations = radical_inspirations(
        rewrite_id, noun_exclusions, source_text)
    template = RADICAL_PROMPT_PATH.read_text(encoding="utf-8")
    prompt = template.format(
        inspirations="\n".join(f"- {value}" for value in inspirations),
        recent_premises=recent_premises or "No recent RADICAL premise warnings.",
        identity_guidance=identity_guidance or "",
    )
    premise_config = (controlling_premise_config
                      or RadicalControllingPremiseConfig.from_environment())
    controlling_premise = None
    if premise_config.enabled:
        controlling_premise = select_radical_controlling_premise(rewrite_id)
        if controlling_premise is not None:
            spark_marker = "The optional sparks below are loose visual provocations."
            if spark_marker not in prompt:
                raise ValueError("RADICAL prompt is missing its optional-sparks marker")
            prompt = prompt.replace(
                spark_marker,
                controlling_premise_guidance(controlling_premise)
                + "\n\n" + spark_marker,
                1,
            )
    title = str(masked.get("title", "No title provided")).strip()
    description = str(masked.get("description", "")).strip()
    extract = str(masked.get("extract", "No extract provided")).strip()
    full_prompt = (
        f"{prompt}\n\nText to Transform:\nTitle: {title}"
        f"{(' - ' + description) if description else ''}\nExtract: {extract}"
    )
    return {
        "full_prompt": full_prompt,
        "contenders": {},
        "preprocessing": preprocessing,
        "title_to_change": title,
        "extract_to_change": extract,
        "radical_inspirations": inspirations,
        "radical_controlling_premise_enabled": premise_config.enabled,
        "radical_controlling_premise": controlling_premise,
    }
