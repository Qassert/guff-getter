"""Offline Phase 4E slang and fictional-place construction for review."""
from dataclasses import dataclass
from functools import lru_cache
import json, random, re
from pathlib import Path

RESOURCE = Path(__file__).parents[1] / "resources/vocabulary/phase4e_expression_components.json"


@lru_cache(maxsize=1)
def _data():
    return json.loads(RESOURCE.read_text(encoding="utf-8"))


@dataclass(frozen=True)
class ComedyExpression:
    phrase: str
    family: str
    role: str
    mechanism: str
    template: str
    approval_status: str = "machine_checked"


class ComedyExpressionGenerator:
    def __init__(self, seed=None, version="phase4f"):
        if version not in {"phase4e", "phase4f"}:
            raise ValueError("expression version must be phase4e or phase4f")
        self.random = random.Random(seed); self.data = _data(); self.version = version

    def _slang(self):
        bank = self.data["slang"]
        templates = [
            ("mild_insult", "noun_phrase", "comic_identity", "you {insult_modifiers} {insult_nouns}"),
            ("disbelief", "exclamation", "mock_disbelief", "well, butter {exclamation_objects}"),
            ("useless_comparison", "predicate", "comic_comparison", "about as useful as {useless_objects}"),
            ("incompetence_idiom", "short_clause", "failed_organisation", "couldn't {failed_tasks} in {factories}"),
            ("mock_outrage", "noun_phrase", "mock_outrage", "{outrage}"),
        ]
        if self.version == "phase4f":
            bank = dict(bank)
            bank.update({
                "social_failures": ["the confidence of a wet gazebo", "the timing of a startled undertaker", "the charm of an overdue rates notice", "the discretion of a village tannoy", "the authority of a borrowed waistcoat", "the focus of a pigeon at a buffet", "the tact of a reversing brass band", "the urgency of a council fern"],
                "predicaments": ["a raffle in a thunderstorm", "a christening at a tyre depot", "an audit in a paddling pool", "a wake in a trampoline showroom", "a summit in a broom cupboard", "a wedding in a bus shelter", "a coup in a garden centre", "a séance in lost property"],
                "reactions": ["I have seen firmer leadership from blancmange", "that has put the gazebo among the magistrates", "someone has over-polished the emergency", "this is how cardigans become evidence", "well, call the vicar and hide the receipts", "that could sour the mood in an empty lift", "the wheels have come off the apology", "even the wallpaper looks embarrassed"],
                "euphemisms": ["a strategic trouser realignment", "an unscheduled dignity leak", "a full ceremonial wobble", "a confidential biscuit incident", "a temporary shortage of moral upholstery", "an aggressive misunderstanding with gravity", "a minor collapse of personal government", "an outbreak of competitive discretion"],
            })
            templates.extend([
                ("social_comparison", "predicate", "social_comparison", "equipped with {social_failures}"),
                ("predicament", "short_clause", "situational_absurdity", "like {predicaments}"),
                ("sarcastic_observation", "short_clause", "sarcastic_observation", "{reactions}"),
                ("comic_euphemism", "noun_phrase", "comic_euphemism", "{euphemisms}"),
                ("compound_putdown", "noun_phrase", "comic_identity", "you {insult_modifiers} {insult_nouns} with {social_failures}"),
                ("outraged_address", "exclamation", "mock_disbelief", "what in the {insult_modifiers} {insult_nouns}"),
                ("incompetence_portrait", "short_clause", "failed_organisation", "couldn't {failed_tasks} with {social_failures}"),
                ("double_comparison", "predicate", "comic_comparison", "as {useless_objects} with {social_failures}"),
            ])
        if self.version == "phase4f":
            weights=[]
            for _, _, _, pattern in templates:
                slots=re.findall(r"{(\w+)}", pattern)
                capacity=1
                for slot in slots: capacity *= len(bank[slot])
                weights.append(min(12, max(1, capacity ** .5)))
            ident, role, mechanism, pattern = self.random.choices(templates, weights, k=1)[0]
        else:
            ident, role, mechanism, pattern = self.random.choice(templates)
        slots = re.findall(r"{(\w+)}", pattern)
        return ComedyExpression(pattern.format(**{slot:self.random.choice(bank[slot]) for slot in slots}),
                                "slang", role, mechanism, ident)

    def _place(self):
        bank = self.data["places"]
        templates = [
            ("village", "settlement", "believable_morphology", "{prefixes} {stems}{settlement_suffixes}"),
            ("bare_village", "settlement", "believable_morphology", "{stems}{settlement_suffixes}"),
            ("road", "road", "civic_absurdity", "{roads}"),
            ("institution", "public_institution", "institutional_absurdity", "{institutions}"),
            ("venue", "business_or_venue", "social_absurdity", "{venues}"),
            ("feature", "geographical_feature", "landscape_absurdity", "{features}"),
            ("estate", "housing_estate", "municipal_absurdity", "{stems} View Estate"),
        ]
        if self.version == "phase4f":
            bank = dict(bank)
            bank.update({
                "business_adjectives": ["Reluctant", "Bent", "Provisional", "Whispering", "Unclaimed", "Crooked", "Deputy", "Apologetic", "Mildly Alarmed", "Overdressed", "Last-Minute", "Questionable"],
                "business_nouns": ["Ferret", "Teaspoon", "Waistcoat", "Turnip", "Gazebo", "Peacock", "Clipboard", "Kettle", "Pigeon", "Wheelbarrow", "Cardigan"],
                "business_types": ["Hotel", "Tea Rooms", "Emporium", "Removal Service", "Solicitors", "Motors", "Garden Centre", "Funeral Buffet"],
                "landmark_nouns": ["Monument", "Footbridge", "Clock Tower", "Roundabout", "Bandstand", "Underpass", "Viewing Platform", "Memorial Bench"],
                "landmark_causes": ["Premature Optimism", "the Great Receipt Shortage", "Municipal Regret", "Unsupervised Bunting", "the Lost Tuesday", "the Indoor Storm", "the Apology Rebellion", "the Pudding Settlement"],
                "industrial_uses": ["Advanced Loitering", "Emergency Chutney", "Indoor Weather", "Ceremonial Packaging", "Applied Gossip", "Competitive Filing", "Provisional Gravy", "Quiet Alarm"],
                "road_heads": ["Last Apology", "Bent Spoon", "Doubtful Victory", "Three Pigeons", "Indoor Rain", "Unclaimed Hat", "Deputy Mayor"],
                "road_types": ["Lane", "Close", "Parade", "Crescent", "Mews", "Approach", "Rise", "Passage"],
            })
            templates.extend([
                ("business", "business_or_venue", "commercial_absurdity", "The {business_adjectives} {business_nouns} {business_types}"),
                ("landmark", "landmark", "commemorative_absurdity", "{landmark_nouns} of {landmark_causes}"),
                ("industrial_park", "industrial_park", "industrial_absurdity", "{industrial_uses} Industrial Park"),
                ("composed_road", "road", "civic_absurdity", "{road_heads} {road_types}"),
                ("district", "district", "believable_morphology", "{prefixes} {stems} District"),
            ])
        if self.version == "phase4f":
            weights=[]
            for _, _, _, pattern in templates:
                slots=re.findall(r"{(\w+)}", pattern)
                capacity=1
                for slot in slots: capacity *= len(bank[slot])
                weights.append(min(15, max(1, capacity ** .5)))
            ident, role, mechanism, pattern = self.random.choices(templates, weights, k=1)[0]
        else:
            ident, role, mechanism, pattern = self.random.choice(templates)
        slots = re.findall(r"{(\w+)}", pattern)
        phrase = pattern.format(**{slot:self.random.choice(bank[slot]) for slot in slots})
        return ComedyExpression(phrase, "places", role, mechanism, ident)

    def generate(self, family, count):
        if family not in {"slang", "places"}: raise ValueError("Unknown expression family")
        results, seen = [], set(); attempts = 0
        while len(results) < count and attempts < count * 100:
            attempts += 1; item = self._slang() if family == "slang" else self._place()
            key = item.phrase.casefold()
            if key in seen or len(item.phrase.split()) > 14: continue
            seen.add(key); results.append(item)
        if len(results) != count: raise ValueError(f"{family} expansion exhausted at {len(results)}")
        return results
