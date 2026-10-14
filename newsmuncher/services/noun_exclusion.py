"""Default-off rolling exclusion for provenance-backed comic noun identities."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import lru_cache
import hashlib
import csv
import json
import os
from pathlib import Path
import re

from pymongo.errors import DuplicateKeyError

from newsmuncher.services.lexical_exposure import meaningful_words


NOUN_EXCLUSION_ENV = "NEWSMUNCHER_NOUN_EXCLUSION"
GENERIC_NOUNS = frozenset({
    "article", "boat", "body", "case", "day", "event", "group", "head",
    "item", "machine", "member", "news", "object", "office", "part", "people",
    "person", "place", "report", "result", "room", "story", "system", "thing",
    "time", "week", "word", "work", "year",
})
OPTIONAL_ARTICLES = frozenset({"a", "an", "the"})
GRAMMATICAL_COMPONENTS = frozenset({
    "about", "after", "against", "along", "among", "around", "as", "at",
    "before", "behind", "below", "beneath", "beside", "between", "beyond",
    "by", "during", "for", "from", "in", "inside", "into", "near", "of",
    "on", "onto", "outside", "over", "through", "to", "toward", "under",
    "until", "upon", "with", "within", "without",
})
COMPONENT_RE = re.compile(r"[a-z]+", re.I)


@lru_cache(maxsize=1)
def structural_components():
    """Words supplied by template grammar rather than comic noun identities."""
    result = set(OPTIONAL_ARTICLES) | set(GRAMMATICAL_COMPONENTS)
    root = Path(__file__).resolve().parents[1] / "resources"
    for path in (
        root / "concepts" / "comedy_concept_components.json",
        root / "descriptors" / "comedy_descriptor_components.json",
    ):
        data = json.loads(path.read_text(encoding="utf-8"))
        templates = data.get("templates", ())
        groups = templates.values() if isinstance(templates, dict) else (templates,)
        for group in groups:
            for template in group:
                literal = re.sub(r"\{[^}]+\}", " ", template.get("pattern", ""))
                result.update(component_words(literal, omit_articles=True))
    return frozenset(result)


def _bank_values(bank):
    if isinstance(bank, dict):
        for values in bank.values():
            yield from values
    else:
        yield from bank


@lru_cache(maxsize=1)
def verified_noun_anchors():
    """Return independently catalogued, single-token noun identities.

    Multiword vocabulary is retained as a phrase identity when it is accepted,
    but its modifiers are not promoted to hard noun exclusions.  A component
    such as ``gravy`` still qualifies when it also exists as its own typed
    vocabulary entry (for example, in the power-source bank).
    """
    root = Path(__file__).resolve().parents[1] / "resources"
    anchors = set()

    def add_heads(values):
        for value in values:
            words = component_words(value, omit_articles=True)
            if words:
                anchors.add(words[-1])

    concept_data = json.loads((
        root / "concepts" / "comedy_concept_components.json"
    ).read_text(encoding="utf-8"))
    # Base and topic slots are the generator's explicit noun-bearing slots.
    # Modifier banks are intentionally excluded even when they contain words
    # that can be nouns in another context (``powered``, ``royal``, etc.).
    concept_noun_banks = {
        template[field]
        for templates in concept_data["templates"].values()
        for template in templates
        for field in ("base_bank", "topic_bank")
        if template.get(field)
    }
    for name in concept_noun_banks:
        add_heads(_bank_values(concept_data["banks"][name]))

    catalogue = json.loads((
        root / "vocabulary" / "comedy_vocabulary_catalogue.json"
    ).read_text(encoding="utf-8"))
    add_heads(item["text"] for item in catalogue["ingredients"]
              if item.get("family") in {"animals", "objects", "slang"}
              and item.get("approval_status") == "editorially_reviewed")

    thematic = json.loads((
        root / "vocabulary" / "thematic_ingredient_seeds.json"
    ).read_text(encoding="utf-8"))
    for domain in thematic["domains"]:
        seeds = domain.get("seeds", {})
        add_heads(item["text"] for item in seeds.get("entities", ()))

    for filename in ("nouns.csv", "animalsAndObjects.csv", "slang.csv"):
        with (root / "words" / filename).open(newline="", encoding="utf-8-sig") as handle:
            add_heads(cell for row in csv.reader(handle) for cell in row if cell)

    return frozenset(anchors - set(GENERIC_NOUNS) - set(structural_components()))


class NounExclusionExhausted(RuntimeError):
    """No eligible candidate can satisfy a required prompt slot."""


@dataclass(frozen=True)
class NounExclusionConfig:
    mode: str = "off"
    capacity: int = 5000
    reservation_minutes: int = 15

    @classmethod
    def from_environment(cls):
        return cls(os.getenv(NOUN_EXCLUSION_ENV, "off").strip().lower())

    def __post_init__(self):
        if self.mode not in {"off", "evaluation"}:
            raise ValueError(f"{NOUN_EXCLUSION_ENV} must be off or evaluation")
        if self.capacity < 10 or self.reservation_minutes < 1:
            raise ValueError("Invalid noun-exclusion limits")

    @property
    def enabled(self):
        return self.mode == "evaluation"


def canonical_noun(word):
    word = str(word).casefold().strip("-' ")
    if len(word) > 4 and word.endswith("ies"):
        return word[:-3] + "y"
    if len(word) > 4 and word.endswith(("ches", "shes", "xes", "zes")):
        return word[:-2]
    if len(word) > 3 and word.endswith("s") and not word.endswith(("ss", "us", "is")):
        return word[:-1]
    return word


def component_words(text, omit_articles=False):
    words = tuple(canonical_noun(word) for word in COMPONENT_RE.findall(str(text or "")))
    return tuple(word for word in words
                 if not (omit_articles and word in OPTIONAL_ARTICLES))


def identity_entries(text):
    words = tuple(word for word in component_words(text, omit_articles=True)
                  if len(word) >= 4)
    if not words:
        return set()
    entries = {"phrase:" + " ".join(words)}
    noun_anchors = verified_noun_anchors()
    # Versioned entries let current extraction coexist with older ledgers that
    # promoted every component to ``noun:``. New anchors are unambiguous.
    entries.update("noun_identity:" + word for word in words
                   if word in noun_anchors)
    return entries


def phrase_found(text, value):
    """Match ordered canonical tokens while ignoring inserted English articles."""
    wanted = component_words(value, omit_articles=True)
    available = component_words(text, omit_articles=True)
    if not wanted:
        return False
    size = len(wanted)
    return any(available[index:index + size] == wanted
               for index in range(len(available) - size + 1))


def protected_words(source_text="", names=(), places=()):
    words = set(component_words(source_text))
    for value in tuple(names or ()) + tuple(places or ()):
        words.update(component_words(str(value)))
    return words


def compile_exclusion_index(exclusions, source_text=""):
    """Compile immutable exclusion records for repeated local matching."""
    protected = protected_words(source_text)
    exclusions = set(exclusions or ())
    # Retain old noun history only when an accepted phrase proves that the word
    # was at an identity boundary. This keeps e.g. gravy from a gravy-powered
    # construction and mower from lawn mower, while safely ignoring historical
    # modifier/action entries whose original role is otherwise unknowable.
    legacy_boundaries = set()
    for entry in exclusions:
        if not entry.startswith("phrase:"):
            continue
        phrase_words = component_words(entry.split(":", 1)[1], omit_articles=True)
        if phrase_words:
            legacy_boundaries.update((phrase_words[0], phrase_words[-1]))
    nouns = {}
    phrases = []
    for entry in exclusions:
        kind, value = entry.split(":", 1)
        words = value.split()
        if any(word in protected for word in words):
            continue
        if kind in {"noun", "noun_identity"}:
            current_or_supported_legacy = (
                kind == "noun_identity" or value in legacy_boundaries)
            if current_or_supported_legacy and value in verified_noun_anchors():
                nouns.setdefault(value, []).append(entry)
        elif kind == "phrase":
            phrase_words = component_words(value, omit_articles=True)
            if phrase_words:
                phrases.append((phrase_words, entry))
    return nouns, tuple(phrases)


def blocked_entries(text, exclusions, source_text="", exclusion_index=None):
    nouns, phrases = (exclusion_index or
                      compile_exclusion_index(exclusions, source_text))
    available = component_words(text, omit_articles=True)
    available_set = set(available)
    found = [entry for word, entries in nouns.items() if word in available_set
             for entry in entries]
    for wanted, entry in phrases:
        size = len(wanted)
        if any(available[index:index + size] == wanted
               for index in range(len(available) - size + 1)):
            found.append(entry)
    return sorted(found)


def filter_candidates(candidates, exclusions, text_field, source_text=""):
    return [item for item in candidates
            if not blocked_entries(str(item.get(text_field, "")), exclusions, source_text)]


def attribute_violations(final_text, exclusions, selected_texts, source_text=""):
    violations = set(blocked_entries(final_text, exclusions, source_text))
    offered = {entry for text in selected_texts
               for entry in blocked_entries(text, exclusions, source_text)}
    return {
        "offered_ingredient_violations": sorted(violations & offered),
        "model_introduced_violations": sorted(violations - offered),
    }


def ingredient_texts(concepts=(), descriptors=(), raw=(), contenders=None):
    for item in concepts or ():
        for field in ("phrase", "base"):
            if item.get(field):
                yield str(item[field])
    for item in descriptors or ():
        for field in ("phrase", "subject"):
            if item.get(field):
                yield str(item[field])
    for item in raw or ():
        for field in ("text", "base", "subject"):
            if item.get(field):
                yield str(item[field])
    for bank in ("nouns", "animals"):
        yield from (str(value) for value in (contenders or {}).get(bank, ()))


def extract_final_entries(*, title, body, source_text, concepts=(), descriptors=(),
                          raw=(), contenders=None, names=(), places=()):
    final_text = f"{title}\n{body}"
    protected = protected_words(source_text, names, places)
    entries = set()
    for identity in ingredient_texts(concepts, descriptors, raw, contenders):
        if not identity or not phrase_found(final_text, identity):
            continue
        for entry in identity_entries(identity):
            if not any(word in protected for word in entry.split(":", 1)[1].split()):
                entries.add(entry)
    for item in tuple(concepts or ()) + tuple(descriptors or ()):
        if item.get("premise_key") and phrase_found(final_text, item.get("phrase", "")):
            entries.add("premise:" + str(item["premise_key"]))
    return entries


class NounExclusionMemory:
    """Persistent bounded FIFO with short atomic per-generation reservations."""

    def __init__(self, collection, scope, config=None, now=None):
        self.collection = collection
        self.config = config or NounExclusionConfig()
        self.now = now or (lambda: datetime.now(timezone.utc))
        digest = hashlib.sha256(str(scope).encode("utf-8")).hexdigest()[:24]
        self.record_id = "scope:" + digest
        self.entries = []
        self.reservations = []

    def load(self):
        if not self.config.enabled:
            return []
        now = self.now()
        self.collection.update_one(
            {"_id": self.record_id},
            {"$pull": {"reservations": {"offer_until": {"$lte": now}}}},
        )
        doc = self.collection.find_one({"_id": self.record_id}) or {}
        self.entries = list(doc.get("entries", []))[-self.config.capacity:]
        self.reservations = list(doc.get("reservations", []))
        return self.entries

    def exclusions(self, generation_id=None):
        values = set(self.entries)
        for reservation in self.reservations:
            if reservation.get("generation_id") != generation_id:
                values.update(reservation.get("entries", ()))
        return values

    def reserve(self, generation_id, entries):
        if not self.config.enabled:
            return True
        entries = sorted(set(entries))
        if not entries:
            return True
        now = self.now()
        query = {"_id": self.record_id, "entries": {"$nin": entries},
                 "reservations.entries": {"$nin": entries}}
        update = {
            "$setOnInsert": {"version": 1, "record_type": "noun_exclusion", "entries": []},
            "$push": {"reservations": {"generation_id": str(generation_id),
                                        "entries": entries,
                                        "offer_until": now + timedelta(
                                            minutes=self.config.reservation_minutes)}},
        }
        try:
            result = self.collection.update_one(query, update, upsert=True)
        except DuplicateKeyError:
            return False
        if result.matched_count or result.upserted_id is not None:
            self.reservations.append(update["$push"]["reservations"])
            return True
        return False

    def release(self, generation_id):
        if self.config.enabled:
            self.collection.update_one(
                {"_id": self.record_id},
                {"$pull": {"reservations": {"generation_id": str(generation_id)}}},
            )
            self.reservations = [item for item in self.reservations
                                 if item.get("generation_id") != str(generation_id)]

    def complete(self, generation_id, new_entries):
        if not self.config.enabled:
            return False
        new_entries = sorted(set(new_entries))
        for _ in range(4):
            doc = self.collection.find_one({"_id": self.record_id}) or {}
            if not doc:
                try:
                    result = self.collection.update_one(
                        {"_id": self.record_id},
                        {"$setOnInsert": {"version": 1,
                                          "record_type": "noun_exclusion"},
                         "$set": {"entries": new_entries[-self.config.capacity:],
                                  "reservations": [], "revision": 1}},
                        upsert=True,
                    )
                except DuplicateKeyError:
                    continue
                if result.matched_count or result.upserted_id is not None:
                    self.entries = new_entries[-self.config.capacity:]
                    self.reservations = []
                    return True
                continue
            revision = int(doc.get("revision", 0))
            entries = list(doc.get("entries", []))
            for entry in new_entries:
                if entry not in entries:
                    entries.append(entry)
            entries = entries[-self.config.capacity:]
            reservations = [item for item in doc.get("reservations", [])
                            if item.get("generation_id") != str(generation_id)]
            revision_query = ({"$or": [{"revision": 0}, {"revision": {"$exists": False}}]}
                              if revision == 0 else {"revision": revision})
            result = self.collection.update_one(
                {"_id": self.record_id, **revision_query},
                {"$set": {"entries": entries, "reservations": reservations,
                           "revision": revision + 1}},
            )
            if result.matched_count:
                self.entries, self.reservations = entries, reservations
                return True
        raise RuntimeError("Concurrent noun-exclusion update did not settle")
