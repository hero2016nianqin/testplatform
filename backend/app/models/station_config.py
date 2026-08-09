from typing import Optional
from datetime import datetime
from sqlalchemy import String, Text, Integer, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.utils.compat import JSONField

from app.core.database import Base


class EquipmentConfig(Base):
    """装备参数"""
    __tablename__ = "equipment_configs"

    id: Mapped[int] = mapped_column(primary_key=True)
    station_id: Mapped[int] = mapped_column(Integer, ForeignKey("test_stations.id"), nullable=False, unique=True)
    auto_load_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    debug_mode_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    equipment_ip: Mapped[str] = mapped_column(String(50), default="192.168.1.100")
    equipment_service_address: Mapped[str] = mapped_column(String(200), default="")
    process_control_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    test_mode_normal: Mapped[bool] = mapped_column(Boolean, default=True)
    test_mode_verify: Mapped[bool] = mapped_column(Boolean, default=False)
    test_mode_calibration: Mapped[bool] = mapped_column(Boolean, default=False)
    barcode_verify_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    station = relationship("TestStation", back_populates="equipment_config")

    def to_dict(self):
        return {
            "id": self.id, "station_id": self.station_id,
            "auto_load_enabled": self.auto_load_enabled,
            "debug_mode_enabled": self.debug_mode_enabled,
            "equipment_ip": self.equipment_ip,
            "equipment_service_address": self.equipment_service_address,
            "process_control_enabled": self.process_control_enabled,
            "test_mode_normal": self.test_mode_normal,
            "test_mode_verify": self.test_mode_verify,
            "test_mode_calibration": self.test_mode_calibration,
            "barcode_verify_enabled": self.barcode_verify_enabled,
        }


class HardwareParam(Base):
    """硬件参数"""
    __tablename__ = "hardware_params"

    id: Mapped[int] = mapped_column(primary_key=True)
    station_id: Mapped[int] = mapped_column(Integer, ForeignKey("test_stations.id"), nullable=False, index=True)
    param_name: Mapped[str] = mapped_column(String(200), nullable=False)
    param_value: Mapped[str] = mapped_column(String(500), default="")
    group_name: Mapped[str] = mapped_column(String(100), default="default")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    station = relationship("TestStation", back_populates="hardware_params")

    def to_dict(self):
        return {
            "id": self.id, "station_id": self.station_id,
            "param_name": self.param_name, "param_value": self.param_value,
            "group_name": self.group_name, "sort_order": self.sort_order,
        }


class SoftwareConfig(Base):
    """软件参数"""
    __tablename__ = "software_configs"

    id: Mapped[int] = mapped_column(primary_key=True)
    station_id: Mapped[int] = mapped_column(Integer, ForeignKey("test_stations.id"), nullable=False)
    project_name: Mapped[str] = mapped_column(String(200), default="")
    dut_version: Mapped[str] = mapped_column(String(100), default="")
    dut_firmware_version: Mapped[str] = mapped_column(String(100), default="")
    dut_hardware_version: Mapped[str] = mapped_column(String(100), default="")
    selected_test_item_ids = mapped_column(JSONField, default=list)
    sequence_id: Mapped[int] = mapped_column(Integer, default=0)
    sequence_data = mapped_column(JSONField, default=dict)
    process_type: Mapped[str] = mapped_column(String(50), default="")
    workstation: Mapped[str] = mapped_column(String(50), default="")
    selected_code: Mapped[str] = mapped_column(String(100), default="")
    bom_code: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    station = relationship("TestStation", back_populates="software_config")

    def to_dict(self):
        import json
        return {
            "id": self.id, "station_id": self.station_id,
            "project_name": self.project_name,
            "dut_version": self.dut_version,
            "dut_firmware_version": self.dut_firmware_version,
            "dut_hardware_version": self.dut_hardware_version,
            "selected_test_item_ids": self.selected_test_item_ids or [],
            "sequence_id": self.sequence_id or 0,
            "sequence_data": self.sequence_data or {},
            "process_type": self.process_type or "",
            "workstation": self.workstation or "",
            "selected_code": self.selected_code or "",
            "bom_code": self.bom_code or "",
        }


class ScenarioConfig(Base):
    """场景参数"""
    __tablename__ = "scenario_configs"

    id: Mapped[int] = mapped_column(primary_key=True)
    station_id: Mapped[int] = mapped_column(Integer, ForeignKey("test_stations.id"), nullable=False, unique=True)
    scenario_data = mapped_column(JSONField, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    station = relationship("TestStation", back_populates="scenario_config")

    def to_dict(self):
        return {
            "id": self.id, "station_id": self.station_id,
            "scenario_data": self.scenario_data or {},
        }
