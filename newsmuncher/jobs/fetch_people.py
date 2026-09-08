from newsmuncher.config import TEMP_FILE
import json
import requests
import random
import time
import string
from urllib.parse import quote
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

from newsmuncher.utils.clean_data import clean_data

API_URL = "https://en.wikipedia.org/w/api.php"
SUMMARY_URL = "https://en.wikipedia.org/api/rest_v1/page/summary/"
HEADERS = {"User-Agent": "NewsMuncher/1.0 (personal hobby project)"}

def _wait_if_rate_limited(response):
    """Honor a rate limit before the caller stops this fetch invocation."""
    if response.status_code != 429:
        return False

    delay = 5.0
    retry_after = response.headers.get("Retry-After")
    if retry_after:
        try:
            delay = max(delay, int(retry_after))
        except ValueError:
            try:
                retry_at = parsedate_to_datetime(retry_after)
                if retry_at.tzinfo is None:
                    retry_at = retry_at.replace(tzinfo=timezone.utc)
                delay = max(delay, (retry_at - datetime.now(timezone.utc)).total_seconds())
            except (TypeError, ValueError, OverflowError):
                pass
    print(f"Wikimedia rate limit (HTTP 429): waiting {delay:.1f} seconds, then stopping this fetch.")
    time.sleep(delay)
    return True


def fetch_data(min_chars=160, max_chars=500, max_retries=10):
    """Fetch one category batch, then try locally shuffled biographies."""
    if max_retries <= 0:
        return None

    with requests.Session() as session:
        session.headers.update(HEADERS)
        try:
            # Sample living-person biographies from a random category sort position.
            # This is intentionally not a uniform sample of all biographies.
            prefix = "".join(random.choices(string.ascii_uppercase, k=3))
            response = session.get(
                API_URL,
                params={
                    "action": "query",
                    "format": "json",
                    "list": "categorymembers",
                    "cmtitle": "Category:Living people",
                    "cmnamespace": 0,
                    "cmtype": "page",
                    "cmsort": "sortkey",
                    "cmstartsortkeyprefix": prefix,
                    "cmlimit": 200,
                },
                timeout=15,
            )
            if _wait_if_rate_limited(response):
                return None
            response.raise_for_status()
            category_data = response.json()
            if "error" in category_data:
                raise ValueError(f"Wikipedia API error: {category_data['error']}")
            candidates = category_data["query"]["categorymembers"]
            if not candidates:
                raise ValueError(f"No biographies returned for category position {prefix}.")
        except (requests.RequestException, KeyError, ValueError) as e:
            print(f"Could not fetch Wikipedia biography batch: {e}")
            return None

        random.shuffle(candidates)
        for attempt, person in enumerate(candidates[:max_retries]):
            if attempt:
                time.sleep(1)
            try:
                response = session.get(
                    SUMMARY_URL + quote(person["title"], safe=""),
                    timeout=15,
                )
                if _wait_if_rate_limited(response):
                    return None
                response.raise_for_status()
                summary = response.json()
                if summary.get("type") == "disambiguation":
                    raise ValueError("Wikipedia returned a disambiguation page.")
                abstract = clean_data(summary.get("extract", ""))
                resource_name = clean_data(summary.get("title", person["title"]))
                description = clean_data(summary.get("description", ""))
                if not description:
                    raise ValueError(f"No short description returned for {person['title']}.")

                # Validate abstract length
                if min_chars <= len(abstract) <= max_chars:
                    temp_data = {
                        "title": resource_name,
                        "description": description,
                        "extract": abstract
                    }

                    # Save data to temp file instead of posting
                    with open(TEMP_FILE, "w") as file:
                        json.dump(temp_data, file, indent=4)

                    print(f"Fetched person data stored in {TEMP_FILE}. Run confirm_data.py to store it in the API.")
                    return temp_data

                print(f"Retry {attempt + 1}/{max_retries}: Invalid summary length ({len(abstract)} chars).")

            except (requests.RequestException, IndexError, KeyError, ValueError) as e:
                print(f"Retry {attempt + 1}/{max_retries}: {e}")

    print("Failed to fetch valid person data after retries.")
    return None

if __name__ == "__main__":
    fetch_data()
