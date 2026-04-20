from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse

from app.api.routes.auth import get_current_user
from app.services.camera_alert_service import build_camera_alerts
from app.services.camera_profile_url_service import (
    build_camera_profile_stream_url,
    build_web_playback_url,
    sanitize_url_for_display,
)
from app.services.camera_event_log_service import get_camera_events
from app.services.config_service import read_config
from app.services.hls_gateway_service import (
    list_hls_sessions,
    resolve_hls_file,
    start_hls_session,
    stop_hls_session,
)
from app.services.network_camera_pool_service import network_camera_pool_status
from app.services.onvif_discovery_service import discover_onvif_devices

router = APIRouter(
    prefix="/cameras",
    tags=["cameras"],
    dependencies=[Depends(get_current_user)],
)


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


@router.get("/alerts")
def get_camera_alerts(
    max_read_latency_ms: float = Query(default=350.0, ge=50.0, le=5000.0),
    max_detection_staleness_seconds: float = Query(default=8.0, ge=1.0, le=120.0),
) -> dict[str, object]:
    status = network_camera_pool_status()
    source_stats = status.get("sources", [])
    alerts = build_camera_alerts(
        source_stats=source_stats if isinstance(source_stats, list) else [],
        max_read_latency_ms=max_read_latency_ms,
        max_detection_staleness_seconds=max_detection_staleness_seconds,
    )
    return {"alerts_count": len(alerts), "alerts": alerts}


@router.post("/playback/start")
def start_camera_playback(profile_name: str = Query(min_length=1)) -> dict[str, object]:
    config = read_config(mask_secrets=False)
    profile = next(
        (item for item in config.network_camera_profiles if item.name == profile_name),
        None,
    )
    if profile is None:
        raise HTTPException(status_code=404, detail="Profil camera introuvable")
    if not profile.enabled:
        raise HTTPException(status_code=400, detail="Profil camera desactive")

    direct_url = build_web_playback_url(profile)
    if direct_url:
        return {
            "mode": "direct",
            "profile_name": profile.name,
            "playback_url": sanitize_url_for_display(direct_url),
            "audio_expected": profile.protocol in {"hls", "http"},
        }

    stream_url = build_camera_profile_stream_url(profile)
    try:
        session = start_hls_session(profile_name=profile.name, source_url=stream_url)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    session_id = str(session["id"])
    return {
        "mode": "hls_proxy",
        "profile_name": profile.name,
        "session_id": session_id,
        "playback_url": f"/api/cameras/hls/{session_id}/index.m3u8",
        "audio_expected": True,
    }


@router.get("/playback/sessions")
def get_playback_sessions() -> dict[str, object]:
    return {"sessions": list_hls_sessions()}


@router.delete("/playback/sessions/{session_id}")
def delete_playback_session(session_id: str) -> dict[str, object]:
    removed = stop_hls_session(session_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Session introuvable")
    return {"ok": True}


@router.get("/hls/{session_id}/{filename:path}")
def get_hls_asset(session_id: str, filename: str):
    resolved = resolve_hls_file(session_id, filename)
    if resolved is None:
        raise HTTPException(status_code=404, detail="HLS asset introuvable")
    media_type = "application/vnd.apple.mpegurl"
    if Path(filename).suffix.lower() == ".ts":
        media_type = "video/mp2t"
    return FileResponse(path=resolved, media_type=media_type)
