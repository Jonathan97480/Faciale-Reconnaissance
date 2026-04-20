import sqlite3

from app.core.database import get_connection, init_db


def test_init_db_migrates_legacy_faces_table_and_drops_it(monkeypatch, tmp_path):
    db_path = tmp_path / "legacy.db"
    monkeypatch.setenv("FACE_APP_DB_PATH", str(db_path))

    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE faces (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                encoding_json TEXT,
                adresse TEXT,
                metier TEXT,
                lieu_naissance TEXT,
                age INTEGER,
                annee_naissance INTEGER,
                autres_infos_html TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute(
            """
            INSERT INTO faces (
                name, encoding_json, adresse, metier, lieu_naissance,
                age, annee_naissance, autres_infos_html, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "Legacy User",
                "[0.1, 0.2, 0.3]",
                "Port Louis",
                "Analyste",
                "Curepipe",
                31,
                1995,
                "Texte legacy",
                "2026-01-02 03:04:05",
            ),
        )
        connection.commit()

    init_db()

    with get_connection() as connection:
        legacy_exists = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'faces'"
        ).fetchone()
        profile = connection.execute(
            """
            SELECT id, name, adresse, metier, lieu_naissance, age,
                   annee_naissance, autres_infos_text, created_at
            FROM face_profiles
            """
        ).fetchone()
        embedding = connection.execute(
            "SELECT face_id, encoding_json, created_at FROM face_embeddings"
        ).fetchone()

    assert legacy_exists is None
    assert profile is not None
    assert profile["id"] == 1
    assert profile["name"] == "Legacy User"
    assert profile["adresse"] == "Port Louis"
    assert profile["metier"] == "Analyste"
    assert profile["lieu_naissance"] == "Curepipe"
    assert profile["age"] == 31
    assert profile["annee_naissance"] == 1995
    assert profile["autres_infos_text"] == "Texte legacy"
    assert profile["created_at"] == "2026-01-02 03:04:05"
    assert embedding is not None
    assert embedding["face_id"] == 1
    assert embedding["encoding_json"] == "[0.1, 0.2, 0.3]"
    assert embedding["created_at"] == "2026-01-02 03:04:05"


def test_init_db_does_not_create_legacy_faces_table_on_fresh_db(monkeypatch, tmp_path):
    monkeypatch.setenv("FACE_APP_DB_PATH", str(tmp_path / "fresh.db"))

    init_db()

    with get_connection() as connection:
        legacy_exists = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'faces'"
        ).fetchone()

    assert legacy_exists is None


def test_init_db_drops_empty_legacy_faces_table(monkeypatch, tmp_path):
    db_path = tmp_path / "empty-legacy.db"
    monkeypatch.setenv("FACE_APP_DB_PATH", str(db_path))

    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE faces (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                encoding_json TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.commit()

    init_db()

    with get_connection() as connection:
        legacy_exists = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'faces'"
        ).fetchone()

    assert legacy_exists is None


def test_init_db_rebuilds_legacy_detections_referencing_faces(monkeypatch, tmp_path):
    db_path = tmp_path / "legacy-detections.db"
    monkeypatch.setenv("FACE_APP_DB_PATH", str(db_path))

    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE faces (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                encoding_json TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE detections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                status TEXT NOT NULL,
                face_id INTEGER,
                score REAL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                faces_json TEXT,
                camera_id INTEGER DEFAULT 0,
                FOREIGN KEY(face_id) REFERENCES faces(id)
            )
            """
        )
        connection.execute(
            "INSERT INTO faces (name, encoding_json, created_at) VALUES (?, ?, ?)",
            ("Legacy User", "[0.1, 0.2]", "2026-01-02 03:04:05"),
        )
        connection.execute(
            """
            INSERT INTO detections (status, face_id, score, created_at, faces_json, camera_id)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            ("reconnu", 1, 0.91, "2026-01-02 03:05:06", '[{"status":"reconnu"}]', 4),
        )
        connection.commit()

    init_db()

    with get_connection() as connection:
        foreign_keys = connection.execute("PRAGMA foreign_key_list(detections)").fetchall()
        detection = connection.execute(
            """
            SELECT id, status, face_id, score, created_at, faces_json, camera_id
            FROM detections
            """
        ).fetchone()

    assert foreign_keys == []
    assert detection is not None
    assert detection["id"] == 1
    assert detection["status"] == "reconnu"
    assert detection["face_id"] == 1
    assert detection["score"] == 0.91
    assert detection["created_at"] == "2026-01-02 03:05:06"
    assert detection["faces_json"] == '[{"status":"reconnu"}]'
    assert detection["camera_id"] == 4
