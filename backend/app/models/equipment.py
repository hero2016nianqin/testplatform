from typing import Optional
from datetime import datetime
from sqlalchemy import String, Text, Integer, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.utils.compat import JSONField

from app.core.database import Base


class EquipmentDefinition(Base):
    """装备定义（模板）"""
    __tablename__ = "equipment_definitions"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    code: Mapped[Optional[str]] = mapped_column(String(50), unique=True, nullable=True)
    description: Mapped[str] = mapped_column(Text, default="")
    current_version: Mapped[str] = mapped_column(String(20), default="1.0.0")
    default_equipment_config = mapped_column(JSONField, default=dict)
    default_hardware_params = mapped_column(JSONField, default=list)
    default_software_config = mapped_column(JSONField, default=dict)
    default_scenario_config = mapped_column(JSONField, default=dict)
    layout_config = mapped_column(JSONField, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    stations = relationship("TestStation", back_populates="definition", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id, "name": self.name, "code": self.code,
            "description": self.description, "current_version": self.current_version,
            "layout_config": self.layout_config or self._default_layout(),
        }

    @staticmethod
    def _default_layout():
        return {
            "cabinets": [
                {"name": "机柜 1", "chassis": [
                    {"name": "机框 1", "slot_count": 4},
                    {"name": "机框 2", "slot_count": 4},
                ]}
            ]
        }


class EquipmentMetrics(Base):
    """装备级指标"""
    __tablename__ = "equipment_metrics"

    id: Mapped[int] = mapped_column(primary_key=True)
    station_id: Mapped[int] = mapped_column(Integer, ForeignKey("test_stations.id"), nullable=False, unique=True)
    metrics_json = mapped_column(JSONField, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    def to_dict(self):
        return {"id": self.id, "station_id": self.station_id, "metrics": self.metrics_json or []}


class EquipmentPropertyPage(Base):
    """装备级属性页"""
    __tablename__ = "equipment_property_pages"

    id: Mapped[int] = mapped_column(primary_key=True)
    station_id: Mapped[int] = mapped_column(Integer, ForeignKey("test_stations.id"), nullable=False, unique=True)
    page_json = mapped_column(JSONField, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    def to_dict(self):
        return {"id": self.id, "station_id": self.station_id, "page_data": self.page_json or {}}
