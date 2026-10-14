#!/usr/bin/env python3
"""Run the controlled Phase 4M off/on finished-article experiment."""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import csv
import hashlib
import json
import os
from pathlib import Path
import random
import re
from statistics import mean
from uuid import NAMESPACE_URL, uuid5

from newsmuncher.config import PROJECT_ROOT, PROMPT_FILE
from newsmuncher.services.comedy_audit import build_audit_record
from newsmuncher.services.comedy_variants import build_variant
from newsmuncher.services.concept_selection import CONCEPT_GUIDANCE, ConceptRegistry, ConceptSelectionConfig
from newsmuncher.services.descriptor_selection import (DESCRIPTOR_GUIDANCE, DescriptorRegistry,
                                                        DescriptorSelectionConfig, prompt_descriptor)
from newsmuncher.services.final_joke_memory import FinalJokeMemory, FinalJokeMemoryConfig
from newsmuncher.services.lexical_exposure import (LexicalExposureConfig, LexicalExposureMemory,
                                                   build_lexical_event, exposure_keys,
                                                   meaningful_words, text_penalty)
from newsmuncher.services.name_selection import (INVENTED_NAME_GUIDANCE, InventedNameRegistry,
                                                 NameSelectionConfig)
from newsmuncher.services.topic_memory import TopicMemory, TopicMemoryConfig, build_topic_event
from newsmuncher.services.rewrite_title import final_title
from newsmuncher.utils.clean_data import (copy_edit_pass, format_shizzalise_result,
                                         prepare_prompt, send_prompt)
from newsmuncher.utils.file_handler import load_prompt
from scripts.diagnostics.run_comedy_phase4k_experiment import (MemoryCollection, SOURCES_PATH,
                                                               append_jsonl, local_banks)


BASE_OUTPUT = PROJECT_ROOT / "local_audits" / "phase4m_live_experiment"
GROUPS = ("off", "evaluation")
REPETITIONS = 3
FEATURES = {
    "NEWSMUNCHER_EXPANDED_VOCABULARY": "evaluation",
    "NEWSMUNCHER_EXPANDED_DESCRIPTORS": "evaluation",
    "NEWSMUNCHER_EXPANDED_NAMES": "off",
    "NEWSMUNCHER_COMEDY_SEMANTIC_MEMORY": "evaluation",
    "NEWSMUNCHER_FINAL_JOKE_MEMORY": "evaluation",
    "NEWSMUNCHER_COMEDY_TOPIC_MEMORY": "evaluation",
    "NEWSMUNCHER_COMEDY_AUDIT_LOG": "on",
    "NEWSMUNCHER_COMEDY_VARIANT": "A",
    "NEWSMUNCHER_NAME_MODE": "invented",
    "NEWSMUNCHER_CONCEPT_MODE": "generated",
    "NEWSMUNCHER_DESCRIPTOR_MODE": "generated",
}
WATCH_WORDS = ("gravy", "custard", "marmalade", "cucumber slicer", "crumpet", "milk float")
NON_NOUN_SUFFIXES = ("ly", "ing", "ed", "ous", "ive", "able", "ible", "al", "ful", "less")


def _term_pattern(phrase):
    return re.compile(r"(?<!\w)" + re.escape(phrase).replace(r"\ ", r"[- ]") +
                      r"s?(?!\w)", re.I)


def _experiment_sources():
    sources = json.loads(SOURCES_PATH.read_text(encoding="utf-8"))[:6]
    if len(sources) != 6 or len({item["id"] for item in sources}) != 6:
        raise ValueError("Phase 4M requires six distinct Phase 4K source fixtures")
    return sources


def _stores():
    collections = {name: MemoryCollection() for name in
                   ("names", "concepts", "descriptors", "final", "topics", "lexical")}
    return {
        "collections": collections,
        "names": InventedNameRegistry(collections["names"], NameSelectionConfig(
            semantic_memory_mode="evaluation")),
        "concepts": ConceptRegistry(collections["concepts"], ConceptSelectionConfig(
            vocabulary_mode="evaluation", semantic_memory_mode="evaluation")),
        "descriptors": DescriptorRegistry(collections["descriptors"], DescriptorSelectionConfig(
            vocabulary_mode="evaluation", semantic_memory_mode="evaluation")),
        "final": FinalJokeMemory(collections["final"], FinalJokeMemoryConfig("evaluation")),
        "topics": TopicMemory(collections["topics"], TopicMemoryConfig("evaluation")),
    }


