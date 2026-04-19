import time

import cv2

from app.services.encoder_service import extract_faces_with_boxes
from app.services.network_camera_pool_service import get_network_camera_frame
from app.services.recognition_service import recognize_face


def _annotate_frame(frame):
    preview_frame = frame.copy()
    face_data = extract_faces_with_boxes(frame)
    for box, embedding in face_data:
        result = recognize_face(embedding)
        if result.status == "reconnu" and result.face_name:
            label = result.face_name
            color = (0, 255, 0)
        else:
            label = "inconnu"
            color = (0, 165, 255)
        left, top, right, bottom = box
        cv2.rectangle(preview_frame, (left, top), (right, bottom), color, 2)
        cv2.putText(
            preview_frame,
            label,
            (left, max(0, top - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            color,
            2,
        )
    return preview_frame


def get_network_preview_jpeg(source: str) -> bytes | None:
    frame = get_network_camera_frame(source)
    if frame is None:
        return None
    preview_frame = _annotate_frame(frame)
    ok, encoded = cv2.imencode(".jpg", preview_frame)
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
