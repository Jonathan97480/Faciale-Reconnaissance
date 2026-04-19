import threading
import traceback

from app.services.camera_service import capture_frame
from app.services.config_service import read_config
from app.services.encoder_service import extract_embeddings
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

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                frame = capture_frame()
                embeddings = extract_embeddings(frame)
                results = recognize_faces(embeddings)
                save_detection(results)

                config = read_config()
                self._stop_event.wait(config.detection_interval_seconds)
            except Exception:
                # Keep loop alive even if one iteration fails (camera/DB/model transient errors).
                print("[DETECTION_LOOP] iteration error:")
                print(traceback.format_exc())
                self._stop_event.wait(0.5)


detection_loop = DetectionLoop()
