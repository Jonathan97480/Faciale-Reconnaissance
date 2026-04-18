import pytest
from fastapi.testclient import TestClient

from app.main import create_app


def test_delete_face(monkeypatch, tmp_path):
    """Deleting an existing face returns 204; deleting again returns 404."""
    monkeypatch.setenv("FACE_APP_DB_PATH", str(tmp_path / "test.db"))

    with TestClient(create_app()) as client:
        created = client.post("/api/faces", json={"name": "Bob", "encoding": None})
        assert created.status_code == 200
        face_id = created.json()["id"]

        first_delete = client.delete(f"/api/faces/{face_id}")
        assert first_delete.status_code == 204

        second_delete = client.delete(f"/api/faces/{face_id}")
        assert second_delete.status_code == 404
