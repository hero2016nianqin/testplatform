from typing import Optional, Any
from pydantic import BaseModel, Field


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=200)


class IdParam(BaseModel):
    id: int


class BatchOperation(BaseModel):
    ids: list[int]
    action: str
