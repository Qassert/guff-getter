"""Filesystem paths anchored to this checkout, independent of the working directory."""
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_DIR.parent
ENV_FILE = PROJECT_ROOT / ".env"
TEMPLATES_DIR = PACKAGE_DIR / "templates"
STATIC_DIR = PACKAGE_DIR / "static"
RESOURCES_DIR = PACKAGE_DIR / "resources"
PROMPT_FILE = RESOURCES_DIR / "prompts" / "rewrite.txt"
WORDS_DIR = RESOURCES_DIR / "words"
DATA_DIR = PROJECT_ROOT / "data"
SEEDS_DIR = DATA_DIR / "seeds"
AVATARS_DIR = DATA_DIR / "avatars"
PREVIEWS_DIR = DATA_DIR / "previews"
TEMP_FILE = PREVIEWS_DIR / "temp_data.json"
TEMP_SHIZZ_FILE = PREVIEWS_DIR / "shizz_data.json"

GENERATED_IMAGES_DIR = DATA_DIR / "generated_images"
