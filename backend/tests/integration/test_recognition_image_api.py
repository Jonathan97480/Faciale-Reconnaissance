from fastapi.testclient import TestClient

from app.main import create_app


def test_analyze_image_returns_multi_face_json(monkeypatch, tmp_path):
    monkeypatch.setenv("FACE_APP_DB_PATH", str(tmp_path / "test.db"))

    monkeypatch.setattr(
        "app.api.routes.recognition.analyze_image_bytes",
        lambda _: {
            "faces_count": 2,
            "faces": [
                {
                    "status": "inconnu",
                    "face_id": None,
                    "face_name": None,
                    "score": None,
                    "box": {"x1": 10, "y1": 12, "x2": 40, "y2": 54},
                    "expanded_box": {"x1": 6, "y1": 8, "x2": 44, "y2": 58},
                    "face_image_base64": "ZmFrZQ==",
                },
                {
                    "status": "reconnu",
                    "face_id": 7,
                    "face_name": "Alice",
                    "score": 0.91,
                    "box": {"x1": 60, "y1": 20, "x2": 95, "y2": 64},
                    "expanded_box": {"x1": 54, "y1": 14, "x2": 99, "y2": 68},
                    "face_image_base64": "ZmFrZTI=",
                },
            ],
        },
    )

    with TestClient(create_app()) as client:
        response = client.post(
            "/api/recognition/analyze-image",
            content=b"fake-image-bytes",
            headers={"Content-Type": "image/jpeg"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["faces_count"] == 2
    assert payload["faces"][0]["status"] == "inconnu"
    assert payload["faces"][1]["face_name"] == "Alice"


def test_analyze_image_rejects_invalid_content_type(monkeypatch, tmp_path):
    monkeypatch.setenv("FACE_APP_DB_PATH", str(tmp_path / "test.db"))

    with TestClient(create_app()) as client:
        response = client.post(
            "/api/recognition/analyze-image",
            content=b"not-an-image",
            headers={"Content-Type": "application/json"},
        )

    assert response.status_code == 415


def test_analyze_image_returns_400_when_image_invalid(monkeypatch, tmp_path):
    monkeypatch.setenv("FACE_APP_DB_PATH", str(tmp_path / "test.db"))

    def fail(_: bytes):
        raise ValueError("Image invalide")

    monkeypatch.setattr("app.api.routes.recognition.analyze_image_bytes", fail)

    with TestClient(create_app()) as client:
        response = client.post(
            "/api/recognition/analyze-image",
            content=b"bad-image",
            headers={"Content-Type": "image/jpeg"},
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "Image invalide"


def test_analyze_images_batch_handles_success_and_errors(monkeypatch, tmp_path):
    monkeypatch.setenv("FACE_APP_DB_PATH", str(tmp_path / "test.db"))

    def fake_analyze(image_bytes: bytes):
        if image_bytes == b"bad":
            raise ValueError("Image invalide")
        return {
            "faces_count": 1,
            "faces": [
                {
                    "status": "inconnu",
                    "face_id": None,
                    "face_name": None,
                    "score": None,
                    "box": {"x1": 1, "y1": 2, "x2": 10, "y2": 12},
                    "expanded_box": {"x1": 0, "y1": 1, "x2": 12, "y2": 14},
                    "face_image_base64": "ZmFrZQ==",
                }
            ],
        }

    monkeypatch.setattr("app.api.routes.recognition.analyze_image_bytes", fake_analyze)

    with TestClient(create_app()) as client:
        response = client.post(
            "/api/recognition/analyze-images",
            json={
                "items": [
                    {
                        "filename": "first.jpg",
                        "content_type": "image/jpeg",
                        "image_base64": "Z29vZA==",
                    },
                    {
                        "filename": "bad.jpg",
                        "content_type": "image/jpeg",
                        "image_base64": "YmFk",
                    },
                    {
                        "filename": "wrong.txt",
                        "content_type": "text/plain",
                        "image_base64": "eA==",
                    },
                ]
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["items_count"] == 3
    assert payload["success_count"] == 1
    assert payload["error_count"] == 2
    assert payload["items"][0]["ok"] is True
    assert payload["items"][1]["error"] == "Image invalide"
    assert payload["items"][2]["error"] == "Content-Type image attendu"


def test_analyze_images_batch_rejects_empty_request(monkeypatch, tmp_path):
    monkeypatch.setenv("FACE_APP_DB_PATH", str(tmp_path / "test.db"))

    with TestClient(create_app()) as client:
        response = client.post("/api/recognition/analyze-images", json={"items": []})

    assert response.status_code == 422


def test_analyze_images_batch_rejects_invalid_base64(monkeypatch, tmp_path):
    monkeypatch.setenv("FACE_APP_DB_PATH", str(tmp_path / "test.db"))

    with TestClient(create_app()) as client:
        response = client.post(
            "/api/recognition/analyze-images",
            json={
                "items": [
                    {
                        "filename": "broken.jpg",
                        "content_type": "image/jpeg",
                        "image_base64": "%%%",
                    }
                ]
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success_count"] == 0
    assert payload["error_count"] == 1
    assert payload["items"][0]["error"] == "image_base64 invalide"
