from fastapi.testclient import TestClient

from app.main import create_app
from tests.auth_utils import configure_auth_env, login


def test_preview_returns_jpeg_when_camera_available(monkeypatch, tmp_path):
    monkeypatch.setenv("FACE_APP_DB_PATH", str(tmp_path / "test.db"))
    configure_auth_env(monkeypatch)
    monkeypatch.setattr(
        "app.api.routes.recognition.capture_preview_jpeg",
        lambda: b"fake-jpeg-bytes",
    )

    with TestClient(create_app()) as client:
        login(client)
        response = client.get("/api/recognition/preview")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
    assert response.content == b"fake-jpeg-bytes"


def test_preview_returns_503_when_camera_unavailable(monkeypatch, tmp_path):
    monkeypatch.setenv("FACE_APP_DB_PATH", str(tmp_path / "test.db"))
    configure_auth_env(monkeypatch)
    monkeypatch.setattr("app.api.routes.recognition.capture_preview_jpeg", lambda: None)

    with TestClient(create_app()) as client:
        login(client)
        response = client.get("/api/recognition/preview")

    assert response.status_code == 503


def test_preview_stream_returns_mjpeg(monkeypatch, tmp_path):
    monkeypatch.setenv("FACE_APP_DB_PATH", str(tmp_path / "test.db"))
    configure_auth_env(monkeypatch)

    def fake_stream():
        yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\nfake\r\n"

    monkeypatch.setattr("app.api.routes.recognition.stream_preview_frames", fake_stream)

    with TestClient(create_app()) as client:
        login(client)
        response = client.get("/api/recognition/preview/stream")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("multipart/x-mixed-replace")
    assert b"--frame" in response.content
