import threading
import time
import traceback

from app.services.camera_service import capture_frame
from app.services.camera_profile_url_service import build_enabled_profile_urls
from app.services.config_service import read_config
from app.services.detection_runtime_state import set_source_annotations
from app.services.encoder_service import configure_inference_device, extract_faces_with_boxes
from app.services.network_camera_pool_service import (
    collect_network_camera_frames,
    sync_network_camera_sources,
)
from app.services.recognition_service import recognize_face, save_detection


class DetectionLoop:
    def __init__(self) -> None:
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._status_lock = threading.Lock()
        self._source_cursor = 0
        self._configured_device_preference: str | None = None
        self._performance = {
            "capture_ms": None,
            "inference_ms": None,
            "db_ms": None,
            "cycle_ms": None,
            "processed_sources": 0,
            "results_count": 0,
            "updated_at": None,
        }

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)
        self._configured_device_preference = None
        self._set_performance(
            capture_ms=None,
            inference_ms=None,
            db_ms=None,
            cycle_ms=None,
            processed_sources=0,
            results_count=0,
        )

    def _set_performance(self, **metrics) -> None:
        with self._status_lock:
            self._performance = {
                **self._performance,
                **metrics,
                "updated_at": time.time(),
            }

    def status(self) -> dict[str, bool | dict[str, object]]:
        running = bool(self._thread and self._thread.is_alive())
        with self._status_lock:
            performance = dict(self._performance)
        return {"running": running, "performance": performance}

    @staticmethod
    def _process_frame(frame) -> tuple[list, list[tuple]]:
        results = []
        annotations = []
        for box, embedding in extract_faces_with_boxes(frame):
            result = recognize_face(embedding)
            results.append(result)
            if result.status == "reconnu" and result.face_name:
                label = result.face_name
                color = (0, 255, 0)
            else:
                label = "inconnu"
                color = (0, 165, 255)
            annotations.append((box, label, color))
        return results, annotations

    def _ordered_frame_items(self, frame_items: list[tuple[str, object]]) -> list[tuple[str, object]]:
        if not frame_items:
            return []
        count = len(frame_items)
        cursor = self._source_cursor % count
        return frame_items[cursor:] + frame_items[:cursor]

    def _sync_inference_device(self, preference: str) -> None:
        if preference == self._configured_device_preference:
            return
        configure_inference_device(preference)
        self._configured_device_preference = preference

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                cycle_started_at = time.monotonic()
                config = read_config()
                self._sync_inference_device(config.inference_device_preference)
                profile_urls = build_enabled_profile_urls(config.network_camera_profiles)
                merged_network_sources = list(config.network_camera_sources)
                for url in profile_urls:
                    if url not in merged_network_sources:
                        merged_network_sources.append(url)
                sync_network_camera_sources(
                    merged_network_sources,
                    max_sources=10,
                    retry_base_seconds=config.network_camera_retry_base_seconds,
                    retry_max_seconds=config.network_camera_retry_max_seconds,
                )

                capture_started_at = time.monotonic()
                frame_items: list[tuple[str, object]] = []
                primary_frame = capture_frame()
                if primary_frame is not None:
                    frame_items.append(("local", primary_frame))
                frame_items.extend(collect_network_camera_frames())
                capture_ms = (time.monotonic() - capture_started_at) * 1000.0
                ordered_items = self._ordered_frame_items(frame_items)

                cycle_budget_seconds = config.multi_camera_cycle_budget_seconds
                started_at = time.monotonic()
                all_results = []
                inference_ms = 0.0

                processed_count = 0
                for source, frame in ordered_items:
                    if processed_count > 0 and (time.monotonic() - started_at) >= cycle_budget_seconds:
                        break
                    try:
                        inference_started_at = time.monotonic()
                        results, annotations = self._process_frame(frame)
                        inference_ms += (time.monotonic() - inference_started_at) * 1000.0
                        all_results.extend(results)
                        if source:
                            set_source_annotations(source, annotations)
                    except Exception:
                        print("[DETECTION_LOOP] frame processing error:")
                        print(traceback.format_exc())
                    processed_count += 1

                if frame_items:
                    self._source_cursor = (self._source_cursor + max(1, processed_count)) % len(frame_items)

                db_started_at = time.monotonic()
                save_detection(all_results)
                db_ms = (time.monotonic() - db_started_at) * 1000.0

                elapsed = time.monotonic() - started_at
                cycle_ms = (time.monotonic() - cycle_started_at) * 1000.0
                self._set_performance(
                    capture_ms=round(capture_ms, 3),
                    inference_ms=round(inference_ms, 3),
                    db_ms=round(db_ms, 3),
                    cycle_ms=round(cycle_ms, 3),
                    processed_sources=processed_count,
                    results_count=len(all_results),
                )
                sleep_delay = max(0.0, config.detection_interval_seconds - elapsed)
                self._stop_event.wait(sleep_delay)
            except Exception:
                # Keep loop alive even if one iteration fails (camera/DB/model transient errors).
                print("[DETECTION_LOOP] iteration error:")
                print(traceback.format_exc())
                self._configured_device_preference = None
                self._stop_event.wait(0.5)


detection_loop = DetectionLoop()
