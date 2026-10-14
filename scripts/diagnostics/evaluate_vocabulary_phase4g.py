"""Equivalent-seed Phase 4G semantic-memory audit; local generation only."""
from __future__ import annotations

from collections import Counter, deque
import argparse
import csv
import json
import random
import re
from statistics import mean
from time import monotonic

from newsmuncher.config import WORDS_DIR
from newsmuncher.services.comedy_concepts import ComedyConceptGenerator, normalised
from newsmuncher.services.comedy_descriptors import (
    assemble_descriptor_slate, descriptor_candidate_pool,
)
from newsmuncher.services.comedy_names import ComedyNameGenerator
from newsmuncher.services.semantic_memory import descriptor_premise_family, name_sound_family


QUOTAS = {
    "nouns": {"everyday_british": 1, "cheeky_object": 2, "absurd_invention": 2,
              "bureaucratic_nonsense": 3, "emergency_equipment": 1,
              "ceremonial_object": 1},
    "animals": {"everyday_british": 2, "cheeky_object": 2,
                "absurd_invention": 2, "ridiculous_creature": 4},
}


def legacy(name):
    with (WORDS_DIR / name).open(encoding="utf-8", newline="") as source:
        return list(dict.fromkeys(value.strip() for row in csv.reader(source)
                                  for value in row if value.strip()))


def rolling(values, per, windows=(5, 10, 20)):
    chunks = [values[i:i + per] for i in range(0, len(values), per)]
    result = {"offered": len(values), "unique": len(set(values))}
    for width in windows:
        samples = []
        for end in range(width, len(chunks) + 1):
            window = sum(chunks[end - width:end], [])
            samples.append(len(window) - len(set(window)))
        result[f"rolling_{width}"] = round(mean(samples), 2) if samples else 0
    return result


def choose_concepts(seed, vocabulary_mode, recent):
    pool = [(item, target) for target, quotas in QUOTAS.items() for category in quotas
            for item in ComedyConceptGenerator(
                f"{seed}:{target}:{category}", vocabulary_mode=vocabulary_mode
            ).generate(30, category=category)]
    jitter = random.Random(seed + ":concept-order")
    jitter.shuffle(pool)
    pool.sort(key=lambda pair: recent[pair[0].comic_mechanism])
    selected=[]; bases=set(); premises=set(); counts=Counter()
    for item, target in pool:
        key=(target,item.category)
        if counts[key] >= QUOTAS[target][item.category]: continue
        if normalised(item.base) in bases or item.premise_key in premises: continue
        selected.append(item); counts[key]+=1; bases.add(normalised(item.base)); premises.add(item.premise_key)
        if len(selected)==20: break
    if len(selected)!=20: raise RuntimeError("concept audit exhausted")
    return selected


def choose_names(seed, expansion, recent):
    generated=[]
    for style, needed in (("cheeky",7),("absurd",3)):
        pool=ComedyNameGenerator(seed + ":" + style, expansion_mode=expansion).generate(40, style)
        order={item.name:i for i,item in enumerate(pool)}
        pool.sort(key=lambda item:(recent[f"{style}:{name_sound_family(item.surname_component)}"],order[item.name]))
        generated.extend(pool[:needed])
    return generated


