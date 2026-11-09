"""Default-off, evidence-led suggestions for the existing copy-edit pass."""
from __future__ import annotations

from dataclasses import dataclass
import os
import re

from newsmuncher.services.lexical_exposure import exposure_keys, meaningful_words, text_penalty


REPETITION_REPLACEMENT_ENV = "NEWSMUNCHER_REPETITION_REPLACEMENT"
PHRASE_REPLACEMENT_ENV = "NEWSMUNCHER_PHRASE_REPLACEMENT"
NARRATIVE_EXCLUSIONS = frozenset({
    "arranged", "arranging", "candidacy", "entered", "entering", "raced",
    "racing", "working", "worked", "announced", "claimed", "confirmed",
    "continued", "described", "explained", "reported", "said", "told",
})


@dataclass(frozen=True)
class RepetitionReplacementConfig:
    mode: str = "off"
    minimum_exposure: float = 6.0
    maximum_targets: int = 3
    maximum_alternatives: int = 2
    maximum_substitutions: int = 2

    @classmethod
    def from_environment(cls):
        return cls(os.getenv(REPETITION_REPLACEMENT_ENV, "off").strip().lower())

    def __post_init__(self):
        if self.mode not in {"off", "evaluation"}:
            raise ValueError(f"{REPETITION_REPLACEMENT_ENV} must be off or evaluation")

    @property
    def enabled(self):
        return self.mode == "evaluation"


@dataclass(frozen=True)
class PhraseReplacementConfig:
    mode: str = "off"

    @classmethod
    def from_environment(cls):
        return cls(os.getenv(PHRASE_REPLACEMENT_ENV, "off").strip().lower())

    def __post_init__(self):
        if self.mode not in {"off", "evaluation"}:
            raise ValueError(f"{PHRASE_REPLACEMENT_ENV} must be off or evaluation")

    @property
    def enabled(self):
        return self.mode == "evaluation"


def _occurrences(text, value):
    if not value:
        return 0
    return len(re.findall(rf"(?<!\w){re.escape(str(value))}(?!\w)", str(text), re.I))


def _identity_candidates(concepts, descriptors, raw_ingredients):
    for item in concepts or ():
        value = item.get("base") or item.get("phrase")
        if value:
            yield str(value), "concept", item.get("target_bank", ""), item
    for item in descriptors or ():
        value = item.get("subject")
        if value:
            yield str(value), "descriptor", item.get("grammatical_role", ""), item
    for item in raw_ingredients or ():
        value = item.get("base") or item.get("subject") or item.get("text")
        if value:
            kind = "descriptor" if item.get("grammatical_role") else "concept"
            role = item.get("grammatical_role") or item.get("target_bank", "")
            yield str(value), kind, role, item


def _protected_values(names=(), places=()):
    protected = set()
    for value in tuple(names or ()) + tuple(places or ()):
        protected.update(meaningful_words(str(value)))
        normalized = " ".join(meaningful_words(str(value)))
        if normalized:
            protected.add(normalized)
    return protected


