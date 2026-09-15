"""Shared speech-only provider for the comparison harness and narration."""
from openai import OpenAI

MODEL = "gpt-4o-mini-tts"
VOICES = (("Cedar", "cedar"), ("Marin", "marin"), ("Coral", "coral"))
TIMEOUT = 60


def generate_openai(key, voice, text):
    with OpenAI(api_key=key, max_retries=0, timeout=TIMEOUT) as client:
        with client.audio.speech.with_streaming_response.create(
            model=MODEL, voice=voice, input=text, response_format="mp3"
        ) as response:
            return response.read()
