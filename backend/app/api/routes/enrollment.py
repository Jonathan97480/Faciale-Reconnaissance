import time

from fastapi import APIRouter, Depends, HTTPException

from app.api.routes.auth import get_current_user
from app.core.schemas import FaceCreatePayload, FaceEnrollPayload, FaceRecord
from app.services.camera_service import capture_frame
from app.services.config_service import read_config
from app.services.encoder_service import configure_inference_device, extract_averaged_embedding
from app.services.face_service import create_face

router = APIRouter(
    prefix="/faces",
    tags=["enrollment"],
    dependencies=[Depends(get_current_user)],
)


@router.post("/enroll", response_model=FaceRecord)
def enroll_face(payload: FaceEnrollPayload) -> FaceRecord:
    """Capture N frames from the webcam, average embeddings, and store the face.

    N is configurable via enroll_frames_count in the app configuration.
    Using multiple frames produces a more stable reference embedding.
    """
    config = read_config()
    configure_inference_device(config.inference_device_preference)
    n = config.enroll_frames_count

    frames = []
    for _ in range(n):
        frame = capture_frame()
        if frame is not None:
            frames.append(frame)
        time.sleep(0.1)

    if not frames:
        raise HTTPException(status_code=503, detail="Webcam unavailable")

    embedding = extract_averaged_embedding(frames)
    if embedding is None:
        raise HTTPException(status_code=422, detail="No face detected in webcam frames")

    return create_face(FaceCreatePayload(name=payload.name, encoding=embedding))
