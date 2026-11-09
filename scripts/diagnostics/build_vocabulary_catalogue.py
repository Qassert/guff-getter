"""Build the offline Phase 4C catalogue from reviewed and sourced resources."""
from __future__ import annotations
import csv, json, re
from pathlib import Path
from scripts.diagnostics.evaluate_vocabulary_expansion import (
    PROTOTYPE_ANIMALS, PROTOTYPE_NAME_COMPONENTS, catalogues,
)

ROOT = Path(__file__).parents[2]
RES = ROOT / "newsmuncher/resources"
OUT = RES / "vocabulary/comedy_vocabulary_catalogue.json"
OEWN = RES / "vocabulary/oewn_2025_phase4c.json"

SOURCES = {
    "newsmuncher-curated": {"name": "Existing NewsMuncher curated comedy resources",
        "url": None, "licence_id": "INTERNAL-UNVERIFIED",
        "attribution": "Existing repository material; ownership/licence review required before external redistribution."},
    "phase4a-editorial-seed": {"name": "NewsMuncher Phase 4A editorial seed",
        "url": None, "licence_id": "INTERNAL-UNVERIFIED",
        "attribution": "Locally authored prototype additions; formal editorial approval pending."},
    "legacy-local-filter": {"name": "Existing NewsMuncher legacy banks, conservatively filtered",
        "url": None, "licence_id": "INTERNAL-UNVERIFIED",
        "attribution": "Repository-local legacy material; machine checked, not editorially approved."},
    "oewn-2025": {"name": "Open English WordNet 2025 Edition",
        "url": "https://en-word.net/static/english-wordnet-2025-json.zip", "licence_id": "CC-BY-4.0",
        "attribution": "Open English WordNet Community, 2025 Edition; derived from Princeton WordNet."},
    "phase4c-original": {"name": "NewsMuncher Phase 4C original construction components",
        "url": None, "licence_id": "INTERNAL-UNVERIFIED",
        "attribution": "Locally constructed machine-checked ingredients; editorial approval pending."},
    "wordfreq-3.1.1": {"name": "wordfreq 3.1.1",
        "url": "https://github.com/rspeer/wordfreq", "licence_id": "Apache-2.0",
        "attribution": "Robyn Speer and wordfreq contributors; used only for familiarity ranking."},
}

def slug(value): return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
def normalized(value): return re.sub(r"[^a-z0-9]+", "", value.casefold())

UNSUITABLE = re.compile(
    r"(?:fuck|shit|piss|cock|dick|cunt|twat|arse|\bass\b|cum|jizz|pube|labia|vagina|"
    r"penis|boob|\btit|slut|whore|dildo|felch|wank|fart|butt|rape|anal|testicle|testes|"
    r"pedoph|homo|shemale|spastic|retard|nigger|chink|spic|kike|paddy|towel.?head|"
    r"diaper.?head|camel.?jockey|christ.?killer|surrender monkey|nazi|dominatrix|fetish|"
    r"blowjob|douche|bastard|bitch|junkie|sex|hoe|perv)", re.I)
GENERIC = {"adult","primary","royal","imperial","coat","scale","saddle","feeder","poll","subject",
           "feature","section","span","cover","room","upper","low","favor","park","hospital","form",
           "entry","term","case","point","set","addition","property","capital","basic","local","positive","two","extra",
           "black","white","good","back","overall","working","release","video","school","college","america"}

def csv_values(name):
    with (RES / "words" / name).open(encoding="utf-8", newline="") as source:
        return list(dict.fromkeys(value.strip() for row in csv.reader(source)
                                  for value in row if value.strip()))

def familiarity(frequency):
    return "common" if frequency >= 4 else "unusual" if frequency >= 2.3 else "obscure"

def animal_class(definition):
    groups=(("bird", "bird avian fowl"),("fish", "fish shark ray eel"),("insect", "insect beetle moth butterfly fly ant bee wasp"),
            ("arachnid", "spider scorpion tick mite arachnid"),("crustacean", "crab lobster shrimp crustacean"),
            ("mollusc", "mollusk mollusc snail slug octopus squid clam oyster"),("reptile", "reptile snake lizard turtle tortoise crocodile"),
            ("amphibian", "amphibian frog toad salamander newt"),("mammal", "mammal"),("invertebrate", "worm jellyfish sponge animal"))
    folded=definition.casefold()
    return next((name for name,words in groups if any(re.search(rf"\b{re.escape(word)}\b",folded) for word in words.split())),"other_animal")

