import json
import sqlite3

from app.core.database import get_connection, init_db
from app.services.recognition_service import (
    invalidate_face_reference_cache,
    recognize_face,
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
