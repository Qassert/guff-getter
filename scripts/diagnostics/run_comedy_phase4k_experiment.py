#!/usr/bin/env python3
"""Run the bounded Phase 4K experiment through the real text provider pipeline."""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import random
import re
from statistics import mean
from types import SimpleNamespace
from uuid import uuid5, NAMESPACE_URL

from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from newsmuncher.config import PROJECT_ROOT, PROMPT_FILE, WORDS_DIR
from newsmuncher.services.comedy_audit import build_audit_record
from newsmuncher.services.comedy_variants import build_variant
from newsmuncher.services.concept_selection import CONCEPT_GUIDANCE, ConceptRegistry, ConceptSelectionConfig
from newsmuncher.services.descriptor_selection import (DESCRIPTOR_GUIDANCE, DescriptorRegistry,
                                                        DescriptorSelectionConfig, prompt_descriptor)
from newsmuncher.services.final_joke_memory import FinalJokeMemory, FinalJokeMemoryConfig
from newsmuncher.services.name_selection import (INVENTED_NAME_GUIDANCE, InventedNameRegistry,
                                                 NameSelectionConfig)
from newsmuncher.services.topic_memory import TopicMemory, TopicMemoryConfig, build_topic_event
from newsmuncher.services.vocabulary_catalogue import BLOCKED
from newsmuncher.services.word_shuffle import read_bank
from newsmuncher.services.rewrite_title import final_title
from newsmuncher.utils.clean_data import (copy_edit_pass, format_shizzalise_result,
                                         prepare_prompt, send_prompt)
from newsmuncher.utils.file_handler import load_prompt
from scripts.diagnostics.export_comedy_comparison import export as export_blind


SOURCES_PATH = Path(__file__).parent / "fixtures" / "phase4k_sources.json"
BASE_OUTPUT = PROJECT_ROOT / "local_audits" / "phase4k_experiment"
VARIANTS = "ABCD"
BASE_FEATURES = {
    "NEWSMUNCHER_EXPANDED_VOCABULARY": "evaluation",
    "NEWSMUNCHER_EXPANDED_DESCRIPTORS": "evaluation",
    "NEWSMUNCHER_EXPANDED_NAMES": "off",
    "NEWSMUNCHER_COMEDY_SEMANTIC_MEMORY": "evaluation",
    "NEWSMUNCHER_FINAL_JOKE_MEMORY": "evaluation",
    "NEWSMUNCHER_COMEDY_TOPIC_MEMORY": "evaluation",
    "NEWSMUNCHER_COMEDY_AUDIT_LOG": "on",
    "NEWSMUNCHER_NAME_MODE": "invented",
    "NEWSMUNCHER_CONCEPT_MODE": "generated",
    "NEWSMUNCHER_DESCRIPTOR_MODE": "generated",
}


def _get(document, path):
    value = document
    for part in path.split("."):
        if isinstance(value, list):
            return [item.get(part) for item in value if isinstance(item, dict)]
        if not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    return value


def _matches(document, query):
    for key, wanted in query.items():
        if key == "$and" and not all(_matches(document, item) for item in wanted): return False
        if key == "$or" and not any(_matches(document, item) for item in wanted): return False
        if key.startswith("$"): continue
        actual = _get(document, key)
        if isinstance(wanted, dict):
            if "$exists" in wanted and (actual is not None) != wanted["$exists"]: return False
            if "$lte" in wanted and (actual is None or actual > wanted["$lte"]): return False
            if "$in" in wanted and actual not in wanted["$in"]: return False
            if "$ne" in wanted:
                if isinstance(actual, list) and wanted["$ne"] in actual: return False
                if not isinstance(actual, list) and actual == wanted["$ne"]: return False
        elif actual != wanted:
            return False
    return True


def _apply(document, update, inserted=False):
    if inserted: document.update(deepcopy(update.get("$setOnInsert", {})))
    document.update(deepcopy(update.get("$set", {})))
    for key, amount in update.get("$inc", {}).items(): document[key] = document.get(key, 0) + amount
    for key in update.get("$unset", {}): document.pop(key, None)
    for key, spec in update.get("$push", {}).items():
        values = list(spec.get("$each", [])) if isinstance(spec, dict) else [spec]
        document.setdefault(key, []).extend(deepcopy(values))
        if isinstance(spec, dict) and "$slice" in spec:
            document[key] = document[key][spec["$slice"]:]


