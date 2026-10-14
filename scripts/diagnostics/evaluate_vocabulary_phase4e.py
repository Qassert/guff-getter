"""Deterministic, provider-free Phase 4E 250-MUNGE comparison."""
from collections import Counter
import csv, random, resource
from pathlib import Path
from statistics import mean
from time import monotonic

from newsmuncher.config import WORDS_DIR
from newsmuncher.services.comedy_descriptors import descriptor_slate
from newsmuncher.services.comedy_names import ComedyNameGenerator
from newsmuncher.services.comedy_expressions import ComedyExpressionGenerator


def _legacy(filename):
    with (WORDS_DIR / filename).open(encoding="utf-8", newline="") as source:
        return list(dict.fromkeys(x.strip() for row in csv.reader(source) for x in row if x.strip()))


def _rolling(values, per_rewrite, width=10):
    chunks = [values[i:i+per_rewrite] for i in range(0, len(values), per_rewrite)]
    repeats = []
    for start in range(max(0, len(chunks)-width+1)):
        window = [x for chunk in chunks[start:start+width] for x in chunk]
        repeats.append(len(window)-len(set(window)))
    return round(mean(repeats), 2) if repeats else 0


def _metrics(values, per_rewrite):
    return {"offered": len(values), "unique": len(set(values)),
            "duplicates": len(values)-len(set(values)),
            "rolling_ten_repeats": _rolling(values, per_rewrite)}


def run(rewrites=250):
    legacy_slang, legacy_places = _legacy("slang.csv"), _legacy("places.csv")
    outputs = {}
    for mode in ("current", "expanded"):
        descriptors=[]; subjects=[]; mechanisms=[]; names=[]; roots=[]; patterns=[]
        slang=[]; places=[]; appeared=[]; prompt_sizes=[]; times=[]
        memory_before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        for number in range(rewrites):
            seed=f"phase4e:{mode}:{number}"; started=monotonic()
            expansion = "evaluation" if mode == "expanded" else "off"
            d=descriptor_slate(seed, expansion_mode=expansion)
            n=ComedyNameGenerator(seed, expansion_mode=expansion).generate(10)
            if mode == "expanded":
                s=ComedyExpressionGenerator(seed+":slang").generate("slang",10)
                p=ComedyExpressionGenerator(seed+":places").generate("places",10)
                slang_values=[x.phrase for x in s]; place_values=[x.phrase for x in p]
            else:
                rng=random.Random(seed)
                slang_values=rng.sample(legacy_slang,10); place_values=rng.sample(legacy_places,10)
            times.append((monotonic()-started)*1000)
            descriptors.extend(x.phrase for x in d); subjects.extend(x.subject for x in d)
            mechanisms.extend(x.comic_mechanism for x in d)
            names.extend(x.name for x in n); roots.extend(x.surname_component for x in n)
            patterns.extend(x.recipe for x in n)
            slang.extend(slang_values); places.extend(place_values)
            appeared.extend([d[0].phrase,d[1].phrase,n[0].name,n[1].name,
                             slang_values[0],place_values[0]])
            prompt_sizes.append(sum(len(x)+2 for x in ([y.phrase for y in d]+[y.name for y in n]+slang_values+place_values)))
        memory_after = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        outputs[mode]={
            "descriptors":_metrics(descriptors,10), "descriptor_subjects":len(set(subjects)),
            "descriptor_premises":len(set(zip(mechanisms,subjects))),
            "descriptor_mechanisms":dict(Counter(mechanisms)),
            "names":_metrics(names,10), "name_roots":len(set(roots)),
            "name_patterns":dict(Counter(patterns)),
            "slang":_metrics(slang,10), "places":_metrics(places,10),
            "mock_final":_metrics(appeared,6),
            "latency_ms":{"average":round(mean(times),2),"maximum":round(max(times),2)},
            "prompt_characters":{"average":round(mean(prompt_sizes),2),"maximum":max(prompt_sizes)},
            # macOS reports ru_maxrss in bytes. The Phase 4E audit runs on macOS,
            # so keep the unit explicit rather than presenting it as Linux KiB.
            "peak_rss_delta_bytes":max(0, memory_after-memory_before),
            "database_operations":0, "provider_operations":0,
        }
    return outputs


if __name__ == "__main__":
    import argparse,json
    parser=argparse.ArgumentParser(); parser.add_argument("--rewrites",type=int,default=250)
    print(json.dumps(run(parser.parse_args().rewrites),indent=2))
