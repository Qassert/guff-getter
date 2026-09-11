from newsmuncher.services.word_shuffle import BANK_FILES, read_bank, shared_bags
from newsmuncher.utils.source_preprocessing import preserve_source_text, preprocess_source, replacement_guidance, filter_word_banks
from newsmuncher.config import ENV_FILE, WORDS_DIR
import os, re, random, json
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
            "title": {"type": "string"},
            "extract": {"type": "string"},
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
def load_random_words(NumberOfWords):
    """Load a fresh batch of random words, ensuring uniqueness across prompts."""
    random_words = {}
    for category, filename in CSV_FILES.items():
        file_path = os.path.join(WORDS_FOLDER, filename)
        random_words[category] = (shared_bags().draw(category, read_bank(file_path), NumberOfWords)
                                  if category in BANK_FILES else
                                  extract_unique_words(file_path, NumberOfWords))
    print(f"[DEBUG] Looking for word files in: {WORDS_FOLDER}")
    for category, filename in CSV_FILES.items():
        file_path = os.path.join(WORDS_FOLDER, filename)
        print(f"[DEBUG] Checking: {file_path} → Exists: {os.path.exists(file_path)}")

    return random_words


# --------------

def process_batch(data, generate_replacements, flag_name, batch_size):
    """Process a batch of entries and update them."""
    skipped_entries = []
    processed_count = 0

    for key, entry in data.items():  # Iterate through dictionary items
        # Check if entry is a dictionary
        if not isinstance(entry, dict):
            print(f"Skipping invalid entry with key {key}: {entry}")
            skipped_entries.append(key)
            continue

        # Skip entries already processed
        if entry.get(flag_name, False):
            continue

        # Generate replacements for the entry
        replacements = generate_replacements(entry)
        if replacements:
            # Update the entry in the original dictionary
            data[key].update(replacements)
            processed_count += 1
        else:
            # Add to skipped entries if generation failed
            skipped_entries.append(key)

        # Stop after processing the batch size
        if processed_count >= batch_size:
            break

    return skipped_entries


# --------------

def split_list(lst, num_parts=3):
    """Splits a list into roughly equal unique parts, ensuring no repeats."""
    random.shuffle(lst)
    if num_parts <= 0:
        raise ValueError("num_parts must be positive")
    return [lst[i::num_parts] for i in range(num_parts)]


# --------------

def prepare_prompt(entry, NumberOfWords, prompt_template):
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
    original_entry = preserve_source_text(entry)
    preprocessing = preprocess_source(original_entry)
    cleaned_entry = preprocessing["masked"]
    title_to_change = cleaned_entry.get("title", "No title provided").strip() + ' - ' + cleaned_entry.get("description",
                                                                                                      "No description provided").strip()
    extract_to_change = cleaned_entry.get("extract", "No extract provided").strip()

    # Get fresh, unique words for this prompt
    random_words = load_random_words(NumberOfWords)
    # Avoid offering a detected original expression back as a bank ingredient.
    random_words = filter_word_banks(preprocessing, random_words)
    print("[DEBUG] Random Words Loaded:", json.dumps(random_words, indent=2))

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
    guidance = replacement_guidance(preprocessing, random_words)
    full_prompt = f"{filled_prompt_template}\n\n{guidance}\n\nText to Transform:\nTitle: {title_to_change}\nExtract: {extract_to_change}"

    print("\n********************************")
    print("[DEBUG] Final Prompt (Check if placeholders are replaced with UNIQUE words):")
    print(full_prompt)
    print("********************************\n")

    return {
        "full_prompt": full_prompt,
        "contenders": random_words,
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
                model="gpt-5.6-luna",
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

        print("\n********************************")
        print("[DEBUG] Initial Response Data:")
        print(json.dumps(response_data, indent=4))
        print("********************************\n")

        return response_data

    except Exception as e:
        print(f"Error sending prompt: {e}")
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
        return {
            "crazyReplacement1Title": sanitize_text(response_data["title"]),
            "crazyReplacement1Extract": sanitize_text(response_data["extract"]),
            "crazyReplacement1done": True,
            "flagForDeleteCount": 0,
            "flagForFunnyCount": 0,
            "chatHistory": [],
        }
    except (TypeError, ValueError) as e:
        print(f"Error formatting Shizzalise result: {e}")
        return None


def copy_edit_pass(pass1_result):
    """Second AI pass: copy-edit pass-1 output only.

    Receives ONLY the title and extract produced by pass 1.  The original
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
        "Return the result as JSON with 'title' and 'extract' keys. "
        "Do not add commentary, markdown or code fences."
    )

    user_content = json.dumps({'title': title, 'extract': extract}, ensure_ascii=False)

    try:
        with OpenAI(max_retries=0, timeout=30.0) as client:
            response = client.responses.create(
                model="gpt-5.6-luna",
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

        print("\n********************************")
        print("[DEBUG] Copy-edit pass 2 output:")
        print(json.dumps(corrected, indent=4))
        print("********************************\n")

        return {
            "crazyReplacement1Title": sanitize_text(corrected["title"]),
            "crazyReplacement1Extract": sanitize_text(corrected["extract"]),
            "crazyReplacement1done": True,
            "flagForDeleteCount": 0,
            "flagForFunnyCount": 0,
            "chatHistory": [],
        }

    except Exception as exc:
        print(f"Copy-edit pass 2 failed (falling back to pass 1): {exc}")
        return None