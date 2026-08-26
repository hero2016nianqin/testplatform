from typing import Optional
from datetime import datetime
from sqlalchemy import String, Text, Integer, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.database import JSONField


class TestRun(Base):
    """测试批次"""
    __tablename__ = "test_runs"
    __table_args__ = {}

    id: Mapped[int] = mapped_column(primary_key=True)
    batch_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    product_type: Mapped[str] = mapped_column(String(100), default="")
    task_order: Mapped[str] = mapped_column(String(100), default="", index=True)
    serial_number: Mapped[str] = mapped_column(String(200), default="", index=True)
    operator: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    total_items: Mapped[int] = mapped_column(Integer, default=0)
    passed_items: Mapped[int] = mapped_column(Integer, default=0)
    failed_items: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    station_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("test_stations.id"), nullable=True, index=True)
    slot_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("test_slots.id"), nullable=True, index=True)
    sequence_id: Mapped[int] = mapped_column(Integer, default=0)
    sequence_name: Mapped[str] = mapped_column(String(200), default="")
    version_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    sub_scenario_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    selected_item_ids = mapped_column(JSONField, default=list, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)

    results = relationship("TestResult", back_populates="test_run", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id, "batch_id": self.batch_id,
            "product_type": self.product_type, "task_order": self.task_order,
            "serial_number": self.serial_number, "operator": self.operator,
            "status": self.status, "total_items": self.total_items,
            "passed_items": self.passed_items, "failed_items": self.failed_items,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "sequence_id": self.sequence_id or 0,
            "sequence_name": self.sequence_name or "",
            "version_id": self.version_id,
            "sub_scenario_id": self.sub_scenario_id,
            "selected_item_ids": self.selected_item_ids or [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
