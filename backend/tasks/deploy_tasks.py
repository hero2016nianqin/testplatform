"""
版本部署推送任务
对应 design.md §7.4 — _push_version_to_station 完整业务逻辑
"""
import asyncio
import json
from typing import Optional

from sqlalchemy import select

from tasks.celery_app import celery_app
from app.core.database import AsyncSessionLocal
from app.models.version import (
    TestVersion, VersionArchiveItem, ReleaseDeployment,
)
from app.models.station import TestStation
from app.models.station_config import SoftwareConfig
from app.models.equipment import EquipmentMetrics, EquipmentPropertyPage


def run_sync(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _get_station_ids(dep) -> list[int]:
    """根据 deployment 作用域解析目标工站 ID 列表"""
    from sqlalchemy import select as _select
    # 同步化 — 直接用同步方式获取
    import json
    return []


@celery_app.task(bind=True, max_retries=3, default_retry_delay=10)
def push_version_to_station(self, deployment_id: int):
    """执行版本部署推送到目标工站"""
    async def _push():
        async with AsyncSessionLocal() as db:
            r = await db.execute(select(ReleaseDeployment).where(ReleaseDeployment.id == deployment_id))
            dep = r.scalar_one_or_none()
            if not dep:
                return {"error": "发行目标不存在"}
            if dep.status != "approved":
                return {"error": f"发行目标状态异常: {dep.status}"}

            version_id = dep.version_id
            r = await db.execute(select(TestVersion).where(TestVersion.id == version_id))
            version = r.scalar_one_or_none()
            if not version:
                return {"error": "版本不存在"}

            # Resolve target stations
            station_ids = []
            if dep.station_id:
                station_ids = [dep.station_id]
            elif dep.line_id:
                from app.models.station import ProductionLine as _Line
                r = await db.execute(
                    select(TestStation).where(TestStation.line_id == dep.line_id)
                )
                station_ids = [s.id for s in r.scalars().all()]
            elif dep.factory_id:
                from app.models.station import ProductionLine as _Line
                r = await db.execute(
                    select(TestStation)
                    .join(_Line, TestStation.line_id == _Line.id)
                    .where(_Line.factory_id == dep.factory_id)
                )
                station_ids = [s.id for s in r.scalars().all()]
            else:
                r = await db.execute(select(TestStation))
                station_ids = [s.id for s in r.scalars().all()]

            if not station_ids:
                return {"error": "未找到目标工站"}

            # Get archive items once
            r = await db.execute(
                select(VersionArchiveItem).where(VersionArchiveItem.version_id == version_id)
            )
            archive_items = list(r.scalars().all())

            pushed_count = 0
            for sid in station_ids:
                try:
                    await _push_to_single_station(db, sid, version, archive_items)
                    pushed_count += 1
                except Exception:
                    continue

            dep.status = "deployed"
            dep.deployed_at = __import__('datetime').datetime.utcnow()
            await db.flush()

            # Check if all deployments deployed
            r = await db.execute(
                select(ReleaseDeployment).where(
                    ReleaseDeployment.version_id == version_id,
                    ReleaseDeployment.status != "deployed",
                )
            )
            remaining = list(r.scalars().all())
            if not remaining:
                version.status = "deployed"

            await db.commit()
            return {"deployment_id": deployment_id, "pushed_stations": pushed_count}

    try:
        return run_sync(_push())
    except Exception as exc:
        raise self.retry(exc=exc)


async def _push_to_single_station(db, station_id: int, version: TestVersion, archive_items: list):
    """推送版本内容到单个工站 — _push_version_to_station"""
    r = await db.execute(select(TestStation).where(TestStation.id == station_id))
    station = r.scalar_one_or_none()
    if not station:
        return

    # 1. Update deployed version
    station.deployed_version = version.version

    # 2. Push archive items
    for ai in archive_items:
        if ai.type == "metrics_json":
            r = await db.execute(
                select(EquipmentMetrics).where(EquipmentMetrics.station_id == station_id)
            )
            metrics = r.scalar_one_or_none()
            if metrics and ai.data_snapshot:
                metrics.metrics_json = ai.data_snapshot

        elif ai.type == "property_page":
            r = await db.execute(
                select(EquipmentPropertyPage).where(EquipmentPropertyPage.station_id == station_id)
            )
            prop = r.scalar_one_or_none()
            if prop and ai.data_snapshot:
                if isinstance(ai.data_snapshot, dict) and isinstance(prop.page_json, dict):
                    prop.page_json = {**prop.page_json, **ai.data_snapshot}

        elif ai.type == "sequence_step":
            # Accumulate sequence data
            pass

    # 3. Push sequence data to software_config
    if version.sequence_id:
        r = await db.execute(
            select(SoftwareConfig).where(SoftwareConfig.station_id == station_id)
        )
        sw = r.scalar_one_or_none()
        if sw:
            sequence_steps = [
                a.data_snapshot for a in archive_items
                if a.type == "sequence_step" and a.data_snapshot
            ]
            if sequence_steps:
                sw.sequence_data = sequence_steps

    # 4. Update latest_version
    station.latest_version = version.version


@celery_app.task(bind=True, max_retries=3, default_retry_delay=10)
def batch_deploy_versions(self, version_ids: list[int]):
    """批量部署多个版本"""
    results = []
    for vid in version_ids:
        result = push_version_to_station.delay(vid)
        results.append({"version_id": vid, "task_id": result.id})
    return results
