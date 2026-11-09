"""Build the original, machine-checked Phase 4E expansion resources."""
import json
from pathlib import Path

ROOT = Path(__file__).parents[2] / "newsmuncher/resources"

DESCRIPTOR_BANKS = {
    "odd_habit": ["alphabetising other people's lunches", "apologising to automatic doors", "saluting unattended luggage", "interviewing houseplants", "collecting suspicious receipts", "rehearsing arguments with kettles", "rating strangers' umbrellas", "writing memoirs for garden tools", "auditing the office biscuits", "giving weather forecasts to pigeons", "measuring applause with a ruler", "sending thank-you notes to parking meters"],
    "romantic_problem": ["engaged to a disputed scarecrow", "in a love triangle with two parish notices", "secretly courting a rival's gazebo", "emotionally entangled with a vending machine", "on speaking terms with an imaginary fiancé", "divorced from a ceremonial wheelbarrow", "betrothed to the wrong identical beekeeper", "sharing custody of a haunted fondue set", "wooing a traffic warden by semaphore", "romantically pursued by the village tannoy"],
    "condition": ["allergic to reasonable expectations", "suffering from intermittent pageantry", "prone to ceremonial swelling", "medically unable to whisper convincingly", "chronically overqualified for silence", "experiencing acute hat awareness", "liable to develop temporary heraldry", "diagnosed with competitive nostalgia", "recovering from administrative dizziness", "afflicted by spontaneous committee voice"],
    "qualification": ["licensed in advanced curtain diplomacy", "certified in emergency small talk", "doctorally qualified in suspicious puddles", "accredited for indoor weather", "board-certified in decorative panic", "trained in forensic sandwich reconstruction", "qualified to inspect imaginary livestock", "licensed for ceremonial reversing", "diploma-holding in applied awkwardness", "fellowship-trained in municipal romance"],
    "work_failure": ["once lost an entire department behind a filing cabinet", "has been demoted by three photocopiers", "mistakes every fire drill for a promotion", "cannot operate a stapler without witnesses", "has missed fourteen deadlines in chronological order", "accidentally outsourced their own lunch break", "keeps submitting expenses to the weather", "was dismissed for excessive competence claims", "runs meetings entirely by nervous coughing", "has never located the office they manage"],
    "fear": ["terrified of confidently folded maps", "frightened by authoritative knitwear", "unable to face a strongly worded teapot", "haunted by the possibility of adequate parking", "alarmed by fruit with paperwork", "fearful of unlicensed bunting", "panicked by unexpectedly formal ducks", "suspicious of chairs facing north", "dreading the return of competitive mime", "afraid of being recognised by a turnip"],
    "ambition": ["to become regional champion of indoor thunder", "to inherit a moderately important roundabout", "to open Britain's first apology museum", "to be crowned custodian of the emergency spoon", "to achieve diplomatic status for their shed", "to make competitive sighing an Olympic event", "to replace all paperwork with interpretive dance", "to become mayor of a moving vehicle", "to patent the authoritative cardigan", "to discover a legally binding pudding"],
    "scandal": ["whose controversial past involves a rented peacock", "still answering questions about the mayoral hot tub", "implicated in the great gazebo substitution", "named in the confidential marrow report", "formerly banned from three model villages", "linked to an offshore jumble sale", "wanted for questioning over counterfeit applause", "whose allotment years remain heavily redacted", "under inquiry for impersonating a minor tradition", "associated with an unlicensed victory parade"],
    "hobby": ["breeds competitive dust", "restores emotionally damaged bollards", "performs close-up magic for livestock", "collects first editions of instruction leaflets", "races antique office chairs", "paints miniature portraits of large car parks", "teaches etiquette to feral wheelie bins", "practises synchronised complaining", "constructs scale models of awkward silences", "trains moths for amateur dramatics"],
    "rivalry": ["is locked in a feud with the deputy lollipop person", "refuses to acknowledge the reigning pie marshal", "has challenged the village hypnotist to a recount", "is boycotting a neighbour's superior gravel", "maintains a vendetta against the county mime", "has not forgiven the library's new fern", "is competing with a toddler for civic office", "considers the postbox a professional rival", "is suing a cousin over inherited charisma", "has declared cold war on the leisure centre"],
    "restriction": ["legally barred from unsupervised confidence", "forbidden to enter a raffle under their own eyebrows", "restricted to one dramatic entrance per parish", "prohibited from handling ceremonial gravy", "required to surrender all motivational trumpets", "banned from voting in competitive picnics", "licensed only for provisional outrage", "under injunction not to reorganise the horizon", "forbidden to address furniture after dusk", "limited to recreational statesmanship"],
    "achievement": ["award-winning emergency apologiser", "three-time county champion of avoidable confusion", "record-holding indoor mountaineer", "decorated veteran of the stationery crisis", "internationally ranked competitive loiterer", "Britain's youngest retired village elder", "undefeated regional whispering finalist", "medal-winning amateur bureaucrat", "former world record holder for delayed entrances", "prize-winning interpreter of vague notices"],
    "habit_context": ["whenever applause starts", "during formal introductions", "after the second cup of tea", "when left near stationery", "on unofficial Tuesdays", "at family occasions", "under light supervision", "during minor emergencies", "when authority figures blink", "before anyone can object"],
    "romantic_authority": ["according to the parish newsletter", "under disputed gazebo law", "by order of the village florist", "according to three reliable aunties", "under an unsigned engagement notice", "by decree of the leisure centre", "according to the shared allotment diary", "under provisional courtship rules", "by mutual misunderstanding", "according to local semaphore"],
    "condition_context": ["during applause", "after moderate cheese", "near official stationery", "on damp Thursdays", "under fluorescent lighting", "during budget discussions", "when addressed formally", "after hearing a whistle", "near ceremonial fabric", "during unexpected competence"],
    "qualification_minor": ["applied bunting", "indoor weather", "forensic chutney", "ceremonial reversing", "comparative puddles", "administrative mime", "gazebo ethics", "advanced small talk", "municipal romance", "emergency upholstery"],
    "failure_blame": ["the office fern", "a misleading biscuit", "seasonal gravity", "the deputy stapler", "continental drift", "an unauthorised cardigan", "the concept of Tuesday", "a nervous photocopier", "the building's aura", "poorly briefed weather"],
    "fear_origin": ["the incident at the fête", "a difficult harvest festival", "the disputed raffle", "an unfortunate parish meeting", "the indoor regatta", "a childhood encounter with bunting", "the ceremonial spoon inquiry", "the winter of three gazebos", "a tense village picnic", "the great cardigan recall"],
    "ambition_deadline": ["before the next bank holiday", "by close of play", "before the parish notices", "within one financial year", "before the weather changes its mind", "by the annual apology", "before anyone checks the paperwork", "during their natural lifetime", "before the gazebo hearing", "by teatime on Thursday"],
    "scandal_alibi": ["a watertight pudding alibi", "several character references from ducks", "the support of the indoor bowls team", "a receipt from the wrong decade", "a strongly worded denial from a kettle", "an affidavit signed by a turnip", "the complete absence of trousers", "a provisional royal pardon", "two witnesses and a garden hose", "the mayor's selective amnesia"],
    "hobby_motive": ["to impress the post office", "for tax purposes", "in pursuit of minor glory", "to annoy a former headmaster", "under a false sense of duty", "for the parish record books", "to settle an old wager", "in preparation for public office", "for reasons of indoor security", "to win back a disputed hamper"],
    "rivalry_topic": ["a disputed parking cone", "the pronunciation of scone", "custody of the parish whistle", "an inherited folding chair", "regional gazebo precedence", "a missing ceremonial receipt", "the correct height of bunting", "ownership of Tuesday", "an insulting marrow", "the last respectable cardigan"],
    "restriction_hearing": ["a tribunal of concerned aunties", "the annual gazebo hearing", "a review by the pudding inspector", "a parish risk assessment", "the outcome of the bunting inquiry", "an appeal to the deputy mayor", "a hearing before three ferrets", "the leisure centre's final decision", "a formal sandwich inspection", "the return of sensible weather"],
    "achievement_aid": ["using their hands", "adequate rehearsal", "a valid permit", "once consulting a map", "disturbing the neighbours", "professional assistance", "removing their ceremonial hat", "understanding the rules", "visible emotional support", "leaving the refreshments"],
}