class MemoryCollection:
    """Small Mongo-shaped store sufficient for the existing comedy services."""
    def __init__(self): self.docs = {}

    def find(self, query, projection=None):
        return [deepcopy(doc) for doc in self.docs.values() if _matches(doc, query)]

    def find_one(self, query, projection=None):
        return next(iter(self.find(query, projection)), None)

    def update_one(self, query, update, upsert=False):
        existing = next((doc for doc in self.docs.values() if _matches(doc, query)), None)
        if existing is not None:
            _apply(existing, update); return SimpleNamespace(matched_count=1, upserted_id=None)
        key = query.get("_id")
        if key in self.docs: raise DuplicateKeyError("in-memory unique _id collision")
        if not upsert: return SimpleNamespace(matched_count=0, upserted_id=None)
        document = {"_id": key}; _apply(document, update, True); self.docs[key] = document
        return SimpleNamespace(matched_count=0, upserted_id=key)

    def update_many(self, query, update):
        matches = [doc for doc in self.docs.values() if _matches(doc, query)]
        for doc in matches: _apply(doc, update)
        return SimpleNamespace(modified_count=len(matches))

    def find_one_and_update(self, query, update, upsert=False, return_document=None):
        before = self.find_one(query)
        self.update_one(query, update, upsert)
        after = self.find_one({"_id": query.get("_id")})
        return after if return_document == ReturnDocument.AFTER else before


def local_banks(seed, count=10):
    rng = random.Random(seed)
    result = {}
    filenames = {"slang": "slang.csv", "places": "places.csv"}
    for bank, filename in filenames.items():
        values = [value for value in read_bank(Path(WORDS_DIR) / filename)
                  if not any(term in value.casefold() for term in BLOCKED)]
        rng.shuffle(values)
        result[bank] = values[:count]
    result.update({"nouns": [], "animals": [], "adverbs": [], "names": []})
    return result


def scorecard_from_key(key_path, output):
    import csv
    with Path(key_path).open(encoding="utf-8", newline="") as handle:
        labels = [row["output"] for row in csv.DictReader(handle)]
    lines = ["# Phase 4K blind scorecard", "",
             "Score each criterion from 1 (low) to 5 (high).", "",
             "| Output | Funniness | Originality | Coherence | Variety | Overall preference | Comments |",
             "|---|---:|---:|---:|---:|---:|---|"]
    lines += [f"| {label} |  |  |  |  |  |  |" for label in labels]
    Path(output).write_text("\n".join(lines) + "\n", encoding="utf-8")


def metrics(records):
    motifs = {"powered": r"\b[a-z][a-z'-]*[- ]powered\s+[a-z]",
              "parliament": r"\bparliament\w*\b", "royal": r"\broyal\w*\b",
              "crumpet": r"\bcrumpets?\b"}
    output = {}
    for label in VARIANTS:
        rows = [r for r in records if r.get("comparison_variant") == label]
        texts = [f"{r['final']['headline']} {r['final']['article_text']}" for r in rows]
        words = [word for text in texts for word in re.findall(r"[a-z]+(?:'[a-z]+)?", text.casefold())]
        offered = [item for r in rows for item in r["ingredients"]["offered"]["generated_concepts"]]
        raw = [item for r in rows for item in r["ingredients"]["offered"]["raw_hybrid_ingredients"]]
        found = [item for r in rows for item in r["ingredients"]["found_exactly_in_final"]["concepts"]]
        found_raw = [item for r in rows for item in r["ingredients"]["found_exactly_in_final"]["raw_hybrid_ingredients"]]
        joke_keys = [x["key"] for r in rows for x in r["semantic"]["canonical_joke_families"]]
        topic_keys = [x["key"] for r in rows for x in r["semantic"]["topic_memory_detections"]]
        output[label] = {
            "articles": len(rows), "mean_article_words": round(mean(map(len, [re.findall(r'\w+', t) for t in texts])), 2),
            "unique_output_words": len(set(words)), "generated_premises_offered": len(offered),
            "raw_identities_offered": len(raw), "generated_phrases_found_exactly": len(found),
            "raw_identities_found_exactly": len(found_raw),
            "semantic_themes_offered": len({x.get("semantic_theme") for x in offered}),
            "canonical_joke_families": len(set(joke_keys)),
            "repeated_canonical_joke_occurrences": len(joke_keys) - len(set(joke_keys)),
            "repeated_detected_topic_occurrences": len(topic_keys) - len(set(topic_keys)),
            "motifs": {name: sum(bool(re.search(pattern, text, re.I)) for text in texts)
                       for name, pattern in motifs.items()},
        }
    return output


