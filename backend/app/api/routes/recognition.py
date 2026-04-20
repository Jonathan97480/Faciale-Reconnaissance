import base64
import binascii
import asyncio

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, WebSocket
from fastapi.responses import StreamingResponse
from starlette.websockets import WebSocketDisconnect

from app.api.routes.auth import get_current_user, get_websocket_user
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
    current_camera_runtime_status,
    stream_preview_frames,
)
from app.services.camera_alert_service import build_camera_alerts
from app.services.config_service import read_config
from app.services.detection_loop import detection_loop
from app.services.image_recognition_service import analyze_image_bytes
from app.services.network_camera_pool_service import (
    has_network_camera_source,
    network_camera_pool_status,
)
from app.services.network_preview_service import (
    get_network_preview_jpeg,
    stream_network_preview_frames,
)
from app.services.recognition_service import (
    get_detection_history,
    get_latest_detection,
    recognize_face,
    save_detection,
)

router = APIRouter(
    prefix="/recognition",
    tags=["recognition"],
    dependencies=[Depends(get_current_user)],
)


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


def _build_monitoring_snapshot() -> dict[str, object]:
    network_cameras = network_camera_pool_status()
    source_stats = network_cameras.get("sources", [])
    alerts = build_camera_alerts(
        source_stats=source_stats if isinstance(source_stats, list) else [],
        max_read_latency_ms=350.0,
        max_detection_staleness_seconds=8.0,
    )
    return {
        "loop": detection_loop.status(),
        "capture_settings": current_capture_settings(),
        "local_camera": current_camera_runtime_status(),
        "network_cameras": network_cameras,
        "latest_detection": get_latest_detection(),
        "history": get_detection_history(10),
        "camera_alerts": alerts,
    }


@router.get("/loop/status")
def get_loop_status() -> dict[str, object]:
    return {
        "loop": detection_loop.status(),
        "capture_settings": current_capture_settings(),
        "local_camera": current_camera_runtime_status(),
        "network_cameras": network_camera_pool_status(),
    }


@router.websocket("/live")
async def recognition_live(websocket: WebSocket) -> None:
    try:
        get_websocket_user(websocket)
    except HTTPException:
        await websocket.close(code=1008)
        return

    await websocket.accept()
    try:
        while True:
            await websocket.send_json(_build_monitoring_snapshot())
            config = read_config(mask_secrets=True)
            await asyncio.sleep(config.detection_interval_seconds)
    except WebSocketDisconnect:
        return


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


@router.get("/network-preview")
def get_network_preview(source: str = Query(min_length=1)) -> Response:
    if not has_network_camera_source(source):
        raise HTTPException(status_code=404, detail="Flux reseau non configure")
    preview = get_network_preview_jpeg(source)
    if preview is None:
        return Response(status_code=503)
    return Response(content=preview, media_type="image/jpeg")


@router.get("/network-preview/stream")
def get_network_preview_stream(source: str = Query(min_length=1)) -> StreamingResponse:
    if not has_network_camera_source(source):
        raise HTTPException(status_code=404, detail="Flux reseau non configure")
    return StreamingResponse(
        stream_network_preview_frames(source),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )
