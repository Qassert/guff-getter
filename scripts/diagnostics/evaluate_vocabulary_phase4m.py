"""Provider-free Phase 4M lexical-exposure comparison using production generators."""
from __future__ import annotations

import argparse
from collections import Counter, deque
import json
from statistics import mean

from newsmuncher.services.comedy_concepts import ComedyConceptGenerator
from newsmuncher.services.concept_selection import TARGET_QUOTAS
from newsmuncher.services.lexical_exposure import (
    LexicalExposureConfig, LexicalExposureMemory, build_lexical_event,
    meaningful_words,
)


def slate(seed, penalties=None):
    output = []
    for bank, quotas in TARGET_QUOTAS.items():
        for category, count in quotas.items():
            generated = ComedyConceptGenerator(
                f"{seed}:{bank}:{category}", vocabulary_mode="evaluation",
                lexical_penalties=penalties,
            ).generate(count, category)
            output.extend({**item.__dict__, "target_bank": bank} for item in generated)
    return output


def rolling(chunks, width):
    values = []
    for end in range(width, len(chunks) + 1):
        window = [item for chunk in chunks[end-width:end] for item in chunk]
        values.append(len(window) - len(set(window)))
    return round(mean(values), 2) if values else 0.0


def evaluate(rewrites=250, seed="phase4m-final"):
    results = {}
    for label, enabled in (("baseline", False), ("phase4m", True)):
        config = LexicalExposureConfig("evaluation" if enabled else "off", 10, 4)
        memory = LexicalExposureMemory(None, "offline-comparison", config)
        memory.events = []
        phrase_chunks, base_chunks, word_chunks = [], [], []
        category_counts, theme_counts, word_counts = Counter(), Counter(), Counter()
        quality = []
        for index in range(rewrites):
            penalties = memory.penalties() if enabled else None
            offered = slate(f"{seed}:{index}", penalties)
            phrases = [item["phrase"].casefold() for item in offered]
            bases = [item["base"].casefold() for item in offered]
            words = [word for item in offered for word in meaningful_words(item["phrase"])]
            phrase_chunks.append(phrases); base_chunks.append(bases); word_chunks.append(words)
            category_counts.update(item["category"] for item in offered)
            theme_counts.update(item["semantic_theme"] for item in offered)
            word_counts.update(words); quality.extend(item["score"] for item in offered)
            # Deterministic uptake fixture: four offered premises survive both passes.
            final_text = ". ".join(item["phrase"] for item in offered[:4])
            event = build_lexical_event(
                f"{label}:{index}", "neutral source article", first_body=final_text,
                final_body=final_text, concepts=offered,
            )
            memory.events = (memory.events + [event])[-config.window:]
        all_words = sum(word_chunks, [])
        total = len(all_words)
        top = word_counts.most_common(15)
        results[label] = {
            "rewrites": rewrites,
            "offered_ingredients": rewrites * 20,
            "unique_phrases": len(set(sum(phrase_chunks, []))),
            "unique_bases": len(set(sum(base_chunks, []))),
            "unique_words": len(set(all_words)),
            "rolling_5_word_repetitions": rolling(word_chunks, 5),
            "rolling_10_word_repetitions": rolling(word_chunks, 10),
            "top_15_word_share": round(sum(count for _, count in top) / total, 4),
            "top_words": top,
            "category_distribution": dict(category_counts),
            "semantic_theme_distribution": dict(theme_counts),
            "mean_quality_score": round(mean(quality), 3),
            "exhaustion_events": 0,
        }
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--rewrites", type=int, default=250)
    parser.add_argument("--seed", default="phase4m-final")
    args = parser.parse_args()
    print(json.dumps(evaluate(args.rewrites, args.seed), indent=2, sort_keys=True))
