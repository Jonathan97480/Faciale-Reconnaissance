import threading
import time


class DetectionRuntimeState:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._by_source: dict[str, dict[str, object]] = {}

    def set_annotations(self, source: str, annotations: list[tuple]) -> None:
        with self._lock:
            self._by_source[source] = {
                "annotations": list(annotations),
                "updated_at": time.time(),
            }

    def get_annotations(self, source: str) -> list[tuple]:
        with self._lock:
            data = self._by_source.get(source)
            if not data:
                return []
            return list(data["annotations"])

    def get_updated_at(self, source: str) -> float | None:
        with self._lock:
            data = self._by_source.get(source)
            if not data:
                return None
            return float(data["updated_at"])


runtime_detection_state = DetectionRuntimeState()


def set_source_annotations(source: str, annotations: list[tuple]) -> None:
    runtime_detection_state.set_annotations(source, annotations)


def get_source_annotations(source: str) -> list[tuple]:
    return runtime_detection_state.get_annotations(source)


def get_source_annotations_updated_at(source: str) -> float | None:
    return runtime_detection_state.get_updated_at(source)
