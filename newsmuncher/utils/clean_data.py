from newsmuncher.config import ENV_FILE, WORDS_DIR
import os, re, random, json
import openai  # type: ignore
from dotenv import load_dotenv  # type: ignore


WORDS_FOLDER = WORDS_DIR


# Load API key from .env
load_dotenv(ENV_FILE)
openai.api_key = os.getenv("OPENAI_API_KEY")

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
        random_words[category] = extract_unique_words(file_path, NumberOfWords)  # removed category
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
    part_size = max(1, len(lst) // num_parts)
    return [lst[i * part_size:(i + 1) * part_size] for i in range(num_parts)]


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
    cleaned_entry = clean_data(entry)
    title_to_change = cleaned_entry.get("title", "No title provided").strip() + ' - ' + cleaned_entry.get("description",
                                                                                                      "No description provided").strip()
    extract_to_change = cleaned_entry.get("extract", "No extract provided").strip()

    # Get fresh, unique words for this prompt
    random_words = load_random_words(NumberOfWords)
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
    full_prompt = f"{filled_prompt_template}\n\nText to Transform:\nTitle: {title_to_change}\nExtract: {extract_to_change}"

    print("\n********************************")
    print("[DEBUG] Final Prompt (Check if placeholders are replaced with UNIQUE words):")
    print(full_prompt)
    print("********************************\n")

    return {
        "full_prompt": full_prompt,
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
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # gpt-4 gpt-4o-mini gpt-3.5-turbo
            messages=[
                {"role": "system", "content": "You are an assistant that transforms text into absurd versions in strict JSON format."},
                {"role": "user", "content": full_prompt}
            ],
            n=1,  # Single response
            temperature=0.8,
            max_tokens=750
        )

        # Extract response
        response_content = response["choices"][0]["message"]["content"]
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

def correct_grammar(response_data):
    """
    Sends the initial response to the OpenAI API for grammar correction.

    Args:
        response_data (dict): The initial response data to correct.

    Returns:
        dict: A dictionary containing the sanitized and corrected response.
              Returns None if there's an error.
    """
    try:
        # Secondary call to correct grammar and pluralization
        corrected_response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # Cheaper model for grammar correction
            messages=[
                {"role": "system", "content": "You are an assistant that corrects grammar, spelling, case and pluralization in JSON text."},
                {"role": "user", "content": json.dumps(response_data)}
            ],
            n=1,
            temperature=0.2,  # Lower temperature for more consistent corrections
            max_tokens=250
        )

        corrected_content = corrected_response["choices"][0]["message"]["content"]
        corrected_data = json.loads(corrected_content)

        print("\n********************************")
        print("[DEBUG] Corrected Response Data:")
        print(json.dumps(corrected_data, indent=4))
        print("********************************\n")

        return {
            "crazyReplacement1Title": sanitize_text(corrected_data["title"]),
            "crazyReplacement1Extract": sanitize_text(corrected_data["extract"]),
            "crazyReplacement1done": True,
            "flagForDeleteCount": 0,
            "flagForFunnyCount": 0,
            "chatHistory": []
        }

    except Exception as e:
        print(f"Error correcting grammar: {e}")
        return None