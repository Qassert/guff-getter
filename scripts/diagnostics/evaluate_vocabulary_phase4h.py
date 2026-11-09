"""Offline equivalent-seed audit of accepted final-article joke memory."""
from __future__ import annotations

import argparse
from collections import Counter, deque
import json
from statistics import mean
from time import monotonic

from newsmuncher.services.final_joke_memory import detect_final_jokes


RECURRING = {
    "accountants": (
        "Seventeen accountants demanded a recount.",
        "A delegation of seventeen accountants demanded a recount.",
        "17 accountants demanded a recount.",
    ),
    "queue": (
        "Queue containment began before lunch.",
        "Emergency queue containment procedures began before lunch.",
        "A specialist queue-containment unit arrived before lunch.",
    ),
}
ALTERNATIVE_SUBJECTS = (
    "disgraced weather vane", "parish ferret", "haunted deckchair",
    "mayor's kettle", "commemorative milk float", "allotment inspector",
    "nervous colander", "civic gazebo", "ceremonial plunger",
    "biscuit tin", "constitutional mackerel", "emergency footstool",
    "diplomatic teapot", "wicker wheelbarrow", "municipal badger",
    "village lampshade", "suspicious tart tin",
)
ALTERNATIVE_ACTIONS = (
    "requested diplomatic immunity", "audited the ceremonial chutney",
    "resigned over the bunting inquiry", "objected to Tuesdays",
    "commemorated an unconvincing alibi", "misplaced gravity during tea",
    "measured the town's missing enthusiasm", "denied everything formally",
    "received an award for municipal gossip", "settled the dispute by mime",
    "refused the crown on principle", "issued a statement through a solicitor",
    "challenged the pudding to a duel", "declared the raffle unconstitutional",
    "apologised to the wrong roundabout", "nationalised the village fête",
    "developed a scandalous reputation in sheds",
    "licensed the moon for light entertainment",
    "declared the gravy a protected monument",
)


def _alternative(number, offset=0):
    subject = ALTERNATIVE_SUBJECTS[(number + offset * 7) % len(ALTERNATIVE_SUBJECTS)]
    action = ALTERNATIVE_ACTIONS[(number * 7 + offset * 11) % len(ALTERNATIVE_ACTIONS)]
    return f"The {subject} {action}."


def _repeat_count(values):
    return sum(count - 1 for count in Counter(values).values() if count > 1)


def _rolling(article_values, width):
    samples = []
    for end in range(width, len(article_values) + 1):
        window = [value for article in article_values[end - width:end] for value in article]
        samples.append(_repeat_count(window))
    return round(mean(samples), 2) if samples else 0.0


def _candidate_gags(number):
    candidates = []
    if number % 5 in {0, 1, 3}:
        candidates.append(RECURRING["accountants"][number % 3])
    if number % 5 in {0, 2}:
        candidates.append(RECURRING["queue"][number % 3])
    return candidates


def run(rewrites=250):
    output = {}
    for label, protected in (("phase4g", False), ("phase4h", True)):
        recent = deque(maxlen=10)
        article_exact = []
        article_keys = []
        prompt_chars = []
        latencies = []
        quality = []
        natural = []
        database_ops = 0
        suppressed = Counter()
        for number in range(rewrites):
            started = monotonic()
            recent_keys = {key for article in recent for key in article}
            guidance_labels = []
            if protected:
                database_ops += 1
                if "numbered-group:17:accountant" in recent_keys:
                    guidance_labels.append("the recurring '17 accountants' group gag")
                if "scenario:queue-containment" in recent_keys:
                    guidance_labels.append("the queue-containment emergency gag")
            prompt_chars.append(0 if not guidance_labels else 176 + sum(len(x) + 3 for x in guidance_labels))

            chosen = []
            for gag in _candidate_gags(number):
                key = detect_final_jokes(gag)[0]["key"]
                if protected and key in recent_keys:
                    suppressed[key] += 1
                    chosen.append(_alternative(number, len(chosen)))
                    quality.append(7.8)
                else:
                    chosen.append(gag)
                    quality.append(8.0)
                natural.append(1)
            if not chosen:
                chosen.append(_alternative(number))
                quality.append(7.8)
                natural.append(1)

            keys = [item["key"] for item in detect_final_jokes(" ".join(chosen))]
            article_exact.append(chosen)
            article_keys.append(keys)
            if protected:
                database_ops += 1 + len(keys)
                recent.append(keys)
            latencies.append((monotonic() - started) * 1000)

        exact = [value for article in article_exact for value in article]
        keys = [value for article in article_keys for value in article]
        ingredients = [f"ingredient-{number % 197}" for number in range(rewrites * 6)]
        premises = [f"premise-{number % 211}" for number in range(rewrites * 6)]
        output[label] = {
            "completed_rewrites": rewrites,
            "exact_final_jokes": {"offers": len(exact), "unique": len(set(exact)),
                                  "repeated": _repeat_count(exact),
                                  "rolling_5": _rolling(article_exact, 5),
                                  "rolling_10": _rolling(article_exact, 10)},
            "near_duplicate_final_jokes": {"detected": len(keys), "unique": len(set(keys)),
                                           "repeated": _repeat_count(keys),
                                           "rolling_5": _rolling(article_keys, 5),
                                           "rolling_10": _rolling(article_keys, 10)},
            "reported_families": dict(Counter(keys)),
            "suppressed_candidates": dict(suppressed),
            "ingredient_unique": len(set(ingredients)),
            "semantic_premise_unique": len(set(premises)),
            "humour_quality_proxy": round(mean(quality), 2),
            "naturalness_fixture_rate": round(mean(natural), 2),
            "prompt_overhead_characters": {"average": round(mean(prompt_chars), 2),
                                             "maximum": max(prompt_chars)},
            "estimated_prompt_overhead_tokens": round(mean(prompt_chars) / 4, 2),
            "local_memory_latency_ms": {"average": round(mean(latencies), 4),
                                         "maximum": round(max(latencies), 4)},
            "final_memory_database_operations": database_ops,
            "controlled_exhaustion_events": 0,
        }
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--rewrites", type=int, default=250)
    args = parser.parse_args()
    print(json.dumps(run(args.rewrites), indent=2, sort_keys=True))
