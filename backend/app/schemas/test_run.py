from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class RunCreateReq(BaseModel):
    serial_number: str = ""
    product_type: str = ""
    task_order: str = ""
    operator: str = ""
    station_id: int
    slot_id: int
    sequence_id: int = 0
    sequence_name: str = ""
    version_id: Optional[int] = None
    sub_scenario_id: Optional[int] = None


class RunUpdateReq(BaseModel):
    status: str
    total_items: Optional[int] = None
    passed_items: Optional[int] = None
    failed_items: Optional[int] = None
    ended_at: Optional[datetime] = None


class ResultSubmitReq(BaseModel):
    test_item_id: int
    operator: str = ""
    serial_number: str = ""
    actual_value: float
    passed: bool
    deviation: float = 0.0
    duration_ms: int = 0
    remark: str = ""
    is_critical: bool = False


class ResultSubmitResp(BaseModel):
    id: int
    stop: bool
    passed: bool
    message: str = ""


class RunResp(BaseModel):
    id: int
    batch_id: str
    product_type: str
    task_order: str
    serial_number: str
    operator: str
    status: str
    total_items: int
    passed_items: int
    failed_items: int
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    sequence_id: int
    sequence_name: str
    version_id: Optional[int] = None
    sub_scenario_id: Optional[int] = None
    created_at: Optional[datetime] = None
