from newsmuncher.config import TEMP_FILE
import os
import json
import random
import requests  # type: ignore

REUSABLE_API_BASE_URL = os.getenv("REUSABLE_API_BASE_URL", "http://127.0.0.1:8000/reusable")

def fetch_historical_funny_from_api():
    """Fetch the least used historical funny entry from the API and store it temporarily."""
    try:
        # Fetch all entries from the API
        response = requests.get(f"{REUSABLE_API_BASE_URL}/get_all/")
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
        increment_response = requests.put(f"{REUSABLE_API_BASE_URL}/increment_usage/{selected_entry['id']}")
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
    fetch_historical_funny_from_api()
