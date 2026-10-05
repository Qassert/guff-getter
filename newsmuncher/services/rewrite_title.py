"""Bound AI-written final titles without deriving them from the story body."""


def final_title(body, candidate):
    """Return the independently written headline with a hard 18-word cap."""
    candidate = ' '.join((candidate or '').split()).strip('"“”')
    if not candidate:
        raise ValueError("AI-written title is required.")
    return ' '.join(candidate.split()[:18])
