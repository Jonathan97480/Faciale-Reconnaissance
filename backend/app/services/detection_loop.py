import threading
import time
import traceback
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait

from app.services.camera_service import capture_frame
from app.services.config_service import read_config
from app.services.encoder_service import extract_embeddings
from app.services.network_camera_pool_service import (
    collect_network_camera_frames,
    sync_network_camera_sources,
)
from app.services.recognition_service import recognize_faces, save_detection


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
    def _process_frame(frame) -> list:
        embeddings = extract_embeddings(frame)
        return recognize_faces(embeddings)

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                config = read_config()
                sync_network_camera_sources(
                    config.network_camera_sources,
                    max_sources=10,
                )

                frames = []
                primary_frame = capture_frame()
                if primary_frame is not None:
                    frames.append(primary_frame)
                frames.extend([frame for _, frame in collect_network_camera_frames()])

                cycle_budget_seconds = config.multi_camera_cycle_budget_seconds
                started_at = time.monotonic()
                all_results = []

                if frames:
                    max_workers = max(1, min(len(frames), 10))
                    executor = ThreadPoolExecutor(max_workers=max_workers)
                    try:
                        futures = {executor.submit(self._process_frame, frame) for frame in frames}
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
                                try:
                                    all_results.extend(future.result())
                                except Exception:
                                    print("[DETECTION_LOOP] frame processing error:")
                                    print(traceback.format_exc())
                            futures = pending
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
