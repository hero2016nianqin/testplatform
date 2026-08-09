from typing import Optional
from datetime import datetime
from pydantic import BaseModel


class ResultResp(BaseModel):
    id: int
    test_item_id: int
    test_run_id: int
    operator: str
    serial_number: str
    actual_value: float
    passed: bool
    deviation: float
    duration_ms: int
    remark: str
    item_name: Optional[str] = None
    expected_value: Optional[float] = None
    tested_at: Optional[datetime] = None


class RecordQueryParams(BaseModel):
    level: str = "R1"  # R1/R2/R3
    page: int = 1
    page_size: int = 20
    operator: Optional[str] = None
    serial_number: Optional[str] = None
    status: Optional[str] = None
    station_id: Optional[int] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
