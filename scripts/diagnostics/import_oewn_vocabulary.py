"""Import a filtered Phase 4C snapshot from Open English WordNet 2025 JSON.

The official archive is not stored in this repository. Download the 2025 JSON
release from https://en-word.net/static/english-wordnet-2025-json.zip, extract
it, then pass the extracted directory to this script.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

from wordfreq import zipf_frequency

ROOT = Path(__file__).parents[2]
OUTPUT = ROOT / "newsmuncher/resources/vocabulary/oewn_2025_phase4c.json"
BLOCKED = re.compile(
    r"\b(?:nigger|chink|spic|kike|raghead|retard|whore|cunt|rape|porn|dildo|vibrator|condom|death camp)\b",
    re.IGNORECASE,
)


def _usable(text, *, words=4, minimum_frequency=1.5):
    return (text == text.casefold() and len(text) >= 3 and 1 <= len(text.split()) <= words
            and re.fullmatch(r"[a-z][a-z '-]*[a-z]|[a-z]", text)
            and not BLOCKED.search(text)
            and zipf_frequency(text.replace("_", " "), "en") >= minimum_frequency)


def _ranked(path, limit, *, words=4, minimum_frequency=1.5, reject_definition=None):
    payload = json.loads(path.read_text(encoding="utf-8"))
    candidates = []
    for synset_id, synset in payload.items():
        definition = " ".join(synset.get("definition", ()))
        if reject_definition and reject_definition.search(definition):
            continue
        for member in synset.get("members", ()):
            text = member.replace("_", " ").strip()
            if _usable(text, words=words, minimum_frequency=minimum_frequency):
                candidates.append((zipf_frequency(text, "en"), len(text), text,
                                   synset_id, definition[:240]))
    selected, seen = [], set()
    for frequency, _, text, synset_id, definition in sorted(candidates, reverse=True):
        key = re.sub(r"[^a-z0-9]+", "", text)
        singular = re.sub(r"(?:es|s)$", "", key)
        if key in seen or singular in seen:
            continue
        seen.update((key, singular))
        selected.append({"text": text, "synset_id": synset_id,
                         "definition": definition, "zipf_frequency": frequency})
        if len(selected) == limit:
            break
    return selected


def build(source):
    non_identity = re.compile(
        r"\b(?:family|genus|order|suborder|subfamily|class|phylum|tribe|breed|"
        r"cell|tissue|organ|body part|part of|appendage|fin|scale|shell|egg|larva|glands?|"
        r"apparatus|anatomical|covering|plumage|feathers?|leg of|mouth of|structure on|"
        r"muscular pouch|unborn|unhatched|group of|young of|adult of|"
        r"imaginary|mythical|fabulous creature)\b", re.IGNORECASE)
    animals = _ranked(source / "noun.animal.json", 1500, words=4,
                      minimum_frequency=1.2, reject_definition=non_identity)
    objects = _ranked(source / "noun.artifact.json", 3500, words=4, minimum_frequency=1.6)
    adjectives = _ranked(source / "adj.all.json", 1800, words=3, minimum_frequency=2.1)
    adverbs = _ranked(source / "adv.all.json", 700, words=3, minimum_frequency=2.1)
    return {
        "snapshot_version": "oewn-2025-phase4c-1",
        "source_release": "Open English WordNet 2025 Edition",
        "source_url": "https://en-word.net/static/english-wordnet-2025-json.zip",
        "licence_id": "CC-BY-4.0",
        "attribution": "Open English WordNet Community, 2025 Edition; derived from Princeton WordNet.",
        "frequency_source": {"name": "wordfreq", "version": "3.1.1",
                             "licence_id": "Apache-2.0", "purpose": "familiarity ranking only"},
        "filters": {"lowercase": True, "max_words": 4, "frequency_ranked": True,
                    "safety_blocklist": True, "editorial_status": "machine_checked"},
        "animals": animals, "objects": objects,
        "descriptor_adjectives": adjectives, "descriptor_adverbs": adverbs,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    result = build(args.source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print({key: len(value) for key, value in result.items() if isinstance(value, list)})
