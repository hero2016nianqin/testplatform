"""
装备层级管理 API
对应 design.md §4.1, §5.1, §5.2, §7.1, §6.1
"""
from fastapi import APIRouter, Depends, Query
from app.utils.rate_limiter import rate_limit
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps.db_deps import get_db
from app.deps.auth_deps import require_process, require_developer
from app.core.response import success
from app.schemas.station import (
    FactoryCreateReq, FactoryUpdateReq, FactoryResp,
    LineCreateReq, LineUpdateReq, LineResp,
    DefinitionCreateReq, DefinitionUpdateReq, DefinitionResp,
    StationCreateReq, StationUpdateReq, StationResp,
    StationDetailResp, CabinetResp, ChassisResp, SlotResp,
    CabinetParamCreateReq, CabinetParamUpdateReq, CabinetParamResp,
    ChassisParamCreateReq, ChassisParamUpdateReq, ChassisParamResp,
)
from app.schemas.equipment import (
    EquipmentConfigReq, EquipmentConfigResp,
    HardwareParamCreateReq, HardwareParamUpdateReq, HardwareParamResp,
    HardwareBatchReplaceReq,
    SoftwareConfigReq, SoftwareConfigResp,
    ScenarioConfigReq, ScenarioConfigResp,
    MetricsReq, MetricsResp,
    PropertyPageReq, PropertyPageResp, SyncVersionPropsReq,
    ChassisCreateReq, ChassisUpdateReq, SlotUpdateReq,
)
from app.models.station import TestStation
from app.services.station_service import StationService

router = APIRouter(tags=["装备管理"])

svc = StationService()


# ── Factory ──
@router.get("/factories", dependencies=[Depends(rate_limit("factories", 60, 60))])
async def list_factories(db: AsyncSession = Depends(get_db)):
    factories = await svc.list_factories(db)
    return success(data=[FactoryResp(**f.to_dict()) for f in factories])


@router.post("/factories", dependencies=[Depends(require_developer)])
async def create_factory(req: FactoryCreateReq, db: AsyncSession = Depends(get_db)):
    f = await svc.create_factory(db, req.model_dump())
    return success(data=FactoryResp(**f.to_dict()), message="厂区创建成功")


@router.put("/factories/{factory_id}", dependencies=[Depends(require_developer)])
async def update_factory(factory_id: int, req: FactoryUpdateReq, db: AsyncSession = Depends(get_db)):
    f = await svc.update_factory(db, factory_id, req.model_dump(exclude_none=True))
    return success(data=FactoryResp(**f.to_dict()), message="厂区更新成功")


@router.delete("/factories/{factory_id}", dependencies=[Depends(require_developer)])
async def delete_factory(factory_id: int, db: AsyncSession = Depends(get_db)):
    await svc.delete_factory(db, factory_id)
    return success(message="厂区已删除")


# ── Line ──
@router.get("/lines", dependencies=[Depends(rate_limit("lines", 60, 60))])
async def list_lines(
    factory_id: int = Query(None),
    db: AsyncSession = Depends(get_db),
):
    lines = await svc.list_lines(db, factory_id)
    return success(data=[LineResp(**l.to_dict()) for l in lines])


@router.post("/lines", dependencies=[Depends(require_developer)])
async def create_line(req: LineCreateReq, db: AsyncSession = Depends(get_db)):
    l = await svc.create_line(db, req.model_dump())
    return success(data=LineResp(**l.to_dict()), message="线体创建成功")


@router.put("/lines/{line_id}", dependencies=[Depends(require_developer)])
async def update_line(line_id: int, req: LineUpdateReq, db: AsyncSession = Depends(get_db)):
    l = await svc.update_line(db, line_id, req.model_dump(exclude_none=True))
    return success(data=LineResp(**l.to_dict()), message="线体更新成功")


@router.delete("/lines/{line_id}", dependencies=[Depends(require_developer)])
async def delete_line(line_id: int, db: AsyncSession = Depends(get_db)):
    await svc.delete_line(db, line_id)
    return success(message="线体已删除")


