"""Shared, opt-in semantic-family memory for comedy ingredient selection."""
from __future__ import annotations

from datetime import datetime, timezone
import os
import re


SEMANTIC_MEMORY_ENV = "NEWSMUNCHER_COMEDY_SEMANTIC_MEMORY"


def semantic_memory_enabled(value: str | None = None) -> bool:
    """Return whether the separate Phase 4G evaluation mode is enabled."""
    mode = (value if value is not None else os.getenv(SEMANTIC_MEMORY_ENV, "off"))
    mode = mode.strip().lower()
    if mode not in {"off", "evaluation"}:
        raise ValueError(f"{SEMANTIC_MEMORY_ENV} must be off or evaluation")
    return mode == "evaluation"


def utc(value):
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def family_record(kind: str, family: str) -> str:
    compact = re.sub(r"[^a-z0-9]+", "-", family.casefold()).strip("-")
    return f"semantic:{kind}:{compact}"


def name_sound_family(surname: str) -> str:
    """Stable broad sound family; punctuation and inflection do not split it."""
    letters = re.sub(r"[^a-z]", "", surname.casefold())
    skeleton = "".join("v" if char in "aeiouy" else "c" for char in letters)
    return re.sub(r"([cv])\1+", r"\1", skeleton) or "unknown"


def descriptor_subject_anchor(subject: str) -> str:
    """Return the distinctive lexical head used to join close paraphrases."""
    ignored = {
        "competitive", "professional", "national", "amateur", "advanced",
        "county", "level", "speed", "full", "contact", "freestyle",
        "ceremonial", "official", "officially", "making", "minor",
    }
    words = [word for word in re.findall(r"[a-z]+", subject.casefold())
             if len(word) >= 4 and word not in ignored]
    return words[-1] if words else re.sub(r"[^a-z0-9]+", "-", subject.casefold()).strip("-")


def descriptor_premise_family(item) -> str:
    get = item.get if isinstance(item, dict) else lambda key: getattr(item, key)
    return f"{get('semantic_theme')}:{descriptor_subject_anchor(get('subject'))}"


def recency_penalty(doc: dict | None, now: datetime, window_days: int = 30) -> float:
    """Bounded soft penalty: recent/frequent families rank later, never become illegal."""
    if not doc:
        return 0.0
    used = utc(doc.get("last_used_at"))
    if not used:
        return 0.0
    age_days = max(0.0, (now - used).total_seconds() / 86400)
    freshness = max(0.0, 1.0 - age_days / max(1, window_days))
    return round(freshness * (1.0 + min(int(doc.get("use_count", 0)), 8) / 8), 6)


def record_family_use(collection, record_id: str, now: datetime, rewrite_id: str, **fields):
    collection.update_one(
        {"_id": record_id},
        {"$setOnInsert": {"version": 1, "record_type": "semantic_family"},
         "$set": {**fields, "last_used_at": now, "last_rewrite_id": rewrite_id},
         "$inc": {"use_count": 1}},
        upsert=True,
    )
