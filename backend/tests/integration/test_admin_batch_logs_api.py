import os
import pytest
from fastapi.testclient import TestClient
from app.main import app

ADMIN_KEY = os.getenv("FACE_ADMIN_API_KEY", "test-admin-key")

client = TestClient(app)

def test_admin_batch_logs_auth_required():
    resp = client.get("/api/admin/batch-logs/")
    assert resp.status_code == 401
    assert "admin" in resp.json()["detail"].lower()

def test_admin_batch_logs_success(monkeypatch):
    # Insert a fake log for test
    from app.core.database import get_connection
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO api_batch_logs (endpoint, items_count, success_count, error_count, client_ip, user_agent)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            ("/api/production/recognition/analyze-images", 2, 2, 0, "127.0.0.1", "pytest-agent"),
        )
        connection.commit()
    resp = client.get(
        "/api/admin/batch-logs/", headers={"x-admin-api-key": ADMIN_KEY}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "logs" in data
    assert data["total"] >= 1
    assert any(log["user_agent"] == "pytest-agent" for log in data["logs"])

def test_admin_batch_logs_filter(monkeypatch):
    resp = client.get(
        "/api/admin/batch-logs/?endpoint=/api/production/recognition/analyze-images",
        headers={"x-admin-api-key": ADMIN_KEY},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert all(log["endpoint"] == "/api/production/recognition/analyze-images" for log in data["logs"])
