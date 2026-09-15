"""Temporary, standalone voice comparison. No website integration.

Run from the repository root: python -m scripts.compare_tts --provider all --dry-run
Remove --dry-run only when ready for one potentially billable request per provider.
Edit VOICE_POOLS below to curate voices available to your provider accounts.
"""
import argparse
import os
import random
from uuid import uuid4

from dotenv import load_dotenv
import requests

from newsmuncher.config import DATA_DIR, ENV_FILE
from newsmuncher.services.openai_tts import MODEL, VOICES, generate_openai

SAMPLE_TEXT = (
    "Local councillor Nigel Cheeseboard has denied launching twelve ferrets into the "
    "planning committee, despite witnesses describing the meeting as surprisingly productive."
)
OUTPUT_DIR = DATA_DIR / "tts-comparison"
TIMEOUT = 60
KEYS = {"openai": "OPENAI_API_KEY", "elevenlabs": "ELEVENLABS_API_KEY",
        "cartesia": "CARTESIA_API_KEY"}
MODELS = {"openai": MODEL, "elevenlabs": "eleven_multilingual_v2",
          "cartesia": "sonic-3.6"}
CARTESIA_VERSION = "2026-08-14"
# (Display label, API voice ID). Static pools: no paid/list-voices calls to select.
VOICE_POOLS = {
    "openai": VOICES,
    "elevenlabs": (("George", "JBFqnCBsd6RMkjVDRZzb"),
                   ("Rachel", "21m00Tcm4TlvDq8ikWAM")),
    "cartesia": (("Docs example voice", "db6b0ed5-d5d3-463d-ae85-518a07d3c2b4"),
                 ("Barbershop Man", "a0e99841-438c-4a64-b679-ae501e7d6091")),
}


def post_audio(url, headers, payload, **kwargs):
    # requests defaults to no retries. Do not follow redirects with credentials.
    with requests.post(url, headers=headers, json=payload, timeout=TIMEOUT,
                       allow_redirects=False, **kwargs) as response:
        response.raise_for_status()
        if response.status_code != 200:
            raise ValueError("Unexpected response status")
        if not response.headers.get("Content-Type", "").lower().startswith("audio/"):
            raise ValueError("Expected audio response")
        return response.content


def generate_elevenlabs(key, voice, text):
    return post_audio(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice}",
        {"xi-api-key": key, "Accept": "audio/mpeg"},
        {"text": text, "model_id": MODELS["elevenlabs"]},
        params={"output_format": "mp3_44100_128"},
    )


def generate_cartesia(key, voice, text):
    return post_audio(
        "https://api.cartesia.ai/tts/bytes",
        {"Authorization": f"Bearer {key}", "Cartesia-Version": CARTESIA_VERSION},
        {"model_id": MODELS["cartesia"], "transcript": text, "voice": voice,
         "language": "en", "output_format": {
             "container": "mp3", "sample_rate": 44100, "bit_rate": 128000}},
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", choices=(*KEYS, "all"), default="all")
    parser.add_argument("--dry-run", action="store_true", help="No requests or output files")
    args = parser.parse_args(argv)
    load_dotenv(ENV_FILE, override=False)
    providers = tuple(KEYS) if args.provider == "all" else (args.provider,)
    generators = {"openai": generate_openai, "elevenlabs": generate_elevenlabs,
                  "cartesia": generate_cartesia}
    failed = False
    for provider in providers:
        label, voice = random.choice(VOICE_POOLS[provider])
        path = OUTPUT_DIR / f"{provider}-{voice}-{uuid4().hex}.mp3"
        key = os.environ.get(KEYS[provider], "").strip()
        print(f"{provider}: voice={label} ({voice}); model={MODELS[provider]}")
        if args.dry_run:
            print(f"DRY RUN: {len(SAMPLE_TEXT)} characters -> {path}; "
                  f"key {'present' if key else 'missing (would skip)'}; no request")
            continue
        if not key:
            print(f"SKIPPED: set {KEYS[provider]} in environment or root .env")
            failed = True
            continue
        try:
            # Check directory access before spending on synthesis.
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            audio = generators[provider](key, voice, SAMPLE_TEXT)
            if not audio:
                raise ValueError("Empty audio response")
            with path.open("xb") as output:
                output.write(audio)
            print(f"Saved {path} ({len(audio)} bytes)")
        except Exception as exc:
            # Never echo provider bodies, exception messages or request headers/keys.
            print(f"FAILED: {provider} ({type(exc).__name__}); check account/key, "
                  "voice access and output permissions. No retry performed.")
            failed = True
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
