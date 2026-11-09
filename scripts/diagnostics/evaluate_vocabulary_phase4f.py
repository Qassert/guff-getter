"""Equivalent-seed Phase 4F comparison; local resources and mocked uptake only."""
from collections import Counter
import csv, json, random, re, resource
from pathlib import Path
from statistics import mean
from time import monotonic

from newsmuncher.config import WORDS_DIR
from newsmuncher.services.comedy_descriptors import descriptor_slate
from newsmuncher.services.comedy_names import ComedyNameGenerator
from newsmuncher.services.comedy_expressions import ComedyExpressionGenerator


def legacy(filename):
    with (WORDS_DIR / filename).open(encoding="utf-8", newline="") as source:
        return list(dict.fromkeys(x.strip() for row in csv.reader(source) for x in row if x.strip()))


def signature(value):
    letters = re.sub("[^a-z]", "", value.casefold())
    return re.sub(r"([cv])\1+", r"\1", "".join("v" if x in "aeiouy" else "c" for x in letters))


def metrics(values, per=10):
    chunks = [values[i:i+per] for i in range(0, len(values), per)]
    repeats = []
    for i in range(len(chunks)-9):
        window = sum(chunks[i:i+10], [])
        repeats.append(len(window)-len(set(window)))
    return {"offered": len(values), "unique": len(set(values)),
            "duplicates": len(values)-len(set(values)),
            "rolling_ten_repeats": round(mean(repeats), 2) if repeats else 0}


def run(rewrites=250):
    old_slang, old_places = legacy("slang.csv"), legacy("places.csv")
    result = {}
    for label, expansion, expression in (
        ("live", "off", None), ("phase4e", "phase4e", "phase4e"),
        ("phase4f", "evaluation", "phase4f"),
    ):
        data = {key: [] for key in ("descriptor", "subject", "premise", "mechanism", "template",
                                     "name", "root", "recipe", "sound", "slang", "slang_template",
                                     "place", "place_template", "mock_final")}
        latencies=[]; prompt=[]; exhaustion=0
        memory_before=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        for number in range(rewrites):
            # Identical seed and quotas across all three configurations.
            seed=f"phase4f:{number}"; started=monotonic()
            try:
                d=descriptor_slate(seed, expansion_mode=expansion)
                n=ComedyNameGenerator(seed, expansion_mode=expansion).generate(10)
                if expression:
                    s=ComedyExpressionGenerator(seed+":slang", expression).generate("slang",10)
                    p=ComedyExpressionGenerator(seed+":places", expression).generate("places",10)
                else:
                    rng=random.Random(seed+":slang"); s=rng.sample(old_slang,10)
                    rng=random.Random(seed+":places"); p=rng.sample(old_places,10)
            except (RuntimeError, ValueError):
                exhaustion += 1; continue
            sv=[x.phrase for x in s] if expression else s
            pv=[x.phrase for x in p] if expression else p
            data["descriptor"] += [x.phrase for x in d]
            data["subject"] += [x.subject for x in d]
            data["premise"] += [x.premise_key for x in d]
            data["mechanism"] += [x.comic_mechanism for x in d]
            data["template"] += [x.template for x in d]
            data["name"] += [x.name for x in n]; data["root"] += [x.surname_component for x in n]
            data["recipe"] += [x.recipe for x in n]; data["sound"] += [signature(x.surname_component) for x in n]
            data["slang"] += sv; data["place"] += pv
            if expression:
                data["slang_template"] += [x.template for x in s]
                data["place_template"] += [x.template for x in p]
            data["mock_final"] += [d[0].phrase,d[1].phrase,n[0].name,n[1].name,sv[0],pv[0]]
            prompt.append(sum(len(x)+2 for x in [*[y.phrase for y in d],*[y.name for y in n],*sv,*pv]))
            latencies.append((monotonic()-started)*1000)
        memory_after=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        result[label]={
            "descriptors":metrics(data["descriptor"]), "descriptor_subjects":len(set(data["subject"])),
            "descriptor_premises":len(set(data["premise"])), "descriptor_mechanisms":len(set(data["mechanism"])),
            "descriptor_templates":len(set(data["template"])), "names":metrics(data["name"]),
            "name_roots":len(set(data["root"])), "name_recipes":dict(Counter(data["recipe"])),
            "name_sound_patterns":len(set(data["sound"])), "slang":metrics(data["slang"]),
            "slang_templates":len(set(data["slang_template"])), "places":metrics(data["place"]),
            "place_templates":len(set(data["place_template"])), "mock_final":metrics(data["mock_final"],6),
            "latency_ms":{"average":round(mean(latencies),2),"maximum":round(max(latencies),2)},
            "prompt_characters":{"average":round(mean(prompt),2),"maximum":max(prompt)},
            "peak_rss_delta_bytes":max(0,memory_after-memory_before),
            "database_operations":0,"provider_operations":0,"controlled_exhaustion_events":exhaustion,
        }
    return result


if __name__ == "__main__":
    import argparse
    parser=argparse.ArgumentParser(); parser.add_argument("--rewrites",type=int,default=250)
    print(json.dumps(run(parser.parse_args().rewrites),indent=2))
