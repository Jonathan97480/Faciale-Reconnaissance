from fastapi.testclient import TestClient

from app.main import create_app
from tests.auth_utils import configure_auth_env, login


def test_faces_api_returns_autres_infos_field(monkeypatch, tmp_path):
    monkeypatch.setenv("FACE_APP_DB_PATH", str(tmp_path / "test.db"))
    configure_auth_env(monkeypatch)

    with TestClient(create_app()) as client:
        login(client)
        response = client.post(
            "/api/faces",
            json={
                "name": "Alice",
                "autres_infos": "Texte libre",
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["autres_infos"] == "Texte libre"
    assert "autres_infos_html" not in payload


def test_faces_api_accepts_legacy_autres_infos_html_input(monkeypatch, tmp_path):
    monkeypatch.setenv("FACE_APP_DB_PATH", str(tmp_path / "test.db"))
    configure_auth_env(monkeypatch)

    with TestClient(create_app()) as client:
        login(client)
        response = client.post(
            "/api/faces",
            json={
                "name": "Bob",
                "autres_infos_html": "<b>legacy</b>",
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["autres_infos"] == "<b>legacy</b>"
    assert "autres_infos_html" not in payload
