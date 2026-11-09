"""Default-off rolling exclusion for provenance-backed comic noun identities."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from collections import Counter
import hashlib
import csv
import json
import os
from pathlib import Path
import re

from pymongo.errors import DuplicateKeyError

from newsmuncher.services.lexical_exposure import meaningful_words, normal_identity


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
TRACKED_COMIC_IDENTITIES = frozenset({
    "allotment", "apocalypse", "biscuit", "gravy", "queue",
})
AUTOMATIC_REPETITION_ENV = "NEWSMUNCHER_AUTOMATIC_REPETITION_CONTROL"
RECENT_IDENTITY_WINDOW = 12
RECENT_IDENTITY_GUIDANCE_LIMIT = 8


def automatic_repetition_enabled():
    value = os.getenv(AUTOMATIC_REPETITION_ENV, "on").strip().lower()
    if value not in {"on", "off"}:
        raise ValueError(f"{AUTOMATIC_REPETITION_ENV} must be on or off")
    return value == "on"


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


@lru_cache(maxsize=2)
def verified_noun_anchors(include_experimental=False):
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

    if include_experimental:
        from newsmuncher.services.experimental_vocabulary import concept_banks
        add_heads(concept_banks()["domestic_objects"])

    return frozenset(
        (anchors | set(TRACKED_COMIC_IDENTITIES))
        - set(GENERIC_NOUNS) - set(structural_components()))


@lru_cache(maxsize=2)
def recent_comic_identity_anchors(include_experimental=False):
    """Known noun identities suitable for advisory recent-use controls."""
    verified = set(verified_noun_anchors(include_experimental))
    anchors = set(verified)
    root = Path(__file__).resolve().parents[1] / "resources"
    data = json.loads((root / "concepts" /
                       "comedy_concept_components.json").read_text(encoding="utf-8"))
    role_banks = {
        template.get("modifier_bank")
        for templates in data["templates"].values()
        for template in templates
        if template.get("modifier_bank") and any(
            hint in template["modifier_bank"]
            for hint in ("role", "occupation", "profession")
        )
    }
    generic_role_heads = set()
    for bank in role_banks:
        values = list(_bank_values(data["banks"][bank]))
        head_counts = Counter(
            component_words(value, omit_articles=True)[-1]
            for value in values if component_words(value, omit_articles=True))
        for value in values:
            words = component_words(value, omit_articles=True)
            if words and head_counts[words[-1]] == 1:
                anchors.add(words[-1])
        generic_role_heads.update(
            word for word, count in head_counts.items() if count > 1)
        generic_role_heads.update(word for word in head_counts if word in verified)
    # Internal identities qualify only when catalogue structure supplies strong
    # noun evidence: the token occurs in multiple independent banks and is also
    # a complete bank value or a phrase head. This captures e.g. floorboard and
    # parish while excluding one-off adjectives and template grammar.
    occurrences = Counter()
    bank_occurrences = {}
    heads = set()
    singletons = set()
    for filename in ("concepts/comedy_concept_components.json",
                     "descriptors/comedy_descriptor_components.json"):
        resource = json.loads((root / filename).read_text(encoding="utf-8"))
        for bank, values in resource["banks"].items():
            values = list(_bank_values(values))
            bank_words = set()
            for value in values:
                words = component_words(value, omit_articles=True)
                if not words:
                    continue
                bank_words.update(words)
                heads.add(words[-1])
                if len(words) == 1:
                    singletons.add(words[0])
                occurrences.update(set(words))
            for word in bank_words:
                bank_occurrences.setdefault(word, set()).add(filename + ":" + bank)
    anchors.update(
        word for word, banks in bank_occurrences.items()
        if (word in singletons or word in heads) and len(banks) >= 2
        and occurrences[word] >= 2
    )
    return frozenset(
        anchors - set(GENERIC_NOUNS) - set(structural_components())
        - generic_role_heads)


@lru_cache(maxsize=1)
def short_animal_identity_anchors():
    """Reviewed/catalogued animal words omitted by generic lexical scoring."""
    from newsmuncher.services.comedy_concepts import animal_vocabulary
    values = animal_vocabulary()
    return frozenset(
        word for value in values
        for word in component_words(value, omit_articles=True)
        if 2 < len(word) < 4 and word not in structural_components()
    )


def short_animal_mentions(text):
    """Return known short animal identities, including plural/possessive forms."""
    folded = str(text or "").casefold()
    found = set()
    for animal in short_animal_identity_anchors():
        if animal.endswith("y") and animal[-2:-1] not in "aeiou":
            plural = animal[:-1] + "ies"
        elif animal.endswith(("s", "x", "ch", "sh")):
            plural = animal + "es"
        else:
            plural = animal + "s"
        if re.search(rf"(?<![a-z])(?:{re.escape(animal)}|{re.escape(plural)})"
                     rf"(?:['’]s)?(?![a-z])", folded):
            found.add(animal)
    return found


def animal_identity_mentions(text):
    """Return every selectable species with plural and possessive normalisation."""
    from newsmuncher.services.comedy_concepts import animal_mentions
    return animal_mentions(text)


def short_animal_penalty(text, penalties):
    """Apply the soft recent-use penalty consistently to every known species."""
    return sum(float((penalties or {}).get("word:" + animal, 0.0))
               for animal in animal_identity_mentions(text))


def discover_recent_identities(text, source_text=""):
    """Find conservatively recognised comic nouns in displayed output."""
    protected = protected_words(source_text)
    anchors = recent_comic_identity_anchors(
        os.getenv("NEWSMUNCHER_NEW_VOCABULARY", "on").strip().lower() != "off")
    identities = {
        word for word in component_words(text, omit_articles=True)
        if word in anchors and word not in protected
    }
    identities.update(
        animal_identity_mentions(text) - animal_identity_mentions(source_text))
    return sorted(identities)


def construction_label(item):
    """Return the structured joke-bearing component, excluding its replaceable base."""
    if item.get("subject") and not item.get("base"):
        return " ".join(component_words(item["subject"], omit_articles=True))
    phrase = list(component_words(item.get("phrase", ""), omit_articles=True))
    base = component_words(item.get("base") or item.get("subject", ""),
                           omit_articles=True)
    for start in range(len(phrase) - len(base) + 1):
        if tuple(phrase[start:start + len(base)]) == base:
            del phrase[start:start + len(base)]
            break
    grammar = structural_components()
    words = [word for word in phrase if word not in grammar]
    return " ".join(words) if words else ""


def discover_used_constructions(text, source_text="", concepts=(), descriptors=()):
    """Recognise structured premises retained exactly or by a narrow paraphrase."""
    final_words = component_words(text, omit_articles=True)
    source_words = set(component_words(source_text, omit_articles=True))
    results = []
    refusal_cue = re.compile(r"\b(?:refus\w*|reject\w*|won't|wouldn't)\b", re.I)
    for item in tuple(concepts or ()) + tuple(descriptors or ()):
        premise = str(item.get("premise_key", ""))
        label = construction_label(item)
        words = component_words(label, omit_articles=True)
        if not premise or not words or set(words) <= source_words:
            continue
        exact = phrase_found(text, label)
        # Editors commonly replace one leading action while retaining the
        # distinctive multiword object (recognise -> reject linear time).
        core = words[1:] if len(words) >= 3 else ()
        paraphrased = bool(core and len(core) >= 2 and phrase_found(text, " ".join(core)))
        # For a two-word refusal premise, require both its distinctive head and
        # an explicit refusal cue; the head alone is insufficient evidence.
        if (not exact and not paraphrased and len(words) == 2 and
                item.get("semantic_theme") == "principled_refusal" and
                words[-1] in final_words and refusal_cue.search(text)):
            paraphrased = True
        if exact or paraphrased:
            results.append({"key": premise, "label": label,
                            "match": "exact" if exact else "paraphrased"})
    return list({item["key"]: item for item in results}.values())


class NounExclusionExhausted(RuntimeError):
    """No eligible candidate can satisfy a required prompt slot."""


@dataclass(frozen=True)
class NounExclusionConfig:
    mode: str = "off"
    capacity: int = 1500
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


def identity_words(text):
    """Canonical tokens used by persisted phrase identities and their matcher."""
    return tuple(word for word in component_words(text, omit_articles=True)
                 if len(word) >= 4)


def identity_entries(text):
    words = identity_words(text)
    if not words:
        return set()
    animal_phrases = animal_identity_word_sequences()
    entries = (set() if words in animal_phrases
               else {"phrase:" + " ".join(words)})
    noun_anchors = verified_noun_anchors(
        os.getenv("NEWSMUNCHER_NEW_VOCABULARY", "on").strip().lower() != "off")
    # Versioned entries let current extraction coexist with older ledgers that
    # promoted every component to ``noun:``. New anchors are unambiguous.
    animal_words = {sequence[0] for sequence in animal_phrases
                    if len(sequence) == 1}
    entries.update("noun_identity:" + word for word in words
                   if word in noun_anchors and word not in animal_words)
    return entries


@lru_cache(maxsize=1)
def animal_identity_word_sequences():
    """Canonical complete species identities exempt from the hard noun FIFO."""
    from newsmuncher.services.comedy_concepts import animal_vocabulary
    return frozenset(identity_words(value) for value in animal_vocabulary()
                     if identity_words(value))


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
        phrase_words = identity_words(entry.split(":", 1)[1])
        if phrase_words:
            legacy_boundaries.update((phrase_words[0], phrase_words[-1]))
    nouns = {}
    noun_anchors = verified_noun_anchors(
        os.getenv("NEWSMUNCHER_NEW_VOCABULARY", "on").strip().lower() != "off")
    phrases = []
    animal_phrases = animal_identity_word_sequences()
    animal_words = {sequence[0] for sequence in animal_phrases
                    if len(sequence) == 1}
    for entry in exclusions:
        kind, value = entry.split(":", 1)
        words = value.split()
        if any(word in protected for word in words):
            continue
        if kind in {"noun", "noun_identity"}:
            if value in animal_words:
                continue
            current_or_supported_legacy = (
                kind == "noun_identity" or value in legacy_boundaries)
            if current_or_supported_legacy and value in noun_anchors:
                nouns.setdefault(value, []).append(entry)
        elif kind == "phrase":
            phrase_words = identity_words(value)
            if phrase_words and phrase_words not in animal_phrases:
                phrases.append((phrase_words, entry))
    return nouns, tuple(phrases)


def blocked_entries(text, exclusions, source_text="", exclusion_index=None):
    nouns, phrases = (exclusion_index or
                      compile_exclusion_index(exclusions, source_text))
    # Phrase entries are persisted from ``identity_entries``, which omits short
    # connective tokens. Use that exact representation here too: otherwise a
    # stored ``phrase:beast burden`` fails to match ``beast of burden`` during
    # selection but collides when the same canonical key is reserved later.
    available = identity_words(text)
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
    for values in (contenders or {}).values():
        yield from (str(value) for value in values)


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
    # These deliberately curated comic noun identities recur through many
    # constructions and may also be improvised by the writer. Record exact
    # normalized tokens from the displayed result without promoting arbitrary
    # modifiers or using substring matching.
    final_words = set(component_words(final_text, omit_articles=True))
    entries.update(
        "noun_identity:" + identity
        for identity in TRACKED_COMIC_IDENTITIES
        if identity in final_words and identity not in protected
    )
    # Broader metadata-derived identities are recorded separately in the recent
    # identity history. They drive advisory prompt guidance and soft ranking,
    # but do not become permanent hard exclusions merely because they appeared
    # once in prose.
    return entries


class NounExclusionMemory:
    """Persistent bounded FIFO with short atomic per-generation reservations."""

    # Keep the previous history depth for inspection/rollback. Only the newest
    # config.capacity entries participate in hard exclusion and reservation.
    retained_history_capacity = 5000

    def __init__(self, collection, scope, config=None, now=None):
        self.collection = collection
        self.config = config or NounExclusionConfig()
        self.now = now or (lambda: datetime.now(timezone.utc))
        digest = hashlib.sha256(str(scope).encode("utf-8")).hexdigest()[:24]
        self.record_id = "scope:" + digest
        self.entries = []
        self.reservations = []
        self.recent_identity_events = []
        self.last_reservation_conflict = {}

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
        self.recent_identity_events = list(doc.get(
            "recent_identity_events", []))[-RECENT_IDENTITY_WINDOW:]
        return self.entries

    def identity_penalties(self, source_text=""):
        if not self.config.enabled or not automatic_repetition_enabled():
            return Counter()
        protected = protected_words(source_text) | animal_identity_mentions(source_text)
        penalties = Counter()
        for age, event in enumerate(reversed(self.recent_identity_events), 1):
            recency = RECENT_IDENTITY_WINDOW - age + 1
            for identity in set(event.get("identities", ())) - protected:
                penalties["word:" + identity] += recency
            for construction in event.get("constructions", ()):
                key = construction.get("key", "")
                label = construction.get("label", "")
                if key:
                    penalties["premise:" + key] += recency
                identity = normal_identity(label)
                if identity:
                    penalties["identity:" + identity] += recency
        return penalties

    def avoidance_guidance(self, source_text=""):
        penalties = self.identity_penalties(source_text)
        protected = protected_words(source_text) | animal_identity_mentions(source_text)
        appearances = Counter(
            identity
            for event in self.recent_identity_events
            for identity in set(event.get("identities", ())) - protected
        )
        ranked = sorted(
            ((key[5:], value) for key, value in penalties.items()
             if key.startswith("word:") and appearances[key[5:]] >= 2),
            key=lambda item: (-item[1], item[0]),
        )
        construction_appearances = Counter(
            construction.get("key")
            for event in self.recent_identity_events
            for construction in event.get("constructions", ())
            if construction.get("key"))
        construction_labels = {}
        for event in self.recent_identity_events:
            for construction in event.get("constructions", ()):
                construction_labels[construction.get("key")] = construction.get("label")
        construction_ranked = sorted(
            ((key, penalties.get("premise:" + key, 0))
             for key, count in construction_appearances.items() if count >= 2),
            key=lambda item: (-item[1], item[0]),
        )[:3]
        constructions = [construction_labels[key] for key, _ in construction_ranked
                         if construction_labels.get(key)]
        remaining = RECENT_IDENTITY_GUIDANCE_LIMIT - len(constructions)
        selected = [identity for identity, _ in ranked
                    if (len(identity) >= 4 or identity in short_animal_identity_anchors())
                    and identity not in structural_components()][
                        :remaining]
        if not selected and not constructions:
            return ""
        parts = []
        if selected:
            parts.append("comic nouns: " + ", ".join(selected))
        if constructions:
            parts.append("complete comic ideas: " + ", ".join(constructions))
        return (
            "RECENT COMIC IDENTITY VARIETY (soft guidance):\n"
            "Unless the source requires them, avoid leaning again on these recently "
            "repeated " + "; ".join(parts) + ". Use fresh, equally "
            "surreal vocabulary instead. Grammatical joke patterns remain available "
            "when their comic target or punchline changes substantially; avoid the "
            "listed complete ideas and close paraphrases, not the reusable pattern. "
            "Preserve the source facts and comedy style."
        )

    def exclusions(self, generation_id=None):
        values = set(self.entries)
        for reservation in self.reservations:
            if (reservation.get("generation_id") != generation_id
                    and self._reservation_active(reservation, self.now())):
                values.update(reservation.get("entries", ()))
        return values

    @staticmethod
    def _reservation_active(reservation, now):
        expiry = reservation.get("offer_until")
        # Malformed/missing expiry remains blocking; never silently treat an
        # unproven lease as expired. PyMongo may return naive UTC datetimes.
        if not isinstance(expiry, datetime):
            return True
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        return expiry > now

    def reserve(self, generation_id, entries):
        if not self.config.enabled:
            return True
        entries = sorted(set(entries))
        self.last_reservation_conflict = {}
        if not entries:
            return True
        now = self.now()
        query = {
            "_id": self.record_id,
            "$expr": {"$eq": [{"$size": {"$setIntersection": [
                {"$slice": [{"$ifNull": ["$entries", []]}, -self.config.capacity]},
                entries,
            ]}}, 0]},
            "reservations": {"$not": {"$elemMatch": {
                "entries": {"$in": entries},
                "offer_until": {"$not": {"$lte": now}},
            }}},
        }
        update = {
            "$push": {"reservations": {"generation_id": str(generation_id),
                                        "entries": entries,
                                        "offer_until": now + timedelta(
                                            minutes=self.config.reservation_minutes)}},
        }
        # Create the scope independently, then make the exclusion check and
        # reservation one conditional atomic update. Combining both with an
        # upsert made an ordinary filter mismatch surface as DuplicateKeyError
        # on the existing _id and bypassed conflict diagnostics entirely.
        try:
            self.collection.update_one(
                {"_id": self.record_id},
                {"$setOnInsert": {"version": 1,
                                   "record_type": "noun_exclusion",
                                   "entries": [], "reservations": []}},
                upsert=True,
            )
        except DuplicateKeyError:
            # A concurrent creator won; the conditional update below remains
            # authoritative.
            pass
        result = self.collection.update_one(query, update)
        if result.matched_count or result.upserted_id is not None:
            self.reservations.append(update["$push"]["reservations"])
            return True
        # The atomic query deliberately rejects both completed FIFO entries and
        # entries reserved by another generation. Read back only those bounded
        # identifiers so diagnostics can distinguish a stale selection snapshot
        # from genuine concurrent work without exposing prompt/source content.
        current = self.collection.find_one({"_id": self.record_id}) or {}
        completed = sorted(set(entries) & set(
            current.get("entries", [])[-self.config.capacity:]))
        active = []
        owners = set()
        for reservation in current.get("reservations", ()):
            if not self._reservation_active(reservation, now):
                continue
            collisions = sorted(set(entries) & set(reservation.get("entries", ())))
            if collisions:
                active.extend(collisions)
                owners.add(str(reservation.get("generation_id", "")))
        if completed and active:
            reason = "mixed"
        elif completed:
            reason = "completed_history"
        elif active:
            reason = "active_reservation"
        elif not current:
            reason = "missing_scope_document"
        else:
            reason = "atomic_filter_mismatch_without_visible_conflict"
        self.last_reservation_conflict = {
            "reason": reason,
            "completed_entries": completed,
            "active_entries": sorted(set(active)),
            "active_owner_count": len(owners),
        }
        # State may change between the failed atomic update and readback. Retry
        # once only when the fresh authoritative document shows no conflict;
        # never retry a verified hard exclusion or active reservation.
        if not completed and not active and current:
            retry = self.collection.update_one(query, update)
            if retry.matched_count or retry.upserted_id is not None:
                self.reservations.append(update["$push"]["reservations"])
                self.last_reservation_conflict = {}
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

    def complete(self, generation_id, new_entries, recent_identities=(),
                 recent_constructions=()):
        if not self.config.enabled:
            return False
        new_entries = sorted(set(new_entries))
        history_capacity = max(self.retained_history_capacity, self.config.capacity)
        for _ in range(4):
            doc = self.collection.find_one({"_id": self.record_id}) or {}
            if not doc:
                recent_events = ([{"rewrite_id": str(generation_id),
                                   "identities": sorted(set(recent_identities)),
                                   "constructions": list(recent_constructions)}]
                                 if automatic_repetition_enabled() and
                                 (recent_identities or recent_constructions)
                                 else [])
                try:
                    result = self.collection.update_one(
                        {"_id": self.record_id},
                        {"$setOnInsert": {"version": 1,
                                          "record_type": "noun_exclusion"},
                         "$set": {"entries": new_entries[-history_capacity:],
                                  "reservations": [],
                                  "recent_identity_events": recent_events,
                                  "revision": 1}},
                        upsert=True,
                    )
                except DuplicateKeyError:
                    continue
                if result.matched_count or result.upserted_id is not None:
                    self.entries = new_entries[-self.config.capacity:]
                    self.reservations = []
                    self.recent_identity_events = recent_events
                    return True
                continue
            revision = int(doc.get("revision", 0))
            entries = list(doc.get("entries", []))
            active = set(entries[-self.config.capacity:])
            for entry in new_entries:
                if entry not in active:
                    # A released historical identity starts a new quarantine
                    # when actually reused. Repeated active/source-required
                    # identities do not refresh their existing FIFO position.
                    if entry in entries:
                        entries.remove(entry)
                    entries.append(entry)
            entries = entries[-history_capacity:]
            recent_events = list(doc.get("recent_identity_events", []))
            if (automatic_repetition_enabled() and
                    (recent_identities or recent_constructions) and
                    all(event.get("rewrite_id") != str(generation_id)
                        for event in recent_events)):
                recent_events.append({
                    "rewrite_id": str(generation_id),
                    "identities": sorted(set(recent_identities)),
                    "constructions": list(recent_constructions),
                })
            recent_events = recent_events[-RECENT_IDENTITY_WINDOW:]
            reservations = [item for item in doc.get("reservations", [])
                            if item.get("generation_id") != str(generation_id)]
            revision_query = ({"$or": [{"revision": 0}, {"revision": {"$exists": False}}]}
                              if revision == 0 else {"revision": revision})
            result = self.collection.update_one(
                {"_id": self.record_id, **revision_query},
                {"$set": {"entries": entries, "reservations": reservations,
                           "recent_identity_events": recent_events,
                           "revision": revision + 1}},
            )
            if result.matched_count:
                self.entries = entries[-self.config.capacity:]
                self.reservations = reservations
                self.recent_identity_events = recent_events
                return True
        raise RuntimeError("Concurrent noun-exclusion update did not settle")
