"""Deterministic, nomination-only visual descriptions for paid media providers."""
from __future__ import annotations

import hashlib
import re


VERSION = "media-safe-v3"
FALLBACK = (
    "A surreal British editorial scene in an eccentric civic hall, where puzzled "
    "figures inspect an elaborate household contraption while harmless everyday "
    "objects behave with solemn ceremonial importance."
)

# These are detection rules, not disguised provider-bypass substitutions. When a
# clause matches, it is omitted from the visual concept rather than respelled.
_RULES = {
    "sexual": (
        r"\b(?:sex(?:ual|ually)?|porn(?:ographic)?|arous(?:e|ed|al)|orgasm\w*|masturbat\w*|"
        r"shag(?:ged|ging|s)?|spunk\w*|minge\w*|schlong\w*|penis\w*|vagin\w*|"
        r"testicul\w*|nipple\w*|rectal\w*|genital\w*|manboob\w*|boob\w*)\b",
    ),
    "graphic": (
        r"\b(?:dismember\w*|decapitat\w*|eviscerat\w*|gore|gory|blood[- ]soaked|"
        r"severed (?:head|limb)|corpse\w*)\b",
    ),
}
_OBFUSCATION = str.maketrans({"@": "a", "0": "o", "1": "i", "!": "i", "$": "s", "3": "e"})


def _normalise(value: str) -> str:
    value = str(value or "").lower().translate(_OBFUSCATION)
    value = re.sub(r"(?<=\w)[._*\-]+(?=\w)", "", value)
    return re.sub(r"\s+", " ", value).strip()


def _categories(value: str) -> tuple[str, ...]:
    normal = _normalise(value)
    compact = re.sub(r"[^a-z0-9]+", "", normal)
    found = []
    for category, rules in _RULES.items():
        if any(re.search(rule, normal, re.I) for rule in rules):
            found.append(category)
            continue
        # Catch punctuation/spacing inside the clearest high-risk stems.
        if category == "sexual" and any(stem in compact for stem in (
                "sexual", "porn", "arous", "orgasm", "masturbat", "shag",
                "spunk", "minge", "schlong", "penis", "vagin", "testicul", "nipple",
                "manboob", "boob")):
            found.append(category)
    return tuple(found)


def build_media_description(title: str, body: str) -> dict:
    """Return one bounded visual concept without changing the supplied text."""
    title, body = str(title or ""), str(body or "")
    categories = _categories(f"{title}\n{body}")
    if not categories:
        concept = " ".join(f"{title}. {body}".split())[:1400]
        sanitised = False
    else:
        # Partial sentence retention proved unsafe in production: apparently benign
        # fragments can still contain suggestive compounds or depend on an omitted
        # clause for their meaning. A flagged source therefore gets one standalone,
        # positive scene which contains none of the source wording.
        concept = FALLBACK
        sanitised = True
    if not concept.strip():
        concept, sanitised = FALLBACK, True
    return {
        "version": VERSION,
        "concept": concept,
        "sanitised": sanitised,
        "categories": list(categories),
        "source_hash": hashlib.sha256(f"{title}\0{body}".encode()).hexdigest(),
    }


def ensure_media_description(state: dict) -> dict:
    result = state.get("result") or {}
    title = result.get("crazyReplacement1Title", "")
    body = result.get("crazyReplacement1Extract", "")
    expected = hashlib.sha256(f"{title}\0{body}".encode()).hexdigest()
    current = state.get("media_description")
    if not isinstance(current, dict) or current.get("version") != VERSION or current.get("source_hash") != expected:
        current = build_media_description(title, body)
        state["media_description"] = current
    return current
