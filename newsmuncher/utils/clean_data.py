from newsmuncher.services.word_shuffle import BANK_FILES, read_bank, shared_bags
from newsmuncher.utils.source_preprocessing import preserve_source_text, preprocess_source, replacement_guidance, filter_word_banks
from newsmuncher.config import ENV_FILE, WORDS_DIR, comedy_editor_model
from newsmuncher.services.noun_exclusion import blocked_entries, NounExclusionExhausted
import os, re, random, json
from time import monotonic
from openai import OpenAI  # type: ignore
from dotenv import load_dotenv  # type: ignore


WORDS_FOLDER = WORDS_DIR


# Load API key from .env
load_dotenv(ENV_FILE)

# Shared strict output contract for both generation stages.
JSON_FORMAT = {
    "type": "json_schema",
    "name": "rewritten_article",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "extract": {"type": "string"},
            "title": {"type": "string"},
        },
        "required": ["title", "extract"],
        "additionalProperties": False,
    },
}

# CSV file definitions
CSV_FILES = {
    "slang": "slang.csv",
    "nouns": "nouns.csv",
    "adverbs": "adverbs.csv",
    "animals": "animalsAndObjects.csv",
    "names": "names.csv",
    "places": "places.csv"
}


class RewriteProviderQuotaExhausted(RuntimeError):
    """The rewrite provider rejected the request because account credit is exhausted."""


def _is_credit_exhaustion(exc):
    body = getattr(exc, "body", None)
    error = body.get("error", body) if isinstance(body, dict) else {}
    code = error.get("code") if isinstance(error, dict) else None
    error_type = error.get("type") if isinstance(error, dict) else None
    return getattr(exc, "status_code", None) == 429 and (
        code in {"credit_balance_exhausted", "insufficient_quota"}
        or error_type == "insufficient_quota"
    )


def clean_data(data):
    """Recursively cleans and formats data by removing Unicode escapes, normalizing content, and formatting text."""
    if isinstance(data, str):
        # Decode Unicode properly without corrupting characters
        try:
            data = data.encode("utf-8").decode("unicode_escape")
        except UnicodeDecodeError:
            pass  # If decoding fails, keep the original text

        # Remove Unicode numeric escapes and replace them with actual characters
        data = re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), data)
        data = re.sub(r"\\U([0-9a-fA-F]{8})", lambda m: chr(int(m.group(1), 16)), data)

        # Replace problematic characters
        data = data.replace('"', "'").replace("\\", "").replace("_", " ")

        # Normalize spaces and remove extra whitespace
        data = re.sub(r"[\n\r\t]+", " ", data)  # Replace line breaks and tabs with spaces
        data = re.sub(r"\s{2,}", " ", data)  # Replace multiple spaces with a single space

        # Convert text to lowercase
        data = data.lower()

        # Capitalize the first letter of the string and after a full stop
        data = re.sub(r"(^|(?<=\.\s))([a-z])", lambda match: match.group(0).upper(), data)

        return data.strip()
    elif isinstance(data, dict):
        # Clean dictionary values recursively
        return {key: clean_data(value) for key, value in data.items()}
    elif isinstance(data, list):
        # Clean list elements recursively
        return [clean_data(item) for item in data]
    return data  # Return the data unchanged if not a string, dict, or list


# --------------

def sanitize_text(text):
    """Clean and normalize text by replacing special characters and normalizing spaces."""
    # Combine replacements from both functions
    replacements = {
        '\u00a0': ' ', '\\u00a0': ' ',  # Non-breaking space
        '\u2013': '-', '\\u2013': '-',  # En dash
        '\u2014': '-', '\\u2014': '-',  # Em dash
        '\u2018': "'", '\\u2018': "'",  # Left single quotation mark
        '\u2019': "'", '\\u2019': "'",  # Right single quotation mark
        '\u201c': '"', '\\u201c': '"',  # Left double quotation mark
        '\u201d': '"', '\\u201d': '"',  # Right double quotation mark
        '\n': ' ', '\\n': ' ',  # Newline
        '\r': '', '\\r': ''  # Carriage return
    }

    # Apply replacements
    for esc, repl in replacements.items():
        text = text.replace(esc, repl)

    # Normalize spaces (replace multiple spaces with a single space)
    text = re.sub(r"\s{2,}", " ", text)

    return text.strip()


