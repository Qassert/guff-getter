"""Small shared wire contract, with no ML dependencies."""
from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID


class MusicBrief(BaseModel):
    model_config = ConfigDict(extra="forbid")
    music_prompt: str = Field(min_length=1, max_length=600)
    lyrics: str = Field(min_length=1, max_length=500)
    duration_seconds: int = Field(default=25, ge=20, le=30)


class GenerationRequest(MusicBrief):
    request_id: UUID
