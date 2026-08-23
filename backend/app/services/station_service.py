import json
from typing import Optional, List

from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.station import (
    Factory, ProductionLine, TestStation, Cabinet, TestChassis, TestSlot,
)
from app.models.equipment import (
    EquipmentDefinition, EquipmentMetrics, EquipmentPropertyPage,
)
from app.models.station_config import (
    EquipmentConfig, HardwareParam, SoftwareConfig, ScenarioConfig,
)
from app.core.exceptions import NotFoundError, ConflictError


class StationService:

    # ── Factory ──
    @staticmethod
    async def list_factories(db: AsyncSession) -> list[Factory]:
        result = await db.execute(select(Factory).order_by(Factory.sort_order))
        return list(result.scalars().all())

    @staticmethod
    async def create_factory(db, data: dict) -> Factory:
        f = Factory(**data)
        db.add(f)
        await db.flush()
        return f

    @staticmethod
    async def update_factory(db, factory_id: int, data: dict) -> Factory:
        r = await db.execute(select(Factory).where(Factory.id == factory_id))
        f = r.scalar_one_or_none()
        if not f:
            raise NotFoundError("厂区不存在")
        for k, v in data.items():
            if v is not None:
                setattr(f, k, v)
        await db.flush()
        return f

    @staticmethod
    async def delete_factory(db, factory_id: int):
        r = await db.execute(select(Factory).where(Factory.id == factory_id))
        f = r.scalar_one_or_none()
        if not f:
            raise NotFoundError("厂区不存在")
        await db.delete(f)
        await db.flush()

    # ── Line ──
    @staticmethod
    async def list_lines(db, factory_id: Optional[int] = None) -> list[ProductionLine]:
        stmt = select(ProductionLine).order_by(ProductionLine.sort_order)
        if factory_id:
            stmt = stmt.where(ProductionLine.factory_id == factory_id)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def create_line(db, data: dict) -> ProductionLine:
        line = ProductionLine(**data)
        db.add(line)
        await db.flush()
        return line

    @staticmethod
    async def update_line(db, line_id: int, data: dict) -> ProductionLine:
        r = await db.execute(select(ProductionLine).where(ProductionLine.id == line_id))
        line = r.scalar_one_or_none()
        if not line:
            raise NotFoundError("线体不存在")
        for k, v in data.items():
            if v is not None:
                setattr(line, k, v)
        await db.flush()
        return line

    @staticmethod
    async def delete_line(db, line_id: int):
        r = await db.execute(select(ProductionLine).where(ProductionLine.id == line_id))
        line = r.scalar_one_or_none()
        if not line:
            raise NotFoundError("线体不存在")
        await db.delete(line)
        await db.flush()

    # ── EquipmentDefinition ──
    @staticmethod
    async def list_definitions(db) -> list[EquipmentDefinition]:
        result = await db.execute(select(EquipmentDefinition).order_by(EquipmentDefinition.name))
        return list(result.scalars().all())

    @staticmethod
    def _normalize_code(data: dict) -> dict:
        if "code" in data:
            code = data["code"]
            data["code"] = code.strip() if isinstance(code, str) and code.strip() else None
        return data

    @staticmethod
    async def create_definition(db, data: dict) -> EquipmentDefinition:
        StationService._normalize_code(data)
        d = EquipmentDefinition(**data)
        db.add(d)
        await db.flush()
        return d

    @staticmethod
    async def get_definition(db, def_id: int) -> EquipmentDefinition:
        r = await db.execute(select(EquipmentDefinition).where(EquipmentDefinition.id == def_id))
        d = r.scalar_one_or_none()
        if not d:
            raise NotFoundError("装备定义不存在")
        return d

    @staticmethod
    async def delete_definition(db, def_id: int):
        r = await db.execute(select(EquipmentDefinition).where(EquipmentDefinition.id == def_id))
        d = r.scalar_one_or_none()
        if not d:
            raise NotFoundError("装备定义不存在")
        await db.delete(d)
        await db.flush()

    @staticmethod
    async def update_definition(db, def_id: int, data: dict) -> EquipmentDefinition:
        r = await db.execute(select(EquipmentDefinition).where(EquipmentDefinition.id == def_id))
        d = r.scalar_one_or_none()
        if not d:
            raise NotFoundError("装备定义不存在")
        StationService._normalize_code(data)
        for k, v in data.items():
            if v is not None:
                setattr(d, k, v)
        await db.flush()
        return d

    # ── Station ──
    @staticmethod
    async def list_stations(db, line_id: Optional[int] = None) -> list[TestStation]:
        stmt = select(TestStation).order_by(TestStation.sort_order)
        if line_id:
            stmt = stmt.where(TestStation.line_id == line_id)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_station_detail(db, station_id: int) -> tuple:
        r = await db.execute(select(TestStation).where(TestStation.id == station_id))
        station = r.scalar_one_or_none()
        if not station:
            raise NotFoundError("工站不存在")

        r = await db.execute(
            select(Cabinet).where(Cabinet.station_id == station_id).order_by(Cabinet.sort_order)
        )
        cabinets = list(r.scalars().all())

        r = await db.execute(
            select(TestChassis).where(TestChassis.station_id == station_id).order_by(TestChassis.sort_order)
        )
        chassis_list = list(r.scalars().all())

        r = await db.execute(
            select(TestSlot)
            .join(TestChassis, TestSlot.chassis_id == TestChassis.id)
            .where(TestChassis.station_id == station_id)
            .order_by(TestSlot.sort_order)
        )
        slots = list(r.scalars().all())

        slot_map = {}
        for s in slots:
            slot_map.setdefault(s.chassis_id, []).append(s)
        for ch in chassis_list:
            ch._slots = slot_map.get(ch.id, [])

        ch_map = {}
        for ch in chassis_list:
            ch_map.setdefault(ch.cabinet_id, []).append(ch)
        for cab in cabinets:
            cab._chassis_list = ch_map.get(cab.id, [])

        return station, cabinets, chassis_list, slots

    @staticmethod
    async def create_station(db, data: dict) -> TestStation:
        line_id = data.get("line_id")
        definition_id = data.get("definition_id")

        r = await db.execute(select(EquipmentDefinition).where(EquipmentDefinition.id == definition_id))
        definition = r.scalar_one_or_none()
        if not definition:
            raise NotFoundError("装备定义不存在")

        station = TestStation(
            line_id=line_id,
            definition_id=definition_id,
            name=data.get("name"),
            code=data.get("code"),
            description=data.get("description", ""),
            process_type=data.get("process_type", ""),
            workstation=data.get("workstation", ""),
            actuator=data.get("actuator", ""),
            hardware_code=data.get("hardware_code", ""),
            software_code=data.get("software_code", ""),
            created_by=data.get("created_by", ""),
            deployed_version="1.0.0",
            latest_version=definition.current_version or "1.0.0",
        )
        db.add(station)
        await db.flush()

        # 默认配置
        db.add(EquipmentConfig(station_id=station.id))
        db.add(SoftwareConfig(station_id=station.id))
        db.add(ScenarioConfig(station_id=station.id))
        # 使用 get_metrics/get_property_page 避免唯一约束冲突
        await StationService.get_metrics(db, station.id)
        await StationService.get_property_page(db, station.id)

        # 按 layout_config 创建机柜->机框->槽位
        layout = definition.layout_config or {}
        for cab_data in layout.get("cabinets", []):
            cab = Cabinet(station_id=station.id, name=cab_data.get("name", "机柜 1"))
            db.add(cab)
            await db.flush()
            for ch_data in cab_data.get("chassis", []):
                ch = TestChassis(
                    station_id=station.id,
                    cabinet_id=cab.id,
                    name=ch_data.get("name", "机框"),
                    slot_count=ch_data.get("slot_count", 1),
                )
                db.add(ch)
                await db.flush()
                for i in range(ch.slot_count):
                    db.add(TestSlot(chassis_id=ch.id, name=f"槽位 {i+1}", sort_order=i))

        await db.flush()
        return station

    @staticmethod
    async def update_station(db, station_id: int, data: dict) -> TestStation:
        r = await db.execute(select(TestStation).where(TestStation.id == station_id))
        station = r.scalar_one_or_none()
        if not station:
            raise NotFoundError("工站不存在")
        for k, v in data.items():
            if v is not None:
                setattr(station, k, v)
        await db.flush()
        return station

    @staticmethod
    async def delete_station(db, station_id: int):
        r = await db.execute(select(TestStation).where(TestStation.id == station_id))
        station = r.scalar_one_or_none()
        if not station:
            raise NotFoundError("工站不存在")
        await db.delete(station)
        await db.flush()

    # ── Equipment Config ──
    @staticmethod
    async def get_equipment_config(db, station_id: int) -> EquipmentConfig:
        r = await db.execute(select(EquipmentConfig).where(EquipmentConfig.station_id == station_id))
        cfg = r.scalar_one_or_none()
        if not cfg:
            cfg = EquipmentConfig(station_id=station_id)
            db.add(cfg)
            await db.flush()
        return cfg

    @staticmethod
    async def update_equipment_config(db, station_id: int, data: dict) -> EquipmentConfig:
        cfg = await StationService.get_equipment_config(db, station_id)
        for k, v in data.items():
            if v is not None:
                setattr(cfg, k, v)
        await db.flush()
        return cfg

    # ── Hardware Params ──
    @staticmethod
    async def list_hardware_params(db, station_id: int) -> list[HardwareParam]:
        r = await db.execute(
            select(HardwareParam).where(HardwareParam.station_id == station_id).order_by(HardwareParam.sort_order)
        )
        return list(r.scalars().all())

    @staticmethod
    async def create_hardware_param(db, station_id: int, data: dict) -> HardwareParam:
        p = HardwareParam(station_id=station_id, **data)
        db.add(p)
        await db.flush()
        return p

    @staticmethod
    async def update_hardware_param(db, param_id: int, data: dict) -> HardwareParam:
        r = await db.execute(select(HardwareParam).where(HardwareParam.id == param_id))
        p = r.scalar_one_or_none()
        if not p:
            raise NotFoundError("硬件参数不存在")
        for k, v in data.items():
            if v is not None:
                setattr(p, k, v)
        await db.flush()
        return p

    @staticmethod
    async def delete_hardware_param(db, param_id: int):
        r = await db.execute(select(HardwareParam).where(HardwareParam.id == param_id))
        p = r.scalar_one_or_none()
        if not p:
            raise NotFoundError("硬件参数不存在")
        await db.delete(p)
        await db.flush()

    @staticmethod
    async def batch_replace_hardware(db, station_id: int, params: list[dict]):
        await db.execute(delete(HardwareParam).where(HardwareParam.station_id == station_id))
        for i, p in enumerate(params):
            p.setdefault("sort_order", i)
            db.add(HardwareParam(station_id=station_id, **p))
        await db.flush()

    # ── Software Config ──
    @staticmethod
    async def get_software_config(db, station_id: int) -> SoftwareConfig:
        r = await db.execute(select(SoftwareConfig).where(SoftwareConfig.station_id == station_id))
        cfg = r.scalar_one_or_none()
        if not cfg:
            cfg = SoftwareConfig(station_id=station_id)
            db.add(cfg)
            await db.flush()
        return cfg

    @staticmethod
    async def update_software_config(db, station_id: int, data: dict) -> SoftwareConfig:
        cfg = await StationService.get_software_config(db, station_id)
        for k, v in data.items():
            if v is not None:
                setattr(cfg, k, v)
        await db.flush()
        return cfg

    # ── Scenario Config ──
    @staticmethod
    async def get_scenario_config(db, station_id: int) -> ScenarioConfig:
        r = await db.execute(select(ScenarioConfig).where(ScenarioConfig.station_id == station_id))
        cfg = r.scalar_one_or_none()
        if not cfg:
            cfg = ScenarioConfig(station_id=station_id)
            db.add(cfg)
            await db.flush()
        return cfg

    @staticmethod
    async def update_scenario_config(db, station_id: int, data: dict) -> ScenarioConfig:
        cfg = await StationService.get_scenario_config(db, station_id)
        if "scenario_data" in data:
            cfg.scenario_data = data["scenario_data"]
        await db.flush()
        return cfg

    # ── Metrics ──
    @staticmethod
    async def get_metrics(db, station_id: int) -> EquipmentMetrics:
        r = await db.execute(select(EquipmentMetrics).where(EquipmentMetrics.station_id == station_id))
        m = r.scalar_one_or_none()
        if not m:
            m = EquipmentMetrics(station_id=station_id)
            db.add(m)
            await db.flush()
        return m

    @staticmethod
    async def update_metrics(db, station_id: int, metrics: list) -> EquipmentMetrics:
        m = await StationService.get_metrics(db, station_id)
        m.metrics_json = metrics
        await db.flush()
        return m

    # ── Property Page ──
    @staticmethod
    async def get_property_page(db, station_id: int) -> EquipmentPropertyPage:
        r = await db.execute(select(EquipmentPropertyPage).where(EquipmentPropertyPage.station_id == station_id))
        p = r.scalar_one_or_none()
        if not p:
            p = EquipmentPropertyPage(station_id=station_id)
            db.add(p)
            await db.flush()
        return p

    @staticmethod
    async def update_property_page(db, station_id: int, page_data: dict) -> EquipmentPropertyPage:
        p = await StationService.get_property_page(db, station_id)
        p.page_json = page_data
        await db.flush()
        return p

    @staticmethod
    async def sync_version_props(db, station_id: int, version_id: int) -> EquipmentPropertyPage:
        from app.models.version import VersionArchiveItem, SubScenario
        p = await StationService.get_property_page(db, station_id)
        merged: dict = {}
        r = await db.execute(select(VersionArchiveItem).where(
            VersionArchiveItem.version_id == version_id, VersionArchiveItem.type == "property_page"))
        for a in r.scalars().all():
            snap = a.data_snapshot or {}
            if isinstance(snap, dict):
                merged.update(snap)
        r = await db.execute(select(SubScenario).where(SubScenario.version_id == version_id))
        for ss in r.scalars().all():
            pp = ss.property_page or {}
            if isinstance(pp, dict):
                merged.update(pp)
        p.page_json = merged
        await db.flush()
        return p

    # ── Chassis CRUD ──
    @staticmethod
    async def list_chassis(db, station_id: int) -> list[TestChassis]:
        r = await db.execute(
            select(TestChassis).where(TestChassis.station_id == station_id).order_by(TestChassis.sort_order)
        )
        return list(r.scalars().all())

    @staticmethod
    async def create_chassis(db, station_id: int, data: dict) -> TestChassis:
        ch = TestChassis(station_id=station_id, **data)
        db.add(ch)
        await db.flush()
        if ch.slot_count:
            for i in range(ch.slot_count):
                db.add(TestSlot(chassis_id=ch.id, name=f"槽位 {i+1}", sort_order=i))
            await db.flush()
        return ch

    @staticmethod
    async def update_chassis(db, chassis_id: int, data: dict) -> TestChassis:
        r = await db.execute(select(TestChassis).where(TestChassis.id == chassis_id))
        ch = r.scalar_one_or_none()
        if not ch:
            raise NotFoundError("机框不存在")
        for k, v in data.items():
            if v is not None:
                setattr(ch, k, v)
        await db.flush()
        return ch

    @staticmethod
    async def delete_chassis(db, chassis_id: int):
        r = await db.execute(select(TestChassis).where(TestChassis.id == chassis_id))
        ch = r.scalar_one_or_none()
        if not ch:
            raise NotFoundError("机框不存在")
        await db.execute(delete(TestSlot).where(TestSlot.chassis_id == chassis_id))
        await db.delete(ch)
        await db.flush()

    @staticmethod
    async def update_slot(db, slot_id: int, data: dict) -> TestSlot:
        r = await db.execute(select(TestSlot).where(TestSlot.id == slot_id))
        s = r.scalar_one_or_none()
        if not s:
            raise NotFoundError("槽位不存在")
        for k, v in data.items():
            if v is not None:
                setattr(s, k, v)
        await db.flush()
        return s

    @staticmethod
    async def force_restart_chassis(db, chassis_id: int) -> int:
        """强制重启机框 — 重置所有槽位状态为 idle，释放 Redis 锁"""
        r = await db.execute(select(TestChassis).where(TestChassis.id == chassis_id))
        ch = r.scalar_one_or_none()
        if not ch:
            raise NotFoundError("机框不存在")

        r = await db.execute(select(TestSlot).where(TestSlot.chassis_id == chassis_id))
        slots = list(r.scalars().all())
        count = 0
        for slot in slots:
            if slot.status not in ("idle", "disabled"):
                slot.status = "idle"
                slot.current_batch_id = None
                slot.serial_number = None
                count += 1
        await db.flush()

        # 释放 Redis 锁
        from app.utils.slot_lock import release_slot_lock
        for slot in slots:
            try:
                from app.core.redis import get_redis_pool
                from redis.asyncio import Redis
                pool = get_redis_pool()
                async with Redis(connection_pool=pool) as redis:
                    await redis.delete(f"slot_lock:{slot.id}")
            except Exception:
                pass

        return count

    @staticmethod
    async def force_restart_cabinet(db, cabinet_id: int) -> int:
        """强制重启机柜 — 重置该机柜下所有机框的槽位状态为 idle"""
        from app.models.station import Cabinet
        r = await db.execute(select(Cabinet).where(Cabinet.id == cabinet_id))
        cab = r.scalar_one_or_none()
        if not cab:
            raise NotFoundError("机柜不存在")

        r = await db.execute(
            select(TestChassis).where(TestChassis.cabinet_id == cabinet_id)
        )
        chassis_list = list(r.scalars().all())

        total = 0
        for ch in chassis_list:
            total += await StationService.force_restart_chassis(db, ch.id)
        return total

    # ── Cabinet Params ──
    @staticmethod
    async def list_cabinet_params(db, cabinet_id: int):
        from app.models.station import CabinetParam
        r = await db.execute(
            select(CabinetParam).where(CabinetParam.cabinet_id == cabinet_id).order_by(CabinetParam.sort_order)
        )
        return list(r.scalars().all())

    @staticmethod
    async def create_cabinet_param(db, cabinet_id: int, data: dict):
        from app.models.station import CabinetParam
        p = CabinetParam(cabinet_id=cabinet_id, **data)
        db.add(p)
        await db.flush()
        return p

    @staticmethod
    async def update_cabinet_param(db, param_id: int, data: dict):
        from app.models.station import CabinetParam
        r = await db.execute(select(CabinetParam).where(CabinetParam.id == param_id))
        p = r.scalar_one_or_none()
        if not p:
            raise NotFoundError("参数不存在")
        for k, v in data.items():
            if v is not None:
                setattr(p, k, v)
        await db.flush()
        return p

    @staticmethod
    async def delete_cabinet_param(db, param_id: int):
        from app.models.station import CabinetParam
        r = await db.execute(select(CabinetParam).where(CabinetParam.id == param_id))
        p = r.scalar_one_or_none()
        if not p:
            raise NotFoundError("参数不存在")
        await db.delete(p)
        await db.flush()

    # ── Chassis Params ──
    @staticmethod
    async def list_chassis_params(db, chassis_id: int):
        from app.models.station import ChassisParam
        r = await db.execute(
            select(ChassisParam).where(ChassisParam.chassis_id == chassis_id).order_by(ChassisParam.sort_order)
        )
        return list(r.scalars().all())

    @staticmethod
    async def create_chassis_param(db, chassis_id: int, data: dict):
        from app.models.station import ChassisParam
        p = ChassisParam(chassis_id=chassis_id, **data)
        db.add(p)
        await db.flush()
        return p

    @staticmethod
    async def update_chassis_param(db, param_id: int, data: dict):
        from app.models.station import ChassisParam
        r = await db.execute(select(ChassisParam).where(ChassisParam.id == param_id))
        p = r.scalar_one_or_none()
        if not p:
            raise NotFoundError("参数不存在")
        for k, v in data.items():
            if v is not None:
                setattr(p, k, v)
        await db.flush()
        return p

    @staticmethod
    async def delete_chassis_param(db, param_id: int):
        from app.models.station import ChassisParam
        r = await db.execute(select(ChassisParam).where(ChassisParam.id == param_id))
        p = r.scalar_one_or_none()
        if not p:
            raise NotFoundError("参数不存在")
        await db.delete(p)
        await db.flush()

    # ── Version Check ──
    @staticmethod
    async def version_check(db, station_id: int) -> dict:
        r = await db.execute(select(TestStation).where(TestStation.id == station_id))
        st = r.scalar_one_or_none()
        if not st:
            raise NotFoundError("工站不存在")
        return {
            "station_id": station_id,
            "deployed_version": st.deployed_version,
            "latest_version": st.latest_version,
            "needs_update": st.deployed_version != st.latest_version,
        }
