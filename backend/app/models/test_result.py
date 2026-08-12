from typing import Optional
from datetime import datetime
from sqlalchemy import String, Text, Integer, Float, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TestResult(Base):
    """测试结果"""
    __tablename__ = "test_results"
    __table_args__ = {}

    id: Mapped[int] = mapped_column(primary_key=True)
    test_item_id: Mapped[int] = mapped_column(Integer, ForeignKey("test_items.id"), nullable=False, index=True)
    test_run_id: Mapped[int] = mapped_column(Integer, ForeignKey("test_runs.id"), nullable=False, index=True)
    operator: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    serial_number: Mapped[str] = mapped_column(String(200), default="", index=True)
    actual_value: Mapped[float] = mapped_column(Float, nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    deviation: Mapped[float] = mapped_column(Float, default=0.0)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    remark: Mapped[str] = mapped_column(Text, default="")
    tested_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)

    test_item = relationship("TestItem")
    test_run = relationship("TestRun", back_populates="results")

    def to_dict(self):
        return {
            "id": self.id, "test_item_id": self.test_item_id,
            "test_run_id": self.test_run_id, "operator": self.operator,
            "serial_number": self.serial_number,
            "actual_value": self.actual_value, "passed": self.passed,
            "deviation": self.deviation, "duration_ms": self.duration_ms,
            "remark": self.remark,
            "item_name": self.test_item.name if self.test_item else None,
            "expected_value": self.test_item.expected_value if self.test_item else None,
            "tested_at": self.tested_at.isoformat() if self.tested_at else None,
        }
