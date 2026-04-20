import io
import time

from app.services.hls_gateway_service import HlsSessionManager, resolve_hls_file


class _FakeProcess:
    def __init__(self, exit_code, stderr_text):
        self._exit_code = exit_code
        self.stderr = io.StringIO(stderr_text)

    def poll(self):
        return self._exit_code


def test_hls_session_status_reports_manifest_segments_and_ffmpeg_error(tmp_path):
    session_dir = tmp_path / "hls"
    session_dir.mkdir()
    manifest_path = session_dir / "index.m3u8"
    manifest_path.write_text(
        "#EXTM3U\n#EXTINF:2.0,\nseg-0001.ts\n#EXTINF:2.0,\nseg-0002.ts\n",
        encoding="utf-8",
    )

    manager = HlsSessionManager()
    session = {
        "id": "sess-1",
        "profile_name": "Main cam",
        "manifest": str(manifest_path),
        "started_at": 100.0,
        "last_used_at": 101.0,
        "process": _FakeProcess(exit_code=1, stderr_text="Connection refused"),
        "stderr_tail": "",
    }

    status = manager._session_status(session)

    assert status["running"] is False
    assert status["manifest_ready"] is True
    assert status["segment_count"] == 2
    assert status["last_exit_code"] == 1
    assert status["last_error"] == "Connection refused"
    assert status["manifest_updated_at"] is not None


def test_hls_gateway_rejects_non_rtsp_proxy_sources():
    manager = HlsSessionManager()

    try:
        manager._validate_gateway_source_url("http://cam.local/stream.m3u8")
    except ValueError as exc:
        assert str(exc) == "Le proxy HLS accepte uniquement les flux RTSP"
    else:
        raise AssertionError("La source HTTP ne doit pas etre acceptee par le proxy HLS")


def test_stop_session_removes_hls_session_directory(tmp_path):
    session_dir = tmp_path / "sess"
    session_dir.mkdir()
    (session_dir / "index.m3u8").write_text("#EXTM3U\n", encoding="utf-8")

    manager = HlsSessionManager()
    manager._sessions_by_id["abc123def456"] = {
        "id": "abc123def456",
        "profile_name": "Main cam",
        "dir": str(session_dir),
        "process": None,
    }
    manager._sessions_by_profile["Main cam"] = {"id": "abc123def456"}

    removed = manager.stop_session("abc123def456")

    assert removed is True
    assert not session_dir.exists()


def test_resolve_hls_file_rejects_unexpected_asset_name(monkeypatch, tmp_path):
    session_dir = tmp_path / "hls"
    session_dir.mkdir()
    (session_dir / "index.m3u8").write_text("#EXTM3U\n", encoding="utf-8")

    monkeypatch.setattr(
        "app.services.hls_gateway_service.get_hls_session",
        lambda session_id, idle_ttl_seconds=30.0: {
            "id": session_id,
            "dir": str(session_dir),
        },
    )

    assert resolve_hls_file("abc123def456", "index.m3u8") is not None
    assert resolve_hls_file("abc123def456", "../secret.txt") is None
    assert resolve_hls_file("abc123def456", "playlist.m3u8") is None
    assert resolve_hls_file("bad-id", "index.m3u8") is None


def test_hls_manager_prunes_lru_session_when_max_is_reached(tmp_path):
    first_dir = tmp_path / "sess-1"
    second_dir = tmp_path / "sess-2"
    first_dir.mkdir()
    second_dir.mkdir()

    manager = HlsSessionManager()
    now = time.time()
    manager._sessions_by_id = {
        "aaa111bbb222": {
            "id": "aaa111bbb222",
            "profile_name": "Cam A",
            "dir": str(first_dir),
            "process": None,
            "last_used_at": now - 10.0,
        },
        "ccc333ddd444": {
            "id": "ccc333ddd444",
            "profile_name": "Cam B",
            "dir": str(second_dir),
            "process": None,
            "last_used_at": now - 1.0,
        },
    }
    manager._sessions_by_profile = {
        "Cam A": {"id": "aaa111bbb222"},
        "Cam B": {"id": "ccc333ddd444"},
    }

    manager._prune_sessions(max_sessions=2, idle_ttl_seconds=9999.0)

    assert "aaa111bbb222" not in manager._sessions_by_id
    assert "ccc333ddd444" in manager._sessions_by_id


def test_hls_manager_prunes_idle_sessions(tmp_path):
    idle_dir = tmp_path / "sess-idle"
    idle_dir.mkdir()

    manager = HlsSessionManager()
    manager._sessions_by_id = {
        "aaa111bbb222": {
            "id": "aaa111bbb222",
            "profile_name": "Cam idle",
            "dir": str(idle_dir),
            "process": None,
            "last_used_at": time.time() - 60.0,
        }
    }
    manager._sessions_by_profile = {"Cam idle": {"id": "aaa111bbb222"}}

    manager._prune_sessions(max_sessions=2, idle_ttl_seconds=0.1)

    assert manager._sessions_by_id == {}
    assert not idle_dir.exists()