def object_class(definition):
    folded=definition.casefold()
    groups=(("vehicle",("vehicle","car","boat","aircraft","wheeled")),("tool",("tool","implement","instrument used")),
            ("clothing",("garment","clothing","worn on")),("food",("food","dish","edible")),
            ("architecture",("building","structure","room")),("scientific_equipment",("laboratory","scientific instrument","measuring")),
            ("medical_equipment",("medical","surgical","hospital")),("musical_instrument",("musical instrument","music")),
            ("machinery",("machine","engine","apparatus")),("container",("container","receptacle")),
            ("furniture",("furniture","seat","table")),("historical_object",("formerly","ancient","medieval")))
    return next((name for name,terms in groups if any(term in folded for term in terms)),"physical_object")

def descriptor_class(definition):
    folded=definition.casefold()
    groups=(("emotion",("feeling","emotion","angry","fear")),("personality",("character","temperament","personality")),
            ("ability",("ability","skill","capable")),("social_status",("social","status","rank")),
            ("appearance",("appearance","colour","color","shape")),("behaviour",("behavior","behaviour","manner")),
            ("restriction",("forbidden","prohibited","restricted")),("circumstance",("condition","situation","state")),
            ("temporal",("time","period","frequency")),("degree",("degree","extent","intensity")))
    return next((name for name,terms in groups if any(term in folded for term in terms)),"general_description")

def entry(family, text, category, subtype, semantic, mechanisms, source,
          approval="machine_checked", flags=(), grammar=None, familiarity="common", extra=None):
    return {"id": f"{family}:{category}:{slug(text)}", "text": text, "family": family,
        "category": category, "subtype": subtype, "grammar": grammar or {},
        "semantic_class": semantic, "compatible_mechanisms": list(mechanisms),
        "humour": {"style": "british_absurdity", "comic_potential": 3},
        "familiarity": familiarity, "source_id": source,
        "licence_id": SOURCES[source]["licence_id"], "editorial_flags": list(flags),
        "approval_status": approval, **(extra or {})}

