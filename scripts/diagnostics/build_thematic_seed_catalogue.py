#!/usr/bin/env python3
"""Build the reviewed Phase 4P typed-seed companion catalogue locally."""
from __future__ import annotations

import json
from pathlib import Path
import re


ROOT = Path(__file__).parents[2]
DOMAINS = ROOT / "newsmuncher/resources/vocabulary/thematic_domains.json"
OUTPUT = ROOT / "newsmuncher/resources/vocabulary/thematic_ingredient_seeds.json"

FAMILY_PROPERTIES = {
    "living_systems": ["bioluminescent", "symbiotic", "parasitic", "dormant", "migratory", "colonial", "adaptive", "regenerative", "photosensitive"],
    "cosmos_physics": ["resonant", "entangled", "turbulent", "refractive", "relativistic", "magnetised", "oscillating", "supercooled", "phase-shifted"],
    "earth_atmosphere": ["tectonic", "erosional", "volcanic", "stratified", "glacial", "porous", "storm-driven", "mineralised", "wind-carved"],
    "past_societies": ["excavated", "inscribed", "ritualised", "bronze-cast", "archival", "dynastic", "fragmentary", "processional", "stratigraphic"],
    "culture_language": ["reciprocal", "symbolic", "oral", "masked", "polyphonic", "ritualised", "improvised", "dialectal", "divinatory"],
    "built_systems": ["cantilevered", "counterweighted", "interlocking", "load-bearing", "subterranean", "modular", "pneumatic", "signal-controlled", "clockwork"],
    "medicine_mind": ["neurological", "immune-mediated", "circadian", "dose-dependent", "sensory", "prosthetic", "diagnostic", "reflexive", "anaesthetic"],
    "abstract_technology": ["encrypted", "recursive", "probabilistic", "topological", "networked", "error-correcting", "automated", "feedback-controlled", "modular"],
    "performance_arts": ["operatic", "choreographed", "improvised", "syncopated", "projected", "puppeteered", "acrobatic", "misdirected", "foley-driven"],
    "craft_material": ["annealed", "woven", "glazed", "quenched", "marbled", "pigmented", "carved", "tensioned", "hand-finished"],
    "field_practices": ["triangulated", "fermented", "grafted", "acclimatised", "celestially-navigated", "seed-banked", "excavated", "hive-coordinated", "field-tested", "rope-secured"],
}

FAMILY_RELATIONSHIPS = {
    "living_systems": ["mutual dependence", "host parasitism", "colony signalling", "resource competition", "inherited variation", "chemical communication", "predator mimicry", "seasonal migration", "ecological succession"],
    "cosmos_physics": ["harmonic interference", "orbital capture", "phase coupling", "field induction", "pressure equilibrium", "energy transfer", "wave cancellation", "thermal exchange", "quantum correlation"],
    "earth_atmosphere": ["tectonic subduction", "sediment deposition", "storm convergence", "erosion feedback", "mineral replacement", "glacial transport", "pressure inversion", "fault displacement", "ocean circulation"],
    "past_societies": ["ritual succession", "trade exchange", "scribal transmission", "dynastic inheritance", "material reuse", "archaeological layering", "ceremonial obligation", "road taxation", "workshop apprenticeship"],
    "culture_language": ["gift reciprocity", "oral transmission", "status exchange", "symbolic substitution", "dialect contact", "ritual transformation", "collective memory", "competitive display", "mythic inheritance"],
    "built_systems": ["load distribution", "signal interlocking", "counterweight balance", "traffic convergence", "water diversion", "structural resonance", "mechanical feedback", "spatial circulation", "material tension"],
    "medicine_mind": ["sensory adaptation", "immune recognition", "dose response", "neural inhibition", "circadian entrainment", "prosthetic feedback", "symptom masking", "contact transmission", "motor compensation"],
    "abstract_technology": ["recursive dependence", "network centrality", "signal redundancy", "conditional probability", "feedback instability", "cryptographic exchange", "topological equivalence", "error propagation", "automated control"],
    "performance_arts": ["rhythmic counterpoint", "performer substitution", "audience participation", "staged misdirection", "choreographic mirroring", "acoustic projection", "dramatic interruption", "ensemble timing", "visual montage"],
    "craft_material": ["material tension", "thermal expansion", "pigment binding", "grain alignment", "surface adhesion", "tool resonance", "structural joinery", "fibre interlacing", "controlled fracture"],
    "field_practices": ["route triangulation", "rope dependence", "culture fermentation", "pollinator signalling", "graft compatibility", "compass deviation", "stratigraphic association", "seed dormancy", "team acclimatisation", "experimental reconstruction"],
}

