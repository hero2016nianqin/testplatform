from typing import Optional
from datetime import datetime
from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, func, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AccountRegistration(Base):
    """账号注册申请（待审核）"""
    __tablename__ = "account_registration"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    department: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    requested_role: Mapped[str] = mapped_column(String(20), nullable=False, default="operator")
    requested_domains: Mapped[list] = mapped_column(JSON, default=list)
    justification: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")  # pending, approved, rejected
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    reviewer_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    review_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "display_name": self.display_name,
            "department": self.department,
            "requested_role": self.requested_role,
            "requested_domains": self.requested_domains or [],
            "justification": self.justification,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "reviewer_id": self.reviewer_id,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "review_comment": self.review_comment,
        }
