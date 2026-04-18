from typing import Optional
from pydantic import BaseModel, Field

class BatchLogRecord(BaseModel):
    id: int
    endpoint: str
    items_count: int
    success_count: int
    error_count: int
    client_ip: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: str

class BatchLogQueryParams(BaseModel):
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    endpoint: Optional[str] = None
    date_from: Optional[str] = None  # format YYYY-MM-DD
    date_to: Optional[str] = None

class BatchLogQueryResponse(BaseModel):
    total: int
    logs: list[BatchLogRecord]
