from fastapi import FastAPI
from fastapi.testclient import TestClient

from newsmuncher.services.static_media import FallbackStaticFiles


def test_static_media_prefers_local_and_falls_back_to_shared(tmp_path):
    local = tmp_path / "local"
    shared = tmp_path / "shared"
    local.mkdir()
    shared.mkdir()
    (local / "local.png").write_bytes(b"local")
    (shared / "shared.png").write_bytes(b"shared")
    (local / "same.png").write_bytes(b"local wins")
    (shared / "same.png").write_bytes(b"shared loses")

    app = FastAPI()
    app.mount("/media", FallbackStaticFiles((local, shared)))
    client = TestClient(app)

    assert client.get("/media/local.png").content == b"local"
    assert client.get("/media/shared.png").content == b"shared"
    assert client.get("/media/same.png").content == b"local wins"
    assert client.get("/media/missing.png").status_code == 404
