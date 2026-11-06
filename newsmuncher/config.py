"""Filesystem paths anchored to this checkout, independent of the working directory."""
from pathlib import Path
import os

PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_DIR.parent
ENV_FILE = PROJECT_ROOT / ".env"
TEMPLATES_DIR = PACKAGE_DIR / "templates"
STATIC_DIR = PACKAGE_DIR / "static"
RESOURCES_DIR = PACKAGE_DIR / "resources"
PROMPT_FILE = RESOURCES_DIR / "prompts" / "rewrite.txt"
NARRATIVE_SKELETON_PROMPT_FILE = RESOURCES_DIR / "prompts" / "rewrite_narrative_skeleton.txt"
NARRATIVE_SKELETON_PROMPT_ENV = "NEWSMUNCHER_NARRATIVE_SKELETON_PROMPT"
COMEDY_EDITOR_ENV = "NEWSMUNCHER_COMEDY_EDITOR"
COMEDY_EDITOR_MODEL_ENV = "NEWSMUNCHER_COMEDY_EDITOR_MODEL"
DEFAULT_COMEDY_EDITOR_MODEL = "gpt-5.6-luna"


def first_pass_prompt_file():
    mode = os.getenv(NARRATIVE_SKELETON_PROMPT_ENV, "off").strip().lower()
    if mode == "off":
        return PROMPT_FILE
    if mode == "evaluation":
        return NARRATIVE_SKELETON_PROMPT_FILE
    raise ValueError(
        f"{NARRATIVE_SKELETON_PROMPT_ENV} must be off or evaluation")


def comedy_editor_enabled():
    mode = os.getenv(COMEDY_EDITOR_ENV, "off").strip().lower()
    if mode == "off":
        return False
    if mode == "evaluation":
        return True
    raise ValueError(f"{COMEDY_EDITOR_ENV} must be off or evaluation")


def comedy_editor_model():
    return (os.getenv(COMEDY_EDITOR_MODEL_ENV, DEFAULT_COMEDY_EDITOR_MODEL).strip()
            or DEFAULT_COMEDY_EDITOR_MODEL)
WORDS_DIR = RESOURCES_DIR / "words"
DATA_DIR = PROJECT_ROOT / "data"
SEEDS_DIR = DATA_DIR / "seeds"
AVATARS_DIR = DATA_DIR / "avatars"
PREVIEWS_DIR = DATA_DIR / "previews"
TEMP_FILE = PREVIEWS_DIR / "temp_data.json"
TEMP_SHIZZ_FILE = PREVIEWS_DIR / "shizz_data.json"

GENERATED_IMAGES_DIR = DATA_DIR / "generated_images"

GENERATED_AUDIO_DIR = DATA_DIR / "generated_audio"
JINGLE_STATE_FILE = PREVIEWS_DIR / "jingles.sqlite3"

GENERATED_NARRATION_DIR = DATA_DIR / "generated_narration"

GENERATED_VIDEO_DIR = DATA_DIR / "generated_video"

MEDIA_ROOT_ENV = "NEWSMUNCHER_MEDIA_ROOT"
MEDIA_ROOT_POINTER = PROJECT_ROOT / ".newsmuncher-media-root"


def shared_media_root(project_root=PROJECT_ROOT, environ=os.environ):
    """Return an optional read-only media root for an isolated worktree."""
    configured = environ.get(MEDIA_ROOT_ENV, "").strip()
    pointer = project_root / MEDIA_ROOT_POINTER.name
    if not configured and pointer.is_file():
        configured = pointer.read_text(encoding="utf-8").strip()
    return Path(configured).expanduser().resolve() if configured else None


SHARED_MEDIA_ROOT = shared_media_root()


def media_read_directories(local_directory, name):
    directories = [Path(local_directory)]
    if SHARED_MEDIA_ROOT:
        shared = SHARED_MEDIA_ROOT / name
        if shared != directories[0]:
            directories.append(shared)
    return tuple(directories)


GENERATED_IMAGES_READ_DIRS = media_read_directories(GENERATED_IMAGES_DIR, "generated_images")
GENERATED_AUDIO_READ_DIRS = media_read_directories(GENERATED_AUDIO_DIR, "generated_audio")
GENERATED_NARRATION_READ_DIRS = media_read_directories(
    GENERATED_NARRATION_DIR, "generated_narration")
GENERATED_VIDEO_READ_DIRS = media_read_directories(GENERATED_VIDEO_DIR, "generated_video")
