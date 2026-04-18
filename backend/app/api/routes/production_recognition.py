import base64
import binascii
import hmac
import os

from fastapi import APIRouter, Depends, Header, HTTPException, Request

from app.core.schemas import (
    ImageBatchAnalyzeRequest,
    ImageBatchItemResponse,
    ImageBatchRecognitionResponse,
    ImageRecognitionResponse,
)
from app.services.batch_log_service import save_batch_log
from app.services.image_recognition_service import analyze_image_bytes

router = APIRouter(prefix="/production/recognition", tags=["production-recognition"])


def require_api_key(x_api_key: str | None = Header(default=None)) -> str:
    expected_api_key = os.getenv("FACE_API_KEY", "")
    if not expected_api_key:
        raise HTTPException(status_code=503, detail="FACE_API_KEY non configure")
    if not x_api_key or not hmac.compare_digest(x_api_key, expected_api_key):
        raise HTTPException(status_code=401, detail="Cle API invalide")
    return x_api_key


def _is_allowed_image_content_type(content_type: str | None) -> bool:
    if not content_type:
        return True
    return content_type.startswith("image/") or content_type.startswith(
        "application/octet-stream"
    )


@router.post("/analyze-images", response_model=ImageBatchRecognitionResponse)
def analyze_images_production(
    payload: ImageBatchAnalyzeRequest,
    request: Request,
    _: str = Depends(require_api_key),
) -> ImageBatchRecognitionResponse:
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

    response = ImageBatchRecognitionResponse(
        items_count=len(items),
        success_count=success_count,
        error_count=len(items) - success_count,
        items=items,
    )

    save_batch_log(
        endpoint="/api/production/recognition/analyze-images",
        items_count=response.items_count,
        success_count=response.success_count,
        error_count=response.error_count,
        client_ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    return response