# --------------

def extract_unique_words(file_path, num_words):
    """
    Extract unique words from a file, ensuring no duplicates.

    Args:
        file_path (str): Path to the file containing words.
        num_words (int): Number of unique words to extract.

    Returns:
        list: A list of unique words.
    """
    try:
        # Read the file content
        with open(file_path, 'r') as file:
            content = file.read()

        # Split content by commas, remove duplicates, and clean up whitespace
        words = list(set(content.split(',')))
        words = [word.strip() for word in words if word.strip()]

        # Ensure there are enough unique words
        if len(words) < num_words:
            print(f"Warning: Not enough unique words in {file_path}. Returning all available words.")
            return words  # Return all available words if not enough

        # Randomly select the specified number of unique words
        selected_words = random.sample(words, num_words)
        return selected_words

    except FileNotFoundError:
        print(f"File not found: {file_path}")
        return []
    except ValueError as e:
        print(f"Error processing {file_path}: {e}")
        return []


# --------------

# Function to load all random words into a dictionary
def load_random_words(NumberOfWords, excluded=()):
    """Load unclaimed prompt candidates without permanently consuming them."""
    random_words = {}
    for category, filename in CSV_FILES.items():
        if category in excluded:
            random_words[category] = []
            continue
        file_path = os.path.join(WORDS_FOLDER, filename)
        random_words[category] = (shared_bags().draw(category, read_bank(file_path), NumberOfWords)
                                  if category in BANK_FILES else
                                  extract_unique_words(file_path, NumberOfWords))
    print(f"[DEBUG] Looking for word files in: {WORDS_FOLDER}")
    for category, filename in CSV_FILES.items():
        file_path = os.path.join(WORDS_FOLDER, filename)
        print(f"[DEBUG] Checking: {file_path} → Exists: {os.path.exists(file_path)}")

    return random_words


def claim_used_words(contenders, result):
    """Claim only supplied bank words present in the accepted final rewrite."""
    return shared_bags().claim_used(
        contenders,
        result['crazyReplacement1Title'],
        result['crazyReplacement1Extract'],
    )




# --------------

def split_list(lst, num_parts=3):
    """Splits a list into roughly equal unique parts, ensuring no repeats."""
    random.shuffle(lst)
    if num_parts <= 0:
        raise ValueError("num_parts must be positive")
    return [lst[i::num_parts] for i in range(num_parts)]


# --------------

