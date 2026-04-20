
import os
import threading
import time
import traceback

import cv2

from app.services.detection_runtime_state import get_source_annotations
from app.services.detection_runtime_state import get_source_annotations_updated_at
from app.services.config_service import read_config

def _open_capture(camera_index: int = 0, camera_source: str = ""):
    """
    Ouvre une source vidéo : index webcam locale (int), URL réseau (str), ou chemin fichier vidéo.
    Si camera_source est non vide, priorité à cette valeur.
    """
    if camera_source:
        return cv2.VideoCapture(camera_source)
    if os.name == "nt":
        capture = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
        if capture.isOpened():
            return capture
        capture.release()
    return cv2.VideoCapture(camera_index)


class SharedCameraRuntime:
    def __init__(self) -> None:
        self._control_lock = threading.Lock()
        self._frame_lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._capture = None
        self._camera_index: int | None = None
        self._camera_source: str | None = None
        self._latest_frame = None
        self._latest_jpeg: bytes | None = None
        self._latest_frame_at: float | None = None
        self._last_error: str | None = None
        self._consecutive_failures = 0
        self._last_read_duration_ms = 0.0
        self._last_connect_at: float | None = None

    def start(self) -> None:
        with self._control_lock:
            if self._thread and self._thread.is_alive():
                return
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        for thread in (self._thread,):
            if thread and thread.is_alive():
                thread.join(timeout=2)
        with self._control_lock:
            self._release_capture()

    def get_latest_frame(self):
        self.start()
        with self._frame_lock:
            if self._latest_frame is None:
                return None
            return self._latest_frame.copy()

    def get_latest_jpeg(self) -> bytes | None:
        self.start()
        with self._frame_lock:
            return self._latest_jpeg

    def stats(self) -> dict[str, object]:
        with self._frame_lock:
            latest_frame_at = self._latest_frame_at
        return {
            "source": "local",
            "is_running": bool(self._thread and self._thread.is_alive()),
            "has_frame": latest_frame_at is not None,
            "latest_frame_at": latest_frame_at,
            "last_detection_at": get_source_annotations_updated_at("local"),
            "last_error": self._last_error,
            "consecutive_failures": self._consecutive_failures,
            "last_read_duration_ms": round(self._last_read_duration_ms, 2),
            "last_connect_at": self._last_connect_at,
            "camera_index": self._camera_index,
            "camera_source": self._camera_source or "",
        }

    def _set_error(self, message: str) -> None:
        if message == self._last_error:
            self._consecutive_failures += 1
            return
        self._last_error = message
        self._consecutive_failures += 1

    def _set_success(self) -> None:
        self._last_error = None
        self._consecutive_failures = 0

    def _release_capture(self) -> None:
        if self._capture is not None:
            self._capture.release()
            self._capture = None

    def _switch_camera_if_needed(self) -> None:
        config = read_config()
        configured_index = int(config.camera_index)
        configured_source = config.camera_source or ""
        # Si la config n'a pas changé, ne rien faire
        if (
            configured_index == self._camera_index
            and configured_source == (self._camera_source or "")
            and self._capture is not None
        ):
            return

        self._release_capture()
        self._camera_index = configured_index
        self._camera_source = configured_source
        self._capture = _open_capture(configured_index, configured_source)
        if self._capture is not None and self._capture.isOpened():
            self._last_connect_at = time.time()
            self._set_success()
        else:
            self._set_error("Cannot open local camera")

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._switch_camera_if_needed()

                if self._capture is None or not self._capture.isOpened():
                    self._set_error("Local camera unavailable")
                    self._stop_event.wait(0.2)
                    continue

                read_started = time.monotonic()
                ret, frame = self._capture.read()
                self._last_read_duration_ms = (
                    time.monotonic() - read_started
                ) * 1000.0
                if not ret:
                    self._set_error("Local camera read failed")
                    self._stop_event.wait(0.05)
                    continue

                preview_frame = frame.copy()
                current_annotations = get_source_annotations("local")
                for (left, top, right, bottom), label, color in current_annotations:
                    cv2.rectangle(preview_frame, (left, top), (right, bottom), color, 2)
                    cv2.putText(
                        preview_frame, label,
                        (left, max(0, top - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2,
                    )

                success, encoded = cv2.imencode(".jpg", preview_frame)
                if not success:
                    self._stop_event.wait(0.02)
                    continue

                with self._frame_lock:
                    self._latest_frame = frame
                    self._latest_jpeg = encoded.tobytes()
                    self._latest_frame_at = time.time()
                self._set_success()

                # ~30 FPS preview target.
                self._stop_event.wait(0.03)
            except Exception:
                self._set_error("Local camera worker exception")
                print("[CAMERA_RUNTIME] capture loop error:")
                print(traceback.format_exc())
                self._stop_event.wait(0.2)

        self._release_capture()


_camera_runtime = SharedCameraRuntime()


def capture_frame():
    """Return the latest frame from a shared camera runtime or None."""
    return _camera_runtime.get_latest_frame()


def current_capture_settings() -> dict[str, float | int]:
    config = read_config()
    return {
        "detection_interval_seconds": config.detection_interval_seconds,
        "camera_index": config.camera_index,
        "camera_source": config.camera_source,
    }


def current_camera_runtime_status() -> dict[str, object]:
    return _camera_runtime.stats()


def capture_preview_jpeg() -> bytes | None:
    """Return the latest JPEG preview bytes from shared camera runtime."""
    return _camera_runtime.get_latest_jpeg()


def stream_preview_frames():
    """Yield a continuous MJPEG stream from shared camera runtime."""
    _camera_runtime.start()
    while True:
        jpg = _camera_runtime.get_latest_jpeg()
        if jpg is None:
            time.sleep(0.05)
            continue

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n"
            b"Cache-Control: no-cache\r\n\r\n" + jpg + b"\r\n"
        )


def stop_camera_runtime() -> None:
    _camera_runtime.stop()

