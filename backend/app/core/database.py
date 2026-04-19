import os
import sqlite3
from pathlib import Path

DEFAULT_CONFIG = {
    "detection_interval_seconds": "3",
    "match_threshold": "0.6",
    "camera_index": "0",
    "camera_source": "",  # vide = webcam locale, sinon URL ou chemin
    "network_camera_sources_json": "[]",
    "network_camera_profiles_json": "[]",
    "multi_camera_cycle_budget_seconds": "2",
    "enroll_frames_count": "5",
    "face_crop_padding_ratio": "0.2",
    "inference_device_preference": "auto",
}


def get_db_path() -> Path:
    configured_path = os.getenv("FACE_APP_DB_PATH")
    if configured_path:
        return Path(configured_path)
    return Path(__file__).resolve().parents[2] / "data" / "app.db"


def get_connection() -> sqlite3.Connection:
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS faces (
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
        # Migration pour anciens schémas
        face_columns = {row["name"] for row in connection.execute("PRAGMA table_info(faces)").fetchall()}
        migrations = [
            ("adresse", "ALTER TABLE faces ADD COLUMN adresse TEXT"),
            ("metier", "ALTER TABLE faces ADD COLUMN metier TEXT"),
            ("lieu_naissance", "ALTER TABLE faces ADD COLUMN lieu_naissance TEXT"),
            ("age", "ALTER TABLE faces ADD COLUMN age INTEGER"),
            ("annee_naissance", "ALTER TABLE faces ADD COLUMN annee_naissance INTEGER"),
            ("autres_infos_html", "ALTER TABLE faces ADD COLUMN autres_infos_html TEXT"),
        ]
        for col, sql in migrations:
            if col not in face_columns:
                connection.execute(sql)
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS detections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                status TEXT NOT NULL,
                face_id INTEGER,
                score REAL,
                faces_json TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(face_id) REFERENCES faces(id)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS api_batch_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                endpoint TEXT NOT NULL,
                items_count INTEGER NOT NULL,
                success_count INTEGER NOT NULL,
                error_count INTEGER NOT NULL,
                client_ip TEXT,
                user_agent TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS camera_stream_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                event_type TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        detection_columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(detections)").fetchall()
        }
        if "faces_json" not in detection_columns:
            connection.execute("ALTER TABLE detections ADD COLUMN faces_json TEXT")
        # Migration config : ajout camera_source si absent
        config_keys = {row[0] for row in connection.execute("SELECT key FROM config").fetchall()}
        for key, value in DEFAULT_CONFIG.items():
            if key not in config_keys:
                connection.execute(
                    "INSERT INTO config (key, value) VALUES (?, ?)",
                    (key, value),
                )
            else:
                connection.execute(
                    "UPDATE config SET value = value WHERE key = ?",
                    (key,),
                )
        connection.commit()
        connection.commit()
