import os
import shutil
import subprocess
import threading
import time
import uuid
from pathlib import Path
from urllib.parse import urlsplit

from app.core.database import get_db_path
from app.services.network_url_validation_service import validate_network_stream_url


class HlsSessionManager:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._sessions_by_profile: dict[str, dict[str, object]] = {}
        self._sessions_by_id: dict[str, dict[str, object]] = {}

    def _base_dir(self) -> Path:
        return get_db_path().parent / "hls_gateway"

    def _validate_gateway_source_url(self, source_url: str) -> str:
        validated_source_url = validate_network_stream_url(source_url)
        parts = urlsplit(validated_source_url)
        if parts.scheme.lower() != "rtsp":
            raise ValueError("Le proxy HLS accepte uniquement les flux RTSP")
        return validated_source_url

    def _validate_session_id(self, session_id: str) -> str:
        cleaned = session_id.strip()
        if len(cleaned) != 12 or any(char not in "0123456789abcdef" for char in cleaned):
            raise ValueError("Identifiant de session HLS invalide")
        return cleaned

    def _validate_asset_name(self, filename: str) -> str:
        cleaned = filename.strip()
        if not cleaned:
            raise ValueError("Nom de fichier HLS requis")
        candidate = Path(cleaned)
        if candidate.name != cleaned or candidate.is_absolute():
            raise ValueError("Nom de fichier HLS invalide")
        if cleaned == "index.m3u8":
            return cleaned
        if cleaned.startswith("seg-") and cleaned.endswith(".ts"):
            return cleaned
        raise ValueError("Asset HLS non supporte")

    def _collect_expired_session_ids(self, idle_ttl_seconds: float, now: float) -> list[str]:
        expired_ids: list[str] = []
        for session_id, session in self._sessions_by_id.items():
            last_used_at = float(session.get("last_used_at") or 0.0)
            if (now - last_used_at) >= idle_ttl_seconds:
                expired_ids.append(session_id)
        return expired_ids

    def _collect_lru_session_ids(self) -> list[str]:
        ordered = sorted(
            self._sessions_by_id.values(),
            key=lambda session: float(session.get("last_used_at") or 0.0),
        )
        return [str(session["id"]) for session in ordered]

    def _prune_sessions(
        self,
        max_sessions: int | None,
        idle_ttl_seconds: float,
    ) -> None:
        now = time.time()
        for session_id in self._collect_expired_session_ids(idle_ttl_seconds, now):
            self.stop_session(session_id)
        while max_sessions is not None and len(self._sessions_by_id) >= max_sessions:
            lru_ids = self._collect_lru_session_ids()
            if not lru_ids:
                break
            self.stop_session(lru_ids[0])

    def _build_cmd(self, source_url: str, manifest_path: Path) -> list[str]:
        validated_source_url = self._validate_gateway_source_url(source_url)
        return [
            "ffmpeg",
            "-hide_banner",
            "-nostdin",
            "-loglevel",
            "error",
            "-rtsp_transport",
            "tcp",
            "-i",
            validated_source_url,
            "-rw_timeout",
            "5000000",
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

    def _read_stderr_tail(self, session: dict[str, object]) -> str:
        process = session.get("process")
        if not process:
            return str(session.get("stderr_tail", ""))
        stderr = getattr(process, "stderr", None)
        if stderr is None:
            return str(session.get("stderr_tail", ""))
        try:
            content = stderr.read()
        except Exception:
            content = ""
        previous = str(session.get("stderr_tail", ""))
        combined = f"{previous}{content}".strip()
        if len(combined) > 500:
            combined = combined[-500:]
        session["stderr_tail"] = combined
        return combined

    def _manifest_stats(self, manifest_path: Path) -> dict[str, object]:
        manifest_ready = manifest_path.exists()
        manifest_updated_at = manifest_path.stat().st_mtime if manifest_ready else None
        segment_count = 0
        if manifest_ready:
            try:
                lines = manifest_path.read_text(encoding="utf-8", errors="ignore").splitlines()
            except OSError:
                lines = []
            segment_count = sum(1 for line in lines if line.strip().endswith(".ts"))
        return {
            "manifest_ready": manifest_ready,
            "manifest_updated_at": manifest_updated_at,
            "segment_count": segment_count,
        }

    def _session_status(self, session: dict[str, object]) -> dict[str, object]:
        manifest_path = Path(str(session["manifest"]))
        process = session.get("process")
        running = self._is_running(session)
        stderr_tail = self._read_stderr_tail(session)
        last_exit_code = None
        if process and not running:
            last_exit_code = process.poll()
        stats = self._manifest_stats(manifest_path)
        started_at = float(session["started_at"])
        now = time.time()
        return {
            "id": str(session["id"]),
            "profile_name": str(session["profile_name"]),
            "started_at": started_at,
            "last_used_at": float(session["last_used_at"]),
            "running": running,
            "manifest_ready": bool(stats["manifest_ready"]),
            "manifest_updated_at": stats["manifest_updated_at"],
            "segment_count": int(stats["segment_count"]),
            "last_exit_code": last_exit_code,
            "last_error": stderr_tail or None,
            "uptime_seconds": max(0.0, now - started_at),
        }

    def start_or_get_session(
        self,
        profile_name: str,
        source_url: str,
        max_sessions: int = 2,
        idle_ttl_seconds: float = 30.0,
    ) -> dict[str, object]:
        with self._lock:
            self._prune_sessions(max_sessions=max_sessions, idle_ttl_seconds=idle_ttl_seconds)
            existing = self._sessions_by_profile.get(profile_name)
            if existing and self._is_running(existing):
                existing["last_used_at"] = time.time()
                return self._session_status(existing)

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
                "stderr_tail": "",
            }
            self._sessions_by_profile[profile_name] = session
            self._sessions_by_id[session_id] = session
            return self._session_status(session)

    def get_session(self, session_id: str, idle_ttl_seconds: float = 30.0) -> dict[str, object] | None:
        with self._lock:
            self._prune_sessions(max_sessions=None, idle_ttl_seconds=idle_ttl_seconds)
            session = self._sessions_by_id.get(session_id)
            if not session:
                return None
            session["last_used_at"] = time.time()
            return self._session_status(session)

    def list_sessions(self, idle_ttl_seconds: float = 30.0) -> list[dict[str, object]]:
        with self._lock:
            self._prune_sessions(max_sessions=None, idle_ttl_seconds=idle_ttl_seconds)
            items = list(self._sessions_by_id.values())
        return [self._session_status(session) for session in items]

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
        session_dir = Path(str(session["dir"]))
        shutil.rmtree(session_dir, ignore_errors=True)
        return True

    def stop_all(self) -> None:
        for session in self.list_sessions():
            self.stop_session(str(session["id"]))