OVERRIDES = {
    "marine-biology": {"entities": ["bioluminescence", "hydrothermal vent", "coral polyp", "pressure organ"], "processes": ["reef symbiosis", "pressure adaptation", "coral spawning", "tidal migration"]},
    "mycology": {"entities": ["mycelium", "spore", "fruiting body", "hyphal network"], "processes": ["spore dispersal", "parasitic growth", "decomposition", "fungal communication"]},
    "ancient-egypt": {"entities": ["canopic jar", "burial chamber", "papyrus seal", "funerary barge"], "processes": ["burial ritual", "tomb painting", "bronze casting", "hieroglyphic inscription"]},
    "acoustics": {"entities": ["resonator", "standing wave", "echo chamber", "infrasound"], "processes": ["harmonic interference", "acoustic levitation", "wave cancellation", "echolocation"]},
}


def _slug(value):
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")


def _chunks(inspiration):
    cleaned = re.sub(
        r"\b(argumentative|impossible|improbable|unruly|deceptive|suspiciously|"
        r"badly behaved|peculiar|overconfident|rebellious|dubious|unreliable|"
        r"confidently misplaced|catastrophically elaborate|historically accurate)\b",
        "", inspiration, flags=re.I)
    parts = [re.sub(r"\s+", " ", value).strip(" ,-")
             for value in re.split(r",|\band\b", cleaned)]
    return [value for value in parts if value]


def build():
    domains = json.loads(DOMAINS.read_text(encoding="utf-8"))["domains"]
    records = []
    family_index = {}
    for domain in domains:
        family = domain["family"]
        index = family_index.get(family, 0); family_index[family] = index + 1
        properties = FAMILY_PROPERTIES[family]
        relationships = FAMILY_RELATIONSHIPS[family]
        chunks = _chunks(domain["inspiration"])
        while len(chunks) < 4:
            chunks.append(f"{domain['keywords'][len(chunks) % len(domain['keywords'])]} dynamics")
        values = {
            "entities": list(domain["keywords"]),
            "processes": chunks[:4],
            "properties": [properties[(index + offset) % len(properties)] for offset in range(4)],
            "relationships": [relationships[(index + offset) % len(relationships)] for offset in range(4)],
        }
        values.update(OVERRIDES.get(domain["id"], {}))
        seeds = {}
        singular = {"entities": "entity", "processes": "process",
                    "properties": "property", "relationships": "relationship"}
        for kind, texts in values.items():
            seeds[kind] = [
                {"id": f"{domain['id']}:{singular[kind]}:{_slug(text)}", "text": text,
                 "grammar": "noun_phrase" if kind != "properties" else "modifier",
                 "provenance": "original NewsMuncher Phase 4N domain and Phase 4P family pools",
                 "licence_id": "INTERNAL-UNVERIFIED",
                 "approval_status": "reviewed",
                 "safety_status": "reviewed"}
                for text in texts
            ]
        records.append({"domain_id": domain["id"], "family": family, "seeds": seeds})
    return {"version": "thematic-ingredient-seeds-v1", "domains": records}


if __name__ == "__main__":
    OUTPUT.write_text(json.dumps(build(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT} with {len(build()['domains'])} domains")
