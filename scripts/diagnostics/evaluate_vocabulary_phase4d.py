"""Offline Phase 4D live-selector comparison; no provider or real database use."""
from collections import Counter
import contextlib
import io
from statistics import mean
from time import monotonic

from newsmuncher.services.comedy_concepts import ComedyConceptGenerator
from newsmuncher.services.vocabulary_catalogue import (
    cached_catalogue, eligible_concept_entries,
)


def _run(mode, rewrites):
    offered, prompted, appeared = [], [], []
    times, prompt_characters = [], []
    with contextlib.redirect_stdout(io.StringIO()):
        for number in range(rewrites):
            key = f"phase4d:{mode}:{number}"
            started = monotonic(); generated = ComedyConceptGenerator(
                key, vocabulary_mode=mode).generate(20)
            slate = [item.__dict__ for item in generated]
            times.append((monotonic() - started) * 1000)
            offered.extend(item["base"] for item in slate)
            prompted.extend(item["base"] for item in slate)
            prompt_characters.append(sum(len(item["phrase"]) + 2 for item in slate))
            final = slate[number % len(slate):(number % len(slate)) + 3]
            if len(final) < 3: final += slate[:3 - len(final)]
            appeared.extend(item["base"] for item in final)

    def metrics(values):
        counts = Counter(values)
        return {"total": len(values), "unique": len(counts),
                "duplicates": len(values) - len(counts),
                "most_common": counts.most_common(10)}
    return {
        "offered": metrics(offered), "passed_to_prompt": metrics(prompted),
        "appeared_in_mock_final": metrics(appeared),
        "selection_ms": {"average": round(mean(times), 2),
                         "maximum": round(max(times), 2)},
        "concept_prompt_characters": {"average": round(mean(prompt_characters), 2),
                                      "maximum": max(prompt_characters)},
    }


def review_summary():
    result = {}
    for family in ("animals", "objects"):
        reviewed = eligible_concept_entries(family, "reviewed")
        evaluation = eligible_concept_entries(family, "evaluation")
        machine = [x for x in evaluation if x["approval_status"] == "machine_checked"]
        strong = list(reviewed)
        ambiguous_terms = {"first", "second", "three", "four", "five", "number",
                           "head", "young", "baby", "game", "body", "high", "style",
                           "shoulder", "pocket", "host", "kill", "male", "female"}
        awkward = [x for x in machine if len(x["text"].split()) >= 4
                   or x["text"].casefold() in ambiguous_terms]
        unusual = [x for x in machine if x["familiarity"] == "unusual"]
        total_machine = sum(x["approval_status"] == "machine_checked"
                            for x in cached_catalogue().by_family[family])
        result[family] = {
            "reviewed_eligible": len(reviewed), "evaluation_eligible": len(evaluation),
            "machine_checked_only": len(machine),
            "machine_checked_excluded_by_gate": total_machine - len(machine),
            "strong_candidate_examples": [x["text"] for x in strong[:20]],
            "awkward_candidate_examples": [x["text"] for x in awkward[:20]],
            "unusual_needs_review_examples": [x["text"] for x in unusual[:20]],
        }
    return result


def run(rewrites=250):
    return {"rewrites": rewrites, "review": review_summary(),
            "existing": _run("off", rewrites),
            "expanded_evaluation": _run("evaluation", rewrites)}


if __name__ == "__main__":
    import argparse, json
    parser = argparse.ArgumentParser(); parser.add_argument("--rewrites", type=int, default=250)
    print(json.dumps(run(parser.parse_args().rewrites), indent=2))