# ── EquipmentDefinition ──
@router.get("/definitions")
async def list_definitions(db: AsyncSession = Depends(get_db)):
    defs = await svc.list_definitions(db)
    return success(data=[DefinitionResp(**d.to_dict()) for d in defs])


@router.post("/definitions", dependencies=[Depends(require_developer)])
async def create_definition(req: DefinitionCreateReq, db: AsyncSession = Depends(get_db)):
    d = await svc.create_definition(db, req.model_dump())
    return success(data=DefinitionResp(**d.to_dict()), message="装备定义创建成功")


@router.put("/definitions/{def_id}", dependencies=[Depends(require_developer)])
async def update_definition(def_id: int, req: DefinitionUpdateReq, db: AsyncSession = Depends(get_db)):
    d = await svc.update_definition(db, def_id, req.model_dump(exclude_none=True))
    return success(data=DefinitionResp(**d.to_dict()), message="装备定义更新成功")


@router.get("/definitions/{def_id}")
async def get_definition(def_id: int, db: AsyncSession = Depends(get_db)):
    d = await svc.get_definition(db, def_id)
    return success(data=DefinitionResp(**d.to_dict()))


@router.delete("/definitions/{def_id}", dependencies=[Depends(require_developer)])
async def delete_definition(def_id: int, db: AsyncSession = Depends(get_db)):
    await svc.delete_definition(db, def_id)
    return success(message="装备定义已删除")


# ── Station ──
@router.get("", dependencies=[Depends(rate_limit("stations", 60, 60))])
async def list_stations(
    line_id: int = Query(None),
    db: AsyncSession = Depends(get_db),
):
    stations = await svc.list_stations(db, line_id)
    return success(data=[StationResp(**s.to_dict()) for s in stations])


@router.post("", dependencies=[Depends(require_developer)])
async def create_station(req: StationCreateReq, db: AsyncSession = Depends(get_db)):
    s = await svc.create_station(db, req.model_dump())
    return success(data=StationResp(**s.to_dict()), message="工站创建成功")


@router.get("/{station_id}", dependencies=[Depends(rate_limit("station", 60, 60))])
async def get_station(station_id: int, db: AsyncSession = Depends(get_db)):
    s = await db.get(TestStation, station_id)
    if not s:
        from app.core.exceptions import NotFoundError
        raise NotFoundError("工站不存在")
    return success(data=StationResp(**s.to_dict()))


@router.get("/{station_id}/detail", dependencies=[Depends(rate_limit("station_detail", 30, 60))])
async def get_station_detail(station_id: int, db: AsyncSession = Depends(get_db)):
    station, cabinets, chassis_list, slots = await svc.get_station_detail(db, station_id)
    cab_resps = []
    for cab in cabinets:
        ch_resps = []
        for ch in cab._chassis_list:
            slot_resps = [SlotResp(**s.to_dict()) for s in ch._slots]
            ch_resps.append(ChassisResp(**ch.to_dict(), slots=slot_resps))
        cab_resps.append(CabinetResp(**cab.to_dict(), chassis_list=ch_resps))
    detail = StationDetailResp(station=StationResp(**station.to_dict()), cabinets=cab_resps)
    return success(data=detail)


@router.put("/{station_id}", dependencies=[Depends(require_process), Depends(rate_limit("update_station", 60, 60))])
async def update_station(station_id: int, req: StationUpdateReq, db: AsyncSession = Depends(get_db)):
    s = await svc.update_station(db, station_id, req.model_dump(exclude_none=True))
    return success(data=StationResp(**s.to_dict()), message="工站更新成功")


@router.delete("/{station_id}", dependencies=[Depends(require_developer)])
async def delete_station(station_id: int, db: AsyncSession = Depends(get_db)):
    await svc.delete_station(db, station_id)
    return success(message="工站已删除")


# ── Chassis ──
@router.get("/{station_id}/chassis")
async def list_chassis(station_id: int, db: AsyncSession = Depends(get_db)):
    chassis_list = await svc.list_chassis(db, station_id)
    return success(data=[ChassisResp(**ch.to_dict()) for ch in chassis_list])


