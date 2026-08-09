from typing import Optional, List
from pydantic import BaseModel, Field


class TemplateCreateReq(BaseModel):
    name: str = Field(..., max_length=200)
    description: str = ""
    service_address: str = ""
    is_critical: bool = False
    timeout_seconds: int = 60
    category: str = "general"
    sort_order: int = 0


class TemplateUpdateReq(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    service_address: Optional[str] = None
    is_critical: Optional[bool] = None
    timeout_seconds: Optional[int] = None
    category: Optional[str] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


class TemplateResp(BaseModel):
    id: int
    name: str
    description: str
    service_address: str
    is_critical: bool
    timeout_seconds: int
    category: str
    is_active: bool
    sort_order: int


class StepCreateReq(BaseModel):
    template_id: int
    step_order: int
    timeout_seconds: int = 60


class SequenceCreateReq(BaseModel):
    name: str = Field(..., max_length=200)
    description: str = ""
    version: str = "1.0"
    created_by: str = ""
    steps: List[StepCreateReq] = []


class SequenceUpdateReq(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    version: Optional[str] = None
    is_active: Optional[bool] = None


class StepResp(BaseModel):
    id: int
    sequence_id: int
    step_order: int
    timeout_seconds: int
    template_id: int
    template_name: str
    template_service_address: str
    template_is_critical: bool
    template_category: str


class SequenceResp(BaseModel):
    id: int
    name: str
    description: str
    version: str
    is_active: bool
    created_by: str
    step_count: int = 0


class SequenceDetailResp(BaseModel):
    id: int
    name: str
    description: str
    version: str
    is_active: bool
    created_by: str
    steps: List[StepResp] = []
