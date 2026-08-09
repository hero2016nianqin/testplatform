from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class LogQueryParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=200)
    level: Optional[str] = None
    run_id: Optional[int] = None
    slot_id: Optional[int] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class LogResp(BaseModel):
    id: int
    run_id: Optional[int]
    slot_id: Optional[int]
    level: str
    message: str
    created_at: Optional[datetime]


class LogStatsResp(BaseModel):
    total: int
    info_count: int
    warn_count: int
    error_count: int
