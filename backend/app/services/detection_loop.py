import threading
import time
import traceback

from app.services.camera_service import capture_frame
from app.services.camera_service import current_camera_runtime_status
from app.services.camera_profile_url_service import build_enabled_profile_urls
from app.services.config_service import read_config
from app.services.detection_runtime_state import set_source_annotations
from app.services.encoder_service import configure_inference_device, extract_faces_with_boxes
from app.services.network_camera_pool_service import (
    collect_network_camera_frames,
    network_camera_pool_status,
    sync_network_camera_sources,
)
from app.services.recognition_service import recognize_faces, save_detection


class DetectionLoop:
    def __init__(self) -> None:
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._status_lock = threading.Lock()
        self._source_cursor = 0
        self._cycle_counter = 0
        self._configured_device_preference: str | None = None
        self._performance = {
            "capture_ms": None,
            "decode_ms": None,
            "extract_ms": None,
            "matching_ms": None,
            "inference_ms": None,
            "db_ms": None,
            "cycle_ms": None,
            "processed_sources": 0,
            "skipped_stale_sources": 0,
            "skipped_unstable_sources": 0,
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
            decode_ms=None,
            extract_ms=None,
            matching_ms=None,
            inference_ms=None,
            db_ms=None,
            cycle_ms=None,
            processed_sources=0,
            skipped_stale_sources=0,
            skipped_unstable_sources=0,
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
    def _process_frame(frame) -> tuple[list, list[tuple], float, float]:
        results = []
        annotations = []
        extract_started_at = time.monotonic()
        extracted_faces = list(extract_faces_with_boxes(frame))
        extract_ms = (time.monotonic() - extract_started_at) * 1000.0
        embeddings = [embedding for _, embedding in extracted_faces]
        matching_started_at = time.monotonic()
        recognized_results = recognize_faces(embeddings)
        matching_ms = (time.monotonic() - matching_started_at) * 1000.0
        for (box, _), result in zip(extracted_faces, recognized_results):
            results.append(result)
            if result.status == "reconnu" and result.face_name:
                label = result.face_name
                color = (0, 255, 0)
            else:
                label = "inconnu"
                color = (0, 165, 255)
            annotations.append((box, label, color))
        return results, annotations, extract_ms, matching_ms

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

    @staticmethod
    def _derive_network_frame_age_limit_seconds(detection_interval_seconds: float) -> float:
        return max(0.5, detection_interval_seconds * 2.0)

    @staticmethod
    def _build_decode_runtime_map() -> dict[str, float]:
        decode_map: dict[str, float] = {}
        local_runtime = current_camera_runtime_status()
        decode_map["local"] = float(local_runtime.get("last_read_duration_ms") or 0.0)
        for item in network_camera_pool_status().get("sources", []):
            source = str(item.get("source") or "")
            if source:
                decode_map[source] = float(item.get("last_read_duration_ms") or 0.0)
        return decode_map

    @staticmethod
    def _build_network_runtime_map() -> dict[str, dict[str, object]]:
        runtime_map: dict[str, dict[str, object]] = {}
        for item in network_camera_pool_status().get("sources", []):
            source = str(item.get("source") or "")
            if source:
                runtime_map[source] = item
        return runtime_map

    def _should_skip_unstable_source(
        self,
        source: str,
        network_runtime_map: dict[str, dict[str, object]],
        failure_threshold: int,
        cycle_skip: int,
    ) -> bool:
        if source == "local" or cycle_skip <= 0:
            return False
        runtime = network_runtime_map.get(source)
        if not runtime:
            return False
        consecutive_failures = int(runtime.get("consecutive_failures") or 0)
        if consecutive_failures < failure_threshold:
            return False
        return (self._cycle_counter % (cycle_skip + 1)) != 0

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._cycle_counter += 1
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
                stale_frame_limit_seconds = self._derive_network_frame_age_limit_seconds(
                    config.detection_interval_seconds
                )
                network_frames, skipped_stale_sources = collect_network_camera_frames(
                    max_frame_age_seconds=stale_frame_limit_seconds
                )
                frame_items.extend(network_frames)
                capture_ms = (time.monotonic() - capture_started_at) * 1000.0
                decode_runtime_map = self._build_decode_runtime_map()
                network_runtime_map = self._build_network_runtime_map()
                ordered_items = self._ordered_frame_items(frame_items)

                cycle_budget_seconds = config.multi_camera_cycle_budget_seconds
                started_at = time.monotonic()
                all_results = []
                inference_ms = 0.0
                extract_ms = 0.0
                matching_ms = 0.0
                decode_ms = 0.0
                skipped_unstable_sources = 0

                processed_count = 0
                for source, frame in ordered_items:
                    if processed_count > 0 and (time.monotonic() - started_at) >= cycle_budget_seconds:
                        break
                    if self._should_skip_unstable_source(
                        source,
                        network_runtime_map,
                        config.unstable_source_failure_threshold,
                        config.unstable_source_cycle_skip,
                    ):
                        skipped_unstable_sources += 1
                        continue
                    try:
                        inference_started_at = time.monotonic()
                        results, annotations, frame_extract_ms, frame_matching_ms = self._process_frame(
                            frame
                        )
                        inference_ms += (time.monotonic() - inference_started_at) * 1000.0
                        extract_ms += frame_extract_ms
                        matching_ms += frame_matching_ms
                        decode_ms += decode_runtime_map.get(source, 0.0)
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
                if all_results:
                    save_detection(all_results)
                db_ms = (time.monotonic() - db_started_at) * 1000.0

                elapsed = time.monotonic() - started_at
                cycle_ms = (time.monotonic() - cycle_started_at) * 1000.0
                self._set_performance(
                    capture_ms=round(capture_ms, 3),
                    decode_ms=round(decode_ms, 3),
                    extract_ms=round(extract_ms, 3),
                    matching_ms=round(matching_ms, 3),
                    inference_ms=round(inference_ms, 3),
                    db_ms=round(db_ms, 3),
                    cycle_ms=round(cycle_ms, 3),
                    processed_sources=processed_count,
                    skipped_stale_sources=skipped_stale_sources,
                    skipped_unstable_sources=skipped_unstable_sources,
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
