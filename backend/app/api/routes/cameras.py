from fastapi import APIRouter, Query

from app.services.camera_profile_url_service import (
    build_camera_profile_stream_url,
    build_web_playback_url,
    sanitize_url_for_display,
)
from app.services.camera_event_log_service import get_camera_events
from app.services.config_service import read_config
from app.services.onvif_discovery_service import discover_onvif_devices

router = APIRouter(prefix="/cameras", tags=["cameras"])


@router.get("/onvif/discover")
def discover_onvif(timeout_seconds: float = Query(default=2.0, ge=0.5, le=10.0)) -> dict[str, object]:
    devices = discover_onvif_devices(timeout_seconds=timeout_seconds)
    return {"count": len(devices), "devices": devices}


@router.get("/events")
def list_camera_events(limit: int = Query(default=50, ge=1, le=200)) -> dict[str, object]:
    return {"events": get_camera_events(limit=limit)}


@router.get("/profiles/resolved")
def get_resolved_profiles() -> dict[str, object]:
    config = read_config(mask_secrets=True)
    profiles = []
    for profile in config.network_camera_profiles:
        stream_url = build_camera_profile_stream_url(profile)
        web_url = build_web_playback_url(profile)
        profiles.append(
            {
                "name": profile.name,
                "protocol": profile.protocol,
                "enabled": profile.enabled,
                "stream_url": sanitize_url_for_display(stream_url),
                "web_playback_url": sanitize_url_for_display(web_url) if web_url else "",
                "audio_expected": profile.protocol in {"rtsp", "hls", "http"},
            }
        )
    return {"profiles": profiles}
