from app.core.database import get_connection
from app.core.schemas import ConfigPayload


def read_config() -> ConfigPayload:
    with get_connection() as connection:
        rows = connection.execute("SELECT key, value FROM config").fetchall()

    raw_config = {row["key"]: row["value"] for row in rows}
    return ConfigPayload(
        detection_interval_seconds=float(raw_config["detection_interval_seconds"]),
        match_threshold=float(raw_config["match_threshold"]),
        camera_index=int(raw_config["camera_index"]),
        camera_source=raw_config.get("camera_source", ""),
        enroll_frames_count=int(raw_config.get("enroll_frames_count", "5")),
        face_crop_padding_ratio=float(raw_config.get("face_crop_padding_ratio", "0.2")),
    )


def update_config(payload: ConfigPayload) -> ConfigPayload:
    updates = {
        "detection_interval_seconds": str(payload.detection_interval_seconds),
        "match_threshold": str(payload.match_threshold),
        "camera_index": str(payload.camera_index),
        "camera_source": str(payload.camera_source),
        "enroll_frames_count": str(payload.enroll_frames_count),
        "face_crop_padding_ratio": str(payload.face_crop_padding_ratio),
    }

    with get_connection() as connection:
        for key, value in updates.items():
            connection.execute(
                "UPDATE config SET value = ? WHERE key = ?",
                (value, key),
            )
        connection.commit()

    return read_config()
