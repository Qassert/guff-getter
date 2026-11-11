"""Deterministic, nomination-only visual descriptions for paid media providers."""
from __future__ import annotations

import hashlib
import logging
import re


VERSION = "media-safe-v4"
logger = logging.getLogger(__name__)
FALLBACK = (
    "A surreal British editorial scene in an eccentric civic hall, where puzzled "
    "figures inspect an elaborate household contraption while harmless everyday "
    "objects behave with solemn ceremonial importance."
)

# Explicit/graphic matches are omitted at clause boundaries, never disguised.
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
    source = f"{title}. {body}"
    # Only benign, non-explicit anatomy labels receive local neutral wording.
    # Explicit sexual acts and graphic violence never use token substitution.
    rewritten, replacements = re.subn(r"\b(?:manboobs?|boobs?)\b", "peculiar", source,
                                      flags=re.I)
    fragments = [part.strip() for part in re.split(r"(?<=[.!?;])\s+|\n+", rewritten)
                 if part.strip()]
    retained = [part for part in fragments if not _categories(part)]
    omitted = len(fragments) - len(retained)
    concept = " ".join(" ".join(retained).split())[:1400]
    # A neutralised label alone does not provide a usable scene.
    if not re.search(r"[a-z]{3}", re.sub(r"\bpeculiar\b", "", concept, flags=re.I), re.I):
        concept = FALLBACK
        strategy = "generic_fallback"
    elif omitted:
        strategy = "scene_preserving_fallback"
    elif replacements:
        strategy = "targeted_rewrite"
    else:
        strategy = "normal"
    sanitised = bool(replacements or omitted or concept == FALLBACK)
    return {
        "version": VERSION,
        "concept": concept,
        "sanitised": sanitised,
        "categories": list(categories),
        "strategy": strategy,
        "rules": (["benign_anatomy_label"] if replacements else []) +
                 (["omit_flagged_clause"] if omitted else []),
        "preservation": {"retained_clauses": len(retained),
                         "omitted_clauses": omitted,
                         "neutralised_terms": replacements},
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
        # Development diagnostics contain identity, actions and counts, never text.
        logger.debug("media_description rewrite_id=%s sanitised=%s categories=%s "
                     "strategy=%s rules=%s preservation=%s",
                     result.get("rewrite_id"), current["sanitised"],
                     current["categories"], current["strategy"], current["rules"],
                     current["preservation"])
    return current
