from fastapi.testclient import TestClient

from app.main import create_app


def test_get_and_update_config(monkeypatch, tmp_path):
    monkeypatch.setenv("FACE_APP_DB_PATH", str(tmp_path / "test.db"))
    app = create_app()

    with TestClient(app) as client:
        initial = client.get("/api/config")
        assert initial.status_code == 200
        assert initial.json()["detection_interval_seconds"] == 3

        payload = {
            "detection_interval_seconds": 5,
            "match_threshold": 0.72,
            "camera_index": 1,
            "enroll_frames_count": 8,
            "face_crop_padding_ratio": 0.25,
        }
        updated = client.put("/api/config", json=payload)
        assert updated.status_code == 200
        assert updated.json() == payload

        round_trip = client.get("/api/config")
        assert round_trip.status_code == 200
        assert round_trip.json() == payload
