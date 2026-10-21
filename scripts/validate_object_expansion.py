#!/usr/bin/env python3
"""Validate a staged OBJECT vocabulary expansion without importing it.

The validator deliberately keeps automatic rejection narrow.  Exact formatting and
unambiguous number variants are rejected; spelling variants, likely synonyms and
similar names are surfaced for a human editor.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from difflib import SequenceMatcher
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LIVE_VOCABULARY = ROOT / "newsmuncher/static/data/object-generator-vocabulary.csv"
CLASSIC_PHYSICAL = ROOT / "newsmuncher/resources/words/animalsAndObjects.csv"
EXPECTED_COLUMNS = ["category", "word", "domain", "form", "source_file", "review_status"]
VALID_CATEGORIES = {"object", "device"}
VALID_DOMAINS = {
    "kitchen_and_food_preparation", "furniture_and_interiors",
    "cleaning_and_laundry", "tools_and_hardware",
    "electronics_and_computing", "office_and_stationery",
    "plumbing_and_sanitation", "gardening_and_outdoors",
    "clothing_and_accessories", "sports_and_recreation",
    "safety_and_monitoring", "containers_and_storage",
    "domestic_appliances", "transport_and_maritime",
    "lighting_and_heating", "toys_and_novelty",
    "industrial_machinery",
    "scientific_and_laboratory_equipment",
    "agriculture_and_farming",
    "medical_equipment",
    "musical_instruments",
    "historical_weapons_and_armour", "siege_and_fortification",
    "ceremonial_and_religious_objects", "historical_household_and_writing",
    "road_transport", "rail_transport", "maritime_equipment", "aviation_equipment",
    "construction_tools", "construction_machinery", "infrastructure_components",
    "surveying_and_site_equipment", "computer_hardware",
    "electronics_and_test_equipment", "robotics_and_automation",
    "communications_and_media_hardware", "field_and_court_sports",
    "outdoor_and_water_recreation", "indoor_sports_and_games",
    "theatre_and_stage_equipment", "film_and_photography",
    "circus_magic_and_puppetry", "event_and_broadcast_equipment",
    "clothing_and_outerwear", "accessories_and_personal_items",
    "unusual_furniture_and_interiors", "domestic_and_cleaning_objects",
    "space_and_astronomy", "security_and_surveillance",
    "archaeology_and_fieldwork", "emergency_and_miscellaneous_equipment",
    "maritime_deck_equipment", "marine_navigation_and_signalling",
    "fishing_and_aquaculture", "diving_and_underwater_equipment",
    "victorian_domestic_objects", "medieval_household_and_craft",
    "historical_lighting_and_heating", "historical_personal_and_travel",
    "chemistry_glassware", "analytical_instruments",
    "biology_and_microscopy", "physics_and_demonstration_apparatus",
    "gardening_hand_tools", "forestry_and_arboriculture",
    "watering_and_greenhouse_equipment", "landscaping_and_groundskeeping",
    "fairground_rides_and_mechanisms", "carnival_games_and_stalls",
    "festival_and_parade_objects", "circus_performance_equipment",
    "firefighting_equipment", "road_and_medical_rescue",
    "water_and_flood_rescue", "disaster_and_search_equipment",
    "machine_tools_and_metalworking", "forming_and_fabrication",
    "woodworking_and_patternmaking", "factory_handling_and_packaging",
    "camera_and_lens_accessories", "darkroom_and_printing",
    "broadcast_and_recording", "cinema_and_projection",
    "museum_display_and_conservation", "archaeological_excavation",
    "exploration_and_field_equipment", "navigation_and_cartography",
    "unusual_furniture", "architectural_fittings", "public_space_fixtures",
    "institutional_and_library_furniture",
    "domestic_convenience_gadgets", "forgotten_laundry_devices",
    "peculiar_bedroom_objects", "domestic_serving_gadgets",
    "household_maintenance_gadgets", "traditional_toys",
    "novelty_and_practical_jokes", "magic_trick_apparatus",
    "party_and_desk_novelties", "optical_and_mechanical_toys",
    "toilet_fittings", "bathroom_accessories", "plumbing_tools",
    "sanitation_equipment", "historical_sanitation", "egg_and_dairy_tools",
    "specialist_cutters", "baking_and_confectionery",
    "catering_service_equipment", "large_kitchen_machinery",
    "horticultural_oddities", "pest_control_devices",
    "greenhouse_contraptions", "orchard_and_fruit_tools",
    "lawn_and_border_devices", "costume_accessories",
    "theatrical_disguises", "personal_adornment",
    "historical_clothing_hardware", "ceremonial_costume_objects",
    "office_desk_equipment", "filing_and_records",
    "bureaucratic_paraphernalia", "mailing_room_equipment",
    "meeting_and_reception_objects", "vintage_audio_devices",
    "obsolete_computing", "mechanical_inventions",
    "vintage_communications", "projection_and_display_technology",
    "historical_medical_objects", "dental_equipment",
    "physiotherapy_apparatus", "mobility_and_daily_living_aids",
    "clinical_diagnostic_tools", "odd_small_vehicles",
    "transport_accessories", "roadside_objects",
    "travel_luggage_equipment", "vehicle_service_equipment",
}
VALID_FORMS = {
    "passive_object", "hand_tool", "powered_device", "measuring_instrument",
    "container", "fixture", "furnishing", "consumable", "component",
    "location_or_space",
}
VALID_STATUSES = {"proposed", "needs_review", "approved", "imported"}

BRITISH_AMERICAN = {
    "anaesthetic": "anesthetic", "metre": "meter", "mould": "mold",
    "plough": "plow", "steriliser": "sterilizer", "centre": "center",
    "fibre": "fiber", "tyre": "tire",
}
SYNONYM_GROUPS = (
    {"electric drill", "power drill"},
    {"spanner", "wrench"},
    {"plough", "plow"},
    {"anaesthetic machine", "anesthesia machine"},
    {"steriliser", "sterilizer"},
    {"ultrasound scanner", "sonography machine"},
    {"electrocardiograph", "ecg machine", "ekg machine"},
    {"combine harvester", "combine"},
    {"public address system", "pa system"},
)
GENERIC_OBJECT_WORDS = {
    "apparatus", "cabinet", "counter", "device", "equipment", "instrument",
    "machine", "meter", "system", "tool", "unit",
}


class ValidationFailure(ValueError):
    pass


@dataclass(frozen=True)
class Finding:
    kind: str
    word: str
    match: str
    source: str
    reason: str


def normalise(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold().strip()
    return re.sub(r"[^\w]+", " ", value).strip()


def compact_key(value: str) -> str:
    """Normalise case, punctuation and optional internal whitespace."""
    return normalise(value).replace(" ", "")


def singular_key(value: str) -> str:
    """Return a conservative key for an unambiguous final-word plural."""
    words = normalise(value).split()
    if not words:
        return ""
    last = words[-1]
    if len(last) > 4 and last.endswith("ies"):
        last = last[:-3] + "y"
    elif len(last) > 4 and last.endswith(("ches", "shes", "sses", "xes", "zes")):
        last = last[:-2]
    elif len(last) > 3 and last.endswith("s") and not last.endswith(("ss", "us", "is")):
        last = last[:-1]
    words[-1] = last
    return " ".join(words)


def spelling_key(value: str) -> str:
    words = normalise(value).split()
    return " ".join(BRITISH_AMERICAN.get(word, word) for word in words)


def synonym_key(value: str) -> int | None:
    target = normalise(value)
    for index, group in enumerate(SYNONYM_GROUPS):
        if target in {normalise(item) for item in group}:
            return index
    return None


def near_duplicate_name(left: str, right: str) -> bool:
    left_key, right_key = normalise(left), normalise(right)
    ratio = SequenceMatcher(None, left_key, right_key).ratio()
    left_words, right_words = set(left_key.split()), set(right_key.split())
    meaningful_shared = (left_words & right_words) - GENERIC_OBJECT_WORDS
    if meaningful_shared:
        return ratio >= 0.88
    if len(left_words) == len(right_words) == 1:
        return ratio >= 0.94
    return False


def read_csv(path: Path, *, expected_columns: list[str]) -> list[dict[str, str]]:
    try:
        with path.open(encoding="utf-8-sig", newline="") as source:
            reader = csv.DictReader(source, strict=True)
            if reader.fieldnames != expected_columns:
                raise ValidationFailure(
                    f"{path}: expected columns {expected_columns}, got {reader.fieldnames}"
                )
            rows = []
            for number, row in enumerate(reader, 2):
                if None in row or any(value is None for value in row.values()):
                    raise ValidationFailure(f"{path}:{number}: malformed CSV row")
                clean = {key: value.strip() for key, value in row.items()}
                if not any(clean.values()):
                    continue
                rows.append(clean)
            return rows
    except csv.Error as exc:
        raise ValidationFailure(f"{path}: malformed CSV: {exc}") from exc


def read_live(path: Path) -> list[dict[str, str]]:
    return read_csv(path, expected_columns=["category", "word"])


def read_classic_physical(path: Path) -> list[str]:
    with path.open(encoding="utf-8-sig") as source:
        return [word.strip() for word in source.read().split(",") if word.strip()]


def metadata_errors(rows: list[dict[str, str]]) -> list[str]:
    errors = []
    for number, row in enumerate(rows, 2):
        for field in EXPECTED_COLUMNS:
            if not row[field]:
                errors.append(f"row {number}: missing {field}")
        if row["category"] not in VALID_CATEGORIES:
            errors.append(f"row {number}: invalid category {row['category']!r}")
        if row["domain"] not in VALID_DOMAINS:
            errors.append(f"row {number}: invalid domain {row['domain']!r}")
        if row["form"] not in VALID_FORMS:
            errors.append(f"row {number}: invalid form {row['form']!r}")
        if row["review_status"] not in VALID_STATUSES:
            errors.append(f"row {number}: invalid review_status {row['review_status']!r}")
    return errors


def _index(rows: list[dict[str, str]]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        result[normalise(row["word"])].append(row["word"])
    return result


def validate(candidate_path: Path, *, live_path: Path = LIVE_VOCABULARY,
             batch_dir: Path | None = None,
             classic_path: Path | None = CLASSIC_PHYSICAL) -> dict[str, object]:
    candidates = read_csv(candidate_path, expected_columns=EXPECTED_COLUMNS)
    live = [row for row in read_live(live_path) if row["category"] in VALID_CATEGORIES]
    errors = metadata_errors(candidates)
    findings: list[Finding] = []
    live_index = _index(live)
    live_compact = {compact_key(row["word"]): row["word"] for row in live}
    classic = read_classic_physical(classic_path) if classic_path else []
    classic_index = {normalise(word): word for word in classic}
    classic_compact = {compact_key(word): word for word in classic}
    seen: dict[str, str] = {}
    seen_compact: dict[str, str] = {}

    other_rows: list[tuple[dict[str, str], str]] = []
    if batch_dir and batch_dir.exists():
        for path in sorted(batch_dir.glob("object-expansion-batch-*.csv")):
            if path.resolve() == candidate_path.resolve():
                continue
            try:
                rows = read_csv(path, expected_columns=EXPECTED_COLUMNS)
            except ValidationFailure as exc:
                errors.append(str(exc))
                continue
            other_rows.extend((row, path.name) for row in rows)

    comparison = [(row, "live vocabulary", True) for row in live]
    comparison += [
        (row, source, row["review_status"] in {"approved", "imported"})
        for row, source in other_rows
    ]

    for row in candidates:
        word = row["word"]
        key = normalise(word)
        if not key:
            continue
        if key in live_index:
            findings.append(Finding("reject", word, live_index[key][0], "live vocabulary", "exact/format duplicate"))
        elif compact_key(word) in live_compact:
            findings.append(Finding("reject", word, live_compact[compact_key(word)], "live vocabulary",
                                    "whitespace-format duplicate"))
        if key in classic_index:
            findings.append(Finding("review", word, classic_index[key], "Classic vocabulary",
                                    "Classic vocabulary overlap"))
        elif compact_key(word) in classic_compact:
            findings.append(Finding("review", word, classic_compact[compact_key(word)],
                                    "Classic vocabulary", "Classic whitespace overlap"))
        if key in seen:
            findings.append(Finding("reject", word, seen[key], candidate_path.name, "duplicate within batch"))
        elif compact_key(word) in seen_compact:
            findings.append(Finding("reject", word, seen_compact[compact_key(word)], candidate_path.name,
                                    "whitespace-format duplicate within batch"))
        else:
            seen[key] = word
            seen_compact[compact_key(word)] = word

        for other, source, blocking in comparison:
            other_word = other["word"]
            other_key = normalise(other_word)
            if key == other_key:
                if source != "live vocabulary":
                    findings.append(Finding("reject" if blocking else "review", word, other_word, source,
                                            "approved duplicate" if blocking else "pending-batch overlap"))
                continue
            if compact_key(word) == compact_key(other_word):
                findings.append(Finding("reject" if blocking else "review", word, other_word, source,
                                        "whitespace-format duplicate" if blocking else "pending-batch overlap"))
                continue
            if singular_key(word) == singular_key(other_word):
                findings.append(Finding("reject", word, other_word, source, "singular/plural duplicate"))
                continue
            if spelling_key(word) == spelling_key(other_word):
                findings.append(Finding("review", word, other_word, source, "British/American spelling variant"))
                continue
            left_syn, right_syn = synonym_key(word), synonym_key(other_word)
            if left_syn is not None and left_syn == right_syn:
                findings.append(Finding("review", word, other_word, source, "likely synonym"))
                continue
            if near_duplicate_name(word, other_word):
                findings.append(Finding("review", word, other_word, source, "near-duplicate name"))

    # Compare candidate rows with one another for number/spelling/synonym variants.
    for index, left in enumerate(candidates):
        for right in candidates[index + 1:]:
            if normalise(left["word"]) == normalise(right["word"]):
                continue
            if singular_key(left["word"]) == singular_key(right["word"]):
                findings.append(Finding("reject", right["word"], left["word"], candidate_path.name,
                                        "singular/plural duplicate"))
            elif spelling_key(left["word"]) == spelling_key(right["word"]):
                findings.append(Finding("review", right["word"], left["word"], candidate_path.name,
                                        "British/American spelling variant"))
            elif synonym_key(left["word"]) is not None and synonym_key(left["word"]) == synonym_key(right["word"]):
                findings.append(Finding("review", right["word"], left["word"], candidate_path.name,
                                        "likely synonym"))
            else:
                if near_duplicate_name(left["word"], right["word"]):
                    findings.append(Finding("review", right["word"], left["word"], candidate_path.name,
                                            "near-duplicate name"))

    unique_findings = sorted(
        {finding for finding in findings},
        key=lambda item: (item.kind, normalise(item.word), normalise(item.match), item.source, item.reason),
    )
    rejected_words = {item.word for item in unique_findings if item.kind == "reject"}
    review_words = {item.word for item in unique_findings if item.kind == "review"}
    review_words.update(row["word"] for row in candidates if row["review_status"] == "needs_review")
    report = {
        "candidate_file": str(candidate_path),
        "candidate_count": len(candidates),
        "proposed_count": sum(row["review_status"] == "proposed" for row in candidates),
        "accepted_count": len(candidates) - len(rejected_words),
        "needs_review_count": len(review_words - rejected_words),
        "rejected_count": len(rejected_words),
        "counts_by_domain": dict(sorted(Counter(row["domain"] for row in candidates).items())),
        "metadata_errors": sorted(errors),
        "findings": [asdict(item) for item in unique_findings],
        "ready_for_human_review": not errors and not rejected_words,
    }
    return report


def render_text(report: dict[str, object]) -> str:
    lines = [
        f"Candidate file: {report['candidate_file']}",
        f"Candidates: {report['candidate_count']}",
        f"Proposed: {report['proposed_count']}",
        f"Accepted after automatic checks: {report['accepted_count']}",
        f"Needs review: {report['needs_review_count']}",
        f"Automatically rejected: {report['rejected_count']}",
        "Counts by domain:",
    ]
    lines.extend(f"  {domain}: {count}" for domain, count in report["counts_by_domain"].items())
    if report["metadata_errors"]:
        lines.append("Metadata errors:")
        lines.extend(f"  - {error}" for error in report["metadata_errors"])
    if report["findings"]:
        lines.append("Duplicate/review findings:")
        lines.extend(
            f"  - {item['kind']}: {item['word']} ~ {item['match']} "
            f"({item['reason']}; {item['source']})"
            for item in report["findings"]
        )
    lines.append("Ready for human review: " + ("yes" if report["ready_for_human_review"] else "no"))
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate_csv", type=Path)
    parser.add_argument("--live", type=Path, default=LIVE_VOCABULARY)
    parser.add_argument("--batch-dir", type=Path, default=ROOT / "docs")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        report = validate(args.candidate_csv, live_path=args.live, batch_dir=args.batch_dir)
    except (OSError, ValidationFailure) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) if args.json else render_text(report))
    return 0 if report["ready_for_human_review"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
