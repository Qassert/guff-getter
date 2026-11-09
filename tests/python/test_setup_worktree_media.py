from pathlib import Path

import pytest

from scripts.setup_worktree_media import MEDIA_DIRECTORIES, configure_media


def make_source(root: Path):
    for name in MEDIA_DIRECTORIES:
        directory = root / name
        directory.mkdir(parents=True)
        (directory / "example.bin").write_bytes(b"media")


def test_configures_empty_worktree_without_changing_source(tmp_path):
    source = tmp_path / "source"
    project = tmp_path / "worktree"
    make_source(source)
    for name in ("generated_images", "generated_audio"):
        directory = project / "data" / name
        directory.mkdir(parents=True)
        (directory / ".gitkeep").touch()

    pointer = configure_media(source, project)
    assert pointer.read_text(encoding="utf-8") == str(source.resolve()) + "\n"
    assert not any((project / "data" / name).is_symlink() for name in MEDIA_DIRECTORIES)
    assert all((source / name / "example.bin").read_bytes() == b"media"
               for name in MEDIA_DIRECTORIES)
    assert configure_media(source, project) == pointer


def test_refuses_to_replace_worktree_media(tmp_path):
    source = tmp_path / "source"
    project = tmp_path / "worktree"
    make_source(source)
    local = project / "data" / "generated_images"
    local.mkdir(parents=True)
    (local / "keep.png").write_bytes(b"local")

    with pytest.raises(RuntimeError, match="Refusing to bypass nonempty"):
        configure_media(source, project)
    assert (local / "keep.png").read_bytes() == b"local"
    assert not (project / ".newsmuncher-media-root").exists()


def test_validates_every_source_before_making_links(tmp_path):
    source = tmp_path / "source"
    project = tmp_path / "worktree"
    source.mkdir()

    with pytest.raises(FileNotFoundError):
        configure_media(source, project)
    assert not project.exists()
