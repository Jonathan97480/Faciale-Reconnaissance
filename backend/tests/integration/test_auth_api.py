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


def test_bootstrap_status_requires_setup_when_no_admin_is_configured(monkeypatch, tmp_path):
    monkeypatch.setenv("FACE_APP_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.delenv("ADMIN_USERNAME", raising=False)
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    monkeypatch.delenv("JWT_SECRET", raising=False)

    with TestClient(create_app()) as client:
        response = client.get("/api/auth/bootstrap/status")

    assert response.status_code == 200
    assert response.json() == {"setup_required": True, "auth_source": "none"}


def test_bootstrap_creates_first_admin_and_opens_session(monkeypatch, tmp_path):
    monkeypatch.setenv("FACE_APP_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.delenv("ADMIN_USERNAME", raising=False)
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    monkeypatch.delenv("JWT_SECRET", raising=False)

    with TestClient(create_app()) as client:
        bootstrap = client.post(
            "/api/auth/bootstrap",
            json={"username": "rootadmin", "password": "motdepasse-fort"},
        )
        current_user = client.get("/api/auth/me")
        duplicate = client.post(
            "/api/auth/bootstrap",
            json={"username": "otheradmin", "password": "motdepasse-fort"},
        )

    assert bootstrap.status_code == 200
    assert bootstrap.cookies.get("face_access_token")
    assert current_user.status_code == 200
    assert current_user.json()["username"] == "rootadmin"
    assert duplicate.status_code == 409
