from typing import Optional
from pydantic import BaseModel, Field


class TestItemCreateReq(BaseModel):
    name: str = Field(..., max_length=200)
    description: str = ""
    expected_value: float
    min_value: float
    max_value: float
    unit: str = ""
    category: str = "general"
    is_active: bool = True
    sort_order: int = 0


class TestItemUpdateReq(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    expected_value: Optional[float] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    unit: Optional[str] = None
    category: Optional[str] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


class TestItemResp(BaseModel):
    id: int
    name: str
    description: str
    expected_value: float
    min_value: float
    max_value: float
    unit: str
    category: str
    is_active: bool
    sort_order: int
