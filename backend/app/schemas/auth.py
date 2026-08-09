from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class LoginReq(BaseModel):
    username: str
    password: str


class LoginResp(BaseModel):
    id: int
    username: str
    display_name: str
    role: str
    role_label: str
    is_active: bool
    domains: List[str] = []


class RegistrationReq(BaseModel):
    username: str = Field(..., min_length=2, max_length=80)
    display_name: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=6)
    department: str = Field(..., min_length=1, max_length=100)
    requested_role: str = Field(..., min_length=1, max_length=20)
    requested_domains: List[str] = Field(default=[])
    justification: Optional[str] = None


class RegistrationResp(BaseModel):
    id: int
    username: str
    display_name: str
    department: Optional[str] = None
    requested_role: str
    requested_domains: List[str] = []
    justification: Optional[str] = None
    status: str
    created_at: Optional[datetime] = None
    reviewer_id: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    review_comment: Optional[str] = None


class UserCreateReq(BaseModel):
    username: str = Field(..., min_length=2, max_length=80)
    display_name: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=6)
    role: str = Field(default="operator")
    domains: List[str] = Field(default=[])
    department: str = Field(default="")


class UserUpdateReq(BaseModel):
    display_name: Optional[str] = None
    password: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    domains: Optional[List[str]] = None
    department: Optional[str] = None


class ResetPasswordReq(BaseModel):
    new_password: str = Field(..., min_length=8)


class UserResp(BaseModel):
    id: int
    username: str
    display_name: str
    role: str
    role_label: str
    is_active: bool
    last_login: Optional[datetime] = None
    created_at: Optional[datetime] = None
    created_by: Optional[str] = None
    registration_status: Optional[str] = None
    domains: List[str] = []
    department: Optional[str] = None


class AuditLogResp(BaseModel):
    id: int
    user_id: Optional[int] = None
    username: Optional[str] = None
    action: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    detail: Optional[dict] = None
    ip_address: Optional[str] = None
    created_at: Optional[datetime] = None