def prepare_prompt(entry, NumberOfWords, prompt_template, names_override=None, name_guidance="",
                   concept_overrides=None, concept_guidance="", descriptor_overrides=None,
                   descriptor_guidance="", final_joke_guidance="", topic_guidance="",
                   diagnostics=None, word_banks_override=None, theme_sparks=None,
                   noun_exclusions=()):
    """
    Prepares the prompt by cleaning the input data, loading random words, and formatting the prompt template.

    Args:
        entry (dict): The input data containing title, description, and extract.
        NumberOfWords (int): Number of words to load for each category.
        prompt_template (str): The template for the prompt.

    Returns:
        dict: A dictionary containing the formatted prompt and the cleaned title and extract.
              Returns None if there's an error.
    """
    # Clean the input data
    diagnostics = diagnostics if diagnostics is not None else {}
    stage = monotonic()
    original_entry = preserve_source_text(entry)
    preprocessing = preprocess_source(original_entry)
    cleaned_entry = preprocessing["masked"]
    title_to_change = cleaned_entry.get("title", "No title provided").strip() + ' - ' + cleaned_entry.get("description",
                                                                                                      "No description provided").strip()
    extract_to_change = cleaned_entry.get("extract", "No extract provided").strip()

    # Get fresh, unique words for this prompt
    diagnostics["source_preprocessing_ms"] = round((monotonic() - stage) * 1000, 2)
    stage = monotonic()
    excluded = set()
    if concept_overrides:
        excluded.update({"nouns", "animals"})
    if descriptor_overrides is not None:
        excluded.add("adverbs")
    requested_words = max(NumberOfWords * 4, 40) if noun_exclusions else NumberOfWords
    random_words = (load_random_words(requested_words, excluded=excluded)
                    if word_banks_override is None else
                    {key: list(values) for key, values in word_banks_override.items()})
    # Avoid offering a detected original expression back as a bank ingredient.
    random_words = filter_word_banks(preprocessing, random_words)
    if noun_exclusions:
        source_text = "\n".join(str(original_entry.get(key, ""))
                                for key in ("title", "description", "extract"))
        rejected = 0
        for bank in ("nouns", "animals"):
            values = random_words.get(bank, [])
            eligible = [value for value in values
                        if not blocked_entries(value, noun_exclusions, source_text)]
            rejected += len(values) - len(eligible)
            if bank not in excluded and len(eligible) < NumberOfWords:
                raise NounExclusionExhausted(
                    f"Not enough eligible legacy {bank} ingredients. Please try MUNGE IT again.")
            random_words[bank] = eligible[:NumberOfWords]
        for bank in set(random_words) - {"nouns", "animals"}:
            random_words[bank] = random_words[bank][:NumberOfWords]
        diagnostics["noun_exclusion_legacy_rejected"] = rejected
    diagnostics["other_csv_selection_ms"] = round((monotonic() - stage) * 1000, 2)
    stage = monotonic()
    if names_override is not None:
        # Invented slates are server-created identities rather than source-derived
        # word-bank values, and must remain exactly ten after source filtering.
        random_words["names"] = list(names_override)
    contenders = {key: list(values) for key, values in random_words.items()}
    if concept_overrides:
        for bank in ("nouns", "animals"):
            concepts = list(concept_overrides.get(bank, []))
            if not concepts:
                raise ValueError(f"Concept override for {bank} cannot be empty")
            random_words[bank] = concepts
            contenders[bank] = []
    if descriptor_overrides is not None:
        descriptors = list(descriptor_overrides)
        spark_descriptor_count = sum(
            item.get("kind") == "descriptor" for item in (theme_sparks or ()))
        if len(descriptors) + spark_descriptor_count != 10:
            raise ValueError("Generated descriptor override must contain ten values")
        random_words["adverbs"] = descriptors
        # Generated descriptors have their own temporary registry and never
        # enter permanent CSV claims.
        contenders["adverbs"] = []
    # Split word lists into 3 unique parts
    noun_parts = split_list(random_words.get("nouns", []))
    adverb_parts = split_list(random_words.get("adverbs", []))
    animal_parts = split_list(random_words.get("animals", []))
    slang_parts = split_list(random_words.get("slang", []))
    place_parts = split_list(random_words.get("places", []))
    name_parts = split_list(random_words.get("names", []))

    # Check if all parts have enough elements
    if len(place_parts) < 3:
        print("[ERROR] place_parts does not have enough elements.")
        return None

    # Format the prompt with the uniquely assigned words
    filled_prompt_template = prompt_template.format(
        noun_words1=", ".join(noun_parts[0]),
        noun_words2=", ".join(noun_parts[1]),
        noun_words3=", ".join(noun_parts[2]),

        adverb_words1=", ".join(adverb_parts[0]),
        adverb_words2=", ".join(adverb_parts[1]),
        adverb_words3=", ".join(adverb_parts[2]),

        animal_words1=", ".join(animal_parts[0]),
        animal_words2=", ".join(animal_parts[1]),
        animal_words3=", ".join(animal_parts[2]),

        slang_words1=", ".join(slang_parts[0]),
        slang_words2=", ".join(slang_parts[1]),
        slang_words3=", ".join(slang_parts[2]),

        place_words1=", ".join(place_parts[0]),
        place_words2=", ".join(place_parts[1]),
        place_words3=", ".join(place_parts[2]),

        name_words1=", ".join(name_parts[0]),
        name_words2=", ".join(name_parts[1]),
        name_words3=", ".join(name_parts[2])
    )

    # Format the final prompt
    assignment_words = dict(random_words)
    if descriptor_overrides is not None:
        # Role-aware generated descriptors are optional prompt ingredients, not
        # direct adjective substitutions for a masked DESCRIPTION placeholder.
        assignment_words["adverbs"] = []
    guidance = replacement_guidance(preprocessing, assignment_words)
    spark_block = ""
    if theme_sparks:
        spark_lines = [str(item.get("text", "")).strip() for item in theme_sparks]
        spark_lines = [line for line in spark_lines if line]
        if spark_lines:
            spark_block = ("Optional thematic sparks:\n" +
                           "\n".join(f"- {line}" for line in spark_lines) +
                           "\nThese are creative ingredients, not mandatory content. "
                           "Freely combine, distort, ignore or reinterpret them.")
    full_prompt = (f"{filled_prompt_template}\n\n{name_guidance}\n\n{concept_guidance}\n\n"
                   f"{descriptor_guidance}\n\n{final_joke_guidance}\n\n{topic_guidance}\n\n{guidance}\n\n"
                   f"{spark_block}\n\n"
                   f"Text to Transform:\nTitle: {title_to_change}\nExtract: {extract_to_change}")
    diagnostics["prompt_construction_ms"] = round((monotonic() - stage) * 1000, 2)
    diagnostics["prompt_characters"] = len(full_prompt)

    return {
        "full_prompt": full_prompt,
        "contenders": contenders,
        "preprocessing": preprocessing,  # Local only; never passed to send_prompt().
        "title_to_change": title_to_change,
        "extract_to_change": extract_to_change
    }