@router.post("/{station_id}/chassis", dependencies=[Depends(require_process)])
async def create_chassis(
    station_id: int,
    req: ChassisCreateReq,
    db: AsyncSession = Depends(get_db),
):
    r = await db.get(TestStation, station_id)
    if not r:
        from app.core.exceptions import NotFoundError
        raise NotFoundError("工站不存在")
    ch = await svc.create_chassis(db, station_id, req.model_dump())
    return success(data=ChassisResp(**ch.to_dict()), message="机框创建成功")


@router.put("/chassis/{chassis_id}", dependencies=[Depends(require_process)])
async def update_chassis(
    chassis_id: int,
    req: ChassisUpdateReq,
    db: AsyncSession = Depends(get_db),
):
    ch = await svc.update_chassis(db, chassis_id, req.model_dump(exclude_none=True))
    return success(data=ChassisResp(**ch.to_dict()), message="机框更新成功")


@router.delete("/chassis/{chassis_id}", dependencies=[Depends(require_process)])
async def delete_chassis(chassis_id: int, db: AsyncSession = Depends(get_db)):
    await svc.delete_chassis(db, chassis_id)
    return success(message="机框已删除")


# ── Slot ──
@router.put("/slots/{slot_id}", dependencies=[Depends(rate_limit("update_slot", 120, 60))])
async def update_slot(
    slot_id: int,
    req: SlotUpdateReq,
    db: AsyncSession = Depends(get_db),
):
    s = await svc.update_slot(db, slot_id, req.model_dump(exclude_none=True))
    return success(data=SlotResp(**s.to_dict()), message="槽位更新成功")


# ── Cabinet Params ──
@router.get("/cabinets/{cabinet_id}/params")
async def list_cabinet_params(cabinet_id: int, db: AsyncSession = Depends(get_db)):
    params = await svc.list_cabinet_params(db, cabinet_id)
    return success(data=[CabinetParamResp(**p.to_dict()) for p in params])


@router.post("/cabinets/{cabinet_id}/params", dependencies=[Depends(require_process)])
async def create_cabinet_param(
    cabinet_id: int,
    req: CabinetParamCreateReq,
    db: AsyncSession = Depends(get_db),
):
    p = await svc.create_cabinet_param(db, cabinet_id, req.model_dump())
    return success(data=CabinetParamResp(**p.to_dict()), message="参数创建成功")


@router.put("/cabinet-params/{param_id}", dependencies=[Depends(require_process)])
async def update_cabinet_param(
    param_id: int,
    req: CabinetParamUpdateReq,
    db: AsyncSession = Depends(get_db),
):
    p = await svc.update_cabinet_param(db, param_id, req.model_dump(exclude_none=True))
    return success(data=CabinetParamResp(**p.to_dict()), message="参数更新成功")


@router.delete("/cabinet-params/{param_id}", dependencies=[Depends(require_process)])
async def delete_cabinet_param(param_id: int, db: AsyncSession = Depends(get_db)):
    await svc.delete_cabinet_param(db, param_id)
    return success(message="参数已删除")


# ── Chassis Params ──
@router.get("/chassis/{chassis_id}/params")
async def list_chassis_params(chassis_id: int, db: AsyncSession = Depends(get_db)):
    params = await svc.list_chassis_params(db, chassis_id)
    return success(data=[ChassisParamResp(**p.to_dict()) for p in params])


@router.post("/chassis/{chassis_id}/params", dependencies=[Depends(require_process)])
async def create_chassis_param(
    chassis_id: int,
    req: ChassisParamCreateReq,
    db: AsyncSession = Depends(get_db),
):
    p = await svc.create_chassis_param(db, chassis_id, req.model_dump())
    return success(data=ChassisParamResp(**p.to_dict()), message="参数创建成功")


@router.put("/chassis-params/{param_id}", dependencies=[Depends(require_process)])
async def update_chassis_param(
    param_id: int,
    req: ChassisParamUpdateReq,
    db: AsyncSession = Depends(get_db),
):
    p = await svc.update_chassis_param(db, param_id, req.model_dump(exclude_none=True))
    return success(data=ChassisParamResp(**p.to_dict()), message="参数更新成功")


