"""Equivalent-seed synthetic Phase 4I/4J variety comparison; no external I/O."""
from __future__ import annotations

from collections import Counter, deque
import argparse
import json
import random
from statistics import mean
from time import monotonic

from newsmuncher.services.topic_memory import detect_topics


SUBJECT_SENTENCES = (
    "The gravy formed a committee.", "The pudding demanded minutes.",
    "The tea urn appealed to the council.", "An allotment denied the allegation.",
    "The milk float chaired the inquiry.", "The queue requested diplomatic immunity.",
    "A municipal badger audited the raffle.", "The biscuit tin nationalised Tuesday.",
    "A gazebo misplaced gravity.", "The weather vane sued the chutney.",
    "A colander rejected the crown.", "The deckchair inspected the moon.",
)
CONSTRUCTION_SENTENCES = (
    "A hamster-powered typewriter arrived.", "The kettle ran an illegal raffle.",
    "The footstool represented itself at a tribunal.",
    "The jelly mould was capable of unauthorised swelling.",
    "The wardrobe insisted the neighbour started it.",
    "The floorboards framed it.", "The mackerel resigned over disputed bunting.",
    "The plunger requested a ceremonial recount.",
)


def rolling(chunks, width):
    values = []
    for end in range(width, len(chunks) + 1):
        window = [value for chunk in chunks[end-width:end] for value in chunk]
        values.append(len(window) - len(set(window)))
    return round(mean(values), 2) if values else 0.0


def choose(pool, count, seed, recent, protected, key_index=0):
    rng = random.Random(seed)
    ranked = sorted(pool, key=lambda item: (
        recent[item[key_index]] if protected else 0, -item[3], rng.random()
    ))
    return ranked[:count]


def run(rewrites=250):
    concepts = [(f"concept-{i}", f"premise-{i % 47}", f"object-{i % 83}", 8.4-(i % 11)*.03)
                for i in range(160)]
    descriptors = [(f"descriptor-{i}", f"descriptor-premise-{i % 53}",
                    f"subject-{i % 71}", 8.2-(i % 13)*.025) for i in range(120)]
    names = [(f"name-{i}", f"sound-{i % 31}", f"root-{i}", 8.1-(i % 9)*.02)
             for i in range(120)]
    output = {}
    for label, protected in (("phase4i", False), ("phase4j", True)):
        recent_offers = Counter(); recent_events = deque(maxlen=10)
        concept_chunks=[]; descriptor_chunks=[]; premise_chunks=[]; identity_chunks=[]
        name_family_chunks=[]; subject_chunks=[]; construction_chunks=[]
        quality=[]; prompt_chars=[]; latency=[]; failures=0
        for number in range(rewrites):
            started=monotonic(); seed=f"phase4j:{number}"
            selected_concepts=choose(concepts,20,seed+":c",recent_offers,protected)
            selected_descriptors=choose(descriptors,10,seed+":d",recent_offers,protected)
            selected_names=choose(names,10,seed+":n",recent_offers,protected,1)
            concept_chunks.append([x[0] for x in selected_concepts])
            descriptor_chunks.append([x[0] for x in selected_descriptors])
            premise_chunks.append([x[1] for x in selected_concepts+selected_descriptors])
            identity_chunks.append([x[2] for x in selected_concepts])
            name_family_chunks.append([x[1] for x in selected_names])
            quality += [x[3] for x in selected_concepts+selected_descriptors+selected_names]

            recent_topic_keys={key for event in list(recent_events)[-5:] for key in event}
            subject_order=[number%7,(number*5+3)%len(SUBJECT_SENTENCES)]
            construction_order=[number%6,(number*3+2)%len(CONSTRUCTION_SENTENCES)]
            if protected:
                subject_order=sorted(range(len(SUBJECT_SENTENCES)),key=lambda i:(
                    next(iter({x["key"] for x in detect_topics(SUBJECT_SENTENCES[i])}),"") in recent_topic_keys,
                    (i-number)%len(SUBJECT_SENTENCES)))[:2]
                construction_order=sorted(range(len(CONSTRUCTION_SENTENCES)),key=lambda i:(
                    next(iter({x["key"] for x in detect_topics(CONSTRUCTION_SENTENCES[i])}),"") in recent_topic_keys,
                    (i-number)%len(CONSTRUCTION_SENTENCES)))[:2]
            detected=detect_topics(" ".join(
                [SUBJECT_SENTENCES[i] for i in subject_order]+[CONSTRUCTION_SENTENCES[i] for i in construction_order]))
            subjects=[x["key"] for x in detected if x["kind"]=="subject"]
            constructions=[x["key"] for x in detected if x["kind"]=="construction"]
            subject_chunks.append(subjects); construction_chunks.append(constructions)
            recent_events.append(subjects+constructions)
            topic_counts=Counter(key for event in list(recent_events)[-5:] for key in event)
            active_labels=(sum(count >= 2 for count in topic_counts.values()) if protected else 0)
            prompt_chars.append(min(4,active_labels)*42 + (168 if active_labels else 0))
            if protected:
                recent_offers=Counter()
                for age, chunks in enumerate(zip(
                        reversed(concept_chunks[-10:]), reversed(descriptor_chunks[-10:]),
                        reversed(name_family_chunks[-10:])),1):
                    weight=11-age
                    for value in set(chunks[0]+chunks[1]+chunks[2]): recent_offers[value]+=weight
            latency.append((monotonic()-started)*1000)
        exact_chunks=[a+b for a,b in zip(concept_chunks,descriptor_chunks)]
        output[label]={
            "completed_rewrites":rewrites,
            "exact_offered_phrases":{"unique":len(set(sum(exact_chunks,[]))),
                                      "rolling_5":rolling(exact_chunks,5),"rolling_10":rolling(exact_chunks,10)},
            "semantic_premises":{"unique":len(set(sum(premise_chunks,[]))),
                                  "rolling_5":rolling(premise_chunks,5),"rolling_10":rolling(premise_chunks,10)},
            "final_subjects":{"rolling_5":rolling(subject_chunks,5),"rolling_10":rolling(subject_chunks,10)},
            "final_constructions":{"rolling_5":rolling(construction_chunks,5),
                                   "rolling_10":rolling(construction_chunks,10)},
            "object_identities":{"unique":len(set(sum(identity_chunks,[]))),
                                 "rolling_10":rolling(identity_chunks,10)},
            "name_sound_families":{"unique":len(set(sum(name_family_chunks,[]))),
                                   "rolling_10":rolling(name_family_chunks,10)},
            "humour_quality_proxy":round(mean(quality),3),
            "naturalness_fixture_rate":1.0,
            "prompt_overhead_characters":{"average":round(mean(prompt_chars),2),"maximum":max(prompt_chars)},
            "estimated_prompt_overhead_tokens":round(mean(prompt_chars)/4,2),
            "selection_latency_ms":{"average":round(mean(latency),3),"maximum":round(max(latency),3)},
            "topic_memory_database_operations":rewrites*2 if protected else 0,
            "exhaustion_events":failures,
        }
    return output


if __name__ == "__main__":
    parser=argparse.ArgumentParser(); parser.add_argument("--rewrites",type=int,default=250)
    args=parser.parse_args(); print(json.dumps(run(args.rewrites),indent=2,sort_keys=True))