DESCRIPTOR_TEMPLATES = [
    ("peculiar_habit", "behavioural", "peculiar_habit", "{odd_habit} {habit_context}", "odd_habit", "habit_context"),
    ("romantic_complication", "post_noun", "romantic_complication", "{romantic_problem} {romantic_authority}", "romantic_problem", "romantic_authority"),
    ("questionable_condition", "predicate", "questionable_condition", "{condition} {condition_context}", "condition", "condition_context"),
    ("bizarre_qualification", "pre_noun", "bizarre_qualification", "{qualification} with a minor in {qualification_minor}", "qualification", "qualification_minor"),
    ("workplace_incompetence", "short_clause", "workplace_incompetence", "{work_failure} and blamed {failure_blame}", "work_failure", "failure_blame"),
    ("irrational_fear", "predicate", "irrational_fear", "{fear} since {fear_origin}", "fear", "fear_origin"),
    ("peculiar_ambition", "adverbial", "peculiar_ambition", "{ambition} {ambition_deadline}", "ambition", "ambition_deadline"),
    ("personal_scandal", "post_noun", "personal_scandal", "{scandal} despite {scandal_alibi}", "scandal", "scandal_alibi"),
    ("unusual_hobby", "behavioural", "unusual_hobby", "{hobby} {hobby_motive}", "hobby", "hobby_motive"),
    ("social_rivalry", "short_clause", "social_rivalry", "{rivalry} over {rivalry_topic}", "rivalry", "rivalry_topic"),
    ("new_legal_restriction", "predicate", "personal_legal_restriction", "{restriction} pending {restriction_hearing}", "restriction", "restriction_hearing"),
    ("unlikely_achievement", "pre_noun", "unlikely_achievement", "{achievement} without {achievement_aid}", "achievement", "achievement_aid"),
]