def _schedule(sources):
    """Counterbalance group order while preserving each group's sequential memory."""
    rows = []
    for repetition in range(REPETITIONS):
        for source_index, source in enumerate(sources):
            order = GROUPS if (source_index + repetition) % 2 == 0 else tuple(reversed(GROUPS))
            rows.extend((group, repetition, source_index, source) for group in order)
    return rows


def _ingredient_texts(record):
    offered = record["ingredients"]["offered"]
    for item in offered.get("generated_concepts", []):
        yield item.get("phrase", "")
    for item in offered.get("generated_descriptors", []):
        yield item.get("phrase", "")
    for item in offered.get("generated_names", []):
        yield item.get("name", "")


def _rolling_repetition(sets, window):
    values = []
    for index, current in enumerate(sets):
        prior = set().union(*sets[max(0, index - window):index]) if index else set()
        values.append(len(current & prior))
    return round(mean(values), 2) if values else 0.0


def objective_metrics(records):
    output = {}
    for group in GROUPS:
        rows = [row for row in records if row["experiment_group"] == group]
        word_sets, phrase_sets, offered_sets, all_words, all_phrases = [], [], [], [], []
        model_only = set()
        pass_one_only, copy_added, source_exempt = set(), set(), set()
        theme_counts, final_family_counts, watch = Counter(), Counter(), Counter()
        for row in rows:
            source = f"{row['source']['headline']} {row['source']['article_text']}"
            offered = " ".join(_ingredient_texts(row))
            first = f"{row.get('first_pass', {}).get('headline', '')} " \
                    f"{row.get('first_pass', {}).get('article_text', '')}"
            final = f"{row['final']['headline']} {row['final']['article_text']}"
            source_words, offered_words = set(meaningful_words(source)), set(meaningful_words(offered))
            offered_sets.append(offered_words)
            first_words, final_words = set(meaningful_words(first)), set(meaningful_words(final))
            words = list(meaningful_words(final)); all_words.extend(words); word_sets.append(set(words))
            tokens = list(meaningful_words(final))
            phrases = [" ".join(tokens[i:i + 2]) for i in range(len(tokens) - 1)]
            phrase_sets.append(set(phrases)); all_phrases.extend(phrases)
            model_only.update(final_words - source_words - offered_words)
            pass_one_only.update(first_words - source_words - offered_words)
            copy_added.update(final_words - first_words - source_words - offered_words)
            source_exempt.update(final_words & source_words)
            for item in row["ingredients"]["offered"].get("generated_concepts", []):
                theme_counts[item.get("semantic_theme", "unknown")] += 1
            for item in row.get("semantic", {}).get("topic_memory_detections", []):
                final_family_counts[item.get("key", "unknown")] += 1
            for item in row.get("semantic", {}).get("canonical_joke_families", []):
                final_family_counts[item.get("key", "unknown")] += 1
            for phrase in WATCH_WORDS:
                if _term_pattern(phrase).search(final): watch[phrase] += 1
        counts, phrase_counts = Counter(all_words), Counter(all_phrases)
        total = len(all_words)
        top = counts.most_common(15)
        noun_candidates = [(word, count) for word, count in counts.most_common()
                           if count > 1 and not word.endswith(NON_NOUN_SUFFIXES)][:30]
        noun_phrases = [(phrase, count) for phrase, count in phrase_counts.most_common()
                        if count > 1][:30]
        repeated_occurrences = sum(count - 1 for count in counts.values() if count > 1)
        output[group] = {
            "articles": len(rows), "final_meaningful_words": total,
            "unique_meaningful_words": len(counts),
            "unique_meaningful_words_per_1000": round(1000 * len(counts) / total, 2) if total else 0,
            "rolling_five_repeated_words": _rolling_repetition(word_sets, 5),
            "rolling_ten_repeated_words": _rolling_repetition(word_sets, 10),
            "rolling_five_repeated_bigrams": _rolling_repetition(phrase_sets, 5),
            "rolling_ten_repeated_bigrams": _rolling_repetition(phrase_sets, 10),
            "offered_unique_meaningful_words": len(set().union(*offered_sets)),
            "offered_rolling_five_repeated_words": _rolling_repetition(offered_sets, 5),
            "offered_rolling_ten_repeated_words": _rolling_repetition(offered_sets, 10),
            "repeated_word_occurrences_per_1000": round(
                1000 * repeated_occurrences / total, 2) if total else 0,
            "top_15_words": top,
            "top_15_share": round(sum(count for _, count in top) / total, 4) if total else 0,
            "repeated_noun_candidates": noun_candidates,
            "repeated_two_word_phrases": noun_phrases,
            "offered_semantic_families": dict(theme_counts),
            "final_detected_semantic_families": dict(final_family_counts),
            "model_introduced_unique_words": len(model_only),
            "first_pass_model_introduced_unique_words": len(pass_one_only),
            "copy_edit_added_unique_words": len(copy_added),
            "source_required_unique_words_in_final": len(source_exempt),
            "watched_article_counts": dict(watch),
        }
    return output


