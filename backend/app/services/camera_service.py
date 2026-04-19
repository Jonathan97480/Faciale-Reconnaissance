
import os
import threading
import time
import traceback

import cv2

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
        self._annotations_lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._annotation_thread: threading.Thread | None = None
        self._capture = None
        self._camera_index: int | None = None
        self._camera_source: str | None = None
        self._latest_frame = None
        self._latest_jpeg: bytes | None = None
        self._annotations: list = []

    def start(self) -> None:
        with self._control_lock:
            if self._thread and self._thread.is_alive():
                return
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()
            self._annotation_thread = threading.Thread(
                target=self._annotate_run, daemon=True
            )
            self._annotation_thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        for thread in (self._thread, self._annotation_thread):
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

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._switch_camera_if_needed()

                if self._capture is None or not self._capture.isOpened():
                    self._stop_event.wait(0.2)
                    continue

                ret, frame = self._capture.read()
                if not ret:
                    self._stop_event.wait(0.05)
                    continue

                preview_frame = frame.copy()
                with self._annotations_lock:
                    current_annotations = list(self._annotations)
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

                # ~30 FPS preview target.
                self._stop_event.wait(0.03)
            except Exception:
                print("[CAMERA_RUNTIME] capture loop error:")
                print(traceback.format_exc())
                self._stop_event.wait(0.2)

        self._release_capture()

    def _annotate_run(self) -> None:
        from app.services.encoder_service import extract_faces_with_boxes
        from app.services.recognition_service import recognize_face

        while not self._stop_event.is_set():
            try:
                frame = self.get_latest_frame()
                if frame is not None:
                    face_data = extract_faces_with_boxes(frame)
                    annotations = []
                    for box, embedding in face_data:
                        result = recognize_face(embedding)
                        if result.status == "reconnu" and result.face_name:
                            label = result.face_name
                            color = (0, 255, 0)   # vert = reconnu
                        else:
                            label = "inconnu"
                            color = (0, 165, 255)  # orange = inconnu
                        annotations.append((box, label, color))
                    with self._annotations_lock:
                        self._annotations = annotations
            except Exception:
                print("[CAMERA_RUNTIME] annotation loop error:")
                print(traceback.format_exc())
            self._stop_event.wait(1.0)


_camera_runtime = SharedCameraRuntime()


def capture_frame():
    """Return the latest frame from a shared camera runtime or None."""
    return _camera_runtime.get_latest_frame()


def current_capture_settings() -> dict[str, float | int]:
    config = read_config()
    return {
        "detection_interval_seconds": config.detection_interval_seconds,
        "camera_index": config.camera_index,
    }


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

