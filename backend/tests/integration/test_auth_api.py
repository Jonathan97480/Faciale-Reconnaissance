from fastapi.testclient import TestClient

from app.main import create_app
from tests.auth_utils import AUTH_USERNAME, configure_auth_env, login


def test_sensitive_route_requires_authentication(monkeypatch, tmp_path):
    monkeypatch.setenv("FACE_APP_DB_PATH", str(tmp_path / "test.db"))
    configure_auth_env(monkeypatch)

    with TestClient(create_app()) as client:
        response = client.get("/api/config")

    assert response.status_code == 401


def test_login_sets_cookie_and_exposes_current_user(monkeypatch, tmp_path):
    monkeypatch.setenv("FACE_APP_DB_PATH", str(tmp_path / "test.db"))
    configure_auth_env(monkeypatch)

    with TestClient(create_app()) as client:
        login_response = login(client)
        current_user = client.get("/api/auth/me")

    assert login_response.cookies.get("face_access_token")
    assert current_user.status_code == 200
    assert current_user.json()["username"] == AUTH_USERNAME


def test_login_rejects_invalid_credentials(monkeypatch, tmp_path):
    monkeypatch.setenv("FACE_APP_DB_PATH", str(tmp_path / "test.db"))
    configure_auth_env(monkeypatch)

    with TestClient(create_app()) as client:
        response = client.post(
            "/api/auth/login",
            data={"username": AUTH_USERNAME, "password": "wrong-password"},
        )

    assert response.status_code == 401
