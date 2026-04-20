from fastapi.testclient import TestClient

from app.core.database import get_connection
from app.main import create_app
from tests.auth_utils import configure_auth_env, login


def test_get_and_update_config(monkeypatch, tmp_path):
    monkeypatch.setenv("FACE_APP_DB_PATH", str(tmp_path / "test.db"))
    configure_auth_env(monkeypatch)
    app = create_app()

    with TestClient(app) as client:
        login(client)
        initial = client.get("/api/config")
        assert initial.status_code == 200
        assert initial.json()["detection_interval_seconds"] == 3
        assert initial.json()["network_camera_sources"] == []
        assert initial.json()["network_camera_profiles"] == []
        assert initial.json()["multi_camera_cycle_budget_seconds"] == 2
        assert initial.json()["inference_device_preference"] == "auto"
        assert initial.json()["inference_device_active"] in {"cpu", "cuda"}

        payload = {
            "detection_interval_seconds": 5,
            "match_threshold": 0.72,
            "camera_index": 1,
            "camera_source": "",
            "network_camera_sources": [
                "rtsp://camera-1",
                "rtsp://camera-2",
            ],
            "network_camera_profiles": [
                {
                    "name": "Cam RTSP Standard",
                    "protocol": "rtsp",
                    "host": "192.168.1.10",
                    "port": 554,
                    "path": "/stream1",
                    "username": "admin",
                    "password": "admin",
                    "onvif_url": "",
                    "enabled": True,
                }
            ],
            "multi_camera_cycle_budget_seconds": 2,
            "enroll_frames_count": 8,
            "face_crop_padding_ratio": 0.25,
            "inference_device_preference": "cpu",
        }
        updated = client.put("/api/config", json=payload)
        assert updated.status_code == 200
        expected = dict(payload)
        expected["inference_device_active"] = "cpu"
        expected["network_camera_profiles"] = [
            {
                **payload["network_camera_profiles"][0],
                "password": "",
                "has_password": True,
            }
        ]
        assert updated.json() == expected

        round_trip = client.get("/api/config")
        assert round_trip.status_code == 200
        assert round_trip.json() == expected

        with get_connection() as connection:
            row = connection.execute(
                "SELECT value FROM config WHERE key = 'network_camera_profiles_json'"
            ).fetchone()
        assert row is not None
        raw_value = str(row["value"])
        assert "secret" not in raw_value
        assert "enc:v2:" in raw_value
