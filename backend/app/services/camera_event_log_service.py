from app.core.database import get_connection


def log_camera_event(source: str, event_type: str, message: str) -> None:
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO camera_stream_events (source, event_type, message)
            VALUES (?, ?, ?)
            """,
            (source, event_type, message[:500]),
        )
        connection.commit()


def get_camera_events(limit: int = 100) -> list[dict[str, object]]:
    bounded_limit = max(1, min(200, limit))
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, source, event_type, message, created_at
            FROM camera_stream_events
            ORDER BY id DESC
            LIMIT ?
            """,
            (bounded_limit,),
        ).fetchall()
    return [
        {
            "id": int(row["id"]),
            "source": str(row["source"]),
            "event_type": str(row["event_type"]),
            "message": str(row["message"]),
            "created_at": str(row["created_at"]),
        }
        for row in rows
    ]
