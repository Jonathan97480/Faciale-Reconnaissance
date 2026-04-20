import threading
import time
import traceback
from urllib.parse import urlsplit, urlunsplit

import cv2

from app.services.camera_event_log_service import log_camera_event
from app.services.detection_runtime_state import get_source_annotations_updated_at
from app.services.network_url_validation_service import validate_network_stream_url


class NetworkCameraWorker:
    def __init__(
        self,
        source: str,
        retry_base_seconds: float = 0.5,
        retry_max_seconds: float = 8.0,
    ) -> None:
        self.source = validate_network_stream_url(source)
        self._retry_base_seconds = retry_base_seconds
        self._retry_max_seconds = retry_max_seconds
        self._frame_lock = threading.Lock()
        self._control_lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._capture = None
        self._latest_frame = None
        self._latest_frame_at: float | None = None
        self._last_error: str | None = None
        self._consecutive_failures = 0
        self._last_read_duration_ms = 0.0
        self._last_connect_at: float | None = None
        self._next_retry_at: float | None = None
        self._current_retry_delay_seconds = 0.0

    def start(self) -> None:
        with self._control_lock:
            if self._thread and self._thread.is_alive():
                return
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        thread = self._thread
        if thread and thread.is_alive():
            thread.join(timeout=2)
        with self._control_lock:
            self._release_capture()

    def get_latest_frame(self):
        with self._frame_lock:
            if self._latest_frame is None:
                return None
            return self._latest_frame.copy()

    def has_recent_frame(self, max_age_seconds: float | None, now: float | None = None) -> bool:
        if max_age_seconds is None:
            with self._frame_lock:
                return self._latest_frame is not None
        with self._frame_lock:
            latest_frame_at = self._latest_frame_at
        if latest_frame_at is None:
            return False
        reference_now = now if now is not None else time.time()
        return (reference_now - latest_frame_at) <= max_age_seconds

    def stats(self) -> dict[str, object]:
        with self._frame_lock:
            latest_frame_at = self._latest_frame_at
        latest_frame_age_seconds = None
        if latest_frame_at is not None:
            latest_frame_age_seconds = max(0.0, time.time() - latest_frame_at)
        return {
            "source": self.source,
            "is_running": bool(self._thread and self._thread.is_alive()),
            "has_frame": latest_frame_at is not None,
            "latest_frame_at": latest_frame_at,
            "latest_frame_age_seconds": round(latest_frame_age_seconds, 3)
            if latest_frame_age_seconds is not None
            else None,
            "last_detection_at": get_source_annotations_updated_at(self.source),
            "last_error": self._last_error,
            "consecutive_failures": self._consecutive_failures,
            "last_read_duration_ms": round(self._last_read_duration_ms, 2),
            "last_connect_at": self._last_connect_at,
            "next_retry_at": self._next_retry_at,
            "retry_delay_seconds": round(self._current_retry_delay_seconds, 3),
        }

    def _set_error(self, message: str) -> None:
        if message == self._last_error:
            self._consecutive_failures += 1
            return
        self._last_error = message
        self._consecutive_failures += 1
        log_camera_event(self.source, "error", message)

    def _set_success(self) -> None:
        self._last_error = None
        self._consecutive_failures = 0
        self._next_retry_at = None
        self._current_retry_delay_seconds = 0.0

    def update_backoff(self, retry_base_seconds: float, retry_max_seconds: float) -> None:
        self._retry_base_seconds = retry_base_seconds
        self._retry_max_seconds = max(retry_max_seconds, retry_base_seconds)

    def _release_capture(self) -> None:
        if self._capture is not None:
            self._capture.release()
            self._capture = None

    @staticmethod
    def _strip_query_string(source: str) -> str:
        parts = urlsplit(source)
        if not parts.scheme or not parts.netloc or not parts.query:
            return source
        return urlunsplit((parts.scheme, parts.netloc, parts.path, "", parts.fragment))

    @staticmethod
    def _open_capture(source: str):
        # Prefer FFmpeg for network URLs; keep default backend as fallback.
        attempts = [(source, cv2.CAP_FFMPEG), (source, cv2.CAP_ANY)]
        normalized = NetworkCameraWorker._strip_query_string(source)
        if normalized != source:
            attempts.extend([(normalized, cv2.CAP_FFMPEG), (normalized, cv2.CAP_ANY)])

        for attempt_source, backend in attempts:
            capture = cv2.VideoCapture(attempt_source, backend)
            if capture is not None and capture.isOpened():
                return capture
            if capture is not None:
                capture.release()
        return None

    def _ensure_capture(self) -> None:
        if self._capture is not None and self._capture.isOpened():
            return
        if self._next_retry_at is not None:
            remaining = self._next_retry_at - time.time()
            if remaining > 0:
                self._stop_event.wait(min(0.2, remaining))
                return
        self._release_capture()
        self._capture = self._open_capture(self.source)
        if self._capture is not None and self._capture.isOpened():
            self._last_connect_at = time.time()
            self._set_success()
            log_camera_event(self.source, "connect", "Stream connected")
        else:
            self._set_error("Cannot open stream")
            self._schedule_retry()

    def _schedule_retry(self) -> None:
        exponent = max(0, self._consecutive_failures - 1)
        delay = min(
            self._retry_max_seconds,
            self._retry_base_seconds * (2**exponent),
        )
        self._current_retry_delay_seconds = delay
        self._next_retry_at = time.time() + delay

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._ensure_capture()
                if self._capture is None or not self._capture.isOpened():
                    self._stop_event.wait(0.2)
                    continue

                read_started = time.monotonic()
                ok, frame = self._capture.read()
                self._last_read_duration_ms = (time.monotonic() - read_started) * 1000.0
                if not ok or frame is None or frame.size == 0:
                    self._set_error("Capture read failed")
                    self._release_capture()
                    self._schedule_retry()
                    continue

                with self._frame_lock:
                    self._latest_frame = frame
                    self._latest_frame_at = time.time()
                self._set_success()
                self._stop_event.wait(0.03)
            except Exception:
                self._set_error("Worker exception")
                self._schedule_retry()
                print(f"[NETWORK_CAMERA_WORKER] source={self.source} error:")
                print(traceback.format_exc())
                self._stop_event.wait(0.2)

        self._release_capture()


