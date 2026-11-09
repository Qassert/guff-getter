#!/usr/bin/env python3
"""Deterministic, provider-free comparison of Phase 4K prompt ingredients."""
from __future__ import annotations

from collections import Counter, deque
import argparse
import json
from statistics import mean

from newsmuncher.services.comedy_concepts import ComedyConceptGenerator
from newsmuncher.services.comedy_variants import build_variant
from newsmuncher.services.concept_selection import TARGET_QUOTAS


def slate(seed):
    result = []
    for bank, quotas in TARGET_QUOTAS.items():
        for category, count in quotas.items():
            values = ComedyConceptGenerator(f"{seed}:{bank}:{category}").generate(count, category)
            result += [{**item.__dict__, "target_bank": bank} for item in values]
    return result


def repeats(chunks, window):
    history, values = deque(maxlen=window - 1), []
    for chunk in chunks:
        prior = set(x for old in history for x in old)
        values.append(sum(x in prior for x in chunk)); history.append(chunk)
    return mean(values[window - 1:]) if len(values) >= window else 0


def evaluate(rewrites=250, seed="phase4k"):
    report = {}
    for label in "ABCD":
        phrases, words, mechanisms, domains, prompt_sizes = [], [], Counter(), Counter(), []
        raw_domains, generated_scores = [], []
        for index in range(rewrites):
            plan = build_variant(label, slate(f"{seed}:{index}"), f"{seed}:{index}")
            chunk = [item["phrase"].casefold() for item in plan["prompt"]]
            phrases.append(chunk)
            words.append([token for phrase in chunk for token in phrase.split()])
            for item in plan["generated"]:
                mechanisms[item["comic_mechanism"]] += 1
                domains[item["semantic_theme"]] += 1
                generated_scores.append(item["score"])
            for item in plan["raw"]:
                raw_domains.append(item.get("semantic_domain") or item["family"])
            prompt_sizes.append(sum(len(x) for x in chunk) + max(0, len(chunk) - 1) * 2)
        flat_phrases = [x for c in phrases for x in c]
        flat_words = [x for c in words for x in c]
        report[label] = {
            "ingredients": len(flat_phrases), "unique_ingredients": len(set(flat_phrases)),
            "unique_words": len(set(flat_words)), "mechanisms": len(mechanisms),
            "semantic_domains": len(domains) + len(set(raw_domains)),
            "raw_domains": len(set(raw_domains)),
            "rolling_five_repeated_ingredients": round(repeats(phrases, 5), 2),
            "rolling_ten_repeated_ingredients": round(repeats(phrases, 10), 2),
            "average_concept_prompt_characters": round(mean(prompt_sizes), 2),
            "average_generated_quality_proxy": round(mean(generated_scores), 3),
            "limitations": "No model output: humour, coherence, source relevance and latency are unmeasured.",
        }
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rewrites", type=int, default=250)
    parser.add_argument("--seed", default="phase4k-final")
    args = parser.parse_args()
    print(json.dumps(evaluate(args.rewrites, args.seed), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
