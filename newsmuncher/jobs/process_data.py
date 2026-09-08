from newsmuncher.config import PROMPT_FILE
import os
import requests
import random
import json


from newsmuncher.utils.clean_data import *
from newsmuncher.utils.file_handler import *

ENTRIES_API_BASE_URL = os.getenv("ENTRIES_API_BASE_URL", "http://127.0.0.1:8000")
NumberOfWords = 6

# Load the prompt template
prompt_template = load_prompt(PROMPT_FILE)

# Load random words at the start
random_words = load_random_words(NumberOfWords)

def generate_replacements(entry):
    # Generate replacements using the modular functions: prepare_prompt, send_prompt, and correct_grammar.

    # Prepare the prompt
    prepared_data = prepare_prompt(entry, NumberOfWords, prompt_template)
    if not prepared_data:
        print("[ERROR] Failed to prepare prompt.")
        return None

    # Send the prompt and get the initial response
    initial_response = send_prompt(prepared_data["full_prompt"])
    if not initial_response:
        print("[ERROR] Failed to send prompt.")
        return None

    # Correct the grammar of the initial response
    corrected_data = correct_grammar(initial_response)
    if not corrected_data:
        print("[ERROR] Failed to correct grammar.")
        return None

    return corrected_data

def main(batch_size=1):
    try:
        # Fetch entries from the API
        response = requests.get(f"{ENTRIES_API_BASE_URL}/entries/")
        response.raise_for_status()
        api_entries = response.json()

        # Filter entries that are not processed
        entries_to_process = [
            entry for entry in api_entries
            if isinstance(entry, dict) and not entry.get("crazyReplacement1done", False)
        ]

        # Select a maximum of batch_size entries
        selected_entries = random.sample(entries_to_process, min(batch_size, len(entries_to_process)))

        print(f"Entries to process: {len(selected_entries)}")

        if not selected_entries:
            print("No valid entries found to process.")
            return

        for entry in selected_entries:
            # Generate replacements
            replacements = generate_replacements(entry)
            if replacements:
                try:
                    # Update entry via the API
                    update_response = requests.put(
                        f"{ENTRIES_API_BASE_URL}/entry/{entry['id']}",
                        params={
                            "crazyReplacement1Title": replacements["crazyReplacement1Title"],
                            "crazyReplacement1Extract": replacements["crazyReplacement1Extract"]
                        },
                        cookies={"active_pet": entry.get("creationUser")}
                    )
                    update_response.raise_for_status()
                    print(f"Entry {entry['id']} updated successfully.")
                except requests.RequestException as e:
                    print(f"Error updating entry {entry['id']}: {e}")
            else:
                print(f"Failed to generate replacements for entry {entry['id']}.")

    except requests.RequestException as e:
        print(f"Error fetching entries from API: {e}")

if __name__ == "__main__":
    main()