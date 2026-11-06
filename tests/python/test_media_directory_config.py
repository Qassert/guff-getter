from newsmuncher.config import shared_media_root


def test_shared_media_root_defaults_to_none(tmp_path):
    assert shared_media_root(tmp_path, {}) is None


def test_shared_media_root_can_be_set_by_worktree_pointer(tmp_path):
    shared = tmp_path / "shared media"
    shared.mkdir()
    (tmp_path / ".newsmuncher-media-root").write_text(str(shared) + "\n", encoding="utf-8")
    assert shared_media_root(tmp_path, {}) == shared.resolve()


def test_environment_override_wins_over_pointer(tmp_path):
    pointer = tmp_path / "pointer"
    override = tmp_path / "override"
    pointer.mkdir()
    override.mkdir()
    (tmp_path / ".newsmuncher-media-root").write_text(str(pointer), encoding="utf-8")
    assert shared_media_root(tmp_path, {"NEWSMUNCHER_MEDIA_ROOT": str(override)}) == override.resolve()
