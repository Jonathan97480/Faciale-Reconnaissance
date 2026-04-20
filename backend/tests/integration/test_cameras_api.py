from fastapi.testclient import TestClient

from app.main import create_app
from app.services.camera_event_log_service import log_camera_event
from tests.auth_utils import configure_auth_env, login


def test_discover_onvif_endpoint(monkeypatch, tmp_path):
    monkeypatch.setenv("FACE_APP_DB_PATH", str(tmp_path / "test.db"))
    configure_auth_env(monkeypatch)
    app = create_app()

    monkeypatch.setattr(
        "app.api.routes.cameras.discover_onvif_devices",
        lambda timeout_seconds: [{"ip": "192.168.1.20", "port": 3702, "xaddrs": [], "scopes": ""}],
    )

    with TestClient(app) as client:
        login(client)
        response = client.get("/api/cameras/onvif/discover?timeout_seconds=1")
        assert response.status_code == 200
        payload = response.json()
        assert payload["count"] == 1
        assert payload["devices"][0]["ip"] == "192.168.1.20"


def test_camera_events_endpoint(monkeypatch, tmp_path):
    monkeypatch.setenv("FACE_APP_DB_PATH", str(tmp_path / "test.db"))
    configure_auth_env(monkeypatch)
    app = create_app()

    with TestClient(app) as client:
        login(client)
        log_camera_event("rtsp://cam1", "error", "read failed")
        response = client.get("/api/cameras/events?limit=10")
        assert response.status_code == 200
        events = response.json()["events"]
        assert len(events) >= 1
        assert events[0]["source"] == "rtsp://cam1"


def test_camera_profiles_resolved_endpoint(monkeypatch, tmp_path):
    monkeypatch.setenv("FACE_APP_DB_PATH", str(tmp_path / "test.db"))
    configure_auth_env(monkeypatch)
    app = create_app()

    with TestClient(app) as client:
        login(client)
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
            "inference_device_preference": "auto",
            "production_api_rate_limit_window_seconds": 60,
            "production_api_rate_limit_max_requests": 30,
        }
        client.put("/api/config", json=payload)
        response = client.get("/api/cameras/profiles/resolved")
        assert response.status_code == 200
        profiles = response.json()["profiles"]
        assert len(profiles) == 1
        assert profiles[0]["name"] == "Main RTSP"
        assert "@" not in profiles[0]["stream_url"]


def test_camera_alerts_endpoint(monkeypatch, tmp_path):
    monkeypatch.setenv("FACE_APP_DB_PATH", str(tmp_path / "test.db"))
    configure_auth_env(monkeypatch)
    app = create_app()
    monkeypatch.setattr(
        "app.api.routes.cameras.network_camera_pool_status",
        lambda: {
            "sources": [
                {
                    "source": "rtsp://cam1",
                    "has_frame": False,
                    "last_error": "Cannot open stream",
                    "last_read_duration_ms": 420.0,
                    "last_detection_at": None,
                }
            ]
        },
    )

    with TestClient(app) as client:
        login(client)
        response = client.get("/api/cameras/alerts")
        assert response.status_code == 200
        payload = response.json()
        assert payload["alerts_count"] >= 1
        assert payload["alerts"][0]["source"] == "rtsp://cam1"


def test_playback_start_direct_and_proxy(monkeypatch, tmp_path):
    monkeypatch.setenv("FACE_APP_DB_PATH", str(tmp_path / "test.db"))
    configure_auth_env(monkeypatch)
    app = create_app()

    with TestClient(app) as client:
        login(client)
        config_payload = {
            "detection_interval_seconds": 3,
            "match_threshold": 0.6,
            "camera_index": 0,
            "camera_source": "",
            "network_camera_sources": [],
            "network_camera_profiles": [
                {
                    "name": "HLS Cam",
                    "protocol": "hls",
                    "host": "cam.local",
                    "port": 80,
                    "path": "/stream.m3u8",
                    "username": "",
                    "password": "",
                    "onvif_url": "",
                    "enabled": True,
                },
                {
                    "name": "RTSP Cam",
                    "protocol": "rtsp",
                    "host": "192.168.1.44",
                    "port": 554,
                    "path": "/stream1",
                    "username": "admin",
                    "password": "admin",
                    "onvif_url": "",
                    "enabled": True,
                },
            ],
            "multi_camera_cycle_budget_seconds": 2,
            "enroll_frames_count": 5,
            "face_crop_padding_ratio": 0.2,
            "inference_device_preference": "auto",
            "production_api_rate_limit_window_seconds": 60,
            "production_api_rate_limit_max_requests": 30,
        }
        client.put("/api/config", json=config_payload)

        direct = client.post("/api/cameras/playback/start?profile_name=HLS%20Cam")
        assert direct.status_code == 200
        assert direct.json()["mode"] == "direct"

        monkeypatch.setattr(
            "app.api.routes.cameras.start_hls_session",
            lambda profile_name, source_url: {"id": "sess-123"},
        )
        proxy = client.post("/api/cameras/playback/start?profile_name=RTSP%20Cam")
        assert proxy.status_code == 200
        assert proxy.json()["mode"] == "hls_proxy"