# --------------

def send_prompt(full_prompt):
    """
    Sends the prepared prompt to the OpenAI API and returns the initial response.

    Args:
        full_prompt (str): The formatted prompt to send.

    Returns:
        dict: The initial response from the OpenAI API.
              Returns None if there's an error.
    """
    try:
        # Single API call with the improved prompt
        with OpenAI(max_retries=0, timeout=30.0) as client:
            response = client.responses.create(
                model="gpt-6-sol",
                input=[
                    {"role": "system", "content": "You are an assistant that transforms text into absurd versions in strict JSON format."},
                    {"role": "user", "content": full_prompt}
                ],
                reasoning={"effort": "none"},
                text={"format": JSON_FORMAT},
                max_output_tokens=750,
                store=False,
            )

        if response.status != "completed":
            raise ValueError("OpenAI rewrite response was incomplete.")

        # Extract response
        response_content = response.output_text
        response_data = json.loads(response_content)

        return response_data

    except Exception as e:
        print(f"Error sending prompt: {e}")
        if _is_credit_exhaustion(e):
            raise RewriteProviderQuotaExhausted(
                "The OpenAI API account has no credits remaining. Add API credits, then try MUNGE IT again."
            ) from e
        return None


# --------------

def format_shizzalise_result(response_data):
    """Validate and sanitize the generated JSON locally, without another API call."""
    try:
        if not isinstance(response_data, dict):
            raise ValueError("Expected a JSON object from generation.")
        for key in ("title", "extract"):
            if not isinstance(response_data.get(key), str) or not response_data[key].strip():
                raise ValueError(f"Generated {key} must be a nonempty string.")
        title = sanitize_text(response_data["title"])
        title = " ".join(title.split()[:18])
        return {
            "crazyReplacement1Title": title,
            "crazyReplacement1Extract": sanitize_text(response_data["extract"]),
            "crazyReplacement1done": True,
            "flagForDeleteCount": 0,
            "flagForFunnyCount": 0,
            "chatHistory": [],
        }
    except (TypeError, ValueError) as e:
        print(f"Error formatting Shizzalise result: {e}")
        return None


