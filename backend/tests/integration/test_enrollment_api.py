import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from tests.auth_utils import configure_auth_env, login


def test_enroll_face_no_webcam(monkeypatch, tmp_path):
    """When webcam is unavailable, enrollment must return 503."""
    monkeypatch.setenv("FACE_APP_DB_PATH", str(tmp_path / "test.db"))
    configure_auth_env(monkeypatch)

    monkeypatch.setattr("app.api.routes.enrollment.capture_frame", lambda: None)

    with TestClient(create_app()) as client:
        login(client)
        response = client.post("/api/faces/enroll", json={"name": "Alice"})
    assert response.status_code == 503


def test_enroll_face_no_face_detected(monkeypatch, tmp_path):
    """When webcam returns frames with no face, enrollment must return 422."""
    monkeypatch.setenv("FACE_APP_DB_PATH", str(tmp_path / "test.db"))
    configure_auth_env(monkeypatch)

    monkeypatch.setattr("app.api.routes.enrollment.capture_frame", lambda: object())
    monkeypatch.setattr(
        "app.api.routes.enrollment.extract_averaged_embedding", lambda _: None
    )

    with TestClient(create_app()) as client:
        login(client)
        response = client.post("/api/faces/enroll", json={"name": "Alice"})
    assert response.status_code == 422


def test_enroll_face_success(monkeypatch, tmp_path):
    """When faces are detected across frames, enrollment persists the averaged embedding."""
    monkeypatch.setenv("FACE_APP_DB_PATH", str(tmp_path / "test.db"))
    configure_auth_env(monkeypatch)
    fake_embedding = [0.1] * 512

    monkeypatch.setattr("app.api.routes.enrollment.capture_frame", lambda: object())
    monkeypatch.setattr(
        "app.api.routes.enrollment.extract_averaged_embedding",
        lambda _: fake_embedding,
    )

    with TestClient(create_app()) as client:
        login(client)
        response = client.post("/api/faces/enroll", json={"name": "Alice"})
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Alice"
    assert data["has_encoding"] is True