def _blind_export(records, run_dir, seed):
    rng = random.Random(int.from_bytes(hashlib.sha256(seed.encode()).digest()[:8], "big"))
    groups = {}
    for record in records:
        groups.setdefault(record["experiment_source_id"], []).append(record)
    lines = ["# NewsMuncher Phase 4M blind comparison", "",
             "Read and score all versions before opening answer_key.csv.", ""]
    keys = []
    for article_index, source_id in enumerate(sorted(groups), 1):
        versions = list(groups[source_id]); rng.shuffle(versions)
        source = versions[0]["source"]
        lines += [f"## Source {article_index}", "", f"**{source['headline']}**", "",
                  source["article_text"], ""]
        for version_index, record in enumerate(versions, 1):
            label = f"Source {article_index} — Version {version_index}"
            lines += [f"### {label}", "", f"**{record['final']['headline']}**", "",
                      record["final"]["article_text"], ""]
            keys.append({"output": label, "group": record["experiment_group"],
                         "repetition": record["experiment_repetition"],
                         "rewrite_id": record["rewrite_id"], "source_id": source_id})
    (run_dir / "blind_comparison.md").write_text("\n".join(lines), encoding="utf-8")
    with (run_dir / "answer_key.csv").open("w", encoding="utf-8", newline="") as handle:
        fields = (keys[0].keys() if keys else
                  ("output", "group", "repetition", "rewrite_id", "source_id"))
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerows(keys)


def execute(run_dir, dry_run=False):
    sources = _experiment_sources()
    run_dir.mkdir(parents=True, exist_ok=False)
    (run_dir / "sources.json").write_text(json.dumps(sources, ensure_ascii=False, indent=2) + "\n")
    states = {group: _stores() for group in GROUPS}
    records, errors = [], []
    prompt_template = load_prompt(PROMPT_FILE)
    schedule = _schedule(sources)
    manifest = {
        "experiment": "phase4m-live-off-on", "created_at": datetime.now(timezone.utc).isoformat(),
        "dry_run": dry_run, "model": "gpt-6-sol", "phase4k_variant": "A",
        "provider_calls_planned": 0 if dry_run else 72,
        "source_ids": [source["id"] for source in sources],
        "memory_policy": "isolated stores per group; 18 sequential articles accumulate within each group",
        "schedule": [{"group": g, "repetition": r, "source_id": s["id"]}
                     for g, r, _, s in schedule],
        "configuration": FEATURES,
    }
    for sequence, (group, repetition, source_index, source) in enumerate(schedule):
        state = states[group]
        rewrite_id = str(uuid5(NAMESPACE_URL, f"{run_dir.name}:{group}:{repetition}:{source['id']}"))
        key = f"phase4m:{group}:{repetition}:{source_index}:{rewrite_id}"
        lexical = LexicalExposureMemory(
            state["collections"]["lexical"], f"phase4m-{group}",
            LexicalExposureConfig(group if group == "evaluation" else "off"))
        try:
            source_text = "\n".join(source[k] for k in ("title", "description", "extract"))
            lexical.load(); penalties = lexical.penalties(source_text); guidance = lexical.guidance(source_text)
            state["topics"].load()
            names = state["names"].offer(key, state["topics"].recent_name_families())
            recent_concepts = sum((state["topics"].penalties(field, prefix) for field, prefix in (
                ("concept_phrases", "phrase:"), ("concept_premises", "premise:"),
                ("concept_bases", "base:"))), Counter())
            concepts = state["concepts"].offer(key, recent_concepts, lexical_penalties=penalties)
            plan = build_variant("A", concepts, key, "evaluation", lexical_penalties=penalties)
            themes = Counter(item["semantic_theme"] for item in concepts)
            descriptor_penalties = sum((state["topics"].penalties(field, prefix) for field, prefix in (
                ("descriptor_phrases", "offered:"), ("descriptor_premises", "offered-premise:"))), Counter())
            descriptors = state["descriptors"].offer(
                key, [theme for theme, count in themes.items() if count >= 3], descriptor_penalties,
                lexical_penalties=penalties)
            overrides = {bank: [x["phrase"] for x in plan["prompt"] if x["target_bank"] == bank]
                         for bank in ("nouns", "animals")}
            timing = {"comedy_variant": plan["counts"], "sequence": sequence}
            random.seed(f"{key}:prompt")
            prepared = prepare_prompt(
                source, 10, prompt_template, names_override=names,
                name_guidance=INVENTED_NAME_GUIDANCE, concept_overrides=overrides,
                concept_guidance=CONCEPT_GUIDANCE,
                descriptor_overrides=[prompt_descriptor(x) for x in descriptors],
                descriptor_guidance=DESCRIPTOR_GUIDANCE,
                final_joke_guidance=state["final"].guidance(),
                topic_guidance="\n\n".join(x for x in (state["topics"].guidance(), guidance) if x),
                diagnostics=timing, word_banks_override=local_banks(key))
            if dry_run:
                first_result = {"crazyReplacement1Title": f"DRY RUN {source['id']}",
                                "crazyReplacement1Extract": "No provider call made."}
                result = dict(first_result)
            else:
                first_result = format_shizzalise_result(send_prompt(prepared["full_prompt"]))
                if not first_result: raise RuntimeError("first rewrite call returned no valid article")
                result = copy_edit_pass(first_result) or dict(first_result)
                result["crazyReplacement1Title"] = final_title(
                    result["crazyReplacement1Extract"], result["crazyReplacement1Title"])
            family_map = state["names"].offered_family_map(key)
            topic_event = build_topic_event(rewrite_id, result, source, names, family_map,
                                            plan["generated"], descriptors)
            state["final"].accept(rewrite_id, result["crazyReplacement1Title"],
                                  result["crazyReplacement1Extract"], source_text)
            state["names"].accept(key, rewrite_id, names, result["crazyReplacement1Title"],
                                  result["crazyReplacement1Extract"])
            state["concepts"].accept(key, rewrite_id, plan["generated"],
                                     result["crazyReplacement1Title"],
                                     result["crazyReplacement1Extract"], source_text)
            state["descriptors"].accept(key, rewrite_id, descriptors,
                                        result["crazyReplacement1Title"],
                                        result["crazyReplacement1Extract"], source_text)
            state["topics"].record(topic_event)
            event = build_lexical_event(
                rewrite_id, source_text, first_result["crazyReplacement1Title"],
                first_result["crazyReplacement1Extract"], result["crazyReplacement1Title"],
                result["crazyReplacement1Extract"], plan["generated"], descriptors, plan["raw"])
            lexical.record(event)
            selected = []
            for kind, items, field in (("concept", plan["generated"], "phrase"),
                                       ("descriptor", descriptors, "phrase")):
                for item in items:
                    if (penalty := text_penalty(item.get(field, ""), penalties)):
                        selected.append({"kind": kind, "text": item[field], "penalty": penalty})
            record = build_audit_record(
                rewrite_id=rewrite_id, source=source, result=result, names=names,
                concepts=plan["generated"], descriptors=descriptors,
                contenders=prepared["contenders"], timings=timing,
                raw_ingredients=plan["raw"], comparison_variant="A",
                environment={**FEATURES, "NEWSMUNCHER_LEXICAL_DIVERSITY": group},
                first_pass=first_result,
                lexical_context={"recent_events": len(lexical.events),
                                 "penalties": dict(penalties),
                                 "selected_with_penalty": selected})
            record.update({"experiment_group": group, "experiment_repetition": repetition + 1,
                           "experiment_source_id": source["id"],
                           "experiment_source_category": source["category"]})
            append_jsonl(run_dir / f"group_{group}.jsonl", record); records.append(record)
        except Exception as exc:
            state["names"].release(key); state["concepts"].release(key); state["descriptors"].release(key)
            error = {"group": group, "source_id": source["id"], "repetition": repetition + 1,
                     "error_type": type(exc).__name__, "message": str(exc)[:300]}
            errors.append(error); append_jsonl(run_dir / "errors.jsonl", error)
    for record in records: append_jsonl(run_dir / "combined.jsonl", record)
    _blind_export(records, run_dir, run_dir.name)
    measurement = objective_metrics(records)
    (run_dir / "vocabulary_measurements.json").write_text(
        json.dumps(measurement, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    validation = {"successful_outputs": len(records), "expected_outputs": 36,
                  "errors": len(errors), "group_counts": Counter(
                      record["experiment_group"] for record in records),
                  "lexical_documents": {group: len(states[group]["collections"]["lexical"].docs)
                                        for group in GROUPS}}
    manifest.update({"validation": validation, "objective_metrics": measurement})
    (run_dir / "run_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, default=dict) + "\n", encoding="utf-8")
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
    # Deliberately do not print group metrics or the answer key before blind review.
    print(json.dumps({"run_dir": str(run_dir),
                      "successful_outputs": manifest["validation"]["successful_outputs"],
                      "blind_comparison": str(run_dir / "blind_comparison.md")}))


if __name__ == "__main__":
    main()
