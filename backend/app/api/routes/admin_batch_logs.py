from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from app.core.schemas_batch_log import BatchLogQueryParams, BatchLogQueryResponse, BatchLogRecord
from app.services.batch_log_query_service import query_batch_logs
from app.core.database import get_connection

from fastapi import Security, Header
import os
import hmac

def require_admin_api_key(x_admin_api_key: Optional[str] = Header(default=None)) -> str:
    expected_key = os.getenv("FACE_ADMIN_API_KEY", "")
    if not expected_key:
        raise HTTPException(status_code=503, detail="FACE_ADMIN_API_KEY non configurée")
    if not x_admin_api_key or not hmac.compare_digest(x_admin_api_key, expected_key):
        raise HTTPException(status_code=401, detail="Clé admin invalide")
    return x_admin_api_key

router = APIRouter(prefix="/admin/batch-logs", tags=["admin-batch-logs"])

@router.get("/", response_model=BatchLogQueryResponse)
def get_batch_logs(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    endpoint: Optional[str] = Query(default=None),
    date_from: Optional[str] = Query(default=None),
    date_to: Optional[str] = Query(default=None),
    _: str = Depends(require_admin_api_key),
) -> BatchLogQueryResponse:
    logs = query_batch_logs(limit=limit, offset=offset, endpoint=endpoint, date_from=date_from, date_to=date_to)
    # Total count for pagination
    with get_connection() as connection:
        total = connection.execute("SELECT COUNT(*) FROM api_batch_logs").fetchone()[0]
    return BatchLogQueryResponse(total=total, logs=[BatchLogRecord(**row) for row in logs])
