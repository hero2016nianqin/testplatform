from typing import Optional
from datetime import datetime
from sqlalchemy import String, Text, Integer, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Factory(Base):
    """厂区"""
    __tablename__ = "factories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    code: Mapped[Optional[str]] = mapped_column(String(50), unique=True, nullable=True)
    description: Mapped[str] = mapped_column(Text, default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    lines = relationship("ProductionLine", back_populates="factory", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id, "name": self.name, "code": self.code,
            "description": self.description, "sort_order": self.sort_order,
        }


class ProductionLine(Base):
    """线体"""
    __tablename__ = "production_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    factory_id: Mapped[int] = mapped_column(Integer, ForeignKey("factories.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    description: Mapped[str] = mapped_column(Text, default="")
    scenario: Mapped[str] = mapped_column(String(100), default="")
    created_by: Mapped[str] = mapped_column(String(100), default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    factory = relationship("Factory", back_populates="lines")
    stations = relationship("TestStation", back_populates="line", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id, "factory_id": self.factory_id, "name": self.name,
            "code": self.code, "description": self.description, "scenario": self.scenario,
            "created_by": self.created_by, "sort_order": self.sort_order,
        }


class TestStation(Base):
    """测试工站"""
    __tablename__ = "test_stations"

    id: Mapped[int] = mapped_column(primary_key=True)
    line_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("production_lines.id"), nullable=True, index=True)
    definition_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("equipment_definitions.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    description: Mapped[str] = mapped_column(Text, default="")
    deployed_version: Mapped[str] = mapped_column(String(20), default="1.0.0")
    latest_version: Mapped[str] = mapped_column(String(20), default="1.0.0")
    process_type: Mapped[str] = mapped_column(String(50), default="")
    workstation: Mapped[str] = mapped_column(String(50), default="")
    actuator: Mapped[str] = mapped_column(String(100), default="")
    hardware_code: Mapped[str] = mapped_column(String(100), default="")
    software_code: Mapped[str] = mapped_column(String(100), default="")
    created_by: Mapped[str] = mapped_column(String(100), default="")
    has_settings: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    line = relationship("ProductionLine", back_populates="stations")
    definition = relationship("EquipmentDefinition", back_populates="stations")
    cabinets = relationship("Cabinet", back_populates="station", cascade="all, delete-orphan")
    chassis_list = relationship("TestChassis", back_populates="station", cascade="all, delete-orphan")
    equipment_config = relationship("EquipmentConfig", uselist=False, back_populates="station", cascade="all, delete-orphan")
    hardware_params = relationship("HardwareParam", back_populates="station", cascade="all, delete-orphan")
    software_config = relationship("SoftwareConfig", uselist=False, back_populates="station", cascade="all, delete-orphan")
    scenario_config = relationship("ScenarioConfig", uselist=False, back_populates="station", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id, "line_id": self.line_id, "definition_id": self.definition_id,
            "name": self.name, "code": self.code, "description": self.description,
            "deployed_version": self.deployed_version, "latest_version": self.latest_version,
            "needs_update": self.deployed_version != self.latest_version,
            "process_type": self.process_type, "workstation": self.workstation,
            "actuator": self.actuator, "hardware_code": self.hardware_code,
            "software_code": self.software_code, "created_by": self.created_by,
            "has_settings": self.has_settings, "sort_order": self.sort_order,
        }


class Cabinet(Base):
    """机柜"""
    __tablename__ = "cabinets"

    id: Mapped[int] = mapped_column(primary_key=True)
    station_id: Mapped[int] = mapped_column(Integer, ForeignKey("test_stations.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), default="机柜 1")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    station = relationship("TestStation", back_populates="cabinets")
    chassis_list = relationship("TestChassis", back_populates="cabinet", cascade="all, delete-orphan")
    params = relationship("CabinetParam", back_populates="cabinet", cascade="all, delete-orphan")

    def to_dict(self):
        return {"id": self.id, "station_id": self.station_id, "name": self.name, "sort_order": self.sort_order}


class TestChassis(Base):
    """机框"""
    __tablename__ = "test_chassis"

    id: Mapped[int] = mapped_column(primary_key=True)
    station_id: Mapped[int] = mapped_column(Integer, ForeignKey("test_stations.id"), nullable=False, index=True)
    cabinet_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("cabinets.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slot_count: Mapped[int] = mapped_column(Integer, default=1)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    station = relationship("TestStation", back_populates="chassis_list")
    cabinet = relationship("Cabinet", back_populates="chassis_list")
    slots = relationship("TestSlot", back_populates="chassis", cascade="all, delete-orphan")
    params = relationship("ChassisParam", back_populates="chassis", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id, "station_id": self.station_id, "cabinet_id": self.cabinet_id,
            "name": self.name, "slot_count": self.slot_count, "sort_order": self.sort_order,
        }


class TestSlot(Base):
    """槽位"""
    __tablename__ = "test_slots"

    id: Mapped[int] = mapped_column(primary_key=True)
    chassis_id: Mapped[int] = mapped_column(Integer, ForeignKey("test_chassis.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="idle", index=True)
    current_batch_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    chassis = relationship("TestChassis", back_populates="slots")

    def to_dict(self):
        return {
            "id": self.id, "chassis_id": self.chassis_id, "name": self.name,
            "status": self.status, "current_batch_id": self.current_batch_id,
            "sort_order": self.sort_order,
        }


class CabinetParam(Base):
    """机柜参数"""
    __tablename__ = "cabinet_params"

    id: Mapped[int] = mapped_column(primary_key=True)
    cabinet_id: Mapped[int] = mapped_column(Integer, ForeignKey("cabinets.id"), nullable=False, index=True)
    param_name: Mapped[str] = mapped_column(String(200), nullable=False)
    param_value: Mapped[str] = mapped_column(String(500), default="")
    group_name: Mapped[str] = mapped_column(String(100), default="default")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    cabinet = relationship("Cabinet", back_populates="params")

    def to_dict(self):
        return {
            "id": self.id, "cabinet_id": self.cabinet_id,
            "param_name": self.param_name, "param_value": self.param_value,
            "group_name": self.group_name, "sort_order": self.sort_order,
        }


class ChassisParam(Base):
    """机框参数"""
    __tablename__ = "chassis_params"

    id: Mapped[int] = mapped_column(primary_key=True)
    chassis_id: Mapped[int] = mapped_column(Integer, ForeignKey("test_chassis.id"), nullable=False, index=True)
    param_name: Mapped[str] = mapped_column(String(200), nullable=False)
    param_value: Mapped[str] = mapped_column(String(500), default="")
    group_name: Mapped[str] = mapped_column(String(100), default="default")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    chassis = relationship("TestChassis", back_populates="params")

    def to_dict(self):
        return {
            "id": self.id, "chassis_id": self.chassis_id,
            "param_name": self.param_name, "param_value": self.param_value,
            "group_name": self.group_name, "sort_order": self.sort_order,
        }
