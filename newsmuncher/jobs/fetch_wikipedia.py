from newsmuncher.utils.source_preprocessing import preserve_source_text
from newsmuncher.config import TEMP_FILE
import json
import requests
import time
import os


from newsmuncher.utils.clean_data import *


API_URL = "https://en.wikipedia.org/api/rest_v1/page/random/summary"

def fetch_data(min_chars=160, max_chars=500, max_retries=10):
    """Fetch a random Wikipedia summary and store it temporarily."""
    for attempt in range(max_retries):
        try:
            response = requests.get(
                API_URL,
                headers={"User-Agent": "NewsMuncher/1.0 (personal hobby project)"},
            )
            response.raise_for_status()
            data = response.json()

            extract = preserve_source_text(data.get("extract", ""))
            if min_chars <= len(extract) <= max_chars:
                temp_data = {
                    "title": preserve_source_text(data.get("title", "")),
                    "description": preserve_source_text(data.get("description", "")),
                    "extract": extract
                }

                # Save data to temp file instead of posting
                with open(TEMP_FILE, "w") as file:
                    json.dump(temp_data, file, indent=4)

                print(f"Fetched Wikipedia data stored in {TEMP_FILE}. Run confirm_data.py to store it in the API.")
                return temp_data

            print(f"Retry {attempt + 1}/{max_retries}: Invalid extract length ({len(extract)} chars).")

        except requests.RequestException as e:
            print(f"Retry {attempt + 1}/{max_retries}: {e}")

        time.sleep(1)

    print("Failed to fetch valid Wikipedia data after retries.")
    return None

if __name__ == "__main__":
    fetch_data()
