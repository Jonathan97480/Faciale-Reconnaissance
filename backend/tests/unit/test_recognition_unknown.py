import json
import sqlite3

from app.core.database import get_connection, init_db
from app.core.schemas import RecognitionResult
from app.services.recognition_service import (
    get_detection_history,
    get_latest_detection,
    invalidate_face_reference_cache,
    recognize_face,
    save_detection,
)


def _insert_face_with_embedding(name: str, embedding: list[float]) -> None:
    with get_connection() as conn:
        cursor = conn.execute("INSERT INTO face_profiles (name) VALUES (?)", (name,))
        conn.execute(
            "INSERT INTO face_embeddings (face_id, encoding_json) VALUES (?, ?)",
            (cursor.lastrowid, json.dumps(embedding)),
        )
        conn.commit()


def test_returns_inconnu_when_embedding_is_missing(monkeypatch, tmp_path):
    monkeypatch.setenv("FACE_APP_DB_PATH", str(tmp_path / "test.db"))
    init_db()
    invalidate_face_reference_cache()

    result = recognize_face(None)

    assert result.status == "inconnu"
    assert result.face_id is None


def test_returns_inconnu_when_no_faces_enrolled(monkeypatch, tmp_path):
    monkeypatch.setenv("FACE_APP_DB_PATH", str(tmp_path / "test.db"))
    init_db()
    invalidate_face_reference_cache()

    result = recognize_face([0.1] * 128)

    assert result.status == "inconnu"


def test_returns_reconnu_when_match_above_threshold(monkeypatch, tmp_path):
    monkeypatch.setenv("FACE_APP_DB_PATH", str(tmp_path / "test.db"))
    init_db()
    invalidate_face_reference_cache()

    reference = [0.0] * 128
    _insert_face_with_embedding("Alice", reference)

    result = recognize_face(reference)

    assert result.status == "reconnu"
    assert result.face_name == "Alice"


def test_returns_inconnu_when_score_below_threshold(monkeypatch, tmp_path):
    monkeypatch.setenv("FACE_APP_DB_PATH", str(tmp_path / "test.db"))
    init_db()
    invalidate_face_reference_cache()

    with get_connection() as conn:
        conn.execute(
            "UPDATE config SET value = ? WHERE key = ?",
            ("0.9999", "match_threshold"),
        )
        conn.commit()
    _insert_face_with_embedding("Alice", [0.0] * 128)

    result = recognize_face([0.5] * 128)

    assert result.status == "inconnu"


def test_face_reference_cache_avoids_repeated_face_queries(monkeypatch, tmp_path):
    monkeypatch.setenv("FACE_APP_DB_PATH", str(tmp_path / "test.db"))
    init_db()
    invalidate_face_reference_cache()

    reference = [0.0] * 128
    _insert_face_with_embedding("Alice", reference)

    query_count = {"faces": 0}
    original_get_connection = get_connection

    class CountingConnection:
        def __init__(self, connection: sqlite3.Connection) -> None:
            self._connection = connection

        def execute(self, sql, params=()):
            if "SELECT fp.id, fp.name, fe.encoding_json" in sql:
                query_count["faces"] += 1
            return self._connection.execute(sql, params)

        def __getattr__(self, name):
            return getattr(self._connection, name)

        def __enter__(self):
            self._connection.__enter__()
            return self

        def __exit__(self, exc_type, exc, tb):
            return self._connection.__exit__(exc_type, exc, tb)

    def counting_get_connection():
        return CountingConnection(original_get_connection())

    monkeypatch.setattr(
        "app.services.recognition_service.get_connection",
        counting_get_connection,
    )

    first = recognize_face(reference)
    second = recognize_face(reference)

    assert first.status == "reconnu"
    assert second.status == "reconnu"
    assert query_count["faces"] == 1


def test_returns_best_matching_face_when_multiple_references_exist(monkeypatch, tmp_path):
    monkeypatch.setenv("FACE_APP_DB_PATH", str(tmp_path / "test.db"))
    init_db()
    invalidate_face_reference_cache()

    with get_connection() as conn:
        conn.execute(
            "UPDATE config SET value = ? WHERE key = ?",
            ("0.5", "match_threshold"),
        )
        conn.commit()

    best_reference = [1.0] + ([0.0] * 127)
    weaker_reference = [0.7, 0.7] + ([0.0] * 126)
    _insert_face_with_embedding("Best Match", best_reference)
    _insert_face_with_embedding("Weaker Match", weaker_reference)

    result = recognize_face(best_reference)

    assert result.status == "reconnu"
    assert result.face_name == "Best Match"
    assert result.score is not None
    assert result.score > 0.99


def test_ignores_invalid_or_empty_embeddings_loaded_from_db(monkeypatch, tmp_path):
    monkeypatch.setenv("FACE_APP_DB_PATH", str(tmp_path / "test.db"))
    init_db()
    invalidate_face_reference_cache()

    with get_connection() as conn:
        invalid_id = conn.execute(
            "INSERT INTO face_profiles (name) VALUES (?)",
            ("Invalid JSON",),
        ).lastrowid
        empty_id = conn.execute(
            "INSERT INTO face_profiles (name) VALUES (?)",
            ("Empty Reference",),
        ).lastrowid
        valid_id = conn.execute(
            "INSERT INTO face_profiles (name) VALUES (?)",
            ("Valid Reference",),
        ).lastrowid
        conn.execute(
            "INSERT INTO face_embeddings (face_id, encoding_json) VALUES (?, ?)",
            (invalid_id, "{not-json}"),
        )
        conn.execute(
            "INSERT INTO face_embeddings (face_id, encoding_json) VALUES (?, ?)",
            (empty_id, json.dumps([])),
        )
        conn.execute(
            "INSERT INTO face_embeddings (face_id, encoding_json) VALUES (?, ?)",
            (valid_id, json.dumps([0.3] * 128)),
        )
        conn.commit()

    result = recognize_face([0.3] * 128)

    assert result.status == "reconnu"
    assert result.face_name == "Valid Reference"


def test_save_detection_uses_best_recognized_face_as_primary(monkeypatch, tmp_path):
    monkeypatch.setenv("FACE_APP_DB_PATH", str(tmp_path / "test.db"))
    init_db()
    invalidate_face_reference_cache()

    save_detection(
        [
            recognize_face(None),
            RecognitionResult(
                status="reconnu",
                face_id=7,
                face_name="Alice",
                score=0.92,
            ),
            RecognitionResult(
                status="reconnu",
                face_id=8,
                face_name="Bob",
                score=0.81,
            ),
        ]
    )

    latest = get_latest_detection()

    assert latest is not None
    assert latest["status"] == "reconnu"
    assert latest["face_id"] == 7
    assert latest["score"] == 0.92
    assert latest["faces_count"] == 3


def test_detection_history_limits_and_preserves_unknown_fallback(monkeypatch, tmp_path):
    monkeypatch.setenv("FACE_APP_DB_PATH", str(tmp_path / "test.db"))
    init_db()
    invalidate_face_reference_cache()

    save_detection([])
    unknown_entry = get_latest_detection()
    for index in range(60):
        save_detection(
            [
                RecognitionResult(
                    status="reconnu",
                    face_id=index + 1,
                    face_name=f"Face-{index}",
                    score=0.7,
                )
            ]
        )

    history = get_detection_history(limit=100)

    assert unknown_entry is not None
    assert unknown_entry["status"] == "inconnu"
    assert unknown_entry["faces"][0]["status"] == "inconnu"
    assert len(history) == 50
    assert history[0]["face_id"] == 60
    assert history[-1]["face_id"] == 11
