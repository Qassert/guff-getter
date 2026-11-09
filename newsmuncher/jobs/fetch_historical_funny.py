from newsmuncher.config import TEMP_FILE
import os
import json
import random
import requests  # type: ignore

from newsmuncher.jobs.source_content import get_json, reduce_description, source_session
from newsmuncher.utils.source_preprocessing import preserve_source_text

REUSABLE_API_BASE_URL = os.getenv("REUSABLE_API_BASE_URL", "http://127.0.0.1:8000/reusable")
OPENALEX_URL = "https://api.openalex.org/works"


def _openalex_abstract(inverted_index):
    positioned = [
        (position, word)
        for word, positions in (inverted_index or {}).items()
        for position in positions
    ]
    return " ".join(word for _, word in sorted(positioned))


def fetch_openalex(min_words=60):
    """Fetch an English OpenAlex abstract for the former Lonely Hearts teat."""
    try:
        with source_session() as client:
            payload = get_json(client, OPENALEX_URL, params={
                "filter": "has_abstract:true,language:en",
                "sample": 50,
                "per-page": 50,
                "select": "id,doi,display_name,publication_year,type,abstract_inverted_index",
            })
        candidates = []
        for work in payload.get("results", []):
            abstract = _openalex_abstract(work.get("abstract_inverted_index"))
            if work.get("display_name") and len(abstract.split()) >= min_words:
                candidates.append((work, abstract))
        if not candidates:
            raise ValueError("OpenAlex returned no sufficiently descriptive abstracts")
        work, abstract = random.choice(candidates)
        year = work.get("publication_year")
        temp_data = {
            "title": preserve_source_text(work["display_name"]),
            "description": "OpenAlex research abstract" + (f" ({year})" if year else ""),
            "extract": preserve_source_text(reduce_description(abstract)),
            "source_url": work.get("doi") or work.get("id"),
            "source_name": "OpenAlex",
            "source_licence": "CC0 (OpenAlex API data)",
        }
        with open(TEMP_FILE, "w", encoding="utf-8") as target:
            json.dump(temp_data, target, ensure_ascii=False, indent=2)
        return temp_data
    except (requests.RequestException, KeyError, TypeError, ValueError) as error:
        print(f"Could not fetch OpenAlex source content: {error}")
        return None

def fetch_historical_funny_from_api(source=None):
    """Fetch the least used historical funny entry from the API and store it temporarily."""
    if source == "dating":
        return fetch_openalex()
    suffix = "?source=dating" if source == "dating" else ""
    try:
        # Fetch all entries from the API
        response = requests.get(f"{REUSABLE_API_BASE_URL}/get_all/{suffix}")
        response.raise_for_status()
        all_entries = response.json()

        if not all_entries:
            print("No entries found in the API.")
            return None

        # Find the minimum number of times used
        min_used = min(entry["numberOftimesUsed"] for entry in all_entries)

        # Filter entries with the minimum number of times used
        least_used_entries = [entry for entry in all_entries if entry["numberOftimesUsed"] == min_used]

        # Randomly select one of the least used entries
        selected_entry = random.choice(least_used_entries)

        # Increment the number of times used via the API
        increment_response = requests.put(f"{REUSABLE_API_BASE_URL}/increment_usage/{selected_entry['id']}{suffix}")
        increment_response.raise_for_status()

        temp_data = {
            "title": selected_entry.get("title", "Unknown"),
            "description": selected_entry.get("description", "No description available"),
            "extract": selected_entry.get("extract", "No extract available")
        }

        # Save data to temp file instead of posting
        with open(TEMP_FILE, "w") as file:
            json.dump(temp_data, file, indent=4)

        print(f"Fetched historical funny stored in {TEMP_FILE}. Run confirm_data.py to store it in the API.")
        return temp_data

    except requests.exceptions.RequestException as e:
        print(f"Error communicating with the API: {e}")
        return None
    except (KeyError, ValueError) as e:
        print(f"Error processing API response: {e}")
        return None

if __name__ == "__main__":
    import sys
    raise SystemExit(0 if fetch_historical_funny_from_api(
        sys.argv[1] if len(sys.argv) > 1 else None) else 1)
