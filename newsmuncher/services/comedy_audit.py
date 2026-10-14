"""Local-only JSONL audit records for successfully persisted comedy rewrites."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import re

from newsmuncher.config import PROJECT_ROOT
from newsmuncher.services.final_joke_memory import detect_final_jokes
from newsmuncher.services.topic_memory import detect_topics


AUDIT_ENV = "NEWSMUNCHER_COMEDY_AUDIT_LOG"
AUDIT_PATH_ENV = "NEWSMUNCHER_COMEDY_AUDIT_PATH"
DEFAULT_AUDIT_PATH = PROJECT_ROOT / "local_audits" / "comedy_audit.jsonl"
FEATURE_FLAGS = (
    "NEWSMUNCHER_EXPANDED_VOCABULARY",
    "NEWSMUNCHER_EXPANDED_DESCRIPTORS",
    "NEWSMUNCHER_EXPANDED_NAMES",
    "NEWSMUNCHER_COMEDY_SEMANTIC_MEMORY",
    "NEWSMUNCHER_FINAL_JOKE_MEMORY",
    "NEWSMUNCHER_COMEDY_TOPIC_MEMORY",
    "NEWSMUNCHER_LEXICAL_DIVERSITY",
    "NEWSMUNCHER_THEMATIC_DIVERSITY",
    "NEWSMUNCHER_THEME_INGREDIENTS",
    "NEWSMUNCHER_THEME_SPARKS",
    "NEWSMUNCHER_REPETITION_REPLACEMENT",
    "NEWSMUNCHER_PHRASE_REPLACEMENT",
    "NEWSMUNCHER_NOUN_EXCLUSION",
    "NEWSMUNCHER_COMEDY_VARIANT",
    "NEWSMUNCHER_NAME_MODE",
    "NEWSMUNCHER_CONCEPT_MODE",
    "NEWSMUNCHER_DESCRIPTOR_MODE",
)


@dataclass(frozen=True)
class ComedyAuditConfig:
    enabled: bool = False
    path: Path = DEFAULT_AUDIT_PATH

    @classmethod
    def from_environment(cls):
        mode = os.getenv(AUDIT_ENV, "off").strip().lower()
        if mode not in {"off", "on"}:
            raise ValueError(f"{AUDIT_ENV} must be off or on")
        configured = os.getenv(AUDIT_PATH_ENV, "").strip()
        path = Path(configured).expanduser() if configured else DEFAULT_AUDIT_PATH
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        return cls(mode == "on", path)


def _found(text, value):
    return bool(value and re.search(rf"(?<!\w){re.escape(str(value))}(?!\w)", text, re.I))


def _selected(items, fields):
    return [{key: item[key] for key in fields if item.get(key) not in (None, "", [])}
            for item in (items or [])]


def _numeric_metrics(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, dict):
        return {str(key): cleaned for key, item in value.items()
                if (cleaned := _numeric_metrics(item)) is not None}
    return None


def build_audit_record(*, rewrite_id, source, result, names=None, concepts=None,
                       descriptors=None, contenders=None, timings=None, environment=None,
                       timestamp=None, raw_ingredients=None, comparison_variant=None,
                       first_pass=None, lexical_context=None, thematic_context=None,
                       theme_ingredient_context=None,
                       repetition_replacement_context=None,
                       noun_exclusion_context=None, comedy_editor_context=None):
    """Build a fixed-schema record; arbitrary request/provider metadata is excluded."""
    environment = os.environ if environment is None else environment
    title = str(result.get("crazyReplacement1Title", ""))
    body = str(result.get("crazyReplacement1Extract", ""))
    final_text = f"{title}\n{body}"
    offered_names = [{"name": str(name)} for name in (names or [])]
    offered_concepts = _selected(concepts, (
        "phrase", "target_bank", "base", "animal_species", "category",
        "comic_mechanism", "semantic_theme", "premise_key", "generator_version",
    ))
    offered_descriptors = _selected(descriptors, (
        "phrase", "subject", "grammatical_role", "category", "comic_mechanism",
        "semantic_theme", "premise_key", "generator_version",
    ))
    raw_ingredients = list(raw_ingredients or [])
    contenders = contenders or {}
    legacy_offered = {key: [str(value) for value in contenders.get(key, [])]
                      for key in ("nouns", "animals", "adverbs", "slang", "places", "names")
                      if contenders.get(key)}
    found = {
        "names": [item for item in offered_names if _found(final_text, item["name"])],
        "concepts": [item for item in offered_concepts if _found(final_text, item.get("phrase"))],
        "descriptors": [item for item in offered_descriptors if _found(final_text, item.get("phrase"))],
        "legacy": {key: [value for value in values if _found(final_text, value)]
                   for key, values in legacy_offered.items()},
        "raw_hybrid_ingredients": [item for item in raw_ingredients
                                   if _found(final_text, item.get("text"))],
    }
    found["legacy"] = {key: values for key, values in found["legacy"].items() if values}
    joke_families = detect_final_jokes(final_text, "\n".join(str(source.get(key, ""))
                                                               for key in ("title", "description", "extract")))
    source_text = "\n".join(str(source.get(key, ""))
                            for key in ("title", "description", "extract"))
    record = {
        "schema_version": 1,
        "timestamp": (timestamp or datetime.now(timezone.utc)).isoformat(),
        "rewrite_id": str(rewrite_id),
        "source": {
            "headline": str(source.get("title", "")),
            "description": str(source.get("description", "")),
            "article_text": str(source.get("extract", "")),
        },
        "final": {"headline": title, "article_text": body},
        "ingredients": {
            "offered": {
                "generated_names": offered_names,
                "generated_concepts": offered_concepts,
                "generated_descriptors": offered_descriptors,
                "legacy_banks": legacy_offered,
                "raw_hybrid_ingredients": raw_ingredients,
            },
            "found_exactly_in_final": found,
        },
        "semantic": {
            "offered_premise_ids": list(dict.fromkeys(
                item["premise_key"] for item in offered_concepts + offered_descriptors
                if item.get("premise_key"))),
            "found_exact_premise_ids": list(dict.fromkeys(
                item["premise_key"] for item in found["concepts"] + found["descriptors"]
                if item.get("premise_key"))),
            "canonical_joke_families": joke_families,
            "topic_memory_detections": detect_topics(final_text, source_text),
        },
        "feature_flags": {name: environment.get(name, "default") for name in FEATURE_FLAGS},
    }
    if comparison_variant:
        record["comparison_variant"] = str(comparison_variant)
    if first_pass:
        record["first_pass"] = {
            "headline": str(first_pass.get("crazyReplacement1Title", "")),
            "article_text": str(first_pass.get("crazyReplacement1Extract", "")),
        }
    if comedy_editor_context:
        record["comedy_editor"] = {
            "enabled": bool(comedy_editor_context.get("enabled", False)),
            "invoked": bool(comedy_editor_context.get("invoked", False)),
            "model": str(comedy_editor_context.get("model", "")),
            "succeeded": bool(comedy_editor_context.get("succeeded", False)),
            "fell_back": bool(comedy_editor_context.get("fell_back", False)),
            "first_pass_word_count": int(
                comedy_editor_context.get("first_pass_word_count", 0)),
            "target_word_count": int(
                comedy_editor_context.get("target_word_count", 0)),
            "target_min_word_count": int(
                comedy_editor_context.get("target_min_word_count", 0)),
            "target_max_word_count": int(
                comedy_editor_context.get("target_max_word_count", 0)),
            "final_word_count": int(comedy_editor_context.get("final_word_count", 0)),
            "achieved_word_count": int(
                comedy_editor_context.get("achieved_word_count",
                                          comedy_editor_context.get("final_word_count", 0))),
            "percentage_reduction": comedy_editor_context.get("percentage_reduction"),
        }
    if lexical_context:
        penalties = lexical_context.get("penalties", {})
        record["lexical_exposure"] = {
            "recent_events": int(lexical_context.get("recent_events", 0)),
            "selection_penalties": {
                str(key): float(value) for key, value in penalties.items()
                if isinstance(value, (int, float))
            },
            "selected_with_penalty": [
                {"kind": str(item.get("kind", "")),
                 "text": str(item.get("text", "")),
                 "penalty": float(item.get("penalty", 0))}
                for item in lexical_context.get("selected_with_penalty", [])
                if isinstance(item, dict) and isinstance(item.get("penalty"), (int, float))
            ],
        }
    if thematic_context:
        record["thematic_diversity"] = {
            "recent_events": int(thematic_context.get("recent_events", 0)),
            "selection_penalties": {
                str(key): float(value)
                for key, value in thematic_context.get("selection_penalties", {}).items()
                if isinstance(value, (int, float))
            },
            "selected_domains": _selected(thematic_context.get("selected_domains"), (
                "id", "family", "label", "inspiration", "keywords")),
            "influenced_domains": _selected(thematic_context.get("influenced_domains"), (
                "id", "family", "matched_keywords")),
        }
    if theme_ingredient_context:
        selected_theme_items = theme_ingredient_context.get("selected", ())
        first_pass_text = "\n".join((
            str((first_pass or {}).get("crazyReplacement1Title", "")),
            str((first_pass or {}).get("crazyReplacement1Extract", "")),
        ))
        exact_fields = ("text", "target_bank", "grammatical_role", "construction_id")
        record["theme_ingredients"] = {
            "recent_events": int(theme_ingredient_context.get("recent_events", 0)),
            "selected": _selected(theme_ingredient_context.get("selected"), (
                "text", "target_bank", "grammatical_role", "source", "family",
                "domain_ids", "seed_ids", "seed_kinds", "construction_id",
                "cross_domain", "provenance")),
            "selection_penalties": {
                str(key): float(value)
                for key, value in theme_ingredient_context.get(
                    "selection_penalties", {}).items()
                if isinstance(value, (int, float))
            },
            "selection_metrics": _numeric_metrics(
                theme_ingredient_context.get("selection_metrics", {})) or {},
            "theme_sparks_enabled": bool(
                theme_ingredient_context.get("theme_sparks_enabled", False)),
            "prompt_placement": str(
                theme_ingredient_context.get("prompt_placement", "ordinary_ingredient_banks")),
            "found_exactly_in_first_pass": _selected(
                [item for item in selected_theme_items
                 if _found(first_pass_text, item.get("text"))], exact_fields),
            "found_exactly_in_final": _selected(
                [item for item in selected_theme_items
                 if _found(final_text, item.get("text"))], exact_fields),
        }
    if repetition_replacement_context is not None:
        context = repetition_replacement_context
        target_fields = ("text", "kind", "role", "recent_exposure",
                         "first_pass_occurrences", "reason")
        change_fields = ("text", "first_pass_occurrences", "final_occurrences",
                         "exactly_removed", "exactly_added")
        record["repetition_replacement"] = {
            "enabled": bool(context.get("enabled", False)),
            "phrase_replacement_enabled": bool(
                context.get("phrase_replacement_enabled", False)),
            "eligible_targets": _selected(context.get("eligible_targets"),
                target_fields + ("provenance", "ingredient_phrase", "semantic_theme")),
            "rejected_targets": _selected(context.get("rejected_targets"), target_fields),
            "overlap_exclusions": _selected(context.get("overlap_exclusions"), (
                "text", "reason", "overlapping_target", "recent_exposure")),
            "recent_exposure_signals": {
                str(key): float(value)
                for key, value in context.get("recent_exposure_signals", {}).items()
                if isinstance(value, (int, float))
            },
            "offered_alternatives": _selected(context.get("alternatives"), (
                "text", "kind", "role", "recent_exposure", "construction_id",
                "source_phrase", "domain_ids", "seed_kinds", "role_compatible",
                "length_distance")),
            "exact_target_changes": _selected(
                context.get("exact_target_changes"), change_fields),
            "exact_alternative_additions": _selected(
                context.get("exact_alternative_additions"), change_fields),
            "new_recently_overused_terms": [
                str(value) for value in context.get("new_recently_overused_terms", ())],
            "targets_removed_without_supplied_alternative": [
                str(value) for value in context.get(
                    "targets_removed_without_supplied_alternative", ())],
            "inventive_fallback": bool(context.get("inventive_fallback", False)),
            "fallback_domain_cues": [str(value) for value in
                                     context.get("fallback_domain_cues", ())],
            "maximum_substitutions": int(context.get("maximum_substitutions", 2)),
            "copy_edit_fell_back": bool(context.get("copy_edit_fell_back", False)),
        }
    if noun_exclusion_context is not None:
        record["noun_exclusion"] = {
            "enabled": bool(noun_exclusion_context.get("enabled", False)),
            "excluded_before": int(noun_exclusion_context.get("excluded_before", 0)),
            "reserved_ingredients": int(
                noun_exclusion_context.get("reserved_ingredients", 0)),
            "prevented_ingredient_candidates": int(
                noun_exclusion_context.get("prevented_ingredient_candidates", 0)),
            "offered_ingredient_violations": [str(value) for value in
                noun_exclusion_context.get("offered_ingredient_violations", ())],
            "model_introduced_violations": [str(value) for value in
                noun_exclusion_context.get("model_introduced_violations", ())],
            "newly_extracted": [str(value) for value in
                noun_exclusion_context.get("newly_extracted", ())],
        }
    safe_timings = _numeric_metrics(timings or {})
    if safe_timings:
        record["generation_metrics"] = safe_timings
    return record


class ComedyAuditLogger:
    def __init__(self, config=None):
        self.config = config or ComedyAuditConfig.from_environment()

    def append(self, record):
        """Atomically append once per rewrite UUID under an exclusive file lock."""
        if not self.config.enabled:
            return False
        self.config.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        descriptor = os.open(self.config.path, os.O_RDWR | os.O_CREAT, 0o600)
        with os.fdopen(descriptor, "r+", encoding="utf-8") as audit:
            fcntl.flock(audit.fileno(), fcntl.LOCK_EX)
            try:
                audit.seek(0)
                for line in audit:
                    try:
                        if json.loads(line).get("rewrite_id") == record["rewrite_id"]:
                            return False
                    except (json.JSONDecodeError, AttributeError):
                        continue
                audit.seek(0, os.SEEK_END)
                audit.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
                audit.flush()
                os.fsync(audit.fileno())
                return True
            finally:
                fcntl.flock(audit.fileno(), fcntl.LOCK_UN)
