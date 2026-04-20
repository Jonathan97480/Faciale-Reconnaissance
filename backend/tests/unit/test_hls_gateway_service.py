import io

from app.services.hls_gateway_service import HlsSessionManager


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
