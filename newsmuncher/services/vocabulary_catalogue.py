"""Typed comedy-vocabulary catalogues and deterministic bounded selection."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
import json
from pathlib import Path
import random
import re
import unicodedata

RESOURCE_PATH = Path(__file__).parents[1] / "resources/vocabulary/comedy_vocabulary_catalogue.json"
ANIMAL_POLICY_PATH = Path(__file__).parents[1] / "resources/vocabulary/animal_selection_policy.json"
FAMILIES = {"animals", "objects", "descriptors", "names", "slang", "places"}
APPROVALS = {"machine_checked", "editorially_reviewed", "rejected"}
SUPPORTED_LICENCES = {"CC0-1.0", "CC-BY-4.0", "OGL-3.0", "Apache-2.0", "INTERNAL-UNVERIFIED"}
BLOCKED = {"slanteye", "spearchucker", "chinaman", "diaper head", "towel head",
           "camel jockey", "christ killer", "shemale", "spastic", "surrender monkey"}


def normalise(value):
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().casefold()
    return re.sub(r"[^a-z0-9]+", "", value)


@dataclass(frozen=True)
class ValidationIssue:
    level: str
    code: str
    ingredient_id: str
    detail: str


class VocabularyCatalogue:
    def __init__(self, payload):
        self.payload = payload
        self.entries = payload["ingredients"]
        self.sources = payload["sources"]
        self.by_family = {family: [] for family in FAMILIES}
        for entry in self.entries:
            self.by_family.setdefault(entry.get("family"), []).append(entry)

    @classmethod
    def load(cls, path=RESOURCE_PATH):
        return cls(json.loads(Path(path).read_text(encoding="utf-8")))

    def validate(self):
        issues = []
        ids, normalized, near_normalized = set(), {}, {}
        semantic_counts = Counter()
        for entry in self.entries:
            entry_id = entry.get("id", "<missing>")
            required = ("id", "text", "family", "category", "subtype", "grammar",
                        "semantic_class", "compatible_mechanisms", "humour",
                        "familiarity", "source_id", "licence_id", "editorial_flags",
                        "approval_status")
            for field in required:
                if field not in entry:
                    issues.append(ValidationIssue("error", "missing_field", entry_id, field))
            if entry_id in ids:
                issues.append(ValidationIssue("error", "duplicate_id", entry_id, entry_id))
            ids.add(entry_id)
            text = entry.get("text", "")
            key = normalise(text)
            if not key or len(text) > 100 or re.search(r"\s{2,}|[^\w\s'’&+.,/-]", text):
                issues.append(ValidationIssue("error", "malformed_text", entry_id, text))
            family_key = (entry.get("family"), key)
            if family_key in normalized:
                issues.append(ValidationIssue("error", "duplicate_text", entry_id, normalized[family_key]))
            normalized[family_key] = entry_id
            near_key = re.sub(r"(?:es|s)$", "", key)
            prior_near = near_normalized.get((entry.get("family"), near_key))
            if prior_near:
                issues.append(ValidationIssue("warning", "near_duplicate_variant", entry_id, prior_near))
            near_normalized[(entry.get("family"), near_key)] = entry_id
            family = entry.get("family")
            if family not in FAMILIES:
                issues.append(ValidationIssue("error", "invalid_family", entry_id, str(family)))
            if entry.get("approval_status") not in APPROVALS:
                issues.append(ValidationIssue("error", "invalid_approval", entry_id, ""))
            source = self.sources.get(entry.get("source_id"))
            if not source:
                issues.append(ValidationIssue("error", "missing_provenance", entry_id, ""))
            if entry.get("licence_id") not in SUPPORTED_LICENCES:
                issues.append(ValidationIssue("error", "unsupported_licence", entry_id,
                                              str(entry.get("licence_id"))))
            folded = text.casefold()
            if any(re.search(rf"(?<![a-z]){re.escape(term)}(?![a-z])", folded)
                   for term in BLOCKED):
                issues.append(ValidationIssue("error", "discriminatory_content", entry_id, text))
            flags = set(entry.get("editorial_flags", ()))
            if {"trademark_risk", "real_person_risk", "discriminatory"} & flags:
                issues.append(ValidationIssue("error", "blocked_editorial_risk", entry_id,
                                              ",".join(sorted(flags))))
            if entry.get("approval_status") == "editorially_reviewed" and "needs_review" in flags:
                issues.append(ValidationIssue("error", "false_editorial_approval", entry_id, ""))
            grammar = entry.get("grammar", {})
            descriptor_roles = set(grammar.get("roles", ())) or {grammar.get("role")}
            if family == "descriptors" and not descriptor_roles <= {
                "pre_noun", "adverbial", "predicate", "post_noun", "behavioural", "short_clause"
            }:
                issues.append(ValidationIssue("error", "invalid_descriptor_role", entry_id, ""))
            if entry.get("familiarity") == "obscure" and not entry.get("recognisability_note"):
                issues.append(ValidationIssue("warning", "unreviewed_obscurity", entry_id, text))
            semantic_counts[(family, entry.get("semantic_class"))] += 1
        for (family, semantic), count in semantic_counts.items():
            family_total = max(1, len(self.by_family.get(family, ())))
            if count / family_total > .45:
                issues.append(ValidationIssue("warning", "overrepresented_semantic_group",
                                              family, f"{semantic}:{count}/{family_total}"))
        return issues


@lru_cache(maxsize=1)
def cached_catalogue():
    """Load and validate the packaged catalogue once per process."""
    catalogue = VocabularyCatalogue.load()
    errors = [issue for issue in catalogue.validate() if issue.level == "error"]
    if errors:
        raise ValueError(f"Comedy vocabulary catalogue has {len(errors)} validation errors")
    return catalogue


@lru_cache(maxsize=1)
def animal_selection_policy():
    """Editorial classification for terms unsuitable as standalone animals."""
    return json.loads(ANIMAL_POLICY_PATH.read_text(encoding="utf-8"))


def selectable_animal_identity(text):
    excluded = animal_selection_policy()["excluded_standalone_identities"]
    return str(text or "").casefold().strip() not in excluded


def reviewed_machine_animal_identity(text):
    reviewed = animal_selection_policy()["reviewed_machine_checked_identities"]
    return str(text or "").casefold().strip() in reviewed


def eligible_concept_entries(family, approval_mode="reviewed"):
    """Apply the explicit animal/object live-evaluation eligibility policy."""
    if family not in {"animals", "objects"}:
        raise ValueError("Only animals and objects are available for concept integration")
    if approval_mode not in {"reviewed", "evaluation"}:
        raise ValueError("approval_mode must be 'reviewed' or 'evaluation'")
    allowed = ({"editorially_reviewed"} if approval_mode == "reviewed"
               else {"editorially_reviewed", "machine_checked"})
    blocked_flags = {"trademark_risk", "real_person_risk", "discriminatory"}
    entries = []
    for entry in cached_catalogue().by_family[family]:
        grammar = entry.get("grammar", {})
        if (entry.get("approval_status") not in allowed
                or entry.get("familiarity") == "obscure"
                or blocked_flags & set(entry.get("editorial_flags", ()))
                or grammar.get("number") != "singular"
                or grammar.get("countability") != "countable"
                or len(entry.get("text", "").split()) > 5):
            continue
        if family == "animals" and not selectable_animal_identity(entry.get("text")):
            continue
        # The imported WordNet parentage is useful review evidence, but it
        # also labels anatomy, life stages and roles as animals. Until that
        # identity has editorial approval, do not use it as a standalone
        # species. The reviewed generator bank still supplies unusual animals.
        if (family == "animals"
                and entry.get("approval_status") != "editorially_reviewed"
                and not reviewed_machine_animal_identity(entry.get("text"))):
            continue
        if family == "objects" and entry.get("semantic_class") == "unclassified_object":
            continue
        if entry.get("approval_status") == "machine_checked":
            # Coarse WordNet parent labels are useful for review but not safe
            # automatic identities. Require a concrete classified child.
            if (family == "animals" and entry.get("category") == "oewn_animal"
                    and entry.get("semantic_class") in {"animal", "other_animal"}):
                continue
            if (family == "objects" and entry.get("semantic_class") in {
                    "physical_object", "architecture", "historical_object"}):
                continue
            definition = entry.get("definition", "").casefold()
            if any(term in definition for term in (
                    "instrument of execution", "forced labor", "torture",
                    "concentration camp", "sexual device", "dead body")):
                continue
        entries.append(entry)
    return tuple(entries)


class OfflineVocabularySelector:
    """Deterministic local sampling with semantic/familiarity and recent-use balance."""
    def __init__(self, catalogue, seed, recent_ids=()):
        self.catalogue = catalogue
        self.random = random.Random(seed)
        self.recent = set(recent_ids)

    def select(self, family, count, mechanisms=(), roles=()):
        pool = [entry for entry in self.catalogue.by_family[family]
                if entry["approval_status"] != "rejected"
                and not ({"trademark_risk", "real_person_risk", "discriminatory"}
                         & set(entry["editorial_flags"]))
                and (not mechanisms or set(entry["compatible_mechanisms"]) & set(mechanisms))
                and (not roles or ({entry["grammar"].get("role")} |
                                   set(entry["grammar"].get("roles", ()))) & set(roles))]
        if len(pool) < count:
            raise ValueError(f"Not enough compatible {family} ingredients")
        jitter = {entry["id"]: self.random.random() for entry in pool}
        semantic = Counter()
        chosen = []
        familiarity_targets = ("common", "common", "common", "unusual", "unusual", "obscure")
        while len(chosen) < count:
            target = familiarity_targets[len(chosen) % len(familiarity_targets)]
            options = [entry for entry in pool if entry not in chosen]
            options.sort(key=lambda entry: (
                entry["id"] not in self.recent,
                entry["familiarity"] == target,
                -semantic[entry["semantic_class"]],
                entry["humour"].get("comic_potential", 0),
                jitter[entry["id"]] + (.15 if entry["approval_status"] == "editorially_reviewed" else 0),
            ), reverse=True)
            selected = options[0]
            chosen.append(selected); semantic[selected["semantic_class"]] += 1
        return chosen
