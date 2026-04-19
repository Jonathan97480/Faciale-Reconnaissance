from urllib.parse import quote
from urllib.parse import urlsplit, urlunsplit

from app.core.schemas import NetworkCameraProfile


def build_camera_profile_stream_url(profile: NetworkCameraProfile) -> str:
    protocol = profile.protocol
    host = profile.host.strip()
    port = profile.port
    raw_path = profile.path.strip() or "/"
    path = raw_path if raw_path.startswith("/") else f"/{raw_path}"

    username = profile.username.strip()
    password = profile.password
    auth = ""
    if username:
        auth = quote(username, safe="")
        if password:
            auth = f"{auth}:{quote(password, safe='')}"
        auth = f"{auth}@"

    if protocol == "rtsp":
        return f"rtsp://{auth}{host}:{port}{path}"
    if protocol in {"mjpeg", "http", "hls"}:
        return f"http://{auth}{host}:{port}{path}"
    return f"http://{auth}{host}:{port}{path}"


def build_enabled_profile_urls(profiles: list[NetworkCameraProfile]) -> list[str]:
    urls: list[str] = []
    for profile in profiles:
        if not profile.enabled:
            continue
        url = build_camera_profile_stream_url(profile)
        if url not in urls:
            urls.append(url)
    return urls


def sanitize_url_for_display(url: str) -> str:
    parts = urlsplit(url)
    netloc = parts.hostname or ""
    if parts.port:
        netloc = f"{netloc}:{parts.port}"
    return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))


def build_web_playback_url(profile: NetworkCameraProfile) -> str:
    if profile.protocol in {"hls", "http"}:
        return build_camera_profile_stream_url(profile)
    if profile.protocol == "mjpeg":
        return build_camera_profile_stream_url(profile)
    return ""
