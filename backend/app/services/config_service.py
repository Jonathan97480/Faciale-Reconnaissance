import json

from app.core.database import get_connection
from app.core.schemas import ConfigPayload, NetworkCameraProfile
from app.services.secret_crypto_service import decrypt_secret, encrypt_secret


def _profile_identity_key(profile: NetworkCameraProfile) -> str:
    return f"{profile.name}|{profile.protocol}|{profile.host}|{profile.port}|{profile.path}"


def _mask_profile_secrets(profile: NetworkCameraProfile) -> NetworkCameraProfile:
    return NetworkCameraProfile(
        name=profile.name,
        protocol=profile.protocol,
        host=profile.host,
        port=profile.port,
        path=profile.path,
        username=profile.username,
        password="",
        has_password=bool(profile.password),
        onvif_url=profile.onvif_url,
        enabled=profile.enabled,
    )


def read_config(mask_secrets: bool = False) -> ConfigPayload:
    with get_connection() as connection:
        rows = connection.execute("SELECT key, value FROM config").fetchall()

    raw_config = {row["key"]: row["value"] for row in rows}
    raw_sources = raw_config.get("network_camera_sources_json", "[]")
    network_sources: list[str] = []
    try:
        parsed_sources = json.loads(raw_sources)
        if isinstance(parsed_sources, list):
            network_sources = [str(item).strip() for item in parsed_sources if str(item).strip()]
    except json.JSONDecodeError:
        network_sources = []

    raw_profiles = raw_config.get("network_camera_profiles_json", "[]")
    network_profiles: list[NetworkCameraProfile] = []
    try:
        parsed_profiles = json.loads(raw_profiles)
        if isinstance(parsed_profiles, list):
            for item in parsed_profiles:
                if isinstance(item, dict):
                    profile = NetworkCameraProfile(**item)
                    profile.password = decrypt_secret(profile.password)
                    profile.has_password = bool(profile.password)
                    network_profiles.append(profile)
    except (json.JSONDecodeError, TypeError, ValueError):
        network_profiles = []
    if mask_secrets:
        network_profiles = [_mask_profile_secrets(profile) for profile in network_profiles]

    return ConfigPayload(
        detection_interval_seconds=float(raw_config["detection_interval_seconds"]),
        match_threshold=float(raw_config["match_threshold"]),
        camera_index=int(raw_config["camera_index"]),
        camera_source=raw_config.get("camera_source", ""),
        network_camera_sources=network_sources,
        network_camera_profiles=network_profiles,
        multi_camera_cycle_budget_seconds=float(
            raw_config.get("multi_camera_cycle_budget_seconds", "2")
        ),
        enroll_frames_count=int(raw_config.get("enroll_frames_count", "5")),
        face_crop_padding_ratio=float(raw_config.get("face_crop_padding_ratio", "0.2")),
    )


def update_config(payload: ConfigPayload) -> ConfigPayload:
    current = read_config(mask_secrets=False)
    previous_by_key = {
        _profile_identity_key(profile): profile for profile in current.network_camera_profiles
    }
    merged_profiles: list[NetworkCameraProfile] = []
    for incoming in payload.network_camera_profiles:
        incoming_password = incoming.password
        if not incoming_password:
            previous = previous_by_key.get(_profile_identity_key(incoming))
            if previous and previous.password:
                incoming_password = previous.password
        merged_profiles.append(
            NetworkCameraProfile(
                name=incoming.name,
                protocol=incoming.protocol,
                host=incoming.host,
                port=incoming.port,
                path=incoming.path,
                username=incoming.username,
                password=incoming_password,
                has_password=bool(incoming_password),
                onvif_url=incoming.onvif_url,
                enabled=incoming.enabled,
            )
        )

    updates = {
        "detection_interval_seconds": str(payload.detection_interval_seconds),
        "match_threshold": str(payload.match_threshold),
        "camera_index": str(payload.camera_index),
        "camera_source": str(payload.camera_source),
        "network_camera_sources_json": json.dumps(payload.network_camera_sources),
        "network_camera_profiles_json": json.dumps(
            [
                {
                    **profile.model_dump(),
                    "password": encrypt_secret(profile.password),
                    "has_password": bool(profile.password),
                }
                for profile in merged_profiles
            ]
        ),
        "multi_camera_cycle_budget_seconds": str(payload.multi_camera_cycle_budget_seconds),
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

    return read_config(mask_secrets=False)
