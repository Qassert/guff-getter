#!/usr/bin/env python3
"""Configure read-only access to an existing NewsMuncher media store."""

from __future__ import annotations

import argparse
from pathlib import Path


MEDIA_DIRECTORIES = (
    "generated_images",
    "generated_audio",
    "generated_narration",
    "generated_video",
)
SCAFFOLD_FILES = {".gitkeep"}
POINTER_FILE = ".newsmuncher-media-root"


def configure_media(source_data: Path, project_root: Path) -> Path:
    source_data = source_data.expanduser().resolve()
    project_root = project_root.expanduser().resolve()
    destination_data = project_root / "data"
    if source_data == destination_data:
        raise ValueError("Source and destination data directories must differ.")

    for name in MEDIA_DIRECTORIES:
        source = source_data / name
        destination = destination_data / name
        if not source.is_dir():
            raise FileNotFoundError(f"Media source is missing: {source}")
        if destination.exists():
            unexpected = {item.name for item in destination.iterdir()} - SCAFFOLD_FILES
            if unexpected:
                raise RuntimeError(
                    f"Refusing to bypass nonempty media directory {destination}: "
                    + ", ".join(sorted(unexpected))
                )
    pointer = project_root / POINTER_FILE
    pointer.write_text(str(source_data) + "\n", encoding="utf-8")
    return pointer


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Share persistent generated media with an isolated Git worktree."
    )
    parser.add_argument("source_data", type=Path)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    pointer = configure_media(args.source_data, args.project_root)
    print(f"Configured read-only media fallback in {pointer}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
