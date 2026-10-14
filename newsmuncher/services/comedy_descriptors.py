"""Deterministic offline comedy-descriptor generation for editorial review."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
import json, math, random, re, unicodedata
import copy
from pathlib import Path
from functools import lru_cache

from newsmuncher.services.lexical_exposure import weighted_choice

COMPONENTS_PATH = Path(__file__).parents[1] / "resources/descriptors/comedy_descriptor_components.json"
EXPANSION_PATH = Path(__file__).parents[1] / "resources/descriptors/phase4e_descriptor_expansion.json"
CATEGORIES = ("cheeky_british", "broader_absurdity")
ROLES = ("pre_noun", "adverbial", "predicate", "post_noun", "behavioural", "short_clause")
DEFAULT_CATEGORY_WEIGHTS = {"cheeky_british": .70, "broader_absurdity": .30}
DEFAULT_INTENSITY_WEIGHTS = {1: .30, 2: .45, 3: .25}

SEMANTIC_THEMES = {
    "comic_contradiction": "contradiction", "social_embarrassment": "social_display",
    "absurd_legal_restriction": "institutional_control",
    "institutional_interference": "institutional_control",
    "ridiculous_medical_advice": "medical_restriction",
    "disproportionate_emotion": "petty_emotion", "secret_history": "secret_history",
    "impossible_inability": "impossible_trait", "impossible_ability": "impossible_trait",
    "inappropriate_confidence": "misplaced_confidence",
    "class_and_etiquette": "social_ritual", "petty_grievance": "petty_campaign",
    "ridiculous_motivation": "absurd_motive",
    "meteorological_affliction": "weather_anomaly",
    "domestic_supernaturalism": "domestic_supernaturalism",
    "financial_folly": "financial_folly",
    "temporal_quirk": "temporal_quirk",
    "mistaken_relationship": "mistaken_relationship",
    "invented_ritual_status": "invented_ritual",
    "compulsory_ritual": "compulsory_ritual",
    "cosmic_motivation": "cosmic_motive",
    "peculiar_habit": "peculiar_habit", "romantic_complication": "romantic_complication",
    "questionable_condition": "medical_oddity", "bizarre_qualification": "dubious_expertise",
    "workplace_incompetence": "workplace_failure", "irrational_fear": "irrational_fear",
    "peculiar_ambition": "peculiar_ambition", "personal_scandal": "personal_scandal",
    "unusual_hobby": "unusual_hobby", "social_rivalry": "social_rivalry",
    "personal_legal_restriction": "personal_legal_restriction",
    "unlikely_achievement": "unlikely_achievement",
}

ROLE_GUIDANCE = {
    "pre_noun": ("place directly before a person or character noun", "The {phrase} mayor opened the meeting."),
    "adverbial": ("place after an action to explain its motive or circumstances", "The mayor opened the meeting {phrase}."),
    "predicate": ("place after a linking verb such as ‘is’ or ‘was’", "The mayor is {phrase}."),
    "post_noun": ("place after the noun as a comma-delimited postmodifier", "The mayor, {phrase}, opened the meeting."),
    "behavioural": ("attach after the noun as a comma-delimited ongoing behaviour", "The mayor, {phrase}, opened the meeting."),
    "short_clause": ("use with the template’s supplied subject or after a named subject", None),
}


@lru_cache(maxsize=8)
def _load_components(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def normalised(text):
    value = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def quota_plan(count, weights):
    active = [(key, value) for key, value in weights.items() if value > 0]
    if count < 0 or not active or any(value < 0 for value in weights.values()):
        raise ValueError("Generation weights and count must be positive")
    total = sum(value for _, value in active)
    raw = [(key, count * value / total) for key, value in active]
    allocated = {key: math.floor(value) for key, value in raw}
    for key, _ in sorted(raw, key=lambda pair: -(pair[1] - math.floor(pair[1])))[:count-sum(allocated.values())]:
        allocated[key] += 1
    return [key for key, _ in active for _ in range(allocated[key])]


@dataclass(frozen=True)
class GeneratedDescriptor:
    phrase: str
    grammatical_role: str
    comic_mechanism: str
    semantic_theme: str
    premise_key: str
    category: str
    intensity: int
    template: str
    generator_version: str
    word_count: int
    quality_score: float
    editorial_warnings: tuple[str, ...]
    subject: str
    insertion_rule: str
    usage_example: str


@dataclass
class DescriptorDiagnostics:
    requested: int = 0
    proposed: int = 0
    accepted: int = 0
    eligible: int = 0
    unselected: int = 0
    exhausted: bool = False
    rejected: Counter = field(default_factory=Counter)
    categories: Counter = field(default_factory=Counter)
    intensities: Counter = field(default_factory=Counter)
    roles: Counter = field(default_factory=Counter)
    templates: Counter = field(default_factory=Counter)
    mechanisms: Counter = field(default_factory=Counter)
    subjects: Counter = field(default_factory=Counter)

    @property
    def rejected_total(self):
        return sum(self.rejected.values())


@dataclass(frozen=True)
class DescriptorGeneratorConfig:
    category_weights: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_CATEGORY_WEIGHTS))
    intensity_weights: dict[int, float] = field(default_factory=lambda: dict(DEFAULT_INTENSITY_WEIGHTS))
    candidates_per_descriptor: int = 8
    minimum_quality: float = 6.0
    maximum_template_share: float = .10
    maximum_subject_share: float = .025

    def __post_init__(self):
        if set(self.category_weights) - set(CATEGORIES):
            raise ValueError("Unknown descriptor category")
        if set(self.intensity_weights) - {1, 2, 3}:
            raise ValueError("Intensity levels must be 1, 2 or 3")
        if (not sum(self.category_weights.values()) or not sum(self.intensity_weights.values()) or
                any(value < 0 for value in (*self.category_weights.values(), *self.intensity_weights.values()))):
            raise ValueError("Invalid descriptor weights")
        if self.candidates_per_descriptor < 2 or self.minimum_quality < 0:
            raise ValueError("Invalid descriptor selection limits")


class ComedyDescriptorGenerator:
    def __init__(self, seed=None, config=None, components_path=COMPONENTS_PATH,
                 expansion_mode="off", lexical_penalties=None):
        self.random = random.Random(seed)
        self.config = config or DescriptorGeneratorConfig()
        self.data = copy.deepcopy(_load_components(str(Path(components_path).resolve())))
        if expansion_mode not in {"off", "reviewed", "phase4e", "evaluation"}:
            raise ValueError("descriptor expansion mode must be off, reviewed or evaluation")
        if expansion_mode in {"phase4e", "evaluation"}:
            expansion = _load_components(str(EXPANSION_PATH.resolve()))
            for bank, values in expansion["banks"].items():
                self.data["banks"].setdefault(bank, []).extend(values)
            self.data["templates"].extend(expansion["templates"])
            self.data["version"] += "+" + expansion["version"]
        self.version = self.data["version"]
        self.blocked = tuple(value.casefold() for value in self.data["blocked_terms"])
        self.monitored = tuple(value.casefold() for value in self.data["monitored_themes"])
        self.last_diagnostics = DescriptorDiagnostics()
        self.lexical_penalties = lexical_penalties or {}

    def _candidate(self, category, intensity, role=None):
        templates = [item for item in self.data["templates"] if item["category"] == category]
        if role is not None:
            templates = [item for item in templates if item["role"] == role]
        if not templates:
            raise ValueError(f"No descriptor templates for {category}/{role}")
        template = self.random.choices(templates, [item.get("weight", 1) for item in templates], k=1)[0]
        values = {slot: weighted_choice(self.random, self.data["banks"][bank],
                                        self.lexical_penalties)
                  for slot, bank in template["slots"].items()}
        phrase = re.sub(r"\s+", " ", template["pattern"].format(**values)).strip()
        words = re.findall(r"[A-Za-z]+(?:-[A-Za-z]+)?", phrase)
        subject = values[template.get("subject_slot", next(reversed(values)))]
        score = 6.0 + .15 * intensity + min(len(template["slots"]), 2) * .35
        if 2 <= len(words) <= 5: score += .85
        elif len(words) <= 8: score += .65
        elif len(words) <= 10: score += .2
        elif len(words) <= 13: score += .05
        else: score -= .3 * (len(words) - 13)
        if template["mechanism"] in {
            "absurd_legal_restriction", "institutional_interference", "ridiculous_medical_advice",
            "impossible_ability", "impossible_inability", "secret_history", "comic_contradiction",
            "peculiar_habit", "romantic_complication", "questionable_condition",
            "bizarre_qualification", "workplace_incompetence", "irrational_fear",
            "peculiar_ambition", "personal_scandal", "unusual_hobby", "social_rivalry",
            "personal_legal_restriction", "unlikely_achievement",
        }:
            score += .45
        warnings = []
        if len(words) > 10: warnings.append("long descriptor")
        if any(theme in phrase.casefold() for theme in self.monitored): warnings.append("monitored recurring theme")
        insertion_rule, default_example = ROLE_GUIDANCE[template["role"]]
        example_pattern = template.get("example_pattern") or default_example or "{phrase}."
        usage_example = example_pattern.format(phrase=phrase)
        usage_example = usage_example[:1].upper() + usage_example[1:]
        semantic_theme = SEMANTIC_THEMES[template["mechanism"]]
        premise_key = f"{semantic_theme}:{normalised(subject)}"
        return GeneratedDescriptor(
            phrase, template["role"], template["mechanism"], semantic_theme, premise_key, category, intensity,
            template["id"], self.version, len(words), round(score, 2), tuple(warnings), subject,
            insertion_rule, usage_example,
        )

    def rejection_reason(self, item):
        folded = item.phrase.casefold()
        if any(re.search(rf"(?<![a-z]){re.escape(term)}(?![a-z])", folded) for term in self.blocked):
            return "blocked_term"
        words = re.findall(r"[a-z]+", folded)
        if not 2 <= len(words) <= 16: return "word_count"
        if re.search(r"\b(to to|of of|by by|about about|an a|a an)\b", folded): return "awkward_join"
        if len(words) != len(set(words)): return "repeated_word"
        if item.grammatical_role not in ROLES: return "invalid_role"
        if item.quality_score < self.config.minimum_quality: return "quality_score"
        templates = {template["id"] for template in self.data["templates"] if template["category"] == item.category}
        if item.template not in templates: return "template_mismatch"
        return None

    def generate(self, count, category=None, intensity=None, role=None):
        if category is not None and category not in CATEGORIES: raise ValueError("Unknown descriptor category")
        if intensity is not None and intensity not in {1, 2, 3}: raise ValueError("Intensity must be 1, 2 or 3")
        if role is not None and role not in ROLES: raise ValueError("Unknown descriptor role")
        compatible_categories = {
            item["category"] for item in self.data["templates"]
            if role is None or item["role"] == role
        }
        if category is not None and category not in compatible_categories:
            raise ValueError(f"No descriptor templates for {category}/{role}")
        role_weights = {key:value for key,value in self.config.category_weights.items()
                        if key in compatible_categories}
        category_plan = [category] * count if category else quota_plan(count, role_weights)
        intensity_plan = [intensity] * count if intensity else quota_plan(count, self.config.intensity_weights)
        self.random.shuffle(category_plan); self.random.shuffle(intensity_plan)
        report = DescriptorDiagnostics(requested=count)
        accepted, used = [], set()
        category_totals = Counter(category_plan)
        templates_by_category = Counter(item["category"] for item in self.data["templates"]
                                        if role is None or item["role"] == role)
        template_caps = {
            key: max(4, math.ceil(total / templates_by_category[key] * 1.7))
            for key, total in category_totals.items()
        }
        subject_cap = max(3, math.ceil(count * self.config.maximum_subject_share))
        for planned_category, planned_intensity in zip(category_plan, intensity_plan):
            pool = []
            # Large editorial audits approach the bounded space of a few compact
            # templates. Keep searching locally rather than reporting exhaustion
            # after an unlucky run of duplicates near the end of the batch.
            for _ in range(self.config.candidates_per_descriptor * 100):
                candidate = self._candidate(planned_category, planned_intensity, role)
                report.proposed += 1
                fingerprint = normalised(candidate.phrase)
                reason = self.rejection_reason(candidate)
                if reason: report.rejected[reason] += 1
                elif fingerprint in used: report.rejected["duplicate"] += 1
                elif report.templates[candidate.template] >= template_caps[planned_category]: report.rejected["template_diversity_cap"] += 1
                elif report.subjects[candidate.subject] >= subject_cap: report.rejected["subject_diversity_cap"] += 1
                else:
                    pool.append(candidate)
                    report.eligible += 1
                    if len(pool) >= self.config.candidates_per_descriptor: break
            if not pool:
                report.exhausted = True; self.last_diagnostics = report
                raise ValueError(f"Descriptor space exhausted after {len(accepted)} results")
            candidate = max(pool, key=lambda item: (item.quality_score, self.random.random()))
            report.unselected += len(pool) - 1
            accepted.append(candidate); used.add(normalised(candidate.phrase))
            report.categories[candidate.category] += 1; report.intensities[candidate.intensity] += 1
            report.roles[candidate.grammatical_role] += 1; report.templates[candidate.template] += 1
            report.mechanisms[candidate.comic_mechanism] += 1; report.subjects[candidate.subject] += 1
        report.accepted = len(accepted); self.last_diagnostics = report
        assert report.proposed == report.rejected_total + report.eligible
        assert report.eligible == report.accepted + report.unselected
        return accepted


def assemble_descriptor_slate(pool: list[GeneratedDescriptor], seed: str, count: int = 10,
                              avoid_themes=(), diversify=False, family_penalties=None) -> list[GeneratedDescriptor]:
    """Recombine a broad pool into an exact-quota, grammar-complete slate."""
    if count < len(ROLES):
        raise ValueError("A grammar-complete descriptor slate requires at least six items")
    rng = random.Random(seed)
    category_remaining = Counter(quota_plan(count, DEFAULT_CATEGORY_WEIGHTS))
    intensity_remaining = Counter(quota_plan(count, DEFAULT_INTENSITY_WEIGHTS))
    # Assign scarce roles first, then fill the remaining slots. Backtracking
    # makes role coverage and both quota systems true invariants for every seed.
    role_counts = Counter(item.grammatical_role for item in pool)
    required_roles = sorted(ROLES, key=lambda role: role_counts[role])
    requirements = required_roles + [None] * (count - len(required_roles))
    jitter = {normalised(item.phrase): rng.random() for item in pool}
    family_penalties = family_penalties or {}

    def search(position, chosen, categories, intensities, phrases, subjects):
        if position == count:
            return chosen if not any(categories.values()) and not any(intensities.values()) else None
        required_role = requirements[position]
        mechanisms = Counter(item.comic_mechanism for item in chosen)
        candidates = [item for item in pool
                      if (required_role is None or item.grammatical_role == required_role)
                      and categories[item.category] > 0 and intensities[item.intensity] > 0
                      and normalised(item.phrase) not in phrases
                      and normalised(item.subject) not in subjects]
        candidates.sort(key=lambda item: (
            item.semantic_theme not in avoid_themes,
            not mechanisms[item.comic_mechanism], item.word_count <= 8,
            -mechanisms[item.comic_mechanism],
            -max(family_penalties.get(item.comic_mechanism, 0.0),
                 family_penalties.get("premise:" + item.premise_key, 0.0),
                 family_penalties.get("offered:" + normalised(item.phrase), 0.0),
                 family_penalties.get("offered-premise:" + normalised(item.premise_key), 0.0)),
            # Phase 4F samples across the entire quality-filtered stratum instead
            # of repeatedly taking the same tiny set of top-scoring phrases.
            jitter[normalised(item.phrase)] if diversify else item.quality_score,
            item.quality_score if diversify else jitter[normalised(item.phrase)],
        ), reverse=True)
        for item in candidates[:60]:
            categories[item.category] -= 1; intensities[item.intensity] -= 1
            result = search(
                position + 1, chosen + [item], categories, intensities,
                phrases | {normalised(item.phrase)}, subjects | {normalised(item.subject)},
            )
            categories[item.category] += 1; intensities[item.intensity] += 1
            if result is not None:
                return result
        return None

    chosen = search(0, [], category_remaining, intensity_remaining, set(), set())
    if chosen is not None:
        rng.shuffle(chosen)
        return chosen
    raise RuntimeError("Could not assemble a role- and subject-diverse descriptor slate")


def descriptor_candidate_pool(seed: str, count: int = 10,
                              expansion_mode: str = "off",
                              lexical_penalties=None) -> list[GeneratedDescriptor]:
    """Generate enough varied material for many deterministic slate assemblies."""
    pool = ComedyDescriptorGenerator(
        f"{seed}:expanded", expansion_mode=expansion_mode,
        lexical_penalties=lexical_penalties).generate(max(500, count * 50))
    for role in ROLES:
        pool.extend(ComedyDescriptorGenerator(
            f"{seed}:role:{role}", expansion_mode=expansion_mode,
            lexical_penalties=lexical_penalties).generate(
                24, role=role))
    # Deduplicate before registries recombine the pool around active cooldowns.
    return list({normalised(item.phrase): item for item in pool}.values())


def descriptor_slate(seed: str, count: int = 10, avoid_themes=(),
                     expansion_mode: str = "off") -> list[GeneratedDescriptor]:
    """Build an exact-weight slate with role, mechanism and subject diversity."""
    return assemble_descriptor_slate(
        descriptor_candidate_pool(seed, count, expansion_mode), seed, count,
        avoid_themes=avoid_themes, diversify=expansion_mode == "evaluation",
    )