class NetworkCameraPool:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._workers: dict[str, NetworkCameraWorker] = {}

    def sync_sources(
        self,
        sources: list[str],
        max_sources: int = 10,
        retry_base_seconds: float = 0.5,
        retry_max_seconds: float = 8.0,
    ) -> None:
        unique_sources: list[str] = []
        for source in sources:
            cleaned = source.strip()
            if cleaned and cleaned not in unique_sources:
                unique_sources.append(cleaned)
        unique_sources = unique_sources[:max_sources]

        with self._lock:
            current_sources = set(self._workers.keys())
            desired_sources = set(unique_sources)

            for source in current_sources - desired_sources:
                worker = self._workers.pop(source)
                worker.stop()
                log_camera_event(source, "stop", "Source removed from runtime")

            for source in unique_sources:
                if source in self._workers:
                    self._workers[source].update_backoff(
                        retry_base_seconds=retry_base_seconds,
                        retry_max_seconds=retry_max_seconds,
                    )
                    continue
                worker = NetworkCameraWorker(
                    source,
                    retry_base_seconds=retry_base_seconds,
                    retry_max_seconds=retry_max_seconds,
                )
                worker.start()
                self._workers[source] = worker
                log_camera_event(source, "start", "Source added to runtime")

    def collect_frames(
        self,
        max_frame_age_seconds: float | None = None,
    ) -> tuple[list[tuple[str, object]], int]:
        with self._lock:
            items = list(self._workers.items())
        frames: list[tuple[str, object]] = []
        skipped_stale = 0
        now = time.time()
        for source, worker in items:
            if not worker.has_recent_frame(max_frame_age_seconds, now=now):
                skipped_stale += 1
                continue
            frame = worker.get_latest_frame()
            if frame is not None:
                frames.append((source, frame))
            else:
                skipped_stale += 1
        return frames, skipped_stale

    def get_frame_for_source(self, source: str):
        with self._lock:
            worker = self._workers.get(source)
        if worker is None:
            return None
        return worker.get_latest_frame()

    def has_source(self, source: str) -> bool:
        with self._lock:
            return source in self._workers

    def stop(self) -> None:
        with self._lock:
            workers = list(self._workers.values())
            self._workers.clear()
        for worker in workers:
            worker.stop()

    def status(self) -> dict[str, object]:
        with self._lock:
            items = list(self._workers.items())
        source_stats = [worker.stats() for _, worker in items]
        return {
            "configured_sources_count": len(source_stats),
            "configured_sources": [item["source"] for item in source_stats],
            "sources": source_stats,
        }


network_camera_pool = NetworkCameraPool()


def sync_network_camera_sources(
    sources: list[str],
    max_sources: int = 10,
    retry_base_seconds: float = 0.5,
    retry_max_seconds: float = 8.0,
) -> None:
    network_camera_pool.sync_sources(
        sources,
        max_sources=max_sources,
        retry_base_seconds=retry_base_seconds,
        retry_max_seconds=retry_max_seconds,
    )


def collect_network_camera_frames(
    max_frame_age_seconds: float | None = None,
) -> tuple[list[tuple[str, object]], int]:
    return network_camera_pool.collect_frames(max_frame_age_seconds=max_frame_age_seconds)


def stop_network_camera_pool() -> None:
    network_camera_pool.stop()


def network_camera_pool_status() -> dict[str, object]:
    return network_camera_pool.status()


def get_network_camera_frame(source: str):
    return network_camera_pool.get_frame_for_source(source)


def has_network_camera_source(source: str) -> bool:
    return network_camera_pool.has_source(source)
