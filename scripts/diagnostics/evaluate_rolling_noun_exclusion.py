"""Provider-free Phase 4W proof of concept for rolling comic-noun exclusion."""
from __future__ import annotations

import argparse
from collections import OrderedDict
import json
from pathlib import Path
import re
import statistics
import threading

from newsmuncher.services.lexical_exposure import meaningful_words


# Heads that carry little comic identity by themselves. A compound is retained,
# but these words do not become broad anchors: "gravy boat" blocks gravy, not boat.
GENERIC_NOUNS = frozenset({
    "article", "boat", "body", "case", "day", "event", "group", "head",
    "item", "machine", "member", "news", "object", "office", "part", "people",
    "person", "place", "report", "result", "room", "story", "system", "thing",
    "time", "week", "word", "work", "year",
})


def _found(text, phrase):
    return bool(phrase and re.search(rf"(?<!\w){re.escape(phrase)}(?!\w)", text, re.I))


def _offered_identities(record):
    offered = record.get("ingredients", {}).get("offered", {})
    for item in offered.get("generated_concepts", ()):
        yield item.get("base") or item.get("animal_species") or item.get("phrase")
    for item in offered.get("generated_descriptors", ()):
        yield item.get("subject") or item.get("phrase")
    for item in offered.get("raw_hybrid_ingredients", ()):
        yield item.get("text")
    for values in offered.get("legacy_banks", {}).values():
        yield from values


def _protected(record):
    source = record.get("source", {})
    text = "\n".join(str(source.get(k, "")) for k in ("headline", "description", "article_text"))
    words = set(meaningful_words(text))
    offered = record.get("ingredients", {}).get("offered", {})
    for item in offered.get("generated_names", ()):
        words.update(meaningful_words(item.get("name", "")))
    for value in offered.get("legacy_banks", {}).get("names", ()):
        words.update(meaningful_words(value))
    for value in offered.get("legacy_banks", {}).get("places", ()):
        words.update(meaningful_words(value))
    return words


def identity_entries(identity):
    """Return an exact identity and its distinctive component anchors."""
    words = meaningful_words(identity or "")
    if not words:
        return set()
    entries = {"phrase:" + " ".join(words)} if len(words) > 1 else set()
    entries.update("noun:" + word for word in words if word not in GENERIC_NOUNS)
    return entries


def extract_distinctive_nouns(record):
    """Conservative extraction from exact final use of provenance-backed identities."""
    final = record.get("final", {})
    text = "\n".join(str(final.get(k, "")) for k in ("headline", "article_text"))
    protected = _protected(record)
    entries = set()
    for identity in _offered_identities(record):
        if not identity or not _found(text, str(identity)):
            continue
        for entry in identity_entries(str(identity)):
            component_words = meaningful_words(entry.split(":", 1)[1])
            if not any(word in protected for word in component_words):
                entries.add(entry)
    return entries


def blocked_matches(text, exclusions, source_text=""):
    """Detect selected or model-invented exact reuse without another model call."""
    protected = set(meaningful_words(source_text))
    matches = []
    for entry in exclusions:
        kind, value = entry.split(":", 1)
        if kind == "noun" and value in protected:
            continue
        if kind == "phrase" and any(word in protected for word in meaningful_words(value)):
            continue
        if _found(text, value):
            matches.append(entry)
    return sorted(matches)


def filter_and_refill(candidates, exclusions, count, source_text=""):
    """Take the first eligible candidates, continuing until vacancies are filled."""
    selected, rejected = [], []
    for candidate in candidates:
        text = str(candidate.get("text") or candidate.get("phrase") or candidate)
        if blocked_matches(text, exclusions, source_text):
            rejected.append(text)
        elif len(selected) < count:
            selected.append(candidate)
        if len(selected) == count:
            break
    return selected, rejected


class RollingNounLedger:
    """In-memory prototype: bounded FIFO state and reservations isolated per pet."""

    def __init__(self, capacity=5000):
        self.capacity = capacity
        self._entries = {}
        self._reservations = {}
        self._lock = threading.RLock()

    def entries(self, scope):
        with self._lock:
            return tuple(self._entries.get(scope, ()))

    def exclusions(self, scope, except_generation=None):
        with self._lock:
            values = set(self._entries.get(scope, ()))
            for generation, (reserved_scope, entries) in self._reservations.items():
                if reserved_scope == scope and generation != except_generation:
                    values.update(entries)
            return values

    def reserve(self, scope, generation_id, candidates, count, source_text=""):
        with self._lock:
            chosen, rejected = filter_and_refill(
                candidates, self.exclusions(scope, generation_id), count, source_text)
            reserved = set()
            for item in chosen:
                text = str(item.get("text") or item.get("phrase") or item)
                reserved.update(identity_entries(text))
            self._reservations[generation_id] = (scope, reserved)
            return chosen, rejected

    def complete(self, scope, generation_id, entries):
        with self._lock:
            self._reservations.pop(generation_id, None)
            fifo = self._entries.setdefault(scope, OrderedDict())
            for entry in sorted(entries):
                if entry in fifo:
                    continue  # FIFO age is set by first committed appearance.
                fifo[entry] = None
                if len(fifo) > self.capacity:
                    fifo.popitem(last=False)

    def fail(self, generation_id):
        with self._lock:
            self._reservations.pop(generation_id, None)


def load_records(paths):
    records, seen = [], set()
    for path in paths:
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            if record.get("rewrite_id") not in seen:
                seen.add(record.get("rewrite_id")); records.append(record)
    return records


def evaluate(paths, capacity=5000):
    records = load_records(paths)
    counts = [len(extract_distinctive_nouns(record)) for record in records]
    mean = statistics.mean(counts) if counts else 0
    median = statistics.median(counts) if counts else 0
    return {
        "articles": len(records), "capacity": capacity,
        "distinctive_entries": sum(counts),
        "mean_entries_per_article": round(mean, 2),
        "median_entries_per_article": median,
        "estimated_articles_at_mean": round(capacity / mean) if mean else None,
        "estimated_articles_at_median": round(capacity / median) if median else None,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--capacity", type=int, default=5000)
    args = parser.parse_args()
    print(json.dumps(evaluate(args.paths, args.capacity), indent=2))