def append_jsonl(path, record):
    with Path(path).open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
        handle.flush(); os.fsync(handle.fileno())


def execute(run_dir, dry_run=False):
    sources = json.loads(SOURCES_PATH.read_text(encoding="utf-8"))
    if len(sources) != 7 or len({item["id"] for item in sources}) != 7:
        raise ValueError("Phase 4K source fixture must contain seven unique sources")
    run_dir.mkdir(parents=True, exist_ok=False)
    (run_dir / "sources.json").write_text(json.dumps(sources, ensure_ascii=False, indent=2) + "\n")
    manifest = {"experiment": "phase4k-abcd", "created_at": datetime.now(timezone.utc).isoformat(),
                "dry_run": dry_run, "variants": {}, "source_ids": [x["id"] for x in sources],
                "memory_policy": "fresh stores per variant; seven sequential articles share within-variant memory",
                "provider_model": "gpt-6-sol", "provider_calls_planned": 0 if dry_run else 56,
                "configuration": {"expanded_vocabulary": "evaluation", "expanded_descriptors": "evaluation",
                                  "semantic_memory": "evaluation", "final_joke_memory": "evaluation",
                                  "topic_memory": "evaluation", "audit": "local experiment files"}}
    all_records = []
    prompt_template = load_prompt(PROMPT_FILE)
    for label in VARIANTS:
        stores = {name: MemoryCollection() for name in ("names", "concepts", "descriptors", "final", "topics")}
        names = InventedNameRegistry(stores["names"], NameSelectionConfig(semantic_memory_mode="evaluation"))
        concepts = ConceptRegistry(stores["concepts"], ConceptSelectionConfig(
            vocabulary_mode="evaluation", semantic_memory_mode="evaluation"))
        descriptors = DescriptorRegistry(stores["descriptors"], DescriptorSelectionConfig(
            vocabulary_mode="evaluation", semantic_memory_mode="evaluation"))
        final_memory = FinalJokeMemory(stores["final"], FinalJokeMemoryConfig("evaluation"))
        topic_memory = TopicMemory(stores["topics"], TopicMemoryConfig("evaluation"))
        variant_path = run_dir / f"variant_{label}.jsonl"
        errors = []
        for source_index, source in enumerate(sources):
            rewrite_id = str(uuid5(NAMESPACE_URL, f"{run_dir.name}:{label}:{source['id']}"))
            selection_key = f"phase4k:{label}:{source_index}:{rewrite_id}"
            try:
                topic_memory.load()
                name_slate = names.offer(selection_key, topic_memory.recent_name_families())
                recent_concepts = sum((topic_memory.penalties(field, prefix) for field, prefix in (
                    ("concept_phrases", "phrase:"), ("concept_premises", "premise:"),
                    ("concept_bases", "base:"))), Counter())
                full_concepts = concepts.offer(selection_key, recent_concepts)
                plan = build_variant(label, full_concepts, selection_key, "evaluation")
                theme_counts = Counter(item["semantic_theme"] for item in full_concepts)
                descriptor_slate = descriptors.offer(
                    selection_key, [theme for theme, count in theme_counts.items() if count >= 3],
                    sum((topic_memory.penalties(field, prefix) for field, prefix in (
                        ("descriptor_phrases", "offered:"),
                        ("descriptor_premises", "offered-premise:"))), Counter()))
                overrides = {bank: [x["phrase"] for x in plan["prompt"] if x["target_bank"] == bank]
                             for bank in ("nouns", "animals")}
                timing = {"comedy_variant": plan["counts"]}
                random.seed(f"{selection_key}:prompt")
                prepared = prepare_prompt(
                    source, 10, prompt_template, names_override=name_slate,
                    name_guidance=INVENTED_NAME_GUIDANCE, concept_overrides=overrides,
                    concept_guidance=CONCEPT_GUIDANCE + ("\n\n" + plan["guidance"] if plan["guidance"] else ""),
                    descriptor_overrides=[prompt_descriptor(x) for x in descriptor_slate],
                    descriptor_guidance=DESCRIPTOR_GUIDANCE,
                    final_joke_guidance=final_memory.guidance(), topic_guidance=topic_memory.guidance(),
                    diagnostics=timing, word_banks_override=local_banks(selection_key))
                if dry_run:
                    result = {"crazyReplacement1Title": f"DRY RUN {label} {source['id']}",
                              "crazyReplacement1Extract": "No provider call made."}
                else:
                    first = send_prompt(prepared["full_prompt"])
                    result = format_shizzalise_result(first)
                    if not result: raise RuntimeError("first rewrite call returned no valid article")
                    result = copy_edit_pass(result) or result
                    result["crazyReplacement1Title"] = final_title(
                        result["crazyReplacement1Extract"], result["crazyReplacement1Title"])
                source_text = "\n".join(source[k] for k in ("title", "description", "extract"))
                family_map = names.offered_family_map(selection_key)
                topic_event = build_topic_event(
                    rewrite_id, result, source, name_slate, family_map,
                    plan["generated"], descriptor_slate)
                final_memory.accept(rewrite_id, result["crazyReplacement1Title"],
                                    result["crazyReplacement1Extract"], source_text)
                names.accept(selection_key, rewrite_id, name_slate,
                             result["crazyReplacement1Title"], result["crazyReplacement1Extract"])
                concepts.accept(selection_key, rewrite_id, plan["generated"],
                                result["crazyReplacement1Title"], result["crazyReplacement1Extract"], source_text)
                descriptors.accept(selection_key, rewrite_id, descriptor_slate,
                                   result["crazyReplacement1Title"], result["crazyReplacement1Extract"], source_text)
                topic_memory.record(topic_event)
                record = build_audit_record(
                    rewrite_id=rewrite_id, source=source, result=result, names=name_slate,
                    concepts=plan["generated"], descriptors=descriptor_slate,
                    contenders=prepared["contenders"], timings=timing,
                    raw_ingredients=plan["raw"], comparison_variant=label,
                    environment={**BASE_FEATURES, "NEWSMUNCHER_COMEDY_VARIANT": label})
                record["experiment_source_id"] = source["id"]
                record["experiment_source_category"] = source["category"]
                append_jsonl(variant_path, record); all_records.append(record)
            except Exception as exc:
                names.release(selection_key); concepts.release(selection_key); descriptors.release(selection_key)
                error = {"variant": label, "source_id": source["id"],
                         "error_type": type(exc).__name__, "message": str(exc)[:300]}
                errors.append(error); append_jsonl(run_dir / "errors.jsonl", error)
        manifest["variants"][label] = {"successful": sum(r["comparison_variant"] == label for r in all_records),
                                       "errors": errors}
    combined = run_dir / "combined.jsonl"
    for record in all_records: append_jsonl(combined, record)
    export_blind(combined, run_dir / "blind_comparison.md", run_dir / "answer_key.csv",
                 seed=run_dir.name)
    scorecard_from_key(run_dir / "answer_key.csv", run_dir / "scorecard.md")
    objective = metrics(all_records)
    expected_pairs = {(label, source["id"]) for label in VARIANTS for source in sources}
    actual_pairs = {(record["comparison_variant"], record["experiment_source_id"])
                    for record in all_records}
    validation = {
        "seven_per_variant": all(sum(r["comparison_variant"] == label for r in all_records) == 7
                                 for label in VARIANTS),
        "all_28_variant_source_pairs": actual_pairs == expected_pairs and len(all_records) == 28,
        "blind_versions": len(re.findall(
            r"^### Article \d+ — Version \d+$",
            (run_dir / "blind_comparison.md").read_text(encoding="utf-8"), re.M)) == len(all_records),
        "answer_key_rows": sum(1 for _ in (run_dir / "answer_key.csv").open(encoding="utf-8")) - 1 == len(all_records),
    }
    report = ["# Phase 4K automated experiment", "", f"Successful outputs: {len(all_records)}/28", "",
              "Memory isolation: fresh in-memory stores per variant; sequential memory within each variant.", "",
              "## Validation", "", "```json", json.dumps(validation, indent=2), "```", "",
              "## Objective metrics", "", "```json", json.dumps(objective, indent=2), "```", "",
              "Objective metrics do not measure funniness. Use the blind scorecard before opening the key.", ""]
    (run_dir / "experiment_report.md").write_text("\n".join(report), encoding="utf-8")
    manifest["successful_outputs"] = len(all_records); manifest["objective_metrics"] = objective
    manifest["validation"] = validation
    (run_dir / "run_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--output-dir")
    args = parser.parse_args()
    if not args.dry_run and not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY is not configured; no calls made")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = Path(args.output_dir) if args.output_dir else BASE_OUTPUT / stamp
    manifest = execute(run_dir, args.dry_run)
    print(json.dumps({"run_dir": str(run_dir), "successful_outputs": manifest["successful_outputs"]}))


if __name__ == "__main__":
    main()