def copy_edit_pass(pass1_result, repetition_replacement=None):
    """Second AI pass: copy-edit pass-1 output only.

    Receives ONLY the extract produced by pass 1.  The original
    source text is never included.  The purpose is to fix grammar, broken
    sentence structure, subject-verb agreement, and flow while preserving
    all absurdity, bizarre events, rude/slang words, strange names, surreal
    imagery, invented relationships, and overall ridiculousness.

    The model is instructed to act as a highly competent copy editor who
    accepts that every insane thing in the article is completely true.

    Parameters
    ----------
    pass1_result : dict
        Must contain 'crazyReplacement1Title' and 'crazyReplacement1Extract'
        (the sanitised pass-1 output from format_shizzalise_result).

    Returns
    -------
    dict | None
        A result dict in the same schema as format_shizzalise_result, or
        None if the call fails.  The caller falls back to pass1_result on None.
    """
    title = pass1_result.get('crazyReplacement1Title', '')
    extract = pass1_result.get('crazyReplacement1Extract', '')
    if not title or not extract:
        return None

    system_prompt = (
        "You are a highly competent copy editor. "
        "Your task is to improve the grammar, sentence structure, subject-verb agreement, "
        "flow and readability of the text you are given. "
        "You must accept that every single event, person, object and situation in the text "
        "is completely and literally true. "
        "Do NOT make the story sensible, sanitise it, revert it toward normal journalism, "
        "remove any weird or absurd details, or explain any jokes. "
        "Preserve: absurdity, bizarre events, rude or slang words, strange names, "
        "surreal imagery, invented relationships and details, and overall ridiculousness. "
        "Fix only: grammar, broken sentence structure, agreement, flow and readability. "
        "First finish the extract. It is the canonical content. Then derive the title "
        "ONLY from that final extract, never using the preliminary title. "
        "Write a punchy, funny, grammatical headline-like summary that also works naturally "
        "as one sung or rapped lyric. Aim for 12–18 words, with a hard maximum of 18 words and 180 characters. "
        "Use only words present in the final extract; introduce no new subjects, "
        "objects, events or ideas. Return JSON with extract first, then title. "
        "Do not add commentary, markdown or code fences."
    )

    if repetition_replacement:
        targets = [item["text"] for item in repetition_replacement.get("targets", ())][:3]
        alternatives = [item["text"] for item in
                        repetition_replacement.get("alternatives", ())][:2]
        maximum = min(2, int(repetition_replacement.get("maximum_substitutions", 2)))
        phrase_mode = bool(repetition_replacement.get("phrase_replacement"))
        fallback_cues = repetition_replacement.get("fallback_domain_cues", ())
        system_prompt += (
            "\n\nBOUNDED PHRASE-REPLACEMENT EXPERIMENT: " if phrase_mode else
            "\n\nBOUNDED REPETITION-REPLACEMENT EXPERIMENT: "
        )
        action = (
            f"Make one or two targeted substitutions when safe and grammatically feasible, "
            f"with a hard maximum of {maximum}. Prioritise the highest-confidence repeated "
            "comic phrases. " if phrase_mode else
            f"You may make at most {maximum} targeted vocabulary substitutions. "
        )
        fallback = (
            "Otherwise invent one fresh, grammatically compatible and equally absurd replacement "
            "inspired loosely by these thematic domains: " + ", ".join(fallback_cues) + ". "
            if phrase_mode and repetition_replacement.get("inventive_fallback") else ""
        )
        system_prompt += (
            action + "Recently repeated comic targets: " + ", ".join(targets) + ". " +
            "Optional fresher thematic alternatives: " + ", ".join(alternatives) + ". " +
            "Prefer a supplied alternative when it fits naturally. " + fallback +
            "Leave a target unchanged if replacement would weaken grammar, continuity or the joke. "
            "Change only the necessary phrase and local grammatical agreement. Preserve the "
            "surrounding sentence, original narrative sequence, story structure, every "
            "source-derived event and relationship, sentence density, ridiculous combinations, "
            "dense surreal combinations, outrageous British humour, profanity, innuendo, surreal "
            "intensity, existing joke density and comic timing. Do not change names or protected "
            "source details. Do not make the "
            "article more coherent, conventional, realistic, polite or restrained. Do not "
            "rewrite the whole article, remove unrelated jokes, invent a different story or add "
            "another recurring motif. The listed alternatives"
            + (" or the single explicitly allowed fresh fallback" if
               phrase_mode and repetition_replacement.get("inventive_fallback") else "") +
            " are the sole exception to the rule against introducing words absent from the extract."
        )

    user_content = json.dumps({'extract': extract}, ensure_ascii=False)

    try:
        with OpenAI(max_retries=0, timeout=30.0) as client:
            response = client.responses.create(
                model="gpt-6-sol",
                input=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                reasoning={"effort": "none"},
                text={"format": JSON_FORMAT},
                max_output_tokens=750,
                store=False,
            )

        if response.status != "completed":
            raise ValueError("Copy-edit response was incomplete.")

        corrected = json.loads(response.output_text)

        return format_shizzalise_result(corrected)

    except Exception as exc:
        print(f"Copy-edit pass 2 failed (falling back to pass 1): {exc}")
        return None


