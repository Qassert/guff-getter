"""Deterministic, offline comedy-name generation with no live rewrite integration."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
import csv
import copy
import json
import math
from pathlib import Path
import random
import re
import unicodedata

from newsmuncher.config import WORDS_DIR


COMPONENTS_PATH = Path(__file__).parents[1] / "resources" / "names" / "comedy_name_components.json"
EXPANSION_PATH = Path(__file__).parents[1] / "resources" / "names" / "phase4e_name_expansion.json"
LEGACY_NAMES_PATH = WORDS_DIR / "names.csv"
STYLES = ("cheeky", "absurd", "phonetic")


@dataclass(frozen=True)
class GeneratedName:
    name: str
    category: str
    recipe: str
    score: float = 0.0
    first_component: str = ""
    surname_component: str = ""
    meaning: str = ""
    technique: str = ""
    generated: bool = True
    family: str = ""


@dataclass
class GenerationDiagnostics:
    requested: int = 0
    proposed: int = 0
    accepted: int = 0
    exhausted: bool = False
    rejected: Counter = field(default_factory=Counter)
    templates: Counter = field(default_factory=Counter)
    first_components: Counter = field(default_factory=Counter)
    surname_components: Counter = field(default_factory=Counter)

    @property
    def rejected_total(self):
        return sum(self.rejected.values())


@dataclass(frozen=True)
class NameGeneratorConfig:
    cheeky_weight: float = 0.70
    absurd_weight: float = 0.30
    candidates_per_name: int = 12
    minimum_quality: float = 5.0
    # Reserved for Phase 2. These values are deliberately not used by the live app.
    future_category_weights: dict[str, float] = field(default_factory=lambda: {
        "invented": 1.0, "celebrity": 0.0, "historical": 0.0,
    })

    def __post_init__(self):
        if self.cheeky_weight < 0 or self.absurd_weight < 0:
            raise ValueError("Invented-name weights cannot be negative")
        if self.cheeky_weight + self.absurd_weight <= 0:
            raise ValueError("At least one invented-name style must have weight")
        if self.candidates_per_name < 2 or self.minimum_quality < 0:
            raise ValueError("Quality selection settings are invalid")
        if any(value < 0 for value in self.future_category_weights.values()):
            raise ValueError("Future category weights cannot be negative")


def normalized(name: str) -> str:
    text = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().casefold()
    return re.sub(r"[^a-z0-9]+", "", text)


def legacy_names(path: Path = LEGACY_NAMES_PATH) -> set[str]:
    with path.open(encoding="utf-8", newline="") as source:
        return {normalized(value.strip()) for row in csv.reader(source)
                for value in row if value.strip()}


class ComedyNameGenerator:
    """Build and rank filtered review candidates from curated local components."""

    RECIPE_QUALITY = {
        "curated": 9.5, "alliterative": 8.4, "given+double": 7.8,
        "given+nickname+constructed": 7.7, "given+constructed": 7.1,
        "given+classic": 6.8, "title+classic": 7.2, "title+constructed": 7.5,
        "bare+epithet": 8.0, "title+territory": 8.2, "double+title": 8.1,
        "elaborate": 9.0, "phonetic": 10.0, "spoonerism": 10.0,
        "phonetic-generated": 10.0,
    }

    def __init__(self, seed: str | int | None = None, config: NameGeneratorConfig | None = None,
                 components_path: Path = COMPONENTS_PATH, known_names: set[str] | None = None,
                 expansion_mode: str = "off"):
        self.random = random.Random(seed)
        self.config = config or NameGeneratorConfig()
        self.data = json.loads(components_path.read_text(encoding="utf-8"))
        if expansion_mode not in {"off", "reviewed", "phase4e", "evaluation"}:
            raise ValueError("name expansion mode must be off, reviewed or evaluation")
        if expansion_mode in {"phase4e", "evaluation"}:
            expansion = json.loads(EXPANSION_PATH.read_text(encoding="utf-8"))
            self.data = copy.deepcopy(self.data)
            for style in ("cheeky", "absurd"):
                for bank, values in expansion[style].items():
                    self.data[style].setdefault(bank, []).extend(values)
        self.known_names = legacy_names() if known_names is None else {normalized(n) for n in known_names}
        self.blocked_terms = tuple(term.casefold() for term in self.data["blocked_terms"])
        self.blocked_pairs = {tuple(pair) for pair in self.data["blocked_pairs"]}
        self.familiar_jokes = {
            normalized(name) for name in self.data["phonetic_generator"]["familiar_exclusions"]
        }
        self.last_diagnostics = GenerationDiagnostics()

    def rejection_reason(self, name: str, allow_known: bool = False) -> str | None:
        compact = normalized(name)
        if not compact:
            return "empty"
        if compact in self.familiar_jokes:
            return "familiar_joke"
        if not allow_known and compact in self.known_names:
            return "legacy_collision"
        folded = name.casefold()
        if any(re.search(rf"(?<![a-z]){re.escape(term)}(?![a-z])", folded)
               for term in self.blocked_terms):
            return "blocked_term"
        if len(name) > 110:
            return "too_long"
        words = re.findall(r"[A-Za-z]+", unicodedata.normalize("NFKD", name))
        ignored = {
            "sir", "lady", "lord", "professor", "doctor", "dame", "the", "right",
            "honourable", "canon", "baron", "baroness", "viscount", "countess", "of",
            "keeper", "duchess", "earl", "custodian", "inspector", "chairman", "warden",
            "master", "municipal", "royal", "emergency", "third", "fourth", "marquess",
            "hereditary", "wrangler", "deputy", "comptroller", "palace", "bearer", "grand",
            "convenor", "inquiry", "acting", "beadle", "chief", "pursuivant", "permanent",
            "secretary", "honorary", "admiral",
            "d",
        }
        content = [word for word in words if word.casefold() not in ignored]
        if not content:
            return "no_spoken_content"
        if any(len(word) > 1 and not re.search(r"[aeiouy]", word, re.I) for word in content):
            return "missing_vowel"
        if any(re.search(r"[^aeiouy]{6,}", word, re.I) for word in content):
            return "consonant_cluster"
        if any(a.casefold() == b.casefold() for a, b in zip(words, words[1:])):
            return "repeated_word"
        return None

    def acceptable(self, name: str, allow_known: bool = False) -> bool:
        return self.rejection_reason(name, allow_known) is None

    def _weighted_recipe(self, bank):
        recipes, weights = zip(*bank["template_weights"].items())
        return self.random.choices(recipes, weights=weights, k=1)[0]

    def _constructed_surname(self, bank):
        return self.random.choice(bank["surname_roots"]) + self.random.choice(bank["surname_suffixes"])

    def _score(self, candidate: GeneratedName) -> float:
        score = self.RECIPE_QUALITY[candidate.recipe]
        words = re.findall(r"[A-Za-z]+", candidate.name)
        spoken_words = [word for word in words if word.casefold() not in {
            "the", "right", "honourable", "of", "sir", "lady", "lord", "dame", "doctor",
            "professor", "canon", "baron", "baroness", "viscount", "countess",
        }]
        if 2 <= len(spoken_words) <= 6:
            score += 0.8
        elif len(spoken_words) > 10:
            score -= 1.2
        if candidate.first_component and candidate.surname_component:
            if candidate.first_component[0].casefold() == candidate.surname_component[0].casefold():
                score += 1.1
        if 12 <= len(candidate.name) <= 48:
            score += 0.5
        elif len(candidate.name) > 85:
            score -= 0.8
        if "-" in candidate.name:
            score += 0.25
        return round(score, 3)

    def _cheeky_candidate(self, recipe=None) -> GeneratedName:
        bank = self.data["cheeky"]
        recipe = recipe or self._weighted_recipe(bank)
        if recipe == "curated":
            name = self.random.choice(bank["curated"])
            first, surname = name.split(maxsplit=1)
        else:
            given = self.random.choice(bank["given_names"])
            if recipe == "given+classic":
                surname = self.random.choice(bank["classic_surnames"])
                name = f"{given} {surname}"
            elif recipe == "given+constructed":
                surname = self._constructed_surname(bank)
                name = f"{given} {surname}"
            elif recipe == "given+double":
                left = self._constructed_surname(bank)
                right = self.random.choice(bank["classic_surnames"])
                surname = f"{left}-{right}"
                name = f"{given} {surname}"
            elif recipe == "given+nickname+constructed":
                surname = self._constructed_surname(bank)
                name = f'{given} "{self.random.choice(bank["nicknames"])}" {surname}'
            else:
                viable = [root for root in bank["surname_roots"]
                          if any(g[0].casefold() == root[0].casefold() for g in bank["given_names"])]
                root = self.random.choice(viable)
                matching = [g for g in bank["given_names"] if g[0].casefold() == root[0].casefold()]
                given = self.random.choice(matching)
                surname = root + self.random.choice(bank["surname_suffixes"])
                name = f"{given} {surname}"
            first = given
        if (first, surname) in self.blocked_pairs:
            return GeneratedName(name, "cheeky", recipe, -100, first, surname)
        raw = GeneratedName(name, "cheeky", recipe, 0, first, surname)
        return GeneratedName(**{**raw.__dict__, "score": self._score(raw)})

    def _absurd_identity(self, bank):
        gender = self.random.choice(("masculine", "feminine"))
        given = self.random.choice(bank[f"{gender}_given_names"])
        titles = bank[f"{gender}_titles"] + bank["neutral_titles"]
        epithets = bank[f"{gender}_epithets"] + bank["neutral_epithets"]
        return gender, given, self.random.choice(titles), self.random.choice(epithets)

    def _absurd_candidate(self, recipe=None) -> GeneratedName:
        bank = self.data["absurd"]
        recipe = recipe or self._weighted_recipe(bank)
        if recipe == "curated":
            name = self.random.choice(bank["curated"])
            first = next((word for word in name.replace(",", "").split()
                          if word in bank["masculine_given_names"] + bank["feminine_given_names"]), "")
            surname = name.split(first, 1)[1].split(",", 1)[0].strip() if first else name
        else:
            _, first, title, epithet = self._absurd_identity(bank)
            classic = self.random.choice(bank["classic_surnames"])
            constructed = self._constructed_surname(bank)
            if recipe == "title+classic":
                surname, name = classic, f"{title} {first} {classic}"
            elif recipe == "title+constructed":
                surname, name = constructed, f"{title} {first} {constructed}"
            elif recipe == "bare+epithet":
                surname, name = classic, f"{first} {classic}, {epithet}"
            elif recipe == "title+territory":
                surname = constructed
                name = f"{title} {first} {constructed} of {self.random.choice(bank['territories'])}"
            elif recipe == "double+title":
                surname = f"{constructed}-{classic}"
                name = f"{title} {first} {surname}"
            else:
                surname = f"{constructed}-{classic}"
                name = f"{title} {first} {surname}, {epithet}"
        raw = GeneratedName(name, "absurd", recipe, 0, first, surname)
        return GeneratedName(**{**raw.__dict__, "score": self._score(raw)})

    def _phonetic_candidates(self):
        candidates = []
        for family in self.data["phonetic_generator"]["families"]:
            if len(family["surname"]) != len(family["reading"]):
                raise ValueError(f"Phonetic family {family['id']} has mismatched editorial pairs")
            for first in family["first"]:
                for surname, meaning in zip(family["surname"], family["reading"]):
                    name = f"{first} {surname}"
                    raw = GeneratedName(
                        name=name,
                        category="phonetic",
                        recipe="phonetic-generated",
                        first_component=first,
                        surname_component=surname,
                        meaning=meaning,
                        technique=family["technique"],
                        generated=True,
                        family=family["id"],
                    )
                    candidates.append(GeneratedName(
                        **{**raw.__dict__, "score": self._score(raw)}
                    ))
        return candidates

    def _plan(self, count, style):
        if style is not None:
            return [style] * count
        total = self.config.cheeky_weight + self.config.absurd_weight
        cheeky_count = round(count * self.config.cheeky_weight / total)
        plan = ["cheeky"] * cheeky_count + ["absurd"] * (count - cheeky_count)
        self.random.shuffle(plan)
        return plan

    def generate(self, count: int, style: str | None = None) -> list[GeneratedName]:
        if count < 0:
            raise ValueError("Count cannot be negative")
        if style not in (None, *STYLES):
            raise ValueError(f"Unknown style: {style}")
        self.last_diagnostics = diagnostics = GenerationDiagnostics(requested=count)
        if style == "phonetic":
            candidates_by_family = {}
            seen_meanings = set()
            for candidate in self._phonetic_candidates():
                diagnostics.proposed += 1
                reason = self.rejection_reason(candidate.name)
                if candidate.meaning.casefold() in seen_meanings:
                    reason = reason or "duplicate_joke_reading"
                if reason:
                    diagnostics.rejected[reason] += 1
                else:
                    seen_meanings.add(candidate.meaning.casefold())
                    candidates_by_family.setdefault(candidate.family, []).append(candidate)
            for candidates in candidates_by_family.values():
                self.random.shuffle(candidates)
            family_order = list(candidates_by_family)
            self.random.shuffle(family_order)
            chosen = []
            while family_order and len(chosen) < count:
                next_round = []
                for family in family_order:
                    candidates = candidates_by_family[family]
                    if candidates and len(chosen) < count:
                        chosen.append(candidates.pop())
                    if candidates:
                        next_round.append(family)
                self.random.shuffle(next_round)
                family_order = next_round
            if len(chosen) < count:
                diagnostics.exhausted = True
                raise ValueError(
                    f"Only {len(chosen)} editorially approved phonetic constructions are available"
                )
            for candidate in chosen:
                self._record_selected(diagnostics, candidate)
            return chosen

        plan = self._plan(count, style)
        results = []
        used = set()
        family_limit = max(2, math.ceil(count * .01))
        first_limit = max(4, math.ceil(count * .04))
        maximum_rounds = max(100, count * 10)
        rounds = 0
        while plan and rounds < maximum_rounds:
            rounds += 1
            category = plan[0]
            bank = self.data[category]
            recipe = self._weighted_recipe(bank)
            pool = []
            for _ in range(self.config.candidates_per_name):
                diagnostics.proposed += 1
                candidate = (self._cheeky_candidate(recipe) if category == "cheeky"
                             else self._absurd_candidate(recipe))
                fingerprint = normalized(candidate.name)
                reason = self.rejection_reason(candidate.name)
                if candidate.score < self.config.minimum_quality:
                    reason = reason or "low_quality"
                elif fingerprint in used:
                    reason = "exact_duplicate"
                elif diagnostics.surname_components[candidate.surname_component] >= family_limit:
                    reason = "surname_overuse"
                elif diagnostics.first_components[candidate.first_component] >= first_limit:
                    reason = "first_name_overuse"
                if reason:
                    diagnostics.rejected[reason] += 1
                    continue
                reuse_penalty = (
                    diagnostics.surname_components[candidate.surname_component] * 1.8
                    + diagnostics.first_components[candidate.first_component] * .35
                )
                pool.append((candidate.score - reuse_penalty + self.random.random() / 1000, candidate))
            if not pool:
                continue
            candidate = max(pool, key=lambda item: item[0])[1]
            results.append(candidate)
            used.add(normalized(candidate.name))
            self._record_selected(diagnostics, candidate)
            plan.pop(0)
        if plan:
            diagnostics.exhausted = True
            raise ValueError(f"Could not produce {count} unique acceptable {style or 'mixed'} names")
        return results

    @staticmethod
    def _record_selected(diagnostics, candidate):
        diagnostics.accepted += 1
        diagnostics.templates[candidate.recipe] += 1
        if candidate.first_component:
            diagnostics.first_components[candidate.first_component] += 1
        if candidate.surname_component:
            diagnostics.surname_components[candidate.surname_component] += 1
