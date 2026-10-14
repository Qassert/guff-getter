"""Phase 4A offline vocabulary-catalogue prototype; never imported by live code."""
from __future__ import annotations

from collections import Counter
import csv
import json
from pathlib import Path
import random
from statistics import mean
from time import monotonic
import tracemalloc

ROOT = Path(__file__).parents[2]
RESOURCES = ROOT / "newsmuncher" / "resources"

# Editorial seed material demonstrates structured taxonomy and multiword identity.
# It is deliberately a prototype, not a production bank or a downloaded dataset.
PROTOTYPE_ANIMALS = (
    "aye-aye", "blue-footed booby", "naked mole-rat", "leafy seadragon",
    "shoebill", "goblin shark", "saiga antelope", "pink fairy armadillo",
    "star-nosed mole", "proboscis monkey", "quokka", "quoll", "fossa",
    "binturong", "maned wolf", "dik-dik", "markhor", "takin", "okapi",
    "pangolin", "jerboa", "springhare", "colugo", "tree kangaroo",
    "secretary bird", "kakapo", "hoatzin", "potoo", "frogmouth", "kea",
    "harpy eagle", "bearded vulture", "hornbill", "jacana", "kittiwake",
    "tuatara", "thorny devil", "frilled lizard", "mata mata turtle",
    "axolotl", "olm", "surinam toad", "hellbender", "mudpuppy",
    "oarfish", "blobfish", "mudskipper", "coelacanth", "lumpsucker",
    "sarcastic fringehead", "weedy seadragon", "wobbegong", "sawfish",
    "coconut crab", "mantis shrimp", "vampire squid", "dumbo octopus",
    "sea pig", "basket star", "bobbit worm", "giant isopod",
    "goliath birdeater", "whip scorpion", "camel spider", "orchid mantis",
    "atlas moth", "lanternfly", "weevil", "antlion", "dobsonfly",
    "velvet worm", "tardigrade", "horseshoe crab", "sea cucumber",
)

PROTOTYPE_NAME_COMPONENTS = (
    "Aubrey", "Beryl", "Cuthbert", "Daphne", "Euphemia", "Fergus",
    "Gwendoline", "Horatio", "Ivor", "Jemima", "Lavinia", "Montague",
    "Neville", "Octavia", "Percival", "Queenie", "Rupert", "Sybil",
    "Tarquin", "Ursula", "Vernon", "Wilhelmina", "Xanthe", "Yorick",
    "Zebedee", "Bramblewick", "Clatterbuck", "Ditheridge", "Fumblethorpe",
    "Gristlehurst", "Hobblethwaite", "Jollibottom", "Kettleworth",
    "Muddlecombe", "Nettlefold", "Pettifogge", "Quibbleton", "Rattleby",
    "Snodgrass", "Tattershall", "Undercrump", "Vexborough", "Wobbleton",
)

OBJECT_SUFFIXES = (
    "rack", "table", "chair", "bell", "mat", "detector", "holder", "clip",
    "bag", "brush", "broom", "pump", "dish", "tray", "box", "lamp", "tool",
    "machine", "iron", "spoon", "fork", "tin", "bucket", "mop", "cover",
    "board", "cart", "trolley", "cabinet", "stool", "stand", "clock", "hat",
)


def _csv(name):
    with (RESOURCES / "words" / name).open(encoding="utf-8", newline="") as source:
        return list(dict.fromkeys(value.strip() for row in csv.reader(source)
                                  for value in row if value.strip()))


def _components(kind):
    path = RESOURCES / kind / f"comedy_{kind[:-1]}_components.json"
    return json.loads(path.read_text(encoding="utf-8"))


