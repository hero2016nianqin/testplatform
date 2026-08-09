from typing import Optional
from datetime import datetime
from sqlalchemy import String, Text, Integer, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TestItemTemplate(Base):
    """测试项模板（不含参数阈值，参数随版本下发）"""
    __tablename__ = "test_item_templates"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    service_address: Mapped[str] = mapped_column(String(500), default="")
    is_critical: Mapped[bool] = mapped_column(Boolean, default=False)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=60)
    category: Mapped[str] = mapped_column(String(100), default="general", index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    def to_dict(self):
        return {
            "id": self.id, "name": self.name, "description": self.description,
            "service_address": self.service_address, "is_critical": self.is_critical,
            "timeout_seconds": self.timeout_seconds, "category": self.category,
            "is_active": self.is_active, "sort_order": self.sort_order,
        }


class TestSequence(Base):
    """测试序列"""
    __tablename__ = "test_sequences"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    version: Mapped[str] = mapped_column(String(50), default="1.0")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[str] = mapped_column(String(100), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    steps = relationship("TestSequenceStep", back_populates="sequence", cascade="all, delete-orphan", order_by="TestSequenceStep.step_order")

    def to_dict(self):
        return {
            "id": self.id, "name": self.name, "description": self.description,
            "version": self.version, "is_active": self.is_active,
            "created_by": self.created_by,
        }

    def to_dict_with_steps(self):
        d = self.to_dict()
        d["steps"] = [s.to_dict() for s in self.steps]
        return d


class TestSequenceStep(Base):
    """序列步骤"""
    __tablename__ = "test_sequence_steps"

    id: Mapped[int] = mapped_column(primary_key=True)
    sequence_id: Mapped[int] = mapped_column(Integer, ForeignKey("test_sequences.id"), nullable=False, index=True)
    template_id: Mapped[int] = mapped_column(Integer, ForeignKey("test_item_templates.id"), nullable=False)
    step_order: Mapped[int] = mapped_column(Integer, nullable=False)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=60)

    sequence = relationship("TestSequence", back_populates="steps")
    template = relationship("TestItemTemplate")

    def to_dict(self):
        t = self.template
        return {
            "id": self.id, "sequence_id": self.sequence_id,
            "step_order": self.step_order, "timeout_seconds": self.timeout_seconds,
            "template_id": self.template_id,
            "template_name": t.name if t else "",
            "template_service_address": t.service_address if t else "",
            "template_is_critical": t.is_critical if t else False,
            "template_category": t.category if t else "",
        }
