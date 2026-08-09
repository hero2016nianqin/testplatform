from typing import Optional
from datetime import datetime
from sqlalchemy import String, Text, Integer, Float, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TestItem(Base):
    """测试项定义"""
    __tablename__ = "test_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    expected_value: Mapped[float] = mapped_column(Float, nullable=False)
    min_value: Mapped[float] = mapped_column(Float, nullable=False)
    max_value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(50), default="")
    category: Mapped[str] = mapped_column(String(100), default="general", index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    def to_dict(self):
        return {
            "id": self.id, "name": self.name, "description": self.description,
            "expected_value": self.expected_value, "min_value": self.min_value,
            "max_value": self.max_value, "unit": self.unit, "category": self.category,
            "is_active": self.is_active, "sort_order": self.sort_order,
        }
