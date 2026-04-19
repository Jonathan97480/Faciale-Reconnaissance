import os
import shutil
import subprocess
import threading
import time
import uuid
from pathlib import Path

from app.core.database import get_db_path


class HlsSessionManager:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._sessions_by_profile: dict[str, dict[str, object]] = {}
        self._sessions_by_id: dict[str, dict[str, object]] = {}

    def _base_dir(self) -> Path:
        return get_db_path().parent / "hls_gateway"

    def _build_cmd(self, source_url: str, manifest_path: Path) -> list[str]:
        return [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-rtsp_transport",
            "tcp",
            "-i",
            source_url,
            "-analyzeduration",
            "1500000",
            "-probesize",
            "1500000",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-f",
            "hls",
            "-hls_time",
            "2",
            "-hls_list_size",
            "6",
            "-hls_flags",
            "delete_segments+append_list",
            str(manifest_path),
        ]

    def _is_running(self, session: dict[str, object]) -> bool:
        process = session.get("process")
        return bool(process and process.poll() is None)

    def start_or_get_session(self, profile_name: str, source_url: str) -> dict[str, object]:
        with self._lock:
            existing = self._sessions_by_profile.get(profile_name)
            if existing and self._is_running(existing):
                existing["last_used_at"] = time.time()
                return dict(existing)

            ffmpeg = shutil.which("ffmpeg")
            if not ffmpeg:
                raise RuntimeError("FFmpeg is required for RTSP->HLS gateway")

            session_id = uuid.uuid4().hex[:12]
            session_dir = self._base_dir() / session_id
            session_dir.mkdir(parents=True, exist_ok=True)
            manifest_path = session_dir / "index.m3u8"
            cmd = self._build_cmd(source_url, manifest_path)
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
            )
            session = {
                "id": session_id,
                "profile_name": profile_name,
                "source_url": source_url,
                "dir": str(session_dir),
                "manifest": str(manifest_path),
                "process": process,
                "started_at": time.time(),
                "last_used_at": time.time(),
            }
            self._sessions_by_profile[profile_name] = session
            self._sessions_by_id[session_id] = session
            return dict(session)

    def get_session(self, session_id: str) -> dict[str, object] | None:
        with self._lock:
            session = self._sessions_by_id.get(session_id)
            if not session:
                return None
            session["last_used_at"] = time.time()
            return dict(session)

    def list_sessions(self) -> list[dict[str, object]]:
        with self._lock:
            items = list(self._sessions_by_id.values())
        result = []
        for session in items:
            result.append(
                {
                    "id": str(session["id"]),
                    "profile_name": str(session["profile_name"]),
                    "started_at": float(session["started_at"]),
                    "last_used_at": float(session["last_used_at"]),
                    "running": self._is_running(session),
                }
            )
        return result

    def stop_session(self, session_id: str) -> bool:
        with self._lock:
            session = self._sessions_by_id.pop(session_id, None)
            if not session:
                return False
            profile_name = str(session["profile_name"])
            if self._sessions_by_profile.get(profile_name, {}).get("id") == session_id:
                self._sessions_by_profile.pop(profile_name, None)
        process = session.get("process")
        if process and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
        return True

    def stop_all(self) -> None:
        for session in self.list_sessions():
            self.stop_session(str(session["id"]))


hls_gateway_manager = HlsSessionManager()


def start_hls_session(profile_name: str, source_url: str) -> dict[str, object]:
    return hls_gateway_manager.start_or_get_session(profile_name, source_url)


def get_hls_session(session_id: str) -> dict[str, object] | None:
    return hls_gateway_manager.get_session(session_id)


def list_hls_sessions() -> list[dict[str, object]]:
    return hls_gateway_manager.list_sessions()


def stop_hls_session(session_id: str) -> bool:
    return hls_gateway_manager.stop_session(session_id)


def stop_all_hls_sessions() -> None:
    hls_gateway_manager.stop_all()


def resolve_hls_file(session_id: str, filename: str) -> Path | None:
    session = get_hls_session(session_id)
    if not session:
        return None
    session_dir = Path(str(session["dir"])).resolve()
    target = (session_dir / filename).resolve()
    if not str(target).startswith(str(session_dir)):
        return None
    if not os.path.exists(target):
        return None
    return target
