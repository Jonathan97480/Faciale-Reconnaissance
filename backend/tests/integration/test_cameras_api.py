from fastapi.testclient import TestClient

from app.main import create_app
from app.services.camera_event_log_service import log_camera_event


def test_discover_onvif_endpoint(monkeypatch, tmp_path):
    monkeypatch.setenv("FACE_APP_DB_PATH", str(tmp_path / "test.db"))
    app = create_app()

    monkeypatch.setattr(
        "app.api.routes.cameras.discover_onvif_devices",
        lambda timeout_seconds: [{"ip": "192.168.1.20", "port": 3702, "xaddrs": [], "scopes": ""}],
    )

    with TestClient(app) as client:
        response = client.get("/api/cameras/onvif/discover?timeout_seconds=1")
        assert response.status_code == 200
        payload = response.json()
        assert payload["count"] == 1
        assert payload["devices"][0]["ip"] == "192.168.1.20"


def test_camera_events_endpoint(monkeypatch, tmp_path):
    monkeypatch.setenv("FACE_APP_DB_PATH", str(tmp_path / "test.db"))
    app = create_app()

    with TestClient(app) as client:
        log_camera_event("rtsp://cam1", "error", "read failed")
        response = client.get("/api/cameras/events?limit=10")
        assert response.status_code == 200
        events = response.json()["events"]
        assert len(events) >= 1
        assert events[0]["source"] == "rtsp://cam1"


def test_camera_profiles_resolved_endpoint(monkeypatch, tmp_path):
    monkeypatch.setenv("FACE_APP_DB_PATH", str(tmp_path / "test.db"))
    app = create_app()

    with TestClient(app) as client:
        payload = {
            "detection_interval_seconds": 3,
            "match_threshold": 0.6,
            "camera_index": 0,
            "camera_source": "",
            "network_camera_sources": [],
            "network_camera_profiles": [
                {
                    "name": "Main RTSP",
                    "protocol": "rtsp",
                    "host": "192.168.1.30",
                    "port": 554,
                    "path": "/stream1",
                    "username": "admin",
                    "password": "secret",
                    "onvif_url": "",
                    "enabled": True,
                }
            ],
            "multi_camera_cycle_budget_seconds": 2,
            "enroll_frames_count": 5,
            "face_crop_padding_ratio": 0.2,
        }
        client.put("/api/config", json=payload)
        response = client.get("/api/cameras/profiles/resolved")
        assert response.status_code == 200
        profiles = response.json()["profiles"]
        assert len(profiles) == 1
        assert profiles[0]["name"] == "Main RTSP"
        assert "@" not in profiles[0]["stream_url"]