hls_gateway_manager = HlsSessionManager()


def start_hls_session(
    profile_name: str,
    source_url: str,
    max_sessions: int = 2,
    idle_ttl_seconds: float = 30.0,
) -> dict[str, object]:
    return hls_gateway_manager.start_or_get_session(
        profile_name,
        source_url,
        max_sessions=max_sessions,
        idle_ttl_seconds=idle_ttl_seconds,
    )


def get_hls_session(session_id: str, idle_ttl_seconds: float = 30.0) -> dict[str, object] | None:
    return hls_gateway_manager.get_session(session_id, idle_ttl_seconds=idle_ttl_seconds)


def list_hls_sessions(idle_ttl_seconds: float = 30.0) -> list[dict[str, object]]:
    return hls_gateway_manager.list_sessions(idle_ttl_seconds=idle_ttl_seconds)


def stop_hls_session(session_id: str) -> bool:
    return hls_gateway_manager.stop_session(session_id)


def stop_all_hls_sessions() -> None:
    hls_gateway_manager.stop_all()


def resolve_hls_file(
    session_id: str,
    filename: str,
    idle_ttl_seconds: float = 30.0,
) -> Path | None:
    try:
        safe_session_id = hls_gateway_manager._validate_session_id(session_id)
        safe_filename = hls_gateway_manager._validate_asset_name(filename)
    except ValueError:
        return None

    session = get_hls_session(safe_session_id, idle_ttl_seconds=idle_ttl_seconds)
    if not session:
        return None
    session_dir = Path(str(session["dir"])).resolve()
    target = (session_dir / safe_filename).resolve()
    try:
        target.relative_to(session_dir)
    except ValueError:
        return None
    if not os.path.exists(target):
        return None
    return target
