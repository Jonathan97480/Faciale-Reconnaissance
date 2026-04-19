import base64
import binascii

from fastapi import APIRouter, HTTPException, Query, Request, Response
from fastapi.responses import StreamingResponse

from app.core.schemas import (
    ImageBatchAnalyzeRequest,
    ImageBatchItemResponse,
    ImageBatchRecognitionResponse,
    ImageRecognitionResponse,
    RecognitionCheckPayload,
    RecognitionResult,
)
from app.services.camera_service import (
    capture_preview_jpeg,
    current_capture_settings,
    stream_preview_frames,
)
from app.services.detection_loop import detection_loop
from app.services.image_recognition_service import analyze_image_bytes
from app.services.network_camera_pool_service import network_camera_pool_status
from app.services.recognition_service import (
    get_detection_history,
    get_latest_detection,
    recognize_face,
    save_detection,
)

router = APIRouter(prefix="/recognition", tags=["recognition"])


def _is_allowed_image_content_type(content_type: str | None) -> bool:
    if not content_type:
        return True
    return content_type.startswith("image/") or content_type.startswith(
        "application/octet-stream"
    )


@router.post("/check", response_model=RecognitionResult)
def check_face(payload: RecognitionCheckPayload) -> RecognitionResult:
    result = recognize_face(payload.embedding)
    save_detection([result])
    return result


@router.get("/loop/status")
def get_loop_status() -> dict[str, object]:
    return {
        "loop": detection_loop.status(),
        "capture_settings": current_capture_settings(),
        "network_cameras": network_camera_pool_status(),
    }


@router.get("/latest")
def get_latest() -> dict[str, object]:
    latest = get_latest_detection()
    return {"detection": latest}


@router.get("/history")
def get_history(limit: int = Query(default=10, ge=1, le=50)) -> dict[str, object]:
    return {"detections": get_detection_history(limit)}


@router.post("/analyze-image", response_model=ImageRecognitionResponse)
async def analyze_image(request: Request) -> ImageRecognitionResponse:
    content_type = request.headers.get("content-type", "")
    if not _is_allowed_image_content_type(content_type):
        raise HTTPException(status_code=415, detail="Content-Type image attendu")

    image_bytes = await request.body()
    try:
        payload = analyze_image_bytes(image_bytes)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return ImageRecognitionResponse(**payload)


@router.post("/analyze-images", response_model=ImageBatchRecognitionResponse)
def analyze_images(payload: ImageBatchAnalyzeRequest) -> ImageBatchRecognitionResponse:
    if not payload.items:
        raise HTTPException(status_code=400, detail="Aucune image fournie")

    items: list[ImageBatchItemResponse] = []
    success_count = 0

    for item in payload.items:
        if not _is_allowed_image_content_type(item.content_type):
            items.append(
                ImageBatchItemResponse(
                    filename=item.filename,
                    content_type=item.content_type,
                    ok=False,
                    error="Content-Type image attendu",
                    result=None,
                )
            )
            continue

        try:
            image_bytes = base64.b64decode(item.image_base64, validate=True)
        except (binascii.Error, ValueError):
            items.append(
                ImageBatchItemResponse(
                    filename=item.filename,
                    content_type=item.content_type,
                    ok=False,
                    error="image_base64 invalide",
                    result=None,
                )
            )
            continue

        try:
            result_payload = analyze_image_bytes(image_bytes)
            items.append(
                ImageBatchItemResponse(
                    filename=item.filename,
                    content_type=item.content_type,
                    ok=True,
                    error=None,
                    result=ImageRecognitionResponse(**result_payload),
                )
            )
            success_count += 1
        except ValueError as exc:
            items.append(
                ImageBatchItemResponse(
                    filename=item.filename,
                    content_type=item.content_type,
                    ok=False,
                    error=str(exc),
                    result=None,
                )
            )

    return ImageBatchRecognitionResponse(
        items_count=len(items),
        success_count=success_count,
        error_count=len(items) - success_count,
        items=items,
    )


@router.get("/preview")
def get_preview() -> Response:
    preview = capture_preview_jpeg()
    if preview is None:
        return Response(status_code=503)
    return Response(content=preview, media_type="image/jpeg")


@router.get("/preview/stream")
def get_preview_stream() -> StreamingResponse:
    return StreamingResponse(
        stream_preview_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )
