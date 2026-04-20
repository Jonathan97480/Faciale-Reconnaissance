from fastapi.testclient import TestClient

from app.main import create_app
from tests.auth_utils import configure_auth_env, login


def test_preview_returns_jpeg_when_camera_available(monkeypatch, tmp_path):
    monkeypatch.setenv("FACE_APP_DB_PATH", str(tmp_path / "test.db"))
    configure_auth_env(monkeypatch)
    monkeypatch.setattr(
        "app.api.routes.recognition.capture_preview_jpeg",
        lambda: b"fake-jpeg-bytes",
    )

    with TestClient(create_app()) as client:
        login(client)
        response = client.get("/api/recognition/preview")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
    assert response.content == b"fake-jpeg-bytes"


def test_preview_returns_503_when_camera_unavailable(monkeypatch, tmp_path):
    monkeypatch.setenv("FACE_APP_DB_PATH", str(tmp_path / "test.db"))
    configure_auth_env(monkeypatch)
    monkeypatch.setattr("app.api.routes.recognition.capture_preview_jpeg", lambda: None)

    with TestClient(create_app()) as client:
        login(client)
        response = client.get("/api/recognition/preview")

    assert response.status_code == 503


def test_preview_stream_returns_mjpeg(monkeypatch, tmp_path):
    monkeypatch.setenv("FACE_APP_DB_PATH", str(tmp_path / "test.db"))
    configure_auth_env(monkeypatch)

    def fake_stream():
        yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\nfake\r\n"

    monkeypatch.setattr("app.api.routes.recognition.stream_preview_frames", fake_stream)

    with TestClient(create_app()) as client:
        login(client)
        response = client.get("/api/recognition/preview/stream")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("multipart/x-mixed-replace")
    assert b"--frame" in response.content


def test_loop_status_includes_performance_metrics(monkeypatch, tmp_path):
    monkeypatch.setenv("FACE_APP_DB_PATH", str(tmp_path / "test.db"))
    configure_auth_env(monkeypatch)

    with TestClient(create_app()) as client:
        login(client)
        response = client.get("/api/recognition/loop/status")

    assert response.status_code == 200
    payload = response.json()
    assert "loop" in payload
    assert "performance" in payload["loop"]
    performance = payload["loop"]["performance"]
    assert "local_camera" in payload
    assert set(payload["local_camera"]).issuperset(
        {
            "source",
            "is_running",
            "has_frame",
            "latest_frame_at",
            "last_detection_at",
            "last_error",
            "consecutive_failures",
            "last_read_duration_ms",
            "last_connect_at",
        }
    )
    assert set(performance).issuperset(
        {
            "capture_ms",
            "inference_ms",
            "db_ms",
            "cycle_ms",
            "processed_sources",
            "results_count",
            "updated_at",
        }
    )


def test_live_websocket_returns_monitoring_snapshot(monkeypatch, tmp_path):
    monkeypatch.setenv("FACE_APP_DB_PATH", str(tmp_path / "test.db"))
    configure_auth_env(monkeypatch)
    monkeypatch.setattr(
        "app.api.routes.recognition.current_capture_settings",
        lambda: {"camera_index": 0},
    )
    monkeypatch.setattr(
        "app.api.routes.recognition.current_camera_runtime_status",
        lambda: {"source": "local", "has_frame": True, "last_error": None},
    )
    monkeypatch.setattr(
        "app.api.routes.recognition.network_camera_pool_status",
        lambda: {"sources": [{"source": "rtsp://cam"}]},
    )
    monkeypatch.setattr(
        "app.api.routes.recognition.build_camera_alerts",
        lambda **_: [{"source": "rtsp://cam", "level": "warn", "type": "latency"}],
    )
    monkeypatch.setattr(
        "app.api.routes.recognition.get_latest_detection",
        lambda: {"id": 9, "status": "inconnu", "faces": [], "faces_count": 0},
    )
    monkeypatch.setattr(
        "app.api.routes.recognition.get_detection_history",
        lambda limit: [{"id": 8, "faces_count": 1, "faces": []}] if limit == 10 else [],
    )

    with TestClient(create_app()) as client:
        login(client)
        with client.websocket_connect("/api/recognition/live") as websocket:
            payload = websocket.receive_json()

    assert payload["capture_settings"]["camera_index"] == 0
    assert payload["local_camera"]["source"] == "local"
    assert payload["network_cameras"]["sources"][0]["source"] == "rtsp://cam"
    assert payload["camera_alerts"][0]["type"] == "latency"
    assert payload["latest_detection"]["id"] == 9
    assert payload["history"][0]["id"] == 8