NAME_EXPANSION = {
    "version": "phase4e-names-1", "approval_status": "machine_checked",
    "cheeky": {
        "given_names": ["Aubrey", "Basil", "Cecil", "Clive", "Derek", "Ernest", "Gordon", "Howard", "Keith", "Lionel", "Mervyn", "Neville", "Percy", "Rupert", "Stanley", "Tristram", "Wilfred", "Agatha", "Beryl", "Cynthia", "Daphne", "Enid", "Felicity", "Gillian", "Harriet", "Iris", "Joyce", "Mavis", "Noreen", "Pamela", "Sybil", "Verity"],
        "classic_surnames": ["Puddleford", "Nudgecombe", "Crimpworthy", "Titteridge", "Fumbleton", "Prongley", "Snicketts", "Dimpleby", "Quiverance", "Muddlewick", "Bumplethorpe", "Winkworth", "Puckeridge", "Jigglemere", "Tweakham", "Fondlebury", "Smutcombe", "Rumpstead", "Gristlewick", "Ticklehurst"],
        "surname_roots": ["Nudge", "Pucker", "Quiver", "Crimp", "Fumble", "Prong", "Titter", "Dimple", "Jiggle", "Rump", "Wink", "Tweak", "Smut", "Gristle", "Bumple", "Fondle", "Throb", "Coddle", "Frisk", "Plump"],
        "surname_suffixes": ["combe", "hurst", "mere", "wick", "ridge", "ford", "stead", "bury", "worth", "thorpe", "ley", "ham", "ance", "ett", "ington"],
        "nicknames": ["The Nudge", "Two Spoons", "Velvet Elbows", "Quick Fingers", "The Trouser Whisperer", "Madam Wobble", "Soft Focus", "The Parish Prong"],
    },
    "absurd": {
        "masculine_given_names": ["Aloysius", "Bartholomew", "Cuthbert", "Eustace", "Ferdinand", "Godfrey", "Horatio", "Ignatius", "Montague", "Peregrine", "Septimus", "Theobald"],
        "feminine_given_names": ["Araminta", "Clementine", "Dorothea", "Euphemia", "Gwendolen", "Honoria", "Lavinia", "Octavia", "Petronella", "Thomasina", "Wilhelmina", "Zenobia"],
        "classic_surnames": ["Featheringstone", "Pompington", "Quibblehurst", "Thistlecrank", "Marmaduke-Smythe", "Blenkinsop", "Crumplehorn", "Dunderwick", "Flapdoodle", "Ganderleigh", "Huffington-Splott", "Mumblechook"],
        "surname_roots": ["Feather", "Quibble", "Thistle", "Crumple", "Dunder", "Gander", "Mumble", "Pomp", "Fluster", "Blenkin", "Hobble", "Splutter"],
        "surname_suffixes": ["stone", "hurst", "crank", "wick", "leigh", "chook", "bottom", "minster", "dingle", "castle", "snook", "barrow"],
        "neutral_titles": ["Deputy Marquess", "Acting Viscount", "Hereditary Comptroller", "Provisional Chancellor", "Lord-Lieutenant Emeritus"],
        "neutral_epithets": ["Keeper of the Unclaimed Spoon", "Defender of the Lesser Gazebo", "Warden of the Indoor Weather", "Bearer of the Ceremonial Receipt", "Patron of Unnecessary Trumpets"],
        "territories": ["Lower Pompington", "Much Apology", "Little Misunderstanding", "Upper Fluster", "Nether Turnip", "Greater Indoors", "Westward Puddle"],
    },
}

