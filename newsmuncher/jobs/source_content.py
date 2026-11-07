"""Small, dependency-free helpers shared by external source fetch jobs."""

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import unescape
import re
import time

import requests


DEFAULT_HEADERS = {"User-Agent": "NewsMuncher/1.0 (personal hobby project)"}
_TAG = re.compile(r"<[^>]*>")
_SPACE = re.compile(r"\s+")
_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+")


def plain_text(value):
    """Turn API HTML or plain text into normalised plain text."""
    return _SPACE.sub(" ", _TAG.sub(" ", unescape(str(value or "")))).strip()


def reduce_description(value, target_words=80, maximum_words=100):
    """Keep ordered sentences near ``target_words`` without rewriting them."""
    text = plain_text(value)
    words = text.split()
    if len(words) <= target_words:
        return text

    sentences = [part.strip() for part in _SENTENCE_BOUNDARY.split(text) if part.strip()]
    selected = []
    count = 0
    for sentence in sentences:
        sentence_words = sentence.split()
        proposed = count + len(sentence_words)
        if proposed <= maximum_words:
            selected.append(sentence)
            count = proposed
            if count >= target_words:
                break
            continue

        if count >= max(1, target_words - 10):
            break
        remaining = max(1, target_words - count)
        selected.append(" ".join(sentence_words[:remaining]).rstrip(".,;:!?") + "…")
        break

    return " ".join(selected) or " ".join(words[:target_words]).rstrip(".,;:!?") + "…"


def _retry_delay(response):
    value = response.headers.get("Retry-After")
    if not value:
        return 1.0
    try:
        return max(0.0, float(value))
    except ValueError:
        try:
            when = parsedate_to_datetime(value)
            if when.tzinfo is None:
                when = when.replace(tzinfo=timezone.utc)
            return max(0.0, (when - datetime.now(timezone.utc)).total_seconds())
        except (TypeError, ValueError, OverflowError):
            return 1.0


def get_json(session, url, *, params=None, timeout=15, max_retry_wait=15):
    """GET JSON once, with one standards-aware retry after a short 429."""
    response = session.get(url, params=params, timeout=timeout)
    if response.status_code == 429:
        delay = _retry_delay(response)
        if delay > max_retry_wait:
            raise requests.HTTPError(
                f"Rate limited; Retry-After ({delay:.1f}s) exceeds request budget",
                response=response,
            )
        time.sleep(delay)
        response = session.get(url, params=params, timeout=timeout)
    response.raise_for_status()
    return response.json()


def source_session():
    client = requests.Session()
    client.headers.update(DEFAULT_HEADERS)
    return client
