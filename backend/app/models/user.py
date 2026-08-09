from typing import Optional
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, func, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.config import ROLE_LABELS


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="operator")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    created_by: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    registration_status: Mapped[str] = mapped_column(String(20), default="active")
    domains: Mapped[list] = mapped_column(JSON, default=list)
    department: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, default="")

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "display_name": self.display_name,
            "role": self.role,
            "role_label": ROLE_LABELS.get(self.role, self.role),
            "is_active": self.is_active,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "created_by": self.created_by,
            "registration_status": self.registration_status,
            "domains": self.domains or [],
            "department": self.department or "",
        }
