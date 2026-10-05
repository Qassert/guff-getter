"""Deterministic ElevenLabs music plan using the saved hidden title verbatim."""
from jingle_service.contract import MusicBrief
import random

from jingle_service.genres import GENRES, GENRE_PROFILES


def create_jingle_brief(entry):
    if entry.get("nominated") is not True:
        raise ValueError("Only a nominated entry can receive a jingle.")
    title = entry.get("crazyReplacement1Title")
    if not isinstance(title, str) or not title.strip():
        raise ValueError("Nominated rewritten title is required.")
    genre = random.choice(GENRES)
    profile = GENRE_PROFILES[genre]
    positive = [
        genre,
        profile.caption(),
        "short comedy advertising jingle",
        "immediate clear lead vocal with every supplied word sung or rapped intelligibly",
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
