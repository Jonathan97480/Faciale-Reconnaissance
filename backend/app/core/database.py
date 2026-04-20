import os
import sqlite3
from pathlib import Path

DEFAULT_CONFIG = {
    "detection_interval_seconds": "3",
    "match_threshold": "0.6",
    "camera_index": "0",
    "camera_source": "",
    "network_camera_sources_json": "[]",
    "network_camera_profiles_json": "[]",
    "multi_camera_cycle_budget_seconds": "2",
    "enroll_frames_count": "5",
    "face_crop_padding_ratio": "0.2",
    "inference_device_preference": "auto",
    "production_api_rate_limit_window_seconds": "60",
    "production_api_rate_limit_max_requests": "30",
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
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _table_exists(connection: sqlite3.Connection, table_name: str) -> bool:
    row = connection.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type = 'table' AND name = ?
        """,
        (table_name,),
    ).fetchone()
    return row is not None


def _migrate_legacy_faces_columns(connection: sqlite3.Connection) -> None:
    if not _table_exists(connection, "faces"):
        return
    face_columns = {
        row["name"] for row in connection.execute("PRAGMA table_info(faces)").fetchall()
    }
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


def _create_split_face_tables(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS face_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            adresse TEXT,
            metier TEXT,
            lieu_naissance TEXT,
            age INTEGER,
            annee_naissance INTEGER,
            autres_infos_text TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS face_embeddings (
            face_id INTEGER PRIMARY KEY,
            encoding_json TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(face_id) REFERENCES face_profiles(id) ON DELETE CASCADE
        )
        """
        )


def _create_detections_table(connection: sqlite3.Connection, table_name: str) -> None:
    connection.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            status TEXT NOT NULL,
            face_id INTEGER,
            score REAL,
            faces_json TEXT,
            camera_id INTEGER DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


def _migrate_detections_table_if_needed(connection: sqlite3.Connection) -> None:
    if not _table_exists(connection, "detections"):
        return

    foreign_keys = connection.execute("PRAGMA foreign_key_list(detections)").fetchall()
    references_legacy_faces = any(row["table"] == "faces" for row in foreign_keys)
    detection_columns = {
        row["name"] for row in connection.execute("PRAGMA table_info(detections)").fetchall()
    }
    if not references_legacy_faces and "faces_json" in detection_columns:
        return

    _create_detections_table(connection, "detections_migrated")
    faces_json_expr = "faces_json" if "faces_json" in detection_columns else "NULL"
    camera_id_expr = "camera_id" if "camera_id" in detection_columns else "0"
    connection.execute(
        f"""
        INSERT INTO detections_migrated (
            id, status, face_id, score, faces_json, camera_id, created_at
        )
        SELECT
            id, status, face_id, score, {faces_json_expr}, {camera_id_expr}, created_at
        FROM detections
        ORDER BY id ASC
        """
    )
    connection.execute("DROP TABLE detections")
    connection.execute("ALTER TABLE detections_migrated RENAME TO detections")


def _migrate_legacy_faces_to_split_tables(connection: sqlite3.Connection) -> None:
    if not _table_exists(connection, "faces"):
        return
    legacy_rows = connection.execute(
        """
        SELECT id, name, encoding_json, adresse, metier, lieu_naissance, age,
               annee_naissance, autres_infos_html, created_at
        FROM faces
        ORDER BY id ASC
        """
    ).fetchall()
    if legacy_rows:
        existing_profile_ids = {
            row["id"] for row in connection.execute("SELECT id FROM face_profiles").fetchall()
        }
        existing_embedding_ids = {
            row["face_id"]
            for row in connection.execute("SELECT face_id FROM face_embeddings").fetchall()
        }

        for row in legacy_rows:
            if row["id"] not in existing_profile_ids:
                connection.execute(
                    """
                    INSERT INTO face_profiles (
                        id, name, adresse, metier, lieu_naissance, age,
                        annee_naissance, autres_infos_text, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        row["id"],
                        row["name"],
                        row["adresse"],
                        row["metier"],
                        row["lieu_naissance"],
                        row["age"],
                        row["annee_naissance"],
                        row["autres_infos_html"],
                        row["created_at"],
                    ),
                )

            if row["encoding_json"] and row["id"] not in existing_embedding_ids:
                connection.execute(
                    """
                    INSERT INTO face_embeddings (face_id, encoding_json, created_at)
                    VALUES (?, ?, ?)
                    """,
                    (row["id"], row["encoding_json"], row["created_at"]),
                )

    connection.execute("DROP TABLE faces")


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
        _migrate_legacy_faces_columns(connection)
        _create_split_face_tables(connection)
        _migrate_detections_table_if_needed(connection)
        _migrate_legacy_faces_to_split_tables(connection)
        _create_detections_table(connection, "detections")
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
