from typing import Optional
from datetime import datetime
from sqlalchemy import String, Text, Integer, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.utils.compat import JSONField

from app.core.database import Base


class TestVersion(Base):
    """版本"""
    __tablename__ = "test_versions"

    id: Mapped[int] = mapped_column(primary_key=True)
    version: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    project_name: Mapped[str] = mapped_column(String(200), default="", index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(30), default="draft", index=True)
    created_by: Mapped[str] = mapped_column(String(100), default="")
    sequence_id: Mapped[int] = mapped_column(Integer, default=0)
    process_type: Mapped[str] = mapped_column(String(200), default="")
    workstation: Mapped[str] = mapped_column(String(200), default="")
    codes_config = mapped_column(JSONField, default=list)
    type: Mapped[str] = mapped_column(String(30), default="standard")
    bom_code: Mapped[str] = mapped_column(String(200), default="")
    bom_config_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("bom_config.id"), nullable=True)
    tps_name: Mapped[str] = mapped_column(String(200), default="")
    domain_tags: Mapped[str] = mapped_column(String(500), default="")
    inherit_from_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("test_versions.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    steps = relationship("ReleaseStep", back_populates="version", cascade="all, delete-orphan",
                         order_by="ReleaseStep.stage, ReleaseStep.step_order")
    archive_items = relationship("VersionArchiveItem", back_populates="version", cascade="all, delete-orphan")
    deployments = relationship("ReleaseDeployment", back_populates="version", cascade="all, delete-orphan")
    sub_scenarios = relationship("SubScenario", back_populates="version", cascade="all, delete-orphan",
                                  order_by="SubScenario.sort_order")
    binary_files = relationship("VersionBinaryFile", back_populates="version", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id, "version": self.version,
            "project_name": self.project_name, "description": self.description,
            "status": self.status, "created_by": self.created_by,
            "sequence_id": self.sequence_id or 0,
            "process_type": self.process_type or "",
            "workstation": self.workstation or "",
            "codes_config": self.codes_config or [],
            "type": self.type or "standard",
            "bom_code": self.bom_code or "",
            "bom_config_id": self.bom_config_id,
            "tps_name": self.tps_name or "",
            "domain_tags": self.domain_tags or "",
            "inherit_from_id": self.inherit_from_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class SubScenario(Base):
    """子场景"""
    __tablename__ = "sub_scenarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    version_id: Mapped[int] = mapped_column(Integer, ForeignKey("test_versions.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    process_type: Mapped[str] = mapped_column(String(100), default="")
    workstation: Mapped[str] = mapped_column(String(100), default="")
    sequence_id: Mapped[int] = mapped_column(Integer, default=0)
    hardware_params = mapped_column(JSONField, default=dict)
    software_metrics = mapped_column(JSONField, default=list)
    property_page = mapped_column(JSONField, default=dict)
    metrics_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default=None)
    metrics_ini: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default=None)
    bom_snapshot = mapped_column(JSONField, default=list, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    version = relationship("TestVersion", back_populates="sub_scenarios")

    def to_dict(self):
        return {
            "id": self.id, "version_id": self.version_id,
            "name": self.name, "description": self.description or "",
            "sort_order": self.sort_order or 0,
            "process_type": self.process_type or "",
            "workstation": self.workstation or "",
            "sequence_id": self.sequence_id or 0,
            "hardware_params": self.hardware_params or {},
            "software_metrics": self.software_metrics or [],
            "property_page": self.property_page or {},
            "metrics_json": self.metrics_json or "",
            "metrics_ini": self.metrics_ini or "",
            "bom_snapshot": self.bom_snapshot or [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ReleaseStep(Base):
    """审批步骤"""
    __tablename__ = "release_steps"

    id: Mapped[int] = mapped_column(primary_key=True)
    version_id: Mapped[int] = mapped_column(Integer, ForeignKey("test_versions.id"), nullable=False, index=True)
    stage: Mapped[int] = mapped_column(Integer, nullable=False)
    step_order: Mapped[int] = mapped_column(Integer, nullable=False)
    step_name: Mapped[str] = mapped_column(String(100), nullable=False)
    approver_role: Mapped[str] = mapped_column(String(50), default="")
    assigned_to: Mapped[str] = mapped_column(String(100), default="")
    status: Mapped[str] = mapped_column(String(20), default="pending")
    approved_by: Mapped[str] = mapped_column(String(100), default="")
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    comment: Mapped[str] = mapped_column(Text, default="")

    version = relationship("TestVersion", back_populates="steps")

    def to_dict(self):
        return {
            "id": self.id, "version_id": self.version_id,
            "stage": self.stage, "step_order": self.step_order,
            "step_name": self.step_name, "approver_role": self.approver_role,
            "assigned_to": self.assigned_to, "status": self.status,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "comment": self.comment,
        }


class VersionArchiveItem(Base):
    """归档条目"""
    __tablename__ = "version_archive_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    version_id: Mapped[int] = mapped_column(Integer, ForeignKey("test_versions.id"), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    item_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    data_snapshot = mapped_column(JSONField, default=dict)

    version = relationship("TestVersion", back_populates="archive_items")

    def to_dict(self):
        return {
            "id": self.id, "version_id": self.version_id,
            "type": self.type, "item_id": self.item_id,
            "data_snapshot": self.data_snapshot,
        }


class VersionBinaryFile(Base):
    """版本二进制文件"""
    __tablename__ = "version_binary_files"

    id: Mapped[int] = mapped_column(primary_key=True)
    version_id: Mapped[int] = mapped_column(Integer, ForeignKey("test_versions.id"), nullable=False, index=True)
    sub_scenario_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    filename: Mapped[str] = mapped_column(String(200), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    version = relationship("TestVersion", back_populates="binary_files")

    def to_dict(self):
        return {
            "id": self.id, "version_id": self.version_id,
            "sub_scenario_id": self.sub_scenario_id,
            "filename": self.filename, "file_size": self.file_size,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ReleaseDeployment(Base):
    """发行目标"""
    __tablename__ = "release_deployments"

    id: Mapped[int] = mapped_column(primary_key=True)
    version_id: Mapped[int] = mapped_column(Integer, ForeignKey("test_versions.id"), nullable=False, index=True)
    factory_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    factory_name: Mapped[str] = mapped_column(String(200), default="")
    line_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    line_name: Mapped[str] = mapped_column(String(200), default="")
    station_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    station_name: Mapped[str] = mapped_column(String(200), default="")
    assigned_to: Mapped[str] = mapped_column(String(100), default="")
    status: Mapped[str] = mapped_column(String(20), default="pending")
    approved_by: Mapped[str] = mapped_column(String(100), default="")
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    comment: Mapped[str] = mapped_column(Text, default="")
    deployed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    version = relationship("TestVersion", back_populates="deployments")

    def to_dict(self):
        return {
            "id": self.id, "version_id": self.version_id,
            "factory_id": self.factory_id, "factory_name": self.factory_name,
            "line_id": self.line_id, "line_name": self.line_name,
            "station_id": self.station_id, "station_name": self.station_name,
            "assigned_to": self.assigned_to, "status": self.status,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "comment": self.comment,
            "deployed_at": self.deployed_at.isoformat() if self.deployed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
