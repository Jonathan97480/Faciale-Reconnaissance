from fastapi.testclient import TestClient

from app.main import create_app
from tests.auth_utils import configure_auth_env, login

def test_admin_batch_logs_auth_required(monkeypatch, tmp_path):
    monkeypatch.setenv("FACE_APP_DB_PATH", str(tmp_path / "test.db"))
    configure_auth_env(monkeypatch)
    app = create_app()
    with TestClient(app) as client:
        resp = client.get("/api/admin/batch-logs/")
    assert resp.status_code == 401
    assert "auth" in resp.json()["detail"].lower()

def test_admin_batch_logs_success(monkeypatch):
    configure_auth_env(monkeypatch)
    from app.core.database import get_connection

    app = create_app()
    with TestClient(app) as client:
        login(client)
        with get_connection() as connection:
            connection.execute(
                """
                INSERT INTO api_batch_logs (endpoint, items_count, success_count, error_count, client_ip, user_agent)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                ("/api/production/recognition/analyze-images", 2, 2, 0, "127.0.0.1", "pytest-agent"),
            )
            connection.commit()
        resp = client.get("/api/admin/batch-logs/")
        assert resp.status_code == 200
        data = resp.json()
        assert "logs" in data
        assert data["total"] >= 1
        assert any(log["user_agent"] == "pytest-agent" for log in data["logs"])

def test_admin_batch_logs_filter(monkeypatch):
    configure_auth_env(monkeypatch)
    app = create_app()
    with TestClient(app) as client:
        login(client)
        resp = client.get("/api/admin/batch-logs/?endpoint=/api/production/recognition/analyze-images")
        assert resp.status_code == 200
        data = resp.json()
        assert all(log["endpoint"] == "/api/production/recognition/analyze-images" for log in data["logs"])
