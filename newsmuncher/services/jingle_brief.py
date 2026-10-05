"""Deterministic ElevenLabs music plan using the saved hidden title verbatim."""
from jingle_service.contract import MusicBrief
import random

from jingle_service.genres import GENRES, GENRE_PROFILES


def create_jingle_brief(entry):
    if entry.get("nominated") is not True:
        raise ValueError("Only a nominated entry can receive a jingle.")
    # The persisted response title is the complete vocal prompt. The rewritten
    # description/body is intentionally excluded from the ElevenLabs request.
    title = entry.get("crazyReplacement1Title")
    if not isinstance(title, str) or not title.strip():
        raise ValueError("Nominated rewritten title is required.")
    genre = random.choice(GENRES)
    profile = GENRE_PROFILES[genre]
    positive = [
        genre,
        profile.caption(),
        "short advertising jingle",
        "immediate lead vocal",
        "sing the supplied lyrics exactly",
        "every supplied word must be clearly vocalised",
        "no additional lyrics",
        "no invented words",
        "no instrumental intro",
        "catchy, energetic, concise, high quality, clean ending",
    ]
    negative = [
        "instrumental-only",
        "long or ambient intro",
        "indistinct vocals",
        "extended outro",
    ]
    brief = MusicBrief(
        music_prompt=profile.caption(), lyrics=title.strip(), duration_seconds=10,
        genre_profile=profile, positive_styles=positive,
        negative_styles=negative, context_adherence="high")
    return brief, None
