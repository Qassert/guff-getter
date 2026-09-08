from newsmuncher.utils.source_preprocessing import preserve_source_text
from newsmuncher.config import TEMP_FILE
import json
import requests
import time
import os


from newsmuncher.utils.clean_data import *

API_URL = "https://poetrydb.org/random"

def extract_valid_verses(lines, max_chars=500):
    """Extract valid verses within the max character limit."""
    current_block = []
    total_chars = 0

    for line in lines:
        if line == "":
            if total_chars + len(" ".join(current_block)) > max_chars:
                break
            current_block.append("")
        else:
            if total_chars + len(line) + 1 > max_chars:
                break
            current_block.append(line)
            total_chars += len(line) + 1
    return " ".join(current_block).strip()


def fetch_data(min_chars=160, max_chars=500, max_retries=10):
    """Fetch a random poem and store it temporarily."""
    for attempt in range(max_retries):
        try:
            response = requests.get(API_URL)
            response.raise_for_status()
            poem_data = response.json()[0]

            poem_title = preserve_source_text(poem_data.get("title", "Untitled"))
            poem_author = preserve_source_text(poem_data.get("author", "Unknown Author"))
            valid_excerpt = extract_valid_verses(poem_data.get("lines", []), max_chars)

            if min_chars <= len(valid_excerpt) <= max_chars:
                temp_data = {
                    "title": poem_title,
                    "description": poem_author,
                    "extract": preserve_source_text(valid_excerpt)
                }

                # Save data to temp file instead of posting
                with open(TEMP_FILE, "w") as file:
                    json.dump(temp_data, file, indent=4)

                print(f"Fetched poem stored in {TEMP_FILE}. Run confirm_data.py to store it in the API.")
                return temp_data

            print(f"Retry {attempt + 1}/{max_retries}: Invalid excerpt length.")

        except requests.RequestException as e:
            print(f"Retry {attempt + 1}/{max_retries}: {e}")

        time.sleep(1)

    print("Failed to fetch a valid poem after retries.")
    return None

if __name__ == "__main__":
    fetch_data()