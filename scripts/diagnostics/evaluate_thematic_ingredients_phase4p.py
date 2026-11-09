#!/usr/bin/env python3
"""Provider-free four-way Phase 4P ingredient-selection comparison."""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
import json
from statistics import mean
from time import monotonic
from types import SimpleNamespace

from newsmuncher.services.comedy_concepts import ComedyConceptGenerator
from newsmuncher.services.comedy_descriptors import ComedyDescriptorGenerator
from newsmuncher.services.comedy_variants import build_variant
from newsmuncher.services.concept_selection import TARGET_QUOTAS
from newsmuncher.services.lexical_exposure import meaningful_words
from newsmuncher.services.thematic_diversity import (
    ThematicDiversityConfig, ThematicDiversityMemory, thematic_event,
)
from newsmuncher.services.thematic_ingredients import (
    ThemeIngredientConfig, ThemeIngredientMemory, ThematicIngredientBuilder,
    theme_ingredient_event,
)


FAMILIAR = {"gravy", "custard", "marmalade", "crumpet", "bunting", "kettle",
            "parliamentary", "royal", "queue", "milk", "float"}


class MemoryCollection:
    def __init__(self): self.docs = {}
    def find_one(self, query, projection=None):
        return deepcopy(self.docs.get(query["_id"]))
    def update_one(self, query, update, upsert=False):
        key = query["_id"]; document = self.docs.get(key)
        rewrite = query.get("events.rewrite_id", {}).get("$ne")
        if document and rewrite in {x["rewrite_id"] for x in document.get("events", [])}:
            return SimpleNamespace(matched_count=0, upserted_id=None)
        inserted = document is None
        if inserted:
            document = {"_id": key, **deepcopy(update.get("$setOnInsert", {}))}
            self.docs[key] = document
        spec = update["$push"]["events"]
        document.setdefault("events", []).extend(deepcopy(spec["$each"]))
        document["events"] = document["events"][spec["$slice"]:]
        return SimpleNamespace(matched_count=0 if inserted else 1,
                               upserted_id=key if inserted else None)


def concept_slate(seed):
    output = []
    for bank, quotas in TARGET_QUOTAS.items():
        for category, count in quotas.items():
            values = ComedyConceptGenerator(
                f"{seed}:{bank}:{category}", vocabulary_mode="evaluation").generate(
                    count, category)
            output.extend({**item.__dict__, "target_bank": bank} for item in values)
    return output


def descriptor_slate(seed):
    return [item.__dict__ for item in ComedyDescriptorGenerator(
        seed, expansion_mode="evaluation").generate(10)]


def rolling_repetition(chunks, width):
    results = []
    for index, current in enumerate(chunks):
        previous = set().union(*chunks[max(0, index-width):index]) if index else set()
        results.append(len(set(current) & previous))
    return round(mean(results), 3)


def evaluate(generations=500, seed="phase4p-final"):
    configurations = {
        "baseline": (False, False),
        "phase4n": (True, False),
        "phase4p": (False, True),
        "combined": (True, True),
    }
    state = {}
    for label, (phase4n, phase4p) in configurations.items():
        state[label] = {
            "phase4n": phase4n, "phase4p": phase4p,
            "domain_collection": MemoryCollection(),
            "ingredient_collection": MemoryCollection(),
            "phrases": [], "words": [], "constructions": [],
            "domains": Counter(), "families": Counter(), "seed_kinds": Counter(),
            "categories": Counter(), "familiar": Counter(),
            "ranking_losses": 0, "theme_offered": 0, "theme_after_ranking": 0,
            "cross_domain": 0,
            "examples": [],
            "local_seconds": 0.0, "prompt_characters": 0,
        }
    domain_config = ThematicDiversityConfig("evaluation", 4, 20)
    ingredient_config = ThemeIngredientConfig("evaluation", 2, 1, 20)
    for index in range(generations):
        rewrite_seed = f"{seed}:{index}"
        concepts = concept_slate(rewrite_seed)
        descriptors = descriptor_slate(rewrite_seed)
        for label, metrics in state.items():
            started = monotonic()
            selected_domains = []
            if metrics["phase4n"] or metrics["phase4p"]:
                domain_memory = ThematicDiversityMemory(
                    metrics["domain_collection"], label, domain_config)
                domain_memory.load(); selected_domains = domain_memory.select(rewrite_seed)
                domain_memory.record(thematic_event(f"{label}:{index}", selected_domains))
                metrics["theme_offered"] += len(selected_domains)
            plan = build_variant("A", concepts, rewrite_seed, "evaluation")
            prompt_descriptors = list(descriptors)
            selected = []
            if metrics["phase4p"]:
                ingredient_memory = ThemeIngredientMemory(
                    metrics["ingredient_collection"], label, ingredient_config)
                ingredient_memory.load()
                builder = ThematicIngredientBuilder(
                    selected_domains, rewrite_seed, ingredient_config,
                    ingredient_memory.penalties())
                plan = builder.apply_concepts(plan)
                prompt_descriptors, _ = builder.apply_descriptors(descriptors)
                selected = builder.selected
                ingredient_memory.record(theme_ingredient_event(
                    f"{label}:{index}", selected))
                metrics["ranking_losses"] += builder.last_metrics["ranking_losses"]
                metrics["theme_after_ranking"] += len(selected)
                metrics["cross_domain"] += sum(bool(x.get("cross_domain")) for x in selected)
                for item in selected:
                    metrics["domains"].update(item.get("domain_ids", ()))
                    metrics["seed_kinds"].update(item.get("seed_kinds", ()))
                    if len(metrics["examples"]) < 30:
                        metrics["examples"].append({
                            "text": item["text"], "domain_ids": item["domain_ids"],
                            "seed_kinds": item["seed_kinds"],
                            "construction_id": item["construction_id"],
                        })
            phrases = [item.get("phrase", item.get("text", "")) for item in plan["prompt"]]
            phrases.extend(item["phrase"] for item in prompt_descriptors)
            words = [word for phrase in phrases for word in meaningful_words(phrase)]
            constructions = [item.get("comic_mechanism", "raw") for item in plan["prompt"]]
            constructions.extend(item.get("construction_id", item.get("comic_mechanism", ""))
                                 for item in prompt_descriptors)
            metrics["phrases"].append(phrases); metrics["words"].append(words)
            metrics["prompt_characters"] += sum(len(value) for value in phrases)
            metrics["constructions"].append(constructions)
            metrics["categories"].update(item.get("target_bank", "descriptor")
                                          for item in plan["prompt"] + prompt_descriptors)
            metrics["familiar"].update(word for word in words if word in FAMILIAR)
            for domain in selected_domains:
                metrics["families"][domain["family"]] += 1
            metrics["local_seconds"] += monotonic() - started
    results = {}
    for label, metrics in state.items():
        flat_phrases = [x.casefold() for chunk in metrics["phrases"] for x in chunk]
        flat_words = [x for chunk in metrics["words"] for x in chunk]
        all_constructions = [x for chunk in metrics["constructions"] for x in chunk]
        results[label] = {
            "generations": generations,
            "ingredients_offered": len(flat_phrases),
            "unique_ingredients": len(set(flat_phrases)),
            "unique_vocabulary": len(set(flat_words)),
            "conceptual_domains_represented": len(metrics["domains"]),
            "conceptual_families_selected": len(metrics["families"]),
            "cross_domain_ingredients": metrics["cross_domain"],
            "unique_constructions": len(set(all_constructions)),
            "rolling_5_phrase_repetition": rolling_repetition(metrics["phrases"], 5),
            "rolling_10_phrase_repetition": rolling_repetition(metrics["phrases"], 10),
            "rolling_5_construction_repetition": rolling_repetition(
                metrics["constructions"], 5),
            "ranking_stage_losses": metrics["ranking_losses"],
            "theme_domains_before_ranking": metrics["theme_offered"],
            "theme_ingredients_after_ranking": metrics["theme_after_ranking"],
            "familiar_word_share": round(sum(metrics["familiar"].values()) /
                                          max(1, len(flat_words)), 5),
            "mean_ingredient_characters_per_generation": round(
                metrics["prompt_characters"] / generations, 2),
            "mean_local_transformation_ms": round(
                metrics["local_seconds"] * 1000 / generations, 3),
            "familiar_distribution": dict(metrics["familiar"]),
            "seed_kind_distribution": dict(metrics["seed_kinds"]),
            "category_distribution": dict(metrics["categories"]),
            "stored_domain_events": sum(len(x.get("events", ()))
                                        for x in metrics["domain_collection"].docs.values()),
            "stored_ingredient_events": sum(len(x.get("events", ()))
                                            for x in metrics["ingredient_collection"].docs.values()),
            "examples": metrics["examples"],
        }
    results["interpretation"] = {
        "phase4n_ingredient_equivalence_expected": (
            "Phase 4N changes optional prompt guidance, so provider-free ingredient metrics "
            "remain baseline-equivalent."),
        "combined_ingredient_equivalence_expected": (
            "Combined and Phase 4P use the same ingredient architecture; only combined adds "
            "Phase 4N prompt guidance, whose final-text effect needs human/provider evaluation."),
        "humour_limit": "These selection metrics cannot establish which configuration is funniest.",
    }
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--generations", type=int, default=500)
    parser.add_argument("--seed", default="phase4p-final")
    parser.add_argument("--output")
    args = parser.parse_args()
    payload = json.dumps(evaluate(args.generations, args.seed), indent=2, sort_keys=True)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as target:
            target.write(payload + "\n")
    else:
        print(payload)


if __name__ == "__main__":
    main()