def run(rewrites=250, configuration=None):
    slang=legacy("slang.csv"); places=legacy("places.csv")
    output={}
    configurations = (
        ("live","off","off",False),
        ("phase4f","evaluation","evaluation",False),
        ("phase4g","evaluation","evaluation",True),
    )
    for label,vocabulary,descriptor_expansion,semantic in configurations:
        if configuration and label != configuration:
            continue
        recent_concept=Counter(); recent_descriptor=Counter(); recent_name=Counter()
        streams={key:[] for key in ("concept_phrase","concept_premise","animal","object",
                                    "descriptor","descriptor_premise","descriptor_mechanism",
                                    "name","name_sound","slang","place","final_exact",
                                    "final_ingredient","final_premise","final_structure")}
        latency=[]; prompt_sizes=[]; failures=0; database_ops=0
        for number in range(rewrites):
            seed=f"phase4g:{number}"; started=monotonic()
            try:
                # A concept-family ranking experiment was rejected because it
                # worsened prompt-level premise/object reuse. Phase 4G records
                # those families but preserves Phase 4F concept ordering.
                concept_penalties=Counter()
                concepts=choose_concepts(seed,vocabulary,concept_penalties)
                pool=descriptor_candidate_pool(seed+":descriptor",10,descriptor_expansion)
                descriptor_penalties = ({item.comic_mechanism: recent_descriptor[
                    "mechanism:" + item.comic_mechanism] for item in pool}
                    if semantic else {})
                if semantic:
                    descriptor_penalties.update({
                        "premise:" + item.premise_key: recent_descriptor[
                            "premise-family:" + descriptor_premise_family(item)]
                        for item in pool
                    })
                descriptors=assemble_descriptor_slate(
                    pool, seed+":descriptor-slate", diversify=descriptor_expansion=="evaluation",
                    family_penalties=descriptor_penalties,
                )
                names=choose_names(seed,"off",recent_name if semantic else Counter())
            except (ValueError,RuntimeError):
                failures+=1; continue
            rng=random.Random(seed)
            slang_offer=rng.sample(slang,10); place_offer=rng.sample(places,10)
            for item in concepts:
                streams["concept_phrase"].append(item.phrase)
                streams["concept_premise"].append(item.premise_key)
                streams["animal" if item.animal_species else "object"].append(
                    item.animal_species or item.base)
            for item in descriptors:
                streams["descriptor"].append(item.phrase)
                streams["descriptor_premise"].append(item.premise_key)
                streams["descriptor_mechanism"].append(item.comic_mechanism)
            streams["name"] += [item.name for item in names]
            streams["name_sound"] += [name_sound_family(item.surname_component) for item in names]
            streams["slang"] += slang_offer; streams["place"] += place_offer
            # Deterministic mocked uptake: selection-caused repetition remains
            # attributable, while a fixed independent gag models provider-originated reuse.
            accepted_concepts=concepts[:3]; accepted_descriptors=descriptors[:3]; accepted_names=names[:2]
            streams["final_exact"] += [x.phrase for x in accepted_concepts+accepted_descriptors]
            streams["final_exact"] += [x.name for x in accepted_names]
            streams["final_ingredient"] += [x.animal_species or x.base for x in accepted_concepts]
            streams["final_ingredient"] += [x.subject for x in accepted_descriptors]
            streams["final_premise"] += [x.premise_key for x in accepted_concepts+accepted_descriptors]
            streams["final_structure"] += [x.comic_mechanism for x in accepted_concepts+accepted_descriptors]
            if number % 7 == 0:
                streams["final_exact"].append("an unscheduled dignity leak")
                streams["final_structure"].append("provider_independent_callback")
            if semantic:
                for history in (recent_concept, recent_descriptor, recent_name):
                    for key in list(history):
                        history[key] *= .85
                for item in accepted_concepts: recent_concept[item.comic_mechanism]+=1
                for item in accepted_descriptors:
                    recent_descriptor["mechanism:" + item.comic_mechanism]+=1
                    recent_descriptor[
                        "premise-family:" + descriptor_premise_family(item)] += 1
                for item in accepted_names:
                    recent_name[f"{item.category}:{name_sound_family(item.surname_component)}"]+=1
            prompt_sizes.append(sum(len(x)+2 for x in (
                [i.phrase for i in concepts]+[i.phrase for i in descriptors]+[i.name for i in names]
            )))
            latency.append((monotonic()-started)*1000)
            database_ops += 3 + 70 + (9 if semantic else 0)
        output[label]={
            "concept_phrases":rolling(streams["concept_phrase"],20),
            "concept_premises":rolling(streams["concept_premise"],20),
            "animal_identities":rolling(streams["animal"],max(1,len(streams["animal"])//max(1,rewrites))),
            "object_identities":rolling(streams["object"],max(1,len(streams["object"])//max(1,rewrites))),
            "descriptors":rolling(streams["descriptor"],10),
            "descriptor_premises":rolling(streams["descriptor_premise"],10),
            "descriptor_mechanisms":rolling(streams["descriptor_mechanism"],10),
            "names":rolling(streams["name"],10), "name_sounds":rolling(streams["name_sound"],10),
            "slang":rolling(streams["slang"],10), "places":rolling(streams["place"],10),
            "final_fixture":{
                "exact":rolling(streams["final_exact"],9),
                "ingredients":rolling(streams["final_ingredient"],6),
                "premises":rolling(streams["final_premise"],6),
                "structures":rolling(streams["final_structure"],7),
            },
            "within_article_duplicate_prompts":sum(
                len(chunk)!=len(set(chunk)) for chunk in
                [streams["concept_premise"][i:i+20] for i in range(0,len(streams["concept_premise"]),20)]
            ),
            "latency_ms":{"average":round(mean(latency),2),"maximum":round(max(latency),2)},
            "prompt_characters":{"average":round(mean(prompt_sizes),2),"maximum":max(prompt_sizes)},
            "database_operations_estimate":database_ops,
            "controlled_exhaustion_events":failures,
        }
    return output


if __name__ == "__main__":
    parser=argparse.ArgumentParser(); parser.add_argument("--rewrites",type=int,default=250)
    parser.add_argument("--configuration", choices=("live", "phase4f", "phase4g"))
    args=parser.parse_args(); print(json.dumps(run(args.rewrites, args.configuration),indent=2))
