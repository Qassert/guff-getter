"""Small shared wire contract, with no ML dependencies."""
import base64
import hashlib
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator, model_serializer
from uuid import UUID


class GenreProfile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    label: str = Field(min_length=1, max_length=60)
    bpm: int = Field(ge=30, le=300)
    timesignature: Literal["2", "3", "4", "6"] = "4"
    cues: str = Field(min_length=1, max_length=300)
    avoid: str = Field(default="", max_length=80)

    def caption(self):
        meter = "6/8" if self.timesignature == "6" else f"{self.timesignature}/4"
        caption = f"{self.label}. {self.bpm} BPM; {meter}. {self.cues}."
        return caption + (f" Avoid {self.avoid}." if self.avoid else "")


class MusicBrief(BaseModel):
    model_config = ConfigDict(extra="forbid")
    music_prompt: str = Field(min_length=1, max_length=600)
    lyrics: str = Field(min_length=1, max_length=500)
    duration_seconds: int = Field(default=25, ge=20, le=30)
    genre_profile: GenreProfile | None = None

    @model_serializer(mode="wrap")
    def preserve_legacy_shape(self, handler):
        data = handler(self)
        if self.genre_profile is None:
            data.pop("genre_profile", None)
        return data

    def genre_params(self):
        if self.genre_profile is None:
            return {}
        return {"bpm": self.genre_profile.bpm, "timesignature": self.genre_profile.timesignature}



class GenerationRequest(MusicBrief):
    request_id: UUID
    experiment: Literal["narration-reference-v1"] | None = None
    seed: int | None = Field(default=None, ge=0, le=2**31 - 1)
    reference_audio_b64: str | None = Field(default=None, max_length=2_800_000)
    reference_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")

    @model_validator(mode="after")
    def validate_experiment(self):
        if self.experiment is None:
            if any(v is not None for v in (self.seed, self.reference_audio_b64, self.reference_sha256)):
                raise ValueError("Seed/reference require the isolated experiment namespace")
        elif self.seed is None:
            raise ValueError("Experiments require a fixed seed")
        if (self.reference_audio_b64 is None) != (self.reference_sha256 is None):
            raise ValueError("Reference audio and checksum must be supplied together")
        if self.reference_audio_b64 is not None:
            self.reference_bytes()
        return self

    def reference_bytes(self):
        if self.reference_audio_b64 is None:
            return None
        data = base64.b64decode(self.reference_audio_b64, validate=True)
        if not 3 <= len(data) <= 2_000_000:
            raise ValueError("Reference MP3 must be between 3 bytes and 2 MB")
        if hashlib.sha256(data).hexdigest() != self.reference_sha256:
            raise ValueError("Reference checksum mismatch")
        if not (data.startswith(b"ID3") or data[0] == 255 and data[1] & 224 == 224):
            raise ValueError("Reference must be MP3 audio")
        return data

    def marker_request(self):
        # Preserve the exact old production marker shape. Never persist base64 audio.
        return self.model_dump(mode="json", exclude_none=True, exclude={"reference_audio_b64"})

    def output_path(self, root):
        directory = Path(root)
        if self.experiment:
            directory = directory / "experiments" / self.experiment
        return directory / f"{self.request_id}.mp3"

    def write_reference(self, temporary):
        data = self.reference_bytes()
        if data is None:
            return None
        path = Path(temporary) / "reference.mp3"
        with path.open("xb") as output:
            output.write(data)
        return str(path)
