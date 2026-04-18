import json

import pytest

from app.core.database import get_connection, init_db
from app.services.recognition_service import recognize_face


def test_returns_inconnu_when_embedding_is_missing(monkeypatch, tmp_path):
    monkeypatch.setenv("FACE_APP_DB_PATH", str(tmp_path / "test.db"))
    init_db()

    result = recognize_face(None)

    assert result.status == "inconnu"
    assert result.face_id is None


def test_returns_inconnu_when_no_faces_enrolled(monkeypatch, tmp_path):
    monkeypatch.setenv("FACE_APP_DB_PATH", str(tmp_path / "test.db"))
    init_db()

    result = recognize_face([0.1] * 128)

    assert result.status == "inconnu"


def test_returns_reconnu_when_match_above_threshold(monkeypatch, tmp_path):
    monkeypatch.setenv("FACE_APP_DB_PATH", str(tmp_path / "test.db"))
    init_db()

    reference = [0.0] * 128
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO faces (name, encoding_json) VALUES (?, ?)",
            ("Alice", json.dumps(reference)),
        )
        conn.commit()

    result = recognize_face(reference)

    assert result.status == "reconnu"
    assert result.face_name == "Alice"


def test_returns_inconnu_when_score_below_threshold(monkeypatch, tmp_path):
    monkeypatch.setenv("FACE_APP_DB_PATH", str(tmp_path / "test.db"))
    init_db()

    with get_connection() as conn:
        conn.execute(
            "UPDATE config SET value = ? WHERE key = ?",
            ("0.9999", "match_threshold"),
        )
        conn.execute(
            "INSERT INTO faces (name, encoding_json) VALUES (?, ?)",
            ("Alice", json.dumps([0.0] * 128)),
        )
        conn.commit()

    result = recognize_face([0.5] * 128)

    assert result.status == "inconnu"

