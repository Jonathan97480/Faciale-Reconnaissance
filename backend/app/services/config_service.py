import json
import threading
from pathlib import Path

from app.core.database import get_connection, get_db_path
from app.core.schemas import ConfigPayload, NetworkCameraProfile
from app.services.encoder_service import peek_active_device
from app.services.secret_crypto_service import decrypt_secret, encrypt_secret

_cache_lock = threading.Lock()
_config_cache: ConfigPayload | None = None
_config_cache_db_path: str | None = None
_config_cache_fingerprint: tuple[int, int] | None = None


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


def _sanitize_inference_device_preference(value: str | None) -> str:
    cleaned = str(value or "auto").strip().lower()
    if cleaned in {"auto", "cpu", "cuda"}:
        return cleaned
    return "auto"


def invalidate_config_cache() -> None:
    global _config_cache, _config_cache_db_path, _config_cache_fingerprint
    with _cache_lock:
        _config_cache = None
        _config_cache_db_path = None
        _config_cache_fingerprint = None


def _read_db_fingerprint(db_path: Path) -> tuple[int, int]:
    try:
        stat = db_path.stat()
    except FileNotFoundError:
        return (0, 0)
    return (stat.st_mtime_ns, stat.st_size)


def _load_config_from_db(connection) -> ConfigPayload:
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

    preference = _sanitize_inference_device_preference(
        raw_config.get("inference_device_preference", "auto")
    )
    return ConfigPayload(
        detection_interval_seconds=float(raw_config["detection_interval_seconds"]),
        match_threshold=float(raw_config["match_threshold"]),
        match_margin_threshold=float(raw_config.get("match_margin_threshold", "0.03")),
        camera_index=int(raw_config["camera_index"]),
        camera_source=raw_config.get("camera_source", ""),
        network_camera_sources=network_sources,
        network_camera_profiles=network_profiles,
        multi_camera_cycle_budget_seconds=float(
            raw_config.get("multi_camera_cycle_budget_seconds", "2")
        ),
        network_camera_retry_base_seconds=float(
            raw_config.get("network_camera_retry_base_seconds", "0.5")
        ),
        network_camera_retry_max_seconds=float(
            raw_config.get("network_camera_retry_max_seconds", "8")
        ),
        enroll_frames_count=int(raw_config.get("enroll_frames_count", "5")),
        face_crop_padding_ratio=float(raw_config.get("face_crop_padding_ratio", "0.2")),
        inference_device_preference=preference,
        inference_device_active="cpu",
        production_api_rate_limit_window_seconds=float(
            raw_config.get("production_api_rate_limit_window_seconds", "60")
        ),
        production_api_rate_limit_max_requests=int(
            raw_config.get("production_api_rate_limit_max_requests", "30")
        ),
    )


def _get_cached_base_config() -> ConfigPayload:
    global _config_cache, _config_cache_db_path, _config_cache_fingerprint
    db_path = get_db_path()
    current_db_path = str(db_path)
    fingerprint = _read_db_fingerprint(db_path)
    with get_connection() as connection:
        with _cache_lock:
            if (
                _config_cache is not None
                and _config_cache_db_path == current_db_path
                and _config_cache_fingerprint == fingerprint
            ):
                return _config_cache.model_copy(deep=True)

        loaded = _load_config_from_db(connection)

    with _cache_lock:
        _config_cache = loaded
        _config_cache_db_path = current_db_path
        _config_cache_fingerprint = fingerprint
        return loaded.model_copy(deep=True)


def read_config(mask_secrets: bool = False) -> ConfigPayload:
    config = _get_cached_base_config()
    config.inference_device_active = peek_active_device()
    if mask_secrets:
        config.network_camera_profiles = [
            _mask_profile_secrets(profile) for profile in config.network_camera_profiles
        ]
    return config


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
        "match_margin_threshold": str(payload.match_margin_threshold),
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
        "network_camera_retry_base_seconds": str(payload.network_camera_retry_base_seconds),
        "network_camera_retry_max_seconds": str(payload.network_camera_retry_max_seconds),
        "enroll_frames_count": str(payload.enroll_frames_count),
        "face_crop_padding_ratio": str(payload.face_crop_padding_ratio),
        "inference_device_preference": str(payload.inference_device_preference),
        "production_api_rate_limit_window_seconds": str(
            payload.production_api_rate_limit_window_seconds
        ),
        "production_api_rate_limit_max_requests": str(
            payload.production_api_rate_limit_max_requests
        ),
    }

    with get_connection() as connection:
        for key, value in updates.items():
            connection.execute(
                "UPDATE config SET value = ? WHERE key = ?",
                (value, key),
            )
        connection.commit()

    invalidate_config_cache()

    try:
        from app.services.encoder_service import configure_inference_device

        configure_inference_device(payload.inference_device_preference)
    except Exception:
        pass

    return read_config(mask_secrets=False)
