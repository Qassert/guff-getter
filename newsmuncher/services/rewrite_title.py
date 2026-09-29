"""Bound final titles to accepted body content without another model request."""
import re


def final_title(body, candidate):
    """Accept a short grounded summary; otherwise use an extractive body heading.

    Vocabulary validation is conservative, not a semantic entailment proof. The
    model instruction supplies summarisation; fallback cannot invent new words.
    """
    words = lambda text: re.findall(r"[\w]+(?:['’_-][\w]+)*", text.casefold())
    candidate = ' '.join((candidate or '').split()).strip('"“”')
    vocabulary = set(words(body))
    if (candidate and len(candidate) <= 60 and 3 <= len(candidate.split()) <= 8
            and set(words(candidate)) <= vocabulary):
        return candidate
    # Keep original word order and stop at a sentence boundary or the hard cap.
    heading = []
    for word in body.split():
        if len(heading) == 8 or len(' '.join(heading + [word])) > 60:
            break
        heading.append(word)
        if word.endswith(('.', '!', '?')):
            break
    return ' '.join(heading).rstrip('.!?;,:') or body[:60].strip()