@router.delete("/chassis-params/{param_id}", dependencies=[Depends(require_process)])
async def delete_chassis_param(param_id: int, db: AsyncSession = Depends(get_db)):
    await svc.delete_chassis_param(db, param_id)
    return success(message="参数已删除")


# ── Equipment Config ──
@router.get("/{station_id}/equipment")
async def get_equipment(station_id: int, db: AsyncSession = Depends(get_db)):
    cfg = await svc.get_equipment_config(db, station_id)
    return success(data=EquipmentConfigResp(**cfg.to_dict()))


@router.put("/{station_id}/equipment", dependencies=[Depends(require_process), Depends(rate_limit("update_equipment", 30, 60))])
async def update_equipment(station_id: int, req: EquipmentConfigReq, db: AsyncSession = Depends(get_db)):
    cfg = await svc.update_equipment_config(db, station_id, req.model_dump(exclude_none=True))
    return success(data=EquipmentConfigResp(**cfg.to_dict()), message="装备参数更新成功")


# ── Hardware Params ──
@router.get("/{station_id}/hardware")
async def list_hardware(station_id: int, db: AsyncSession = Depends(get_db)):
    params = await svc.list_hardware_params(db, station_id)
    return success(data=[HardwareParamResp(**p.to_dict()) for p in params])


@router.post("/{station_id}/hardware", dependencies=[Depends(require_process)])
async def create_hardware(station_id: int, req: HardwareParamCreateReq, db: AsyncSession = Depends(get_db)):
    p = await svc.create_hardware_param(db, station_id, req.model_dump())
    return success(data=HardwareParamResp(**p.to_dict()), message="硬件参数添加成功")


@router.put("/hardware/{param_id}", dependencies=[Depends(require_process)])
async def update_hardware(param_id: int, req: HardwareParamUpdateReq, db: AsyncSession = Depends(get_db)):
    p = await svc.update_hardware_param(db, param_id, req.model_dump(exclude_none=True))
    return success(data=HardwareParamResp(**p.to_dict()), message="硬件参数更新成功")


@router.delete("/hardware/{param_id}", dependencies=[Depends(require_process)])
async def delete_hardware(param_id: int, db: AsyncSession = Depends(get_db)):
    await svc.delete_hardware_param(db, param_id)
    return success(message="硬件参数已删除")


@router.put("/{station_id}/hardware/batch", dependencies=[Depends(require_developer)])
async def batch_replace_hardware(station_id: int, req: HardwareBatchReplaceReq, db: AsyncSession = Depends(get_db)):
    await svc.batch_replace_hardware(db, station_id, [p.model_dump() for p in req.params])
    return success(message="硬件参数批量替换成功")


# ── Software Config ──
@router.get("/{station_id}/software")
async def get_software(station_id: int, db: AsyncSession = Depends(get_db)):
    cfg = await svc.get_software_config(db, station_id)
    return success(data=SoftwareConfigResp(**cfg.to_dict()))


@router.put("/{station_id}/software", dependencies=[Depends(require_developer), Depends(rate_limit("update_software", 30, 60))])
async def update_software(station_id: int, req: SoftwareConfigReq, db: AsyncSession = Depends(get_db)):
    cfg = await svc.update_software_config(db, station_id, req.model_dump(exclude_none=True))
    return success(data=SoftwareConfigResp(**cfg.to_dict()), message="软件配置更新成功")


# ── Scenario Config ──
@router.get("/{station_id}/scenario")
async def get_scenario(station_id: int, db: AsyncSession = Depends(get_db)):
    cfg = await svc.get_scenario_config(db, station_id)
    return success(data=ScenarioConfigResp(**cfg.to_dict()))


@router.put("/{station_id}/scenario", dependencies=[Depends(require_process), Depends(rate_limit("update_scenario", 30, 60))])
async def update_scenario(station_id: int, req: ScenarioConfigReq, db: AsyncSession = Depends(get_db)):
    cfg = await svc.update_scenario_config(db, station_id, req.model_dump())
    return success(data=ScenarioConfigResp(**cfg.to_dict()), message="场景参数更新成功")


