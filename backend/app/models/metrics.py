from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, Integer, DateTime, ForeignKey, func, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class BomDomainOwner(Base):
    """BOM 编码级别的领域责任人配置，所有版本共享"""
    __tablename__ = "bom_domain_owner"

    id: Mapped[int] = mapped_column(primary_key=True)
    bom_code: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    domain_owners: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "bom_code": self.bom_code,
            "domain_owners": self.domain_owners or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class IndicatorDict(Base):
    __tablename__ = "indicator_dict"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(50), default="")
    domain: Mapped[str] = mapped_column(String(50), default="")
    unit: Mapped[str] = mapped_column(String(20), default="")
    hardware_model: Mapped[str] = mapped_column(String(100), default="")
    test_rule: Mapped[str] = mapped_column(Text, default="")
    params: Mapped[dict] = mapped_column(JSON, nullable=False, server_default="{}")
    test_params: Mapped[list] = mapped_column(JSON, nullable=False, server_default="[]")
    script_source: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[int] = mapped_column(Integer, default=1)
    description: Mapped[str] = mapped_column(Text, default="")
    remark: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "code": self.code,
            "name": self.name,
            "category": self.category,
            "domain": self.domain,
            "unit": self.unit,
            "hardware_model": self.hardware_model,
            "test_rule": self.test_rule,
            "params": self.params or {},
            "test_params": self.test_params or [],
            "script_source": self.script_source or "",
            "status": self.status,
            "description": self.description,
            "remark": self.remark,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class TestItemCollection(Base):
    __tablename__ = "test_item_collection"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    product_type: Mapped[str] = mapped_column(String(100), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[int] = mapped_column(Integer, default=1)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    items = relationship("CollectionTestItem", back_populates="collection", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "code": self.code,
            "product_type": self.product_type,
            "description": self.description,
            "status": self.status,
            "version": self.version,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class CollectionTestItem(Base):
    __tablename__ = "collection_test_item"

    id: Mapped[int] = mapped_column(primary_key=True)
    collection_id: Mapped[int] = mapped_column(ForeignKey("test_item_collection.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    station: Mapped[str] = mapped_column(String(100), default="")
    process_name: Mapped[str] = mapped_column(String(100), default="")
    test_type: Mapped[str] = mapped_column(String(50), default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    service_address: Mapped[Optional[str]] = mapped_column(String(500), default="")
    timeout_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    block_type: Mapped[str] = mapped_column(String(20), default="normal")
    parallel_enabled: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[int] = mapped_column(Integer, default=1)
    # 协同编辑：乐观锁版本号 + 负责人
    item_revision: Mapped[int] = mapped_column(Integer, default=0)
    owner_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    owner_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    # 负责人是否手动覆盖（覆盖后，领域负责人自动填充不再刷新该测试项）
    owner_manual: Mapped[int] = mapped_column(Integer, default=0)

    collection = relationship("TestItemCollection", back_populates="items")
    indicators = relationship("TestItemIndicator", back_populates="test_item", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "collection_id": self.collection_id,
            "name": self.name,
            "station": self.station,
            "station_name": self.station,
            "process_name": self.process_name,
            "test_type": self.test_type,
            "sort_order": self.sort_order,
            "service_address": self.service_address,
            "timeout_seconds": self.timeout_seconds,
            "block_type": self.block_type,
            "parallel_enabled": bool(self.parallel_enabled),
            "status": self.status,
            "item_revision": self.item_revision,
            "owner_id": self.owner_id,
            "owner_name": self.owner_name,
            "owner_manual": bool(self.owner_manual),
        }

    def to_dict_with_indicators(self):
        d = self.to_dict()
        d["indicators"] = [i.to_dict() for i in self.indicators]
        return d


class TestItemIndicator(Base):
    __tablename__ = "test_item_indicator"

    id: Mapped[int] = mapped_column(primary_key=True)
    test_item_id: Mapped[int] = mapped_column(ForeignKey("collection_test_item.id"), nullable=False)
    indicator_id: Mapped[int] = mapped_column(ForeignKey("indicator_dict.id"), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), default="")
    judgment_rule: Mapped[str] = mapped_column(String(20), default="合格")

    test_item = relationship("CollectionTestItem", back_populates="indicators")
    indicator = relationship("IndicatorDict")

    def to_dict(self):
        return {
            "id": self.id,
            "test_item_id": self.test_item_id,
            "indicator_id": self.indicator_id,
            "unit": self.unit,
            "judgment_rule": self.judgment_rule,
        }


class BomConfig(Base):
    __tablename__ = "bom_config"

    id: Mapped[int] = mapped_column(primary_key=True)
    bom_code: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    bom_name: Mapped[str] = mapped_column(String(200), default="")
    collection_id: Mapped[int] = mapped_column(ForeignKey("test_item_collection.id"), nullable=False)
    collection_version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[int] = mapped_column(Integer, default=1)
    version: Mapped[int] = mapped_column(Integer, default=1)
    review_status: Mapped[str] = mapped_column(String(20), default="none")
    review_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    review_operator: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    archived: Mapped[bool] = mapped_column(Integer, default=0)
    archived_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    domain_owners: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    collection = relationship("TestItemCollection")
    indicators = relationship("BomIndicator", back_populates="bom_config", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "bom_code": self.bom_code,
            "bom_name": self.bom_name,
            "collection_id": self.collection_id,
            "collection_version": self.collection_version,
            "status": self.status,
            "version": self.version,
            "review_status": self.review_status,
            "review_comment": self.review_comment,
            "review_operator": self.review_operator,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "archived": bool(self.archived),
            "archived_at": self.archived_at.isoformat() if self.archived_at else None,
            "domain_owners": self.domain_owners or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class BomIndicator(Base):
    __tablename__ = "bom_indicator"

    id: Mapped[int] = mapped_column(primary_key=True)
    bom_config_id: Mapped[int] = mapped_column(ForeignKey("bom_config.id"), nullable=False)
    indicator_id: Mapped[int] = mapped_column(ForeignKey("indicator_dict.id"), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), default="")
    judgment_rule: Mapped[str] = mapped_column(String(20), default="合格")
    test_stage: Mapped[str] = mapped_column(String(50), default="")
    remark: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[int] = mapped_column(Integer, default=1)
    process_name: Mapped[str] = mapped_column(String(100), default="")
    station_name: Mapped[str] = mapped_column(String(100), default="")
    params: Mapped[dict] = mapped_column(JSON, default=list)
    # 协同编辑：乐观锁版本号 + 负责人
    item_revision: Mapped[int] = mapped_column(Integer, default=0)
    owner_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    owner_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    bom_config = relationship("BomConfig", back_populates="indicators")
    indicator = relationship("IndicatorDict")

    def to_dict(self):
        return {
            "id": self.id,
            "bom_config_id": self.bom_config_id,
            "indicator_id": self.indicator_id,
            "indicator_code": self.indicator.code if self.indicator else "",
            "indicator_name": self.indicator.name if self.indicator else "",
            "category": self.indicator.category if self.indicator else "",
            "unit": self.unit,
            "judgment_rule": self.judgment_rule,
            "test_stage": self.test_stage,
            "remark": self.remark,
            "status": self.status,
            "process_name": self.process_name,
            "station_name": self.station_name,
            "params": self.params or [],
            "dict_params": self.indicator.params if self.indicator else {},
            "item_revision": self.item_revision,
            "owner_id": self.owner_id,
            "owner_name": self.owner_name,
        }


class ScriptTemplate(Base):
    """自定义 Python 导出脚本模板"""
    __tablename__ = "script_template"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    source_code: Mapped[str] = mapped_column(Text, nullable=False)
    output_format: Mapped[str] = mapped_column(String(10), default="json")
    status: Mapped[int] = mapped_column(Integer, default=1)
    created_by: Mapped[str] = mapped_column(String(50), default="")
    updated_by: Mapped[str] = mapped_column(String(50), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "source_code": self.source_code,
            "output_format": self.output_format,
            "status": self.status,
            "created_by": self.created_by,
            "updated_by": self.updated_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class IndicatorVersionSnapshot(Base):
    __tablename__ = "indicator_version_snapshot"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(20), nullable=False)
    entity_id: Mapped[int] = mapped_column(nullable=False)
    version: Mapped[int] = mapped_column(nullable=False)
    snapshot_data: Mapped[dict] = mapped_column(JSON, default=dict)
    change_summary: Mapped[str] = mapped_column(Text, default="")
    operator: Mapped[str] = mapped_column(String(50), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "version": self.version,
            "snapshot_data": self.snapshot_data,
            "change_summary": self.change_summary,
            "operator": self.operator,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ParamChangeLog(Base):
    """参数变更日志：记录每次参数修改的详细信息"""
    __tablename__ = "param_change_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    bom_code: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    bom_config_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    bom_version: Mapped[int] = mapped_column(Integer, nullable=False)
    test_item_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    test_item_name: Mapped[str] = mapped_column(String(200), default="")
    indicator_id: Mapped[int] = mapped_column(Integer, nullable=False)
    indicator_code: Mapped[str] = mapped_column(String(50), default="")
    indicator_name: Mapped[str] = mapped_column(String(200), default="")
    param_key: Mapped[str] = mapped_column(String(100), default="")
    param_name: Mapped[str] = mapped_column(String(200), default="")
    old_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    new_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    operator_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    operator_name: Mapped[str] = mapped_column(String(100), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "bom_code": self.bom_code,
            "bom_config_id": self.bom_config_id,
            "bom_version": self.bom_version,
            "test_item_id": self.test_item_id,
            "test_item_name": self.test_item_name,
            "indicator_id": self.indicator_id,
            "indicator_code": self.indicator_code,
            "indicator_name": self.indicator_name,
            "param_key": self.param_key,
            "param_name": self.param_name,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "operator_id": self.operator_id,
            "operator_name": self.operator_name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