def build():
    concept = json.loads((RES/"concepts/comedy_concept_components.json").read_text())
    descriptor = json.loads((RES/"descriptors/comedy_descriptor_components.json").read_text())
    names = json.loads((RES/"names/comedy_name_components.json").read_text())
    oewn=json.loads(OEWN.read_text()) if OEWN.exists() else {"animals":[],"objects":[],"descriptor_adjectives":[],"descriptor_adverbs":[]}
    out=[]; seen=set()
    def add(item):
        key=(item["family"],normalized(item["text"]))
        if key not in seen: seen.add(key); out.append(item)
    creatures=concept["banks"]["creatures"]
    for value in creatures:
        add(entry("animals",value,"creature","common_name","animal",
                  ("ridiculous_occupation","secret_history","impossible_trait"),
                  "newsmuncher-curated","editorially_reviewed",grammar={"number":"singular","countability":"countable"}))
    for value in PROTOTYPE_ANIMALS:
        add(entry("animals",value,"creature","common_name","animal",
                  ("ridiculous_occupation","secret_history","impossible_trait"),
                  "phase4a-editorial-seed",flags=("needs_review",),
                  grammar={"number":"singular","countability":"countable"},familiarity="unusual"))
    for item in oewn["animals"]:
        if item["text"].casefold() in GENERIC or UNSUITABLE.search(item["text"]): continue
        note=f"OEWN definition: {item['definition']}" if item["zipf_frequency"] < 2.3 else None
        add(entry("animals",item["text"],"oewn_animal","common_name",animal_class(item["definition"]),
                  ("ridiculous_occupation","secret_history","impossible_trait"),"oewn-2025",
                  flags=("needs_review",), grammar={"number":"singular","countability":"countable"},
                  familiarity=familiarity(item["zipf_frequency"]),
                  extra={"upstream_id":item["synset_id"],"definition":item["definition"],
                         **({"recognisability_note":note} if note else {})}))
    object_banks=("domestic_objects","devices","cheeky_objects","equipment","ceremonial_objects","emergency_devices")
    for bank in object_banks:
        semantic={"devices":"machine","equipment":"technical_equipment","emergency_devices":"emergency_equipment",
                  "ceremonial_objects":"ceremonial_object"}.get(bank,"household_object")
        for value in concept["banks"][bank]:
            add(entry("objects",value,bank,"physical_object",semantic,
                      ("impossible_technology","institutional_control","ceremonial_status"),
                      "newsmuncher-curated","editorially_reviewed",grammar={"number":"singular","countability":"countable"}))
    for value in catalogues()["objects"][1]:
        add(entry("objects",value,"legacy_candidate","physical_object","unclassified_object",
                  ("institutional_control",),"legacy-local-filter",flags=("needs_review",),
                  grammar={"number":"singular","countability":"countable"},familiarity="unusual"))
    for item in oewn["objects"]:
        if item["text"].casefold() in GENERIC or UNSUITABLE.search(item["text"]): continue
        note=f"OEWN definition: {item['definition']}" if item["zipf_frequency"] < 2.3 else None
        semantic=object_class(item["definition"])
        add(entry("objects",item["text"],"oewn_artifact","physical_object",semantic,
                  ("impossible_technology","institutional_control","ceremonial_status"),"oewn-2025",
                  flags=("needs_review",),grammar={"number":"singular","countability":"countable"},
                  familiarity=familiarity(item["zipf_frequency"]),
                  extra={"upstream_id":item["synset_id"],"definition":item["definition"],
                         "affordance":semantic, **({"recognisability_note":note} if note else {})}))
    bank_roles={}
    for template in descriptor["templates"]:
        for slot,bank in template["slots"].items():
            bank_roles.setdefault(bank,set()).add(template["role"])
    for bank,values in descriptor["banks"].items():
        roles=sorted(bank_roles.get(bank,{"predicate"}))
        mechanisms=sorted({t["mechanism"] for t in descriptor["templates"] if bank in t["slots"].values()}) or ["comic_contradiction"]
        for value in values:
            add(entry("descriptors",value,bank,"descriptor_ingredient",bank,mechanisms,
                      "newsmuncher-curated","editorially_reviewed",grammar={"roles":roles}))
    for source_key,role in (("descriptor_adjectives","predicate"),("descriptor_adverbs","adverbial")):
        for item in oewn[source_key]:
            if (item["text"].casefold() in GENERIC or UNSUITABLE.search(item["text"])
                    or re.search(r"\b(?:first|second|third|fourth|fifth|year-old)\b|^[ivx]+$",item["text"])):
                continue
            add(entry("descriptors",item["text"],f"oewn_{role}","lexical_descriptor",
                      descriptor_class(item["definition"]),("comic_contradiction","social_display","petty_emotion"),
                      "oewn-2025",flags=("needs_review",),grammar={"roles":[role]},
                      familiarity=familiarity(item["zipf_frequency"]),
                      extra={"upstream_id":item["synset_id"],"definition":item["definition"]}))
    for section in ("cheeky","absurd"):
        for bank,values in names[section].items():
            if not isinstance(values,list): continue
            subtype=("given_name" if "given" in bank else "complete_name" if bank == "curated" else "title" if "title" in bank else
                     "epithet" if "epithet" in bank else "territory" if bank=="territories" else "surname_component")
            for value in values:
                if isinstance(value,str):
                    add(entry("names",value,section,subtype,bank,(section,),"newsmuncher-curated",
                              "editorially_reviewed",grammar={"role":subtype}))
    for value in PROTOTYPE_NAME_COMPONENTS:
        add(entry("names",value,"prototype","name_component","unclassified_name_component",
                  ("cheeky","absurd"),"phase4a-editorial-seed",flags=("needs_review",),grammar={"role":"unclassified"}))
    root_candidates=[item for item in oewn["objects"] if len(item["text"].split())==1
                     and 4 <= len(item["text"]) <= 10 and item["text"].casefold() not in GENERIC
                     and not UNSUITABLE.search(item["text"]) and item["zipf_frequency"] < 4.5][:450]
    for item in root_candidates:
        add(entry("names",item["text"].title(),"comic_root","surname_component","object_surname_root",
                  ("cheeky","absurd"),"phase4c-original",flags=("needs_review",),
                  grammar={"role":"surname_component"},familiarity=familiarity(item["zipf_frequency"]),
                  extra={"derived_from_oewn":item["synset_id"]}))
    safe_slang={"exclamation":["blimey","crikey","crumbs","good grief","stone the crows","cor blimey","flipping heck","well I never","what a palaver","bloomin' marvellous"],
                "insult":["berk","nincompoop","plonker","wally","numpty","pillock","prat","muppet","daft apeth","absolute turnip"],
                "idiom":["all mouth and no trousers","gone pear-shaped","lost the plot","not my cup of tea","a right carry-on","full of beans","over-egging the pudding","couldn't organise a raffle","as useful as a chocolate teapot","having a funny turn"]}
    for role,values in safe_slang.items():
        for value in values:
            add(entry("slang",value,role,"colloquial_expression",role,("social_display","petty_emotion"),
                      "phase4a-editorial-seed",flags=("needs_review",),grammar={"role":role},familiarity="common"))
    extra_slang={
      "exclamation":["by gum","great Scott","heavens above","goodness gracious","lord love a duck","my giddy aunt","well knock me down","what the Dickens","would you credit it","you could have knocked me over"],
      "insult":["airhead","anorak","blabbermouth","blockhead","buffoon","bungler","chancer","chump","clodhopper","daftbrush","dingbat","ditherer","duffer","fussbudget","gasbag","git","gobshite","goon","gormless wonder","great pudding","jobsworth","know-all","loudmouth","melt","nitwit","numbskull","oaf","odd bod","old windbag","prize turnip","rotter","scallywag","scatterbrain","silly sausage","slaphead","smart alec","sourpuss","twerp","village idiot","windbag"],
      "idiom":["a few sandwiches short","all fur coat","at sixes and sevens","away with the fairies","barking up the wrong tree","couldn't find their own hat","doesn't know whether to wind a watch","full of hot air","got their knickers in a twist","has bats in the belfry","hasn't got a leg to stand on","in a bit of a pickle","making a mountain out of a molehill","not the sharpest tool","off their trolley","one sandwich short of a picnic","put a sock in it","running around like a headless chicken","talking through their hat","the lights are on but nobody's home","up the wooden hill","would lose their head if it wasn't attached"],
      "intensifier":["a bit","a proper","absolutely","awfully","bloomin'","dead","fairly","flipping","frightfully","jolly","properly","rather","right","thoroughly","utterly"],
      "reaction":["chance would be a fine thing","don't get your knickers in a twist","give over","have a word with yourself","keep your hair on","not on your nelly","pull the other one","steady on","tell that to the marines","that's your lot","you must be joking"]}
    for role,values in extra_slang.items():
        for value in values:
            add(entry("slang",value,"phase4c_safe_sample","colloquial_expression",role,
                      ("social_display","petty_emotion"),"phase4c-original",flags=("needs_review",),
                      grammar={"role":role},familiarity="common",
                      extra={"register":"informal","meaning":role,"safety":"curated_safe_sample"}))
    stems="Bumble Crumble Dither Fumble Guddle Muddle Nettle Piddle Quibble Rattle Snod Tatter Waffle Wibble Wobble Yaffle Bramble Clatter Drizzle Fidget Hobble Jumble Kettle Puddle Scrumble Tootle".split()
    endings="wick ton ham ford bury thorpe combe worth shire bottom bridge dale field haven mere moor cross green under hill".split()
    features=["village","hamlet","road","lane","hill","marsh","institute","museum","registry","academy","observatory","roundabout","services"]
    for value in stems:
        add(entry("places",value,"stem","place_stem","fictional_morphology",("fictional_place",),
                  "phase4a-editorial-seed",flags=("needs_review",),grammar={"role":"stem"}))
    for value in endings:
        add(entry("places",value,"ending","place_suffix","fictional_morphology",("fictional_place",),
                  "phase4a-editorial-seed",flags=("needs_review",),grammar={"role":"suffix"}))
    for value in features:
        add(entry("places",value,"feature","geographical_feature","fictional_feature",("fictional_place",),
                  "phase4a-editorial-seed",flags=("needs_review",),grammar={"role":"feature"}))
    place_roots=[]
    for item in oewn["objects"] + oewn["animals"]:
        text=item["text"]
        if (len(text.split())==1 and 4<=len(text)<=11 and text.isalpha()
                and text.casefold() not in GENERIC and not UNSUITABLE.search(text)
                and item["zipf_frequency"] < 4.4):
            place_roots.append(text.title())
    for value in place_roots[:450]:
        add(entry("places",value,"lexical_stem","place_stem","fictional_morphology",("fictional_place",),
                  "phase4c-original",flags=("needs_review",),grammar={"role":"stem"},familiarity="unusual",
                  extra={"construction_only":True,"not_a_factual_location":True}))
    place_types=("arcade annex baths beacon boulevard borough bothy bypass canal chambers circus common conservatory court croft dock estate exchange folly gardens gate hall heath heights hollow house junction lodge market mews mill mound pavilion pier precinct quay retreat row square station terrace tower vault viaduct walk ward wharf works").split()
    institutions=("Bunting Authority|Civic Biscuit Office|Department of Queues|Institute of Apologies|Ministry of Damp|Municipal Hat Registry|Parish Goose Board|Royal Teapot Archive|Society for Unclaimed Trolleys|Office of Suspicious Shrubbery").split("|")
    for value in place_types:
        add(entry("places",value,"place_type","geographical_feature","fictional_feature",("fictional_place",),
                  "phase4c-original",flags=("needs_review",),grammar={"role":"feature"}))
    for value in institutions:
        add(entry("places",value,"institution","fictional_institution","fictional_institution",("fictional_place",),
                  "phase4c-original",flags=("needs_review",),grammar={"role":"institution"}))
    return {"schema_version":"1.0","catalogue_version":"phase4c-1","sources":SOURCES,"ingredients":out}

if __name__=="__main__":
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(build(),indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(f"wrote {len(build()['ingredients'])} ingredients to {OUT}")
