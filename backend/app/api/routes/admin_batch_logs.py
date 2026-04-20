from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.api.routes.auth import get_current_user
from app.core.database import get_connection
from app.core.schemas_batch_log import BatchLogQueryResponse, BatchLogRecord
from app.services.batch_log_query_service import query_batch_logs

router = APIRouter(
    prefix="/admin/batch-logs",
    tags=["admin-batch-logs"],
    dependencies=[Depends(get_current_user)],
)

@router.get("/", response_model=BatchLogQueryResponse)
def get_batch_logs(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    endpoint: Optional[str] = Query(default=None),
    date_from: Optional[str] = Query(default=None),
    date_to: Optional[str] = Query(default=None),
) -> BatchLogQueryResponse:
    logs = query_batch_logs(limit=limit, offset=offset, endpoint=endpoint, date_from=date_from, date_to=date_to)
    with get_connection() as connection:
        total = connection.execute("SELECT COUNT(*) FROM api_batch_logs").fetchone()[0]
    return BatchLogQueryResponse(total=total, logs=[BatchLogRecord(**row) for row in logs])