def build_repetition_replacement(*, first_pass, source_text, lexical_penalties,
                                 concepts=(), descriptors=(), raw_ingredients=(),
                                 thematic_ingredients=(), names=(), places=(), config=None,
                                 phrase_config=None):
    """Build conservative replacement guidance and exact-evidence diagnostics."""
    config = config or RepetitionReplacementConfig()
    phrase_config = phrase_config or PhraseReplacementConfig()
    diagnostic = {
        "enabled": config.enabled, "eligible_targets": [], "rejected_targets": [],
        "alternatives": [], "maximum_substitutions": config.maximum_substitutions,
        "copy_edit_fell_back": False, "phrase_replacement_enabled": phrase_config.enabled,
        "overlap_exclusions": [], "inventive_fallback": False, "fallback_domain_cues": [],
    }
    if not config.enabled:
        return None, diagnostic

    first_text = "\n".join((
        str(first_pass.get("crazyReplacement1Title", "")),
        str(first_pass.get("crazyReplacement1Extract", "")),
    ))
    source_keys = set(exposure_keys(source_text, include_identity=False))
    protected = _protected_values(names, places)
    seen = set()
    candidates = []
    for identity, kind, role, provenance in _identity_candidates(
            concepts, descriptors, raw_ingredients):
        words = meaningful_words(identity)
        if phrase_config.enabled:
            # The base/subject/text came directly from a selected ingredient. Treat it
            # as one atomic comic identity; never guess phrases from surrounding prose.
            values = [" ".join(words)] if 1 <= len(words) <= 4 else []
        else:
            values = ([" ".join(words)] if 2 <= len(words) <= 4 else []) + list(words)
        for value in values:
            value = value.casefold()
            if value in seen:
                continue
            seen.add(value)
            if phrase_config.enabled:
                component_signals = [float(lexical_penalties.get("word:" + word, 0.0))
                                     for word in meaningful_words(value)]
                identity_signal = float(lexical_penalties.get(
                    "identity:" + "-".join(meaningful_words(value)), 0.0))
                signal = max([identity_signal, *component_signals], default=0.0)
            elif " " in value:
                signal = float(lexical_penalties.get(
                    "identity:" + "-".join(meaningful_words(value)), 0.0))
            else:
                signal = float(lexical_penalties.get("word:" + value, 0.0))
            reason = None
            if _occurrences(first_text, value) == 0:
                reason = "absent_from_first_pass"
            elif value in NARRATIVE_EXCLUSIONS:
                reason = "narrative_or_ordinary_language"
            elif value in protected or any(word in protected for word in meaningful_words(value)):
                reason = "protected_name_or_location"
            elif any(("word:" + word) in source_keys for word in meaningful_words(value)):
                reason = "required_by_source"
            elif signal < config.minimum_exposure:
                reason = "below_recent_exposure_threshold"
            record = {"text": value, "kind": kind, "role": str(role or ""),
                      "recent_exposure": signal,
                      "first_pass_occurrences": _occurrences(first_text, value),
                      "provenance": str(provenance.get("source") or
                                        provenance.get("generator_version") or "selected_ingredient"),
                      "ingredient_phrase": str(provenance.get("phrase") or
                                               provenance.get("text") or identity),
                      "semantic_theme": str(provenance.get("semantic_theme", ""))}
            if reason:
                record["reason"] = reason
                diagnostic["rejected_targets"].append(record)
            else:
                candidates.append(record)
    candidates.sort(key=lambda item: (-item["recent_exposure"],
                                      -len(meaningful_words(item["text"])), item["text"]))
    if phrase_config.enabled:
        selected = []
        for candidate in candidates:
            candidate_words = set(meaningful_words(candidate["text"]))
            overlap = next((item for item in selected
                            if candidate_words & set(meaningful_words(item["text"]))), None)
            if overlap:
                rejected = dict(candidate, reason="overlaps_selected_target",
                                overlapping_target=overlap["text"])
                diagnostic["overlap_exclusions"].append(rejected)
                continue
            selected.append(candidate)
            if len(selected) == config.maximum_targets:
                break
        diagnostic["eligible_targets"] = selected
        for target in selected:
            for word in meaningful_words(target["text"]):
                if word != target["text"] and float(
                        lexical_penalties.get("word:" + word, 0.0)) >= config.minimum_exposure:
                    diagnostic["overlap_exclusions"].append({
                        "text": word, "reason": "component_of_selected_phrase",
                        "overlapping_target": target["text"],
                        "recent_exposure": float(lexical_penalties.get("word:" + word, 0.0)),
                    })
    else:
        diagnostic["eligible_targets"] = candidates[:config.maximum_targets]
    if not diagnostic["eligible_targets"]:
        return None, diagnostic

    target_roles = {(item["kind"], item["role"]) for item in diagnostic["eligible_targets"]}
    target_lengths = [len(meaningful_words(item["text"]))
                      for item in diagnostic["eligible_targets"]]
    alternatives = []
    for item in thematic_ingredients or ():
        full_text = str(item.get("text") or item.get("phrase") or "").strip()
        text = (str(item.get("subject") or item.get("base") or full_text).strip()
                if phrase_config.enabled else full_text)
        if not text or _occurrences(first_text, text):
            continue
        kind = "descriptor" if item.get("grammatical_role") else "concept"
        role = str(item.get("grammatical_role") or item.get("target_bank") or "")
        exact_role = (kind, role) in target_roles
        compatible = exact_role or any(k == kind for k, _ in target_roles)
        if not compatible:
            continue
        word_count = len(meaningful_words(text))
        if phrase_config.enabled and not 1 <= word_count <= 4:
            continue
        alternatives.append({
            "text": text, "kind": kind, "role": role,
            "recent_exposure": text_penalty(text, lexical_penalties),
            "construction_id": str(item.get("construction_id", "")),
            "source_phrase": full_text, "domain_ids": list(item.get("domain_ids", ())),
            "seed_kinds": list(item.get("seed_kinds", ())),
            "role_compatible": exact_role,
            "length_distance": min((abs(word_count - length)
                                    for length in target_lengths), default=99),
        })
    alternatives.sort(key=lambda item: (not item.get("role_compatible", False),
                                        item["recent_exposure"],
                                        item.get("length_distance", 99), item["text"]))
    diagnostic["alternatives"] = alternatives[:config.maximum_alternatives]
    if phrase_config.enabled and not diagnostic["alternatives"] and thematic_ingredients:
        diagnostic["inventive_fallback"] = True
        diagnostic["fallback_domain_cues"] = list(dict.fromkeys(
            domain for item in thematic_ingredients for domain in item.get("domain_ids", ())))[:4]
    if not diagnostic["alternatives"] and not diagnostic["inventive_fallback"]:
        return None, diagnostic
    return {
        "targets": diagnostic["eligible_targets"],
        "alternatives": diagnostic["alternatives"],
        "maximum_substitutions": config.maximum_substitutions,
        "phrase_replacement": phrase_config.enabled,
        "inventive_fallback": diagnostic["inventive_fallback"],
        "fallback_domain_cues": diagnostic["fallback_domain_cues"],
    }, diagnostic


def finish_repetition_diagnostic(diagnostic, first_pass, final_result, fell_back=False):
    """Add conservative exact before/after evidence without semantic claims."""
    if not diagnostic:
        return diagnostic
    first_text = "\n".join((str(first_pass.get("crazyReplacement1Title", "")),
                              str(first_pass.get("crazyReplacement1Extract", ""))))
    final_text = "\n".join((str(final_result.get("crazyReplacement1Title", "")),
                              str(final_result.get("crazyReplacement1Extract", ""))))
    diagnostic["copy_edit_fell_back"] = bool(fell_back)
    diagnostic["exact_target_changes"] = [
        {"text": item["text"], "first_pass_occurrences": _occurrences(first_text, item["text"]),
         "final_occurrences": _occurrences(final_text, item["text"]),
         "exactly_removed": (_occurrences(first_text, item["text"]) > 0 and
                             _occurrences(final_text, item["text"]) == 0)}
        for item in diagnostic.get("eligible_targets", ())
    ]
    diagnostic["exact_alternative_additions"] = [
        {"text": item["text"], "first_pass_occurrences": _occurrences(first_text, item["text"]),
         "final_occurrences": _occurrences(final_text, item["text"]),
         "exactly_added": (_occurrences(first_text, item["text"]) == 0 and
                           _occurrences(final_text, item["text"]) > 0)}
        for item in diagnostic.get("alternatives", ())
    ]
    exposed = {key[5:] for key in diagnostic.get("recent_exposure_signals", {})
               if key.startswith("word:")}
    diagnostic["new_recently_overused_terms"] = sorted(
        word for word in exposed if _occurrences(first_text, word) == 0 and
        _occurrences(final_text, word) > 0)
    supplied_added = any(item["exactly_added"]
                         for item in diagnostic["exact_alternative_additions"])
    diagnostic["targets_removed_without_supplied_alternative"] = [
        item["text"] for item in diagnostic["exact_target_changes"]
        if item["exactly_removed"] and not supplied_added]
    return diagnostic
