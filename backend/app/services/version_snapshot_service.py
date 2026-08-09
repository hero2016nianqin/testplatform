from typing import Optional

from sqlalchemy import select, delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.metrics import (
    IndicatorVersionSnapshot, BomConfig, BomIndicator,
    TestItemCollection, CollectionTestItem, IndicatorDict,
)
from app.core.exceptions import NotFoundError
from app.utils.pagination import paginate


class VersionSnapshotService:

    @staticmethod
    async def list(
        db: AsyncSession,
        *,
        page: int = 1,
        page_size: int = 20,
        entity_type: str = "",
        entity_id: int = 0,
        keyword: str = "",
        operator: str = "",
        date_from: str = "",
        date_to: str = "",
    ):
        from sqlalchemy import or_
        stmt = select(IndicatorVersionSnapshot)
        if entity_type:
            stmt = stmt.where(IndicatorVersionSnapshot.entity_type == entity_type)
        if entity_id:
            stmt = stmt.where(IndicatorVersionSnapshot.entity_id == entity_id)
        if keyword:
            stmt = stmt.where(
                or_(
                    IndicatorVersionSnapshot.change_summary.ilike(f"%{keyword}%"),
                    IndicatorVersionSnapshot.entity_type.ilike(f"%{keyword}%"),
                )
            )
        if operator:
            stmt = stmt.where(IndicatorVersionSnapshot.operator.ilike(f"%{operator}%"))
        if date_from:
            stmt = stmt.where(IndicatorVersionSnapshot.created_at >= date_from)
        if date_to:
            stmt = stmt.where(IndicatorVersionSnapshot.created_at <= date_to + " 23:59:59")
        stmt = stmt.order_by(IndicatorVersionSnapshot.id.desc())
        return await paginate(db, stmt, page, page_size)

    @staticmethod
    async def create(db: AsyncSession, data: dict) -> IndicatorVersionSnapshot:
        obj = IndicatorVersionSnapshot(**data)
        db.add(obj)
        await db.flush()
        return obj

    @staticmethod
    async def get(db: AsyncSession, snapshot_id: int) -> IndicatorVersionSnapshot:
        r = await db.execute(select(IndicatorVersionSnapshot).where(IndicatorVersionSnapshot.id == snapshot_id))
        return r.scalar_one_or_none()

    @staticmethod
    async def snapshot_bom_config(db: AsyncSession, config_id: int, operator: str, change_summary: str = ""):
        """Capture a full snapshot of a BOM config and its indicators."""
        r = await db.execute(select(BomConfig).where(BomConfig.id == config_id))
        config = r.scalar_one_or_none()
        if not config:
            return None
        indicators = []
        ir = await db.execute(
            select(
                BomIndicator.id,
                BomIndicator.indicator_id,
                BomIndicator.unit,
                BomIndicator.judgment_rule,
                BomIndicator.test_stage,
                BomIndicator.remark,
                BomIndicator.status,
                BomIndicator.params,
                BomIndicator.process_name,
                BomIndicator.station_name,
                IndicatorDict.code,
                IndicatorDict.name,
                IndicatorDict.category,
                IndicatorDict.params.label("dict_params"),
            )
            .join(IndicatorDict, BomIndicator.indicator_id == IndicatorDict.id, isouter=True)
            .where(BomIndicator.bom_config_id == config_id)
        )
        for row in ir.all():
            d = row._asdict()
            indicators.append(d)

        current_version = config.version
        snapshot_data = {
            "bom_config": {
                "id": config.id,
                "bom_code": config.bom_code,
                "bom_name": config.bom_name,
                "collection_id": config.collection_id,
                "status": config.status,
            },
            "indicators": indicators,
        }
        obj = IndicatorVersionSnapshot(
            entity_type="bom",
            entity_id=config_id,
            version=current_version,
            snapshot_data=snapshot_data,
            change_summary=change_summary,
            operator=operator,
        )
        db.add(obj)
        await db.flush()
        return obj

    @staticmethod
    async def snapshot_collection(db: AsyncSession, collection_id: int, operator: str, change_summary: str = ""):
        """Capture a full snapshot of a test item collection and its items."""
        r = await db.execute(select(TestItemCollection).where(TestItemCollection.id == collection_id))
        collection = r.scalar_one_or_none()
        if not collection:
            return None
        ir = await db.execute(
            select(CollectionTestItem)
            .where(CollectionTestItem.collection_id == collection_id)
            .order_by(CollectionTestItem.sort_order)
        )
        items = [row.to_dict() for row in ir.scalars().all()]

        current_version = collection.version
        snapshot_data = {
            "collection": {
                "id": collection.id,
                "name": collection.name,
                "code": collection.code,
                "product_type": collection.product_type,
                "description": collection.description,
                "status": collection.status,
            },
            "items": items,
        }
        obj = IndicatorVersionSnapshot(
            entity_type="collection",
            entity_id=collection_id,
            version=current_version,
            snapshot_data=snapshot_data,
            change_summary=change_summary,
            operator=operator,
        )
        db.add(obj)
        await db.flush()
        return obj

    @staticmethod
    async def snapshot_indicator(db: AsyncSession, indicator_id: int, operator: str, change_summary: str = ""):
        """Capture a full snapshot of an indicator dict entry and its params."""
        r = await db.execute(
            select(IndicatorDict).where(IndicatorDict.id == indicator_id)
        )
        indicator = r.scalar_one_or_none()
        if not indicator:
            return None
        snapshot_data = {
            "indicator": indicator.to_dict(),
        }
        obj = IndicatorVersionSnapshot(
            entity_type="indicator",
            entity_id=indicator_id,
            version=1,
            snapshot_data=snapshot_data,
            change_summary=change_summary,
            operator=operator,
        )
        db.add(obj)
        await db.flush()
        return obj

    @staticmethod
    async def rollback(db: AsyncSession, snapshot_id: int, operator: str):
        """Rollback a BOM or collection to the state captured in a snapshot."""
        r = await db.execute(select(IndicatorVersionSnapshot).where(IndicatorVersionSnapshot.id == snapshot_id))
        snapshot = r.scalar_one_or_none()
        if not snapshot:
            raise NotFoundError("版本记录不存在")
        data = snapshot.snapshot_data

        if snapshot.entity_type == "bom":
            config_id = snapshot.entity_id
            r = await db.execute(select(BomConfig).where(BomConfig.id == config_id))
            config = r.scalar_one_or_none()
            if not config:
                raise NotFoundError("BOM配置已不存在")

            bom_data = data.get("bom_config", {})
            config.bom_code = bom_data.get("bom_code", config.bom_code)
            config.bom_name = bom_data.get("bom_name", config.bom_name)
            config.collection_id = bom_data.get("collection_id", config.collection_id)
            config.status = bom_data.get("status", config.status)

            # Replace all indicators
            await db.execute(
                sa_delete(BomIndicator).where(BomIndicator.bom_config_id == config_id)
            )
            for ind in data.get("indicators", []):
                db.add(BomIndicator(
                    bom_config_id=config_id,
                    indicator_id=ind["indicator_id"],
                    unit=ind.get("unit", ""),
                    judgment_rule=ind.get("judgment_rule", "合格"),
                    test_stage=ind.get("test_stage", ""),
                    remark=ind.get("remark", ""),
                    status=ind.get("status", 1),
                    params=ind.get("params") or [],
                ))
            await db.flush()
            await VersionSnapshotService.snapshot_bom_config(
                db, config_id, operator, f"回滚至版本 {snapshot.version}",
            )

        elif snapshot.entity_type == "collection":
            collection_id = snapshot.entity_id
            r = await db.execute(select(TestItemCollection).where(TestItemCollection.id == collection_id))
            collection = r.scalar_one_or_none()
            if not collection:
                raise NotFoundError("测试项集合已不存在")

            coll_data = data.get("collection", {})
            collection.name = coll_data.get("name", collection.name)
            collection.product_type = coll_data.get("product_type", collection.product_type)
            collection.description = coll_data.get("description", collection.description)
            collection.status = coll_data.get("status", collection.status)

            await db.execute(
                sa_delete(CollectionTestItem).where(CollectionTestItem.collection_id == collection_id)
            )
            for item in data.get("items", []):
                db.add(CollectionTestItem(
                    collection_id=collection_id,
                    name=item["name"],
                    station=item.get("station", ""),
                    test_type=item.get("test_type", ""),
                    sort_order=item.get("sort_order", 0),
                    service_address=item.get("service_address", ""),
                    timeout_seconds=item.get("timeout_seconds"),
                    block_type=item.get("block_type", "normal"),
                    parallel_enabled=item.get("parallel_enabled", 0),
                    status=item.get("status", 1),
                ))
            await VersionSnapshotService.snapshot_collection(
                db, collection_id, operator, f"回滚至版本 {snapshot.version}",
            )

        return snapshot