def catalogues():
    concepts = _components("concepts")["banks"]
    descriptors = _components("descriptors")["banks"]
    names = _components("names")
    current_animals = concepts["creatures"]
    current_objects = list(dict.fromkeys(
        value for bank in ("domestic_objects", "devices", "cheeky_objects",
                           "equipment", "ceremonial_objects", "emergency_devices")
        for value in concepts[bank]
    ))
    legacy_physical = [value for value in _csv("animalsAndObjects.csv")
                       if len(value.split()) <= 4 and value.casefold() not in {
                           item.casefold() for item in current_animals
                       }]
    object_candidates = [value for value in legacy_physical
                         if value.casefold().endswith(OBJECT_SUFFIXES)]
    descriptor_current = list(dict.fromkeys(
        value for bank in descriptors.values() for value in bank
    ))
    descriptor_candidates = [value for value in _csv("adverbs.csv")
                             if 1 <= len(value.split()) <= 3 and value.isascii()]
    name_current = list(dict.fromkeys(
        value for section in (names["cheeky"], names["absurd"])
        for key, values in section.items() if isinstance(values, list)
        for value in values if isinstance(value, str)
    ))
    return {
        "animals": (current_animals, list(dict.fromkeys(current_animals + list(PROTOTYPE_ANIMALS)))),
        "objects": (current_objects, list(dict.fromkeys(current_objects + object_candidates))),
        "descriptors": (descriptor_current, list(dict.fromkeys(descriptor_current + descriptor_candidates))),
        "name_components": (name_current, list(dict.fromkeys(name_current + list(PROTOTYPE_NAME_COMPONENTS)))),
        "slang": (_csv("slang.csv")[:200], _csv("slang.csv")),
        "places": (_csv("places.csv")[:200], _csv("places.csv")),
    }


def _simulate(pool, seed, per_rewrite, rewrites=100):
    rng = random.Random(seed)
    shuffled = list(pool); rng.shuffle(shuffled)
    offers, cursor, windows = [], 0, []
    for _ in range(rewrites):
        slate = []
        for _ in range(per_rewrite):
            slate.append(shuffled[cursor % len(shuffled)])
            cursor += 1
            if cursor % len(shuffled) == 0:
                rng.shuffle(shuffled)
        offers.append(slate)
        recent = [value for group in offers[-10:] for value in group]
        windows.append(len(recent) - len(set(recent)))
    flat = [value for slate in offers for value in slate]
    return {
        "offers": len(flat), "unique": len(set(flat)),
        "repeated_occurrences": len(flat) - len(set(flat)),
        "rolling_ten_average_reuse": round(mean(windows), 2),
        "rolling_ten_maximum_reuse": max(windows),
    }


def examples(cats, seed="phase4a", count=50):
    rng = random.Random(seed)
    animals = rng.sample(cats["animals"][1], 10)
    objects = rng.sample(cats["objects"][1], 10)
    descriptors = rng.sample(cats["descriptors"][1], 10)
    names = rng.sample(cats["name_components"][1], 10)
    places = rng.sample(cats["places"][1], 5)
    slang = rng.sample(cats["slang"][1], 5)
    output = []
    for value in animals: output.append(("animal", f"{value} with temporary diplomatic immunity"))
    for value in objects: output.append(("object", f"{value} licensed to inspect suspicious bunting"))
    for value in descriptors: output.append(("descriptor ingredient", value))
    for first, surname in zip(names[:5], names[5:]): output.append(("name", f"{first} {surname}"))
    for value in names[5:]: output.append(("name component", value))
    for value in places: output.append(("place candidate", value))
    for value in slang: output.append(("slang candidate — requires safety review", value))
    return output[:count]


def run(seed="phase4a", rewrites=100):
    tracemalloc.start(); started = monotonic(); cats = catalogues()
    counts = {key: {"current": len(value[0]), "prototype": len(value[1])}
              for key, value in cats.items()}
    comparison = {}
    quotas = {"animals": 4, "objects": 16, "descriptors": 10,
              "name_components": 10, "slang": 10, "places": 10}
    for key, (current, expanded) in cats.items():
        comparison[key] = {
            "current": _simulate(current, f"{seed}:{key}:current", quotas[key], rewrites),
            "prototype": _simulate(expanded, f"{seed}:{key}:prototype", quotas[key], rewrites),
        }
    _, peak = tracemalloc.get_traced_memory(); tracemalloc.stop()
    return {
        "seed": seed, "rewrites": rewrites, "catalogue_counts": counts,
        "comparison": comparison, "examples": examples(cats, seed),
        "local_ms": round((monotonic() - started) * 1000, 2),
        "peak_memory_bytes": peak,
        "database_operations": 0,
    }


if __name__ == "__main__":
    from pprint import pprint
    pprint(run(), sort_dicts=False)
