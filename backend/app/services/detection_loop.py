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
        self._source_cursor = 0

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

    def status(self) -> dict[str, bool]:
        running = bool(self._thread and self._thread.is_alive())
        return {"running": running}

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

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                config = read_config()
                configure_inference_device(config.inference_device_preference)
                profile_urls = build_enabled_profile_urls(config.network_camera_profiles)
                merged_network_sources = list(config.network_camera_sources)
                for url in profile_urls:
                    if url not in merged_network_sources:
                        merged_network_sources.append(url)
                sync_network_camera_sources(
                    merged_network_sources,
                    max_sources=10,
                )

                frame_items: list[tuple[str, object]] = []
                primary_frame = capture_frame()
                if primary_frame is not None:
                    frame_items.append(("local", primary_frame))
                frame_items.extend(collect_network_camera_frames())
                ordered_items = self._ordered_frame_items(frame_items)

                cycle_budget_seconds = config.multi_camera_cycle_budget_seconds
                started_at = time.monotonic()
                all_results = []

                processed_count = 0
                for source, frame in ordered_items:
                    if processed_count > 0 and (time.monotonic() - started_at) >= cycle_budget_seconds:
                        break
                    try:
                        results, annotations = self._process_frame(frame)
                        all_results.extend(results)
                        if source:
                            set_source_annotations(source, annotations)
                    except Exception:
                        print("[DETECTION_LOOP] frame processing error:")
                        print(traceback.format_exc())
                    processed_count += 1

                if frame_items:
                    self._source_cursor = (self._source_cursor + max(1, processed_count)) % len(frame_items)

                save_detection(all_results)

                elapsed = time.monotonic() - started_at
                sleep_delay = max(0.0, config.detection_interval_seconds - elapsed)
                self._stop_event.wait(sleep_delay)
            except Exception:
                # Keep loop alive even if one iteration fails (camera/DB/model transient errors).
                print("[DETECTION_LOOP] iteration error:")
                print(traceback.format_exc())
                self._stop_event.wait(0.5)


detection_loop = DetectionLoop()
