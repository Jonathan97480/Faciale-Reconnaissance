import threading
import time
import traceback

import cv2


class NetworkCameraWorker:
    def __init__(self, source: str) -> None:
        self.source = source
        self._frame_lock = threading.Lock()
        self._control_lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._capture = None
        self._latest_frame = None

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

    def _release_capture(self) -> None:
        if self._capture is not None:
            self._capture.release()
            self._capture = None

    def _ensure_capture(self) -> None:
        if self._capture is not None and self._capture.isOpened():
            return
        self._release_capture()
        self._capture = cv2.VideoCapture(self.source)

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._ensure_capture()
                if self._capture is None or not self._capture.isOpened():
                    self._stop_event.wait(0.2)
                    continue

                ok, frame = self._capture.read()
                if not ok:
                    self._release_capture()
                    self._stop_event.wait(0.05)
                    continue

                with self._frame_lock:
                    self._latest_frame = frame
                self._stop_event.wait(0.03)
            except Exception:
                print(f"[NETWORK_CAMERA_WORKER] source={self.source} error:")
                print(traceback.format_exc())
                self._stop_event.wait(0.2)

        self._release_capture()


class NetworkCameraPool:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._workers: dict[str, NetworkCameraWorker] = {}

    def sync_sources(self, sources: list[str], max_sources: int = 10) -> None:
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

            for source in unique_sources:
                if source in self._workers:
                    continue
                worker = NetworkCameraWorker(source)
                worker.start()
                self._workers[source] = worker

    def collect_frames(self) -> list[tuple[str, object]]:
        with self._lock:
            items = list(self._workers.items())
        frames: list[tuple[str, object]] = []
        for source, worker in items:
            frame = worker.get_latest_frame()
            if frame is not None:
                frames.append((source, frame))
        return frames

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
            sources = list(self._workers.keys())
        return {
            "configured_sources_count": len(sources),
            "configured_sources": sources,
        }


network_camera_pool = NetworkCameraPool()


def sync_network_camera_sources(sources: list[str], max_sources: int = 10) -> None:
    network_camera_pool.sync_sources(sources, max_sources=max_sources)


def collect_network_camera_frames() -> list[tuple[str, object]]:
    return network_camera_pool.collect_frames()


def stop_network_camera_pool() -> None:
    network_camera_pool.stop()


def network_camera_pool_status() -> dict[str, object]:
    return network_camera_pool.status()


def get_network_camera_frame(source: str):
    return network_camera_pool.get_frame_for_source(source)


def has_network_camera_source(source: str) -> bool:
    return network_camera_pool.has_source(source)