# ── Metrics ──
@router.get("/{station_id}/metrics")
async def get_metrics(station_id: int, db: AsyncSession = Depends(get_db)):
    m = await svc.get_metrics(db, station_id)
    return success(data=MetricsResp(**m.to_dict()))


@router.put("/{station_id}/metrics", dependencies=[Depends(require_developer), Depends(rate_limit("update_metrics", 30, 60))])
async def update_metrics(station_id: int, req: MetricsReq, db: AsyncSession = Depends(get_db)):
    m = await svc.update_metrics(db, station_id, req.metrics)
    return success(data=MetricsResp(**m.to_dict()), message="指标更新成功")


# ── Property Page ──
@router.get("/{station_id}/property-page")
async def get_property_page(station_id: int, db: AsyncSession = Depends(get_db)):
    p = await svc.get_property_page(db, station_id)
    return success(data=PropertyPageResp(**p.to_dict()))


@router.put("/{station_id}/property-page", dependencies=[Depends(require_process)])
async def update_property_page(station_id: int, req: PropertyPageReq, db: AsyncSession = Depends(get_db)):
    p = await svc.update_property_page(db, station_id, req.page_data)
    return success(data=PropertyPageResp(**p.to_dict()), message="属性页更新成功")


@router.put("/{station_id}/sync-version-props", dependencies=[Depends(require_process)])
async def sync_version_props(station_id: int, req: SyncVersionPropsReq, db: AsyncSession = Depends(get_db)):
    p = await svc.sync_version_props(db, station_id, req.version_id)
    return success(data=PropertyPageResp(**p.to_dict()), message="版本属性同步成功")


# ── Version Check ──
@router.get("/{station_id}/version-check")
async def version_check(station_id: int, db: AsyncSession = Depends(get_db)):
    result = await svc.version_check(db, station_id)
    return success(data=result)


@router.post("/{station_id}/update-version", dependencies=[Depends(require_developer)])
async def update_station_version(station_id: int, db: AsyncSession = Depends(get_db)):
    result = await svc.version_check(db, station_id)
    if result["needs_update"]:
        st = await db.get(TestStation, station_id)
        if st:
            st.deployed_version = st.latest_version
            await db.flush()
    return success(data=result, message="版本更新成功")


@router.get("/{station_id}/deployed-version")
async def get_deployed_version(
    station_id: int,
    project: str = Query(""),
    sequence_id: int = Query(0),
    db: AsyncSession = Depends(get_db),
):
    from app.services.version_service import VersionService
    result = await VersionService.get_station_deployed_version(db, station_id, project, sequence_id)
    # result is {"code": 0, "data": ...} from Flask v1 compat
    return success(data=result.get("data"))


@router.get("/{station_id}/deployed-versions")
async def list_station_deployed_versions(
    station_id: int,
    deployed_only: bool = Query(False),
    db: AsyncSession = Depends(get_db),
):
    from app.services.version_service import VersionService
    versions = await VersionService.list_station_deployed_versions(db, station_id, deployed_only)
    return success(data=versions)


@router.get("/{station_id}/deployed-archives")
async def get_station_deployed_archives(station_id: int, db: AsyncSession = Depends(get_db)):
    from app.services.version_service import VersionService
    result = await VersionService.get_station_deployed_archives(db, station_id)
    return success(data=result)


# ── Force Restart ──
@router.post("/chassis/{chassis_id}/restart", dependencies=[Depends(require_process)])
async def force_restart_chassis(chassis_id: int, db: AsyncSession = Depends(get_db)):
    info = await svc.force_restart_chassis(db, chassis_id)
    return success(data=info, message=f"已重置 {info['chassis_name']} 下 {info['reset_count']} 个槽位")


@router.post("/cabinets/{cabinet_id}/restart", dependencies=[Depends(require_process)])
async def force_restart_cabinet(cabinet_id: int, db: AsyncSession = Depends(get_db)):
    info = await svc.force_restart_cabinet(db, cabinet_id)
    return success(data=info, message=f"已重置 {info['cabinet_name']} 下 {info['reset_count']} 个槽位")
