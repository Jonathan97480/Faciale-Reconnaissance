import base64

import cv2
import numpy as np

from app.services.config_service import read_config
from app.services.encoder_service import extract_faces_with_boxes
from app.services.recognition_service import recognize_face


def _decode_image(image_bytes: bytes):
    if not image_bytes:
        raise ValueError("Image vide")

    raw = np.frombuffer(image_bytes, dtype=np.uint8)
    frame = cv2.imdecode(raw, cv2.IMREAD_COLOR)
    if frame is None:
        raise ValueError("Image invalide")
    return frame


def _expand_box(
    box: tuple[int, int, int, int],
    width: int,
    height: int,
    padding_ratio: float,
) -> tuple[int, int, int, int]:
    x1, y1, x2, y2 = box
    box_width = max(1, x2 - x1)
    box_height = max(1, y2 - y1)

    pad_x = int(box_width * padding_ratio)
    pad_y = int(box_height * padding_ratio)

    return (
        max(0, x1 - pad_x),
        max(0, y1 - pad_y),
        min(width - 1, x2 + pad_x),
        min(height - 1, y2 + pad_y),
    )


def _to_box_dict(box: tuple[int, int, int, int]) -> dict[str, int]:
    return {
        "x1": int(box[0]),
        "y1": int(box[1]),
        "x2": int(box[2]),
        "y2": int(box[3]),
    }


def _encode_crop_to_base64(frame, box: tuple[int, int, int, int]) -> str | None:
    x1, y1, x2, y2 = box
    crop = frame[y1:y2, x1:x2]
    if crop.size == 0:
        return None

    ok, encoded = cv2.imencode(".jpg", crop)
    if not ok:
        return None

    return base64.b64encode(encoded.tobytes()).decode("ascii")


def analyze_image_bytes(image_bytes: bytes) -> dict[str, object]:
    frame = _decode_image(image_bytes)
    config = read_config()

    height, width = frame.shape[:2]
    face_matches = extract_faces_with_boxes(frame)

    faces: list[dict[str, object]] = []
    for box, embedding in face_matches:
        expanded_box = _expand_box(
            box,
            width,
            height,
            config.face_crop_padding_ratio,
        )
        result = recognize_face(embedding)

        faces.append(
            {
                "status": result.status,
                "face_id": result.face_id,
                "face_name": result.face_name,
                "score": result.score,
                "box": _to_box_dict(box),
                "expanded_box": _to_box_dict(expanded_box),
                "face_image_base64": _encode_crop_to_base64(frame, expanded_box),
            }
        )

    return {
        "faces_count": len(faces),
        "faces": faces,
    }
