import time

import cv2

from app.services.detection_runtime_state import get_source_annotations
from app.services.network_camera_pool_service import get_network_camera_frame


def get_network_preview_jpeg(source: str) -> bytes | None:
    frame = get_network_camera_frame(source)
    if frame is None:
        return None
    preview = frame.copy()
    annotations = get_source_annotations(source)
    for box, label, color in annotations:
        left, top, right, bottom = box
        cv2.rectangle(preview, (left, top), (right, bottom), color, 2)
        cv2.putText(
            preview,
            label,
            (left, max(0, top - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            color,
            2,
        )
    ok, encoded = cv2.imencode(".jpg", preview)
    if not ok:
        return None
    return encoded.tobytes()


def stream_network_preview_frames(source: str):
    while True:
        jpg = get_network_preview_jpeg(source)
        if jpg is None:
            time.sleep(0.05)
            continue
        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n"
            b"Cache-Control: no-cache\r\n\r\n" + jpg + b"\r\n"
        )