def comedy_editor_word_target(text):
    """Return the body-only half-length target and its narrow tolerance."""
    first_pass_words = len(re.findall(r"\b[\w'-]+\b", str(text or "")))
    if not first_pass_words:
        return {"first_pass_word_count": 0, "target_word_count": 0,
                "target_min_word_count": 0, "target_max_word_count": 0}
    return {
        "first_pass_word_count": first_pass_words,
        "target_word_count": max(1, round(first_pass_words * .50)),
        "target_min_word_count": max(1, round(first_pass_words * .45)),
        "target_max_word_count": max(1, round(first_pass_words * .55)),
    }


def comedy_editor_pass(source, pass1_result, word_target=None):
    """Optional concise comedy edit; callers retain pass one on failure."""
    title = pass1_result.get("crazyReplacement1Title", "")
    extract = pass1_result.get("crazyReplacement1Extract", "")
    if not title or not extract:
        return None
    word_target = word_target or comedy_editor_word_target(extract)
    target = word_target["target_word_count"]
    minimum = word_target["target_min_word_count"]
    maximum = word_target["target_max_word_count"]

    system_prompt = (
        "You are the final editor of an outrageously surreal British comedy article. "
        f"The first-pass ARTICLE BODY contains {word_target['first_pass_word_count']} words. "
        f"Produce a final ARTICLE BODY of approximately {target} words, normally within "
        f"{minimum}-{maximum} words. This range excludes the title and is the normal editorial "
        "requirement, with only modest flexibility for exceptionally funny material. "
        "Aggressively remove repetitive concepts, unnecessary explanations, weaker jokes, "
        "excessive descriptions and padding. "
        "Preserve the strongest absurd imagery, bizarre noun collisions, "
        "unexpected animal occupations, profanity, innuendo, irreverence, wonderfully "
        "nonsensical combinations and unpredictable humour. Improve sentence flow, "
        "comic timing and narrative continuity without rationalising the nonsense, making "
        "it realistic, sanitising it or turning it into conventional comedy. Preserve the "
        "source article's principal events, chronology and narrative backbone. Brief invented "
        "fictional connective humour, adjusted relationships and small additional jokes are allowed "
        "when they make the existing absurdity work better. Do not introduce major new events, "
        "characters, storylines or lengthy digressions. Return only strict JSON containing "
        "title and extract. Write a short, absurd, relevant title derived only from the final "
        "edited article, preferably naming its rewritten main subject, person, place or work. "
        "Do not reuse the source title merely because it is available. Return no explanations, "
        "commentary, markdown or code fences."
    )
    source_article = {
        key: str(source.get(key, ""))
        for key in ("title", "description", "extract") if source.get(key)
    }
    user_content = json.dumps({
        "original_source_article": source_article,
        "first_pass_comedy_rewrite": {"title": title, "extract": extract},
    }, ensure_ascii=False)

    try:
        with OpenAI(max_retries=0, timeout=30.0) as client:
            response = client.responses.create(
                model=comedy_editor_model(),
                input=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                reasoning={"effort": "none"},
                text={"format": JSON_FORMAT},
                max_output_tokens=750,
                store=False,
            )
        if response.status != "completed":
            raise ValueError("Comedy-editor response was incomplete.")
        corrected = json.loads(response.output_text)
        if not isinstance(corrected, dict) or not isinstance(corrected.get("extract"), str):
            raise ValueError("Comedy-editor article was invalid.")
        if not isinstance(corrected.get("title"), str) or not corrected["title"].strip():
            # Keep a successful article edit when only its title is malformed.
            first_sentence = re.split(
                r"(?<=[.!?])\s+", corrected["extract"].strip(), maxsplit=1)[0]
            corrected["title"] = " ".join(first_sentence.split()[:12]) or title
        return format_shizzalise_result(corrected)
    except Exception as exc:
        print(f"Comedy editor failed (falling back to pass 1): {type(exc).__name__}")
        return None
