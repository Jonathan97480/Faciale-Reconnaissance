from fastapi.testclient import TestClient

from app.core.database import get_connection
from app.main import create_app
from app.services.rate_limit_service import production_rate_limiter


def test_production_endpoint_requires_api_key(monkeypatch, tmp_path):
    monkeypatch.setenv("FACE_APP_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("FACE_API_KEY", "secret-key")
    production_rate_limiter.reset()

    with TestClient(create_app()) as client:
        response = client.post(
            "/api/production/recognition/analyze-images",
            json={
                "items": [
                    {
                        "filename": "photo.jpg",
                        "content_type": "image/jpeg",
                        "image_base64": "Z29vZA==",
                    }
                ]
            },
        )

    assert response.status_code == 401


def test_production_endpoint_rejects_invalid_api_key(monkeypatch, tmp_path):
    monkeypatch.setenv("FACE_APP_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("FACE_API_KEY", "secret-key")
    production_rate_limiter.reset()

    with TestClient(create_app()) as client:
        response = client.post(
            "/api/production/recognition/analyze-images",
            json={
                "items": [
                    {
                        "filename": "photo.jpg",
                        "content_type": "image/jpeg",
                        "image_base64": "Z29vZA==",
                    }
                ]
            },
            headers={"x-api-key": "wrong-key"},
        )

    assert response.status_code == 401


def test_production_endpoint_logs_batch(monkeypatch, tmp_path):
    monkeypatch.setenv("FACE_APP_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("FACE_API_KEY", "secret-key")
    production_rate_limiter.reset()

    monkeypatch.setattr(
        "app.api.routes.production_recognition.analyze_image_bytes",
        lambda _: {
            "faces_count": 1,
            "faces": [
                {
                    "status": "inconnu",
                    "face_id": None,
                    "face_name": None,
                    "score": None,
                    "box": {"x1": 1, "y1": 1, "x2": 8, "y2": 8},
                    "expanded_box": {"x1": 0, "y1": 0, "x2": 10, "y2": 10},
                    "face_image_base64": "ZmFrZQ==",
                }
            ],
        },
    )

    with TestClient(create_app()) as client:
        response = client.post(
            "/api/production/recognition/analyze-images",
            json={
                "items": [
                    {
                        "filename": "photo.jpg",
                        "content_type": "image/jpeg",
                        "image_base64": "Z29vZA==",
                    },
                    {
                        "filename": "invalid.jpg",
                        "content_type": "image/jpeg",
                        "image_base64": "%%%",
                    },
                ]
            },
            headers={"x-api-key": "secret-key", "user-agent": "pytest-agent"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["items_count"] == 2
    assert payload["success_count"] == 1
    assert payload["error_count"] == 1

    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT endpoint, items_count, success_count, error_count, user_agent
            FROM api_batch_logs
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()

    assert row is not None
    assert row["endpoint"] == "/api/production/recognition/analyze-images"
    assert row["items_count"] == 2
    assert row["success_count"] == 1
    assert row["error_count"] == 1
    assert row["user_agent"] == "pytest-agent"


def test_production_endpoint_rate_limits_requests(monkeypatch, tmp_path):
    monkeypatch.setenv("FACE_APP_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("FACE_API_KEY", "secret-key")
    production_rate_limiter.reset()

    monkeypatch.setattr(
        "app.api.routes.production_recognition.analyze_image_bytes",
        lambda _: {
            "faces_count": 0,
            "faces": [],
        },
    )

    with TestClient(create_app()) as client:
        with get_connection() as connection:
            connection.execute(
                "UPDATE config SET value = ? WHERE key = ?",
                ("60", "production_api_rate_limit_window_seconds"),
            )
            connection.execute(
                "UPDATE config SET value = ? WHERE key = ?",
                ("1", "production_api_rate_limit_max_requests"),
            )
            connection.commit()

        payload = {
            "items": [
                {
                    "filename": "photo.jpg",
                    "content_type": "image/jpeg",
                    "image_base64": "Z29vZA==",
                }
            ]
        }
        headers = {"x-api-key": "secret-key"}

        first = client.post("/api/production/recognition/analyze-images", json=payload, headers=headers)
        second = client.post("/api/production/recognition/analyze-images", json=payload, headers=headers)

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.headers["retry-after"] == "60"
