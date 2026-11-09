"""Immutable routing metadata for the three Create-page MUNGE engines."""
from dataclasses import dataclass
from enum import Enum

from newsmuncher.services.comedy_concepts import animal_mentions

class MungeEngine(str, Enum):
    CLASSIC = "classic"
    CURRENT = "current"
    EXPERIMENTAL = "experimental"


@dataclass(frozen=True)
class MungeEnginePlan:
    engine: MungeEngine
    classic_csv: bool = False
    experimental_options: tuple[tuple[str, str], ...] = ()


def engine_plan(value, experimental_options=None):
    engine = MungeEngine(value)
    if engine is MungeEngine.CLASSIC:
        return MungeEnginePlan(engine, classic_csv=True)
    if engine is MungeEngine.EXPERIMENTAL:
        # Copy caller-owned configuration into an immutable value. Future
        # experiments cannot mutate the CURRENT benchmark's empty options.
        options = tuple(sorted(dict(experimental_options or {}).items()))
        return MungeEnginePlan(engine, experimental_options=options)
    return MungeEnginePlan(MungeEngine.CURRENT)


def modern_prompt_concepts(concepts, animal_limit=4):
    """Expose four strong animal alternatives while retaining all non-animal concepts."""
    concepts = list(concepts or ())
    animals = [(index, item) for index, item in enumerate(concepts)
               if item.get("target_bank") == "animals"]
    ranked = sorted(
        animals,
        key=lambda pair: (
            max(1, len(animal_mentions(pair[1].get("phrase", "")))),
            -float(pair[1].get("score", 0)),
            pair[0],
        ),
    )
    retained_ids = {id(item) for _, item in ranked[:animal_limit]}
    presented = [item for item in concepts
                 if item.get("target_bank") != "animals" or id(item) in retained_ids]
    return presented, {
        "selected_animals": len(animals),
        "presented_animals": min(animal_limit, len(animals)),
        "hidden_animals": max(0, len(animals) - animal_limit),
        "presented_concepts": len(presented),
    }


def project_modern_variant(variant_plan, animal_limit=4):
    """Project a variant consistently across prompt and tracking provenance."""
    presented, metrics = modern_prompt_concepts(variant_plan["prompt"], animal_limit)
    retained = {id(item) for item in presented}
    presented_raw = {item.get("phrase") for item in presented if item.get("raw")}
    variant_plan["prompt"] = presented
    variant_plan["generated"] = [
        item for item in variant_plan["generated"] if id(item) in retained
    ]
    variant_plan["raw"] = [
        item for item in variant_plan.get("raw", ()) if item.get("text") in presented_raw
    ]
    return variant_plan, metrics
