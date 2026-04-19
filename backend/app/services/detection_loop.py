import threading
import time
import traceback
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait

from app.services.camera_service import capture_frame
from app.services.camera_profile_url_service import build_enabled_profile_urls
from app.services.config_service import read_config
from app.services.detection_runtime_state import set_source_annotations
from app.services.encoder_service import extract_faces_with_boxes
from app.services.network_camera_pool_service import (
    collect_network_camera_frames,
    sync_network_camera_sources,
)
from app.services.recognition_service import recognize_face, save_detection


class DetectionLoop:
    def __init__(self) -> None:
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

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

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                config = read_config()
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

                cycle_budget_seconds = config.multi_camera_cycle_budget_seconds
                started_at = time.monotonic()
                all_results = []

                if frame_items:
                    max_workers = max(1, min(len(frame_items), 10))
                    executor = ThreadPoolExecutor(max_workers=max_workers)
                    try:
                        futures = {
                            executor.submit(self._process_frame, frame): source
                            for source, frame in frame_items
                        }
                        while futures:
                            remaining = cycle_budget_seconds - (time.monotonic() - started_at)
                            if remaining <= 0:
                                break
                            done, pending = wait(
                                futures,
                                timeout=remaining,
                                return_when=FIRST_COMPLETED,
                            )
                            for future in done:
                                source = futures.get(future, "")
                                try:
                                    results, annotations = future.result()
                                    all_results.extend(results)
                                    if source:
                                        set_source_annotations(source, annotations)
                                except Exception:
                                    print("[DETECTION_LOOP] frame processing error:")
                                    print(traceback.format_exc())
                            futures = {future: futures[future] for future in pending}
                    finally:
                        executor.shutdown(wait=False, cancel_futures=True)

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
