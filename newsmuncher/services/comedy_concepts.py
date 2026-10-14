"""Deterministic offline comedy-concept generation for editorial review."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
import json
import math
from pathlib import Path
import random
import re
import unicodedata
from functools import lru_cache

from newsmuncher.services.lexical_exposure import weighted_choice


COMPONENTS_PATH = (
    Path(__file__).parents[1] / "resources" / "concepts" / "comedy_concept_components.json"
)
CATEGORIES = (
    "everyday_british",
    "cheeky_object",
    "absurd_invention",
    "ridiculous_creature",
    "bureaucratic_nonsense",
    "emergency_equipment",
    "ceremonial_object",
)
DEFAULT_CATEGORY_WEIGHTS = {
    "everyday_british": 0.15,
    "cheeky_object": 0.20,
    "absurd_invention": 0.20,
    "ridiculous_creature": 0.20,
    "bureaucratic_nonsense": 0.15,
    "emergency_equipment": 0.05,
    "ceremonial_object": 0.05,
}
DEFAULT_INTENSITY_WEIGHTS = {1: 0.30, 2: 0.45, 3: 0.25}

SEMANTIC_THEMES = {
    "unexpected behaviour": "unexpected_behaviour",
    "inappropriate responsibility": "institutional_control",
    "visual incongruity": "visual_incongruity", "British innuendo": "innuendo",
    "comic contrast": "visual_incongruity", "improbable power source": "impossible_technology",
    "absurd capability": "impossible_technology", "ridiculous occupation": "absurd_occupation",
    "scandal or inappropriate responsibility": "institutional_control",
    "implausible personal history": "secret_history",
    "inappropriate official importance": "institutional_control",
    "bureaucratic comic contrast": "institutional_control",
    "improbable emergency purpose": "emergency_response",
    "inappropriate symbolic importance": "ceremonial_status",
    "ridiculous ceremonial purpose": "ceremonial_status",
    "domestic deception": "domestic_deception",
    "scandalous reputation": "innuendo_scandal",
    "impossible measurement": "impossible_measurement",
    "principled refusal": "principled_refusal",
    "absurd dispute resolution": "absurd_dispute",
    "comic disaster aftermath": "disaster_aftermath",
    "commemorated failure": "commemorated_failure",
}


@lru_cache(maxsize=8)
def _load_components(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def normalised(phrase: str) -> str:
    text = unicodedata.normalize("NFKD", phrase).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "", text.casefold())


def _quota_plan(count: int, weights: dict) -> list:
    """Return an exact, largest-remainder allocation in mapping order."""
    active = [(key, value) for key, value in weights.items() if value > 0]
    if count < 0 or not active or any(value < 0 for value in weights.values()):
        raise ValueError("Generation weights and count must be positive")
    total = sum(value for _, value in active)
    raw = [(key, count * value / total) for key, value in active]
    allocated = {key: math.floor(value) for key, value in raw}
    remainder = count - sum(allocated.values())
    order = sorted(raw, key=lambda item: -(item[1] - math.floor(item[1])))
    for key, _ in order[:remainder]:
        allocated[key] += 1
    return [key for key, _ in active for _ in range(allocated[key])]


@dataclass(frozen=True)
class GeneratedConcept:
    phrase: str
    category: str
    base: str
    template: str
    intensity: int
    visual_suitability: int
    grammatical_number: str
    countability: str
    article: str
    generator_version: str
    comic_mechanism: str
    semantic_theme: str
    premise_key: str
    editorial_warnings: tuple[str, ...]
    word_count: int
    score: float
    animal_species: str | None


@dataclass
class ConceptDiagnostics:
    requested: int = 0
    proposed: int = 0
    accepted: int = 0
    exhausted: bool = False
    rejected: Counter = field(default_factory=Counter)
    categories: Counter = field(default_factory=Counter)
    intensities: Counter = field(default_factory=Counter)
    templates: Counter = field(default_factory=Counter)
    bases: Counter = field(default_factory=Counter)

    @property
    def rejected_total(self) -> int:
        return sum(self.rejected.values())


@dataclass(frozen=True)
class ConceptGeneratorConfig:
    category_weights: dict[str, float] = field(
        default_factory=lambda: dict(DEFAULT_CATEGORY_WEIGHTS)
    )
    intensity_weights: dict[int, float] = field(
        default_factory=lambda: dict(DEFAULT_INTENSITY_WEIGHTS)
    )
    candidates_per_concept: int = 14
    minimum_quality: float = 6.0
    maximum_base_share: float = 0.025
    maximum_theme_share: float = 0.035

    def __post_init__(self):
        unknown = set(self.category_weights) - set(CATEGORIES)
        if unknown:
            raise ValueError(f"Unknown categories: {sorted(unknown)}")
        if set(self.intensity_weights) - {1, 2, 3}:
            raise ValueError("Intensity levels must be 1, 2 or 3")
        if any(value < 0 for value in (*self.category_weights.values(),
                                       *self.intensity_weights.values())):
            raise ValueError("Weights cannot be negative")
        if not sum(self.category_weights.values()) or not sum(self.intensity_weights.values()):
            raise ValueError("At least one category and intensity must be enabled")
        if self.candidates_per_concept < 2 or self.minimum_quality < 0:
            raise ValueError("Invalid quality-selection configuration")


class ComedyConceptGenerator:
    """Construct, filter and rank recognisable comic subjects from local banks."""

    VISUAL_SUITABILITY = {
        "everyday_british": 5,
        "cheeky_object": 5,
        "absurd_invention": 5,
        "ridiculous_creature": 5,
        "bureaucratic_nonsense": 4,
        "emergency_equipment": 5,
        "ceremonial_object": 5,
    }
    STRONG_SHORT_CREATURE_JOKES = {
        "shoplifting", "tax-avoiding", "constitutionally protected",
        "parliament-storming", "blackmailing", "picketing", "filibustering",
    }

    def __init__(self, seed: str | int | None = None,
                 config: ConceptGeneratorConfig | None = None,
                 components_path: Path = COMPONENTS_PATH,
                 vocabulary_mode: str = "off", lexical_penalties=None,
                 noun_exclusions=(), source_text="", target_bank=None,
                 component_filter_cache=None, exclusion_index=None):
        self.random = random.Random(seed)
        self.config = config or ConceptGeneratorConfig()
        self.data = _load_components(str(Path(components_path).resolve()))
        self.version = self.data["version"]
        self.blocked_terms = tuple(term.casefold() for term in self.data["blocked_terms"])
        self.overused_themes = tuple(term.casefold() for term in self.data["overused_themes"])
        self.vocabulary_mode = vocabulary_mode
        self.lexical_penalties = lexical_penalties or {}
        self.noun_exclusions = frozenset(noun_exclusions or ())
        self.source_text = source_text
        self.target_bank = target_bank
        self.component_filter_cache = (component_filter_cache
                                       if component_filter_cache is not None else {})
        self.exclusion_index = exclusion_index
        # Hard noun exclusion needs more identities than the historical compact
        # banks provide. Reuse the locally screened evaluation catalogue on that
        # already experimental path; ordinary generation remains as configured.
        catalogue_mode = ("evaluation" if self.noun_exclusions and vocabulary_mode == "off"
                          else vocabulary_mode)
        self.catalogue_banks = self._catalogue_banks(catalogue_mode)
        self._eligible_bank_cache = {}
        self.last_diagnostics = ConceptDiagnostics()

    @staticmethod
    def _catalogue_banks(mode):
        if mode == "off":
            return {}
        if mode not in {"reviewed", "evaluation"}:
            raise ValueError("vocabulary_mode must be off, reviewed or evaluation")
        # Lazy import keeps the default path independent of the large catalogue.
        from newsmuncher.services.vocabulary_catalogue import eligible_concept_entries
        animals = eligible_concept_entries("animals", mode)
        objects = eligible_concept_entries("objects", mode)

        def texts(values):
            return tuple(dict.fromkeys(item["text"] for item in values))

        physical = [item for item in objects if item["semantic_class"] not in {
            "food", "architecture", "historical_object",
        }]
        devices = [item for item in objects if item["semantic_class"] in {
            "machinery", "tool", "vehicle", "scientific_equipment",
            "medical_equipment", "musical_instrument", "physical_object",
        }]
        emergency = [item for item in objects if item["semantic_class"] in {
            "emergency_equipment", "technical_equipment",
        }]
        ceremonial = [item for item in objects
                      if item["semantic_class"] == "ceremonial_object"]
        thematic_path = (Path(__file__).parents[1] / "resources" / "vocabulary" /
                         "thematic_ingredient_seeds.json")
        thematic = json.loads(thematic_path.read_text(encoding="utf-8"))
        def reviewed_seeds(*kinds):
            return tuple(dict.fromkeys(
                item["text"]
                for domain in thematic["domains"]
                for kind in kinds
                for item in domain.get("seeds", {}).get(kind, ())
                if item.get("approval_status") == "reviewed"
                and item.get("safety_status") == "reviewed"
            ))

        reviewed_entities = reviewed_seeds("entities")
        reviewed_noun_processes = reviewed_seeds(
            "entities", "processes", "relationships")
        return {
            "creatures": texts(animals),
            "domestic_objects": texts(physical),
            "cheeky_objects": texts(physical),
            "devices": texts(devices),
            "emergency_devices": texts(emergency),
            "ceremonial_objects": texts(ceremonial),
            # Reviewed thematic entities are noun topics, not prewritten jokes.
            # They widen bureaucratic premises without inventing new templates.
            "bureau_topics": reviewed_entities,
            "bureaucratic_disputes": reviewed_noun_processes,
            "emergency_purposes": reviewed_noun_processes,
            "ceremonial_functions": reviewed_noun_processes,
            "ceremonial_purposes": reviewed_noun_processes,
            "ceremonial_failures": reviewed_noun_processes,
        }

    def _templates_for(self, category: str, intensity: int) -> list[dict]:
        result = []
        for template in self.data["templates"][category]:
            result.append(template)
        return result

    def _bank(self, bank_name: str, intensity: int | None = None,
              semantic_theme: str | None = None):
        cache_key = (bank_name, intensity, semantic_theme)
        if cache_key in self._eligible_bank_cache:
            return self._eligible_bank_cache[cache_key]
        original = self.data["banks"][bank_name]
        if isinstance(original, dict):
            original = original[str(intensity)]
        additions = self.catalogue_banks.get(bank_name, ())
        bank = tuple(dict.fromkeys((*original, *additions)))
        if self.noun_exclusions:
            from newsmuncher.services.noun_exclusion import blocked_entries
            def eligible(value):
                key = (value, semantic_theme)
                if key not in self.component_filter_cache:
                    self.component_filter_cache[key] = (
                        not blocked_entries(value, self.noun_exclusions,
                                            self.source_text, self.exclusion_index)
                        and (semantic_theme is None or
                             "premise:" + semantic_theme + ":" + normalised(value)
                             not in self.noun_exclusions)
                    )
                return self.component_filter_cache[key]
            bank = tuple(value for value in bank if eligible(value))
        self._eligible_bank_cache[cache_key] = bank
        return bank

    def _pick(self, bank_name: str, intensity: int | None = None,
              semantic_theme: str | None = None) -> str:
        bank = self._bank(bank_name, intensity, semantic_theme)
        if not bank:
            raise ValueError(f"No eligible values remain in concept bank {bank_name}")
        return weighted_choice(self.random, bank, self.lexical_penalties)

    def _candidate(self, category: str, intensity: int) -> tuple[GeneratedConcept, str]:
        templates = self._templates_for(category, intensity)
        templates = [template for template in templates
                     if self._bank("creatures" if self.target_bank == "animals"
                                   else template["base_bank"])
                     and ("modifier_bank" not in template or self._bank(
                         template["modifier_bank"], intensity,
                         SEMANTIC_THEMES[template["mechanism"]]))
                     and ("topic_bank" not in template or self._bank(
                         template["topic_bank"], None,
                         SEMANTIC_THEMES[template["mechanism"]]))]
        if not templates:
            raise ValueError(f"No {category} template supports intensity {intensity}")
        template = self.random.choices(
            templates, weights=[item.get("weight", 1) for item in templates], k=1
        )[0]
        base_bank = ("creatures" if self.target_bank == "animals"
                     else template["base_bank"])
        base = self._pick(base_bank)
        values = {"base": base}
        theme = ""
        if "modifier_bank" in template:
            values["modifier"] = self._pick(
                template["modifier_bank"], intensity,
                SEMANTIC_THEMES[template["mechanism"]])
            theme = values["modifier"]
        if "topic_bank" in template:
            values["topic"] = self._pick(
                template["topic_bank"], None,
                SEMANTIC_THEMES[template["mechanism"]])
            theme = values["topic"]
        phrase = re.sub(r"\s+", " ", template["pattern"].format(**values)).strip()
        visual = self.VISUAL_SUITABILITY[category]
        words = re.findall(r"[A-Za-z]+(?:-[A-Za-z]+)?", phrase)
        score = visual + 1.25 + (0.75 if 3 <= len(words) <= 6 else 0.25)
        score += intensity * 0.15
        if template["id"] == "strong_compact_creature":
            score += 0.8  # editorially approved short premises compete on merit
        if category == "bureaucratic_nonsense":
            score += 0.5  # clear human conflict compensates for a less physical phrase
        if len(words) > 8:
            score -= 2.0
        warnings = []
        if len(words) == 2:
            warnings.append("short premise")
        if len(words) > 6:
            warnings.append("long phrase")
        if any(re.search(rf"(?<![a-z]){re.escape(theme)}(?![a-z])", phrase.casefold())
               for theme in self.overused_themes):
            warnings.append("monitored recurring theme")
        article = self._article_for(phrase)
        mechanism = template["mechanism"]
        semantic_theme = SEMANTIC_THEMES[mechanism]
        premise_key = f"{semantic_theme}:{normalised(theme or base)}"
        concept = GeneratedConcept(
            phrase=phrase,
            category=category,
            base=base,
            template=template["id"],
            intensity=intensity,
            visual_suitability=visual,
            grammatical_number="singular",
            countability="countable",
            article=article,
            generator_version=self.version,
            comic_mechanism=mechanism,
            semantic_theme=semantic_theme,
            premise_key=premise_key,
            editorial_warnings=tuple(warnings),
            word_count=len(words),
            score=round(score, 2),
            animal_species=(base if self.target_bank == "animals" or
                            category == "ridiculous_creature" else
                            next(iter(sorted(animal_mentions(phrase))), None)),
        )
        return concept, theme

    @staticmethod
    def _article_for(phrase: str) -> str:
        first = re.match(r"[A-Za-z]+", phrase)
        word = first.group(0).casefold() if first else ""
        if word.startswith(("honorary", "hour")):
            return "an"
        if word.startswith(("uni", "use", "euro", "one")):
            return "a"
        return "an" if word[:1] in "aeiou" else "a"

    def rejection_reason(self, candidate: GeneratedConcept) -> str | None:
        folded = candidate.phrase.casefold()
        if any(re.search(rf"(?<![a-z]){re.escape(term)}(?![a-z])", folded)
               for term in self.blocked_terms):
            return "blocked_term"
        words = re.findall(r"[a-z]+", folded)
        if not 2 <= len(words) <= 8:
            return "word_count"
        if len(words) != len(set(words)):
            return "repeated_word"
        if normalised(candidate.base) not in normalised(candidate.phrase):
            return "base_not_visible"
        if candidate.score < self.config.minimum_quality:
            return "quality_score"
        if candidate.category == "ridiculous_creature" and candidate.word_count == 2:
            premise = candidate.phrase.rsplit(" ", 1)[0].casefold()
            if (candidate.template != "strong_compact_creature" or
                    premise not in self.STRONG_SHORT_CREATURE_JOKES):
                return "weak_short_creature"
        if candidate.category == "ceremonial_object" and candidate.word_count < 3:
            return "weak_short_ceremonial_object"
        valid_templates = {item["id"] for item in self.data["templates"][candidate.category]}
        if candidate.template not in valid_templates:
            return "template_mismatch"
        return None

    def generate(self, count: int, category: str | None = None,
                 intensity: int | None = None) -> list[GeneratedConcept]:
        if category is not None and category not in CATEGORIES:
            raise ValueError(f"Unknown category: {category}")
        if intensity is not None and intensity not in (1, 2, 3):
            raise ValueError("Intensity must be 1, 2 or 3")
        category_plan = ([category] * count if category else
                         _quota_plan(count, self.config.category_weights))
        intensity_plan = ([intensity] * count if intensity else
                          _quota_plan(count, self.config.intensity_weights))
        self.random.shuffle(category_plan)
        self.random.shuffle(intensity_plan)
        diagnostics = ConceptDiagnostics(requested=count)
        accepted: list[GeneratedConcept] = []
        used: set[str] = set()
        themes = Counter()
        bases = Counter()
        short_creatures = 0
        short_creature_cap = max(
            1, math.ceil(category_plan.count("ridiculous_creature") * 0.10)
        )
        base_cap = max(3, math.ceil(count * self.config.maximum_base_share))
        theme_cap = max(3, math.ceil(count * self.config.maximum_theme_share))

        for planned_category, planned_intensity in zip(category_plan, intensity_plan):
            pool: list[tuple[GeneratedConcept, str]] = []
            # Near the end of a large unique batch, several random proposals may
            # already be occupied. Keep searching a bounded component space rather
            # than declaring false exhaustion after one unlucky draw.
            attempts = self.config.candidates_per_concept * 10
            for _ in range(attempts):
                candidate, theme = self._candidate(planned_category, planned_intensity)
                diagnostics.proposed += 1
                fingerprint = normalised(candidate.phrase)
                reason = self.rejection_reason(candidate)
                if reason:
                    diagnostics.rejected[reason] += 1
                elif fingerprint in used:
                    diagnostics.rejected["duplicate"] += 1
                elif (candidate.category == "ridiculous_creature" and
                      candidate.word_count == 2 and
                      short_creatures >= short_creature_cap):
                    diagnostics.rejected["short_creature_variety_cap"] += 1
                elif bases[candidate.base] >= base_cap:
                    diagnostics.rejected["base_overuse"] += 1
                elif theme and themes[theme] >= theme_cap:
                    diagnostics.rejected["theme_overuse"] += 1
                else:
                    pool.append((candidate, theme))
                    if len(pool) >= self.config.candidates_per_concept:
                        break
            if not pool:
                diagnostics.exhausted = True
                self.last_diagnostics = diagnostics
                raise ValueError(
                    f"Concept space exhausted for {planned_category} at intensity "
                    f"{planned_intensity} after {len(accepted)} results"
                )
            # Prefer strong phrasing, then underused bases/themes; seeded jitter breaks ties.
            candidate, theme = max(
                pool,
                key=lambda item: (
                    item[0].score,
                    -bases[item[0].base],
                    -themes[item[1]],
                    self.random.random(),
                ),
            )
            accepted.append(candidate)
            used.add(normalised(candidate.phrase))
            bases[candidate.base] += 1
            if theme:
                themes[theme] += 1
            if candidate.category == "ridiculous_creature" and candidate.word_count == 2:
                short_creatures += 1
            diagnostics.accepted += 1
            diagnostics.categories[candidate.category] += 1
            diagnostics.intensities[candidate.intensity] += 1
            diagnostics.templates[candidate.template] += 1
            diagnostics.bases[candidate.base] += 1
        self.last_diagnostics = diagnostics
        return accepted


@lru_cache(maxsize=1)
def animal_vocabulary() -> tuple[str, ...]:
    """Canonical local species used for conservative accepted-text detection."""
    data = _load_components(str(COMPONENTS_PATH.resolve()))
    return tuple(data["banks"]["creatures"])


def animal_forms(species: str) -> tuple[str, ...]:
    """Return deliberately conservative singular/plural forms."""
    irregular = {"goose": "geese", "mouse": "mice", "sheep": "sheep",
                 "cod": "cod", "salmon": "salmon"}
    if species in irregular:
        plural = irregular[species]
    elif species.endswith("y") and species[-2:-1] not in "aeiou":
        plural = species[:-1] + "ies"
    elif species.endswith(("s", "x", "ch", "sh")):
        plural = species + "es"
    else:
        plural = species + "s"
    return tuple(dict.fromkeys((species, plural)))


@lru_cache(maxsize=1)
def _animal_matcher():
    forms = {form: species for species in animal_vocabulary()
             for form in animal_forms(species)}
    alternatives = "|".join(re.escape(form) for form in sorted(forms, key=len, reverse=True))
    return re.compile(rf"(?<![a-z])(?:{alternatives})(?![a-z])"), forms


def animal_mentions(text: str) -> set[str]:
    """Find only known generator species using word-bounded local matching."""
    folded = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode().casefold()
    matcher, forms = _animal_matcher()
    return {forms[match.group(0)] for match in matcher.finditer(folded)}
