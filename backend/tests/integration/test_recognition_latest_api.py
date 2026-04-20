import json

from fastapi.testclient import TestClient

from app.core.database import get_connection
from app.main import create_app
from app.services.detection_loop import detection_loop
from tests.auth_utils import configure_auth_env, login


def _insert_face_with_embedding(connection, name: str, embedding: list[float]) -> int:
    cursor = connection.execute("INSERT INTO face_profiles (name) VALUES (?)", (name,))
    connection.execute(
        "INSERT INTO face_embeddings (face_id, encoding_json) VALUES (?, ?)",
        (cursor.lastrowid, json.dumps(embedding)),
    )
    return cursor.lastrowid


def test_latest_detection_returns_all_detected_faces(monkeypatch, tmp_path):
    monkeypatch.setenv("FACE_APP_DB_PATH", str(tmp_path / "test.db"))
    configure_auth_env(monkeypatch)

    with TestClient(create_app()) as client:
        login(client)
        detection_loop.stop()
        with get_connection() as conn:
            _insert_face_with_embedding(conn, "Alice", [0.1] * 512)
            _insert_face_with_embedding(conn, "Bob", [0.2] * 512)
            conn.execute(
                """
                INSERT INTO detections (status, face_id, score, faces_json)
                VALUES (?, ?, ?, ?)
                """,
                (
                    "reconnu",
                    1,
                    0.91,
                    json.dumps(
                        [
                            {
                                "status": "reconnu",
                                "face_id": 1,
                                "face_name": "Alice",
                                "score": 0.91,
                            },
                            {
                                "status": "inconnu",
                                "face_id": None,
                                "face_name": None,
                                "score": None,
                            },
                        ]
                    ),
                ),
            )
            conn.commit()

        response = client.get("/api/recognition/latest")

    assert response.status_code == 200
    payload = response.json()["detection"]
    assert payload["faces_count"] == 2
    assert payload["faces"][0]["face_name"] == "Alice"
    assert payload["faces"][1]["status"] == "inconnu"


def test_latest_detection_falls_back_to_legacy_columns(monkeypatch, tmp_path):
    monkeypatch.setenv("FACE_APP_DB_PATH", str(tmp_path / "test.db"))
    configure_auth_env(monkeypatch)

    with TestClient(create_app()) as client:
        login(client)
        detection_loop.stop()
        with get_connection() as conn:
            _insert_face_with_embedding(conn, "Charlie", [0.3] * 512)
            conn.execute(
                """
                INSERT INTO detections (status, face_id, score, faces_json)
                VALUES (?, ?, ?, ?)
                """,
                ("reconnu", 1, 0.88, None),
            )
            conn.commit()

        response = client.get("/api/recognition/latest")

    assert response.status_code == 200
    payload = response.json()["detection"]
    assert payload["faces_count"] == 1
    assert payload["faces"][0]["face_name"] == "Charlie"


def test_detection_history_returns_latest_10_entries(monkeypatch, tmp_path):
    monkeypatch.setenv("FACE_APP_DB_PATH", str(tmp_path / "test.db"))
    configure_auth_env(monkeypatch)

    with TestClient(create_app()) as client:
        login(client)
        detection_loop.stop()
        with get_connection() as conn:
            _insert_face_with_embedding(conn, "Agent", [0.4] * 512)
            for index in range(12):
                conn.execute(
                    """
                    INSERT INTO detections (status, face_id, score, faces_json)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        "reconnu",
                        1,
                        0.8,
                        json.dumps(
                            [
                                {
                                    "status": "reconnu",
                                    "face_id": 1,
                                    "face_name": f"Agent-{index}",
                                    "score": 0.8,
                                }
                            ]
                        ),
                    ),
                )
            conn.commit()

        response = client.get("/api/recognition/history")

    assert response.status_code == 200
    detections = response.json()["detections"]
    assert len(detections) == 10
    assert detections[0]["faces"][0]["face_name"] == "Agent-11"
    assert detections[-1]["faces"][0]["face_name"] == "Agent-2"