EXPRESSION_RESOURCE = {
    "version": "phase4e-expressions-1", "approval_status": "machine_checked",
    "slang": {
        "insult_modifiers": ["absolute", "championship-grade", "parish-certified", "industrially confused", "emotionally laminated", "aggressively decorative", "budget", "deluxe", "free-range", "municipal", "three-piece", "provisional"],
        "insult_nouns": ["waffle merchant", "pudding burglar", "gravy amateur", "sock magistrate", "turnip consultant", "shed philosopher", "carpet admiral", "marmalade witness", "cardigan bandit", "teapot extremist", "gazebo botherer", "clipboard peacock"],
        "exclamation_objects": ["unlicensed crumpets", "the mayor's emergency vest", "a bucket of parliamentary custard", "the sacred wheelie bin", "three startled cardigans", "the deputy's ornamental knees"],
        "useless_objects": ["a chocolate handbrake", "a paper submarine", "a knitted fire escape", "an inflatable anchor", "a solar-powered umbrella", "a marzipan crowbar", "a waterproof teabag", "a silent brass band"],
        "factories": ["a gossip factory", "a panic warehouse", "a scandal refinery", "an excuse foundry", "a rumour mill with planning permission", "a ceremonial complaint office"],
        "failed_tasks": ["organise a scandal", "locate a doorway", "supervise a sandwich", "start a rumour", "fold a complaint", "misplace a deadline", "brief a pigeon", "cancel a panic", "invoice a gazebo", "recognise a Tuesday"],
        "outrage": ["a complete trouser emergency", "an outrage against respectable puddings", "the collapse of indoor civilisation", "a scandal in a cardigan", "an administrative slap in the chutney", "a national shortage of decent eyebrows"],
    },
    "places": {
        "prefixes": ["Little", "Much", "Upper", "Lower", "Nether", "Great", "West", "North", "Bishop's", "Lady", "Saint", "Royal"],
        "stems": ["Wobble", "Puddle", "Crumpet", "Nettle", "Muddle", "Snoring", "Quibble", "Turnip", "Fluster", "Titter", "Bramble", "Gander", "Soggy", "Dither", "Marmalade"],
        "settlement_suffixes": ["wick", "bury", "combe", "ford", "minster", "leigh", "thorpe", "ham", "stead", "mere"],
        "roads": ["Apology Lane", "Suspicious Avenue", "Cardigan Crescent", "Unfinished Business Road", "Deputy Parade", "Mild Concern Close"],
        "institutions": ["Institute of Indoor Weather", "Department of Minor Panic", "National Centre for Competitive Loitering", "Office of Ceremonial Receipts", "Academy of Applied Awkwardness", "Bureau of Unclaimed Spoons"],
        "venues": ["The Reluctant Turnip", "The Three Cardigans", "The Municipal Ferret", "The Apologetic Peacock", "The Bent Clipboard", "The Deputy Crumpet"],
        "features": ["Mount Mild Concern", "the River Apology", "Pudding Tor", "Whispering Kettle Hill", "the Lesser Gravy Falls", "Unlicensed Bunting Marsh"],
    },
}


def write():
    descriptor = {"version": "phase4e-descriptors-1", "approval_status": "machine_checked",
                  "banks": DESCRIPTOR_BANKS, "templates": []}
    categories = ["cheeky_british", "broader_absurdity"] * 6
    for category, (ident, role, mechanism, pattern, bank, secondary) in zip(categories, DESCRIPTOR_TEMPLATES):
        descriptor["templates"].append({"id": ident, "category": category, "role": role,
            "mechanism": mechanism, "pattern": pattern, "slots": {bank: bank, secondary: secondary},
            "subject_slot": bank, "weight": 1})
    outputs = {
        ROOT / "descriptors/phase4e_descriptor_expansion.json": descriptor,
        ROOT / "names/phase4e_name_expansion.json": NAME_EXPANSION,
        ROOT / "vocabulary/phase4e_expression_components.json": EXPRESSION_RESOURCE,
    }
    for path, payload in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    write()
