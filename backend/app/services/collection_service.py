from typing import Optional, List

from sqlalchemy import select, func, distinct
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.metrics import TestItemCollection, CollectionTestItem, TestItemIndicator, IndicatorDict
from app.core.exceptions import NotFoundError, ConflictError
from app.utils.pagination import paginate


class CollectionService:

    @staticmethod
    async def list(
        db: AsyncSession,
        *,
        page: int = 1,
        page_size: int = 20,
        keyword: str = "",
        status: Optional[int] = None,
    ):
        stmt = select(TestItemCollection)
        if keyword:
            stmt = stmt.where(
                TestItemCollection.name.ilike(f"%{keyword}%")
                | TestItemCollection.code.ilike(f"%{keyword}%")
            )
        if status is not None:
            stmt = stmt.where(TestItemCollection.status == status)
        stmt = stmt.order_by(TestItemCollection.id.desc())
        return await paginate(db, stmt, page, page_size)

    @staticmethod
    async def list_all_active(db: AsyncSession) -> List[TestItemCollection]:
        r = await db.execute(
            select(TestItemCollection).where(TestItemCollection.status == 1).order_by(TestItemCollection.id.desc())
        )
        return list(r.scalars().all())

    @staticmethod
    async def get(db: AsyncSession, collection_id: int) -> TestItemCollection:
        r = await db.execute(select(TestItemCollection).where(TestItemCollection.id == collection_id))
        obj = r.scalar_one_or_none()
        if not obj:
            raise NotFoundError("测试项集合不存在")
        return obj

    @staticmethod
    async def create(db: AsyncSession, data: dict) -> TestItemCollection:
        existing = await db.execute(
            select(TestItemCollection).where(TestItemCollection.code == data.get("code"))
        )
        if existing.scalar_one_or_none():
            raise ConflictError("集合编号已存在")
        obj = TestItemCollection(**data)
        db.add(obj)
        await db.flush()
        return obj

    @staticmethod
    async def update(db: AsyncSession, collection_id: int, data: dict, operator: str = "") -> TestItemCollection:
        obj = await CollectionService.get(db, collection_id)
        for k, v in data.items():
            if v is not None:
                setattr(obj, k, v)
        await db.flush()
        from app.services.version_snapshot_service import VersionSnapshotService
        await VersionSnapshotService.snapshot_collection(db, collection_id, operator, "更新集合信息")
        await db.refresh(obj)
        return obj

    @staticmethod
    async def update_status(db: AsyncSession, collection_id: int, status: int, operator: str = ""):
        obj = await CollectionService.get(db, collection_id)
        obj.status = status
        await db.flush()
        from app.services.version_snapshot_service import VersionSnapshotService
        await VersionSnapshotService.snapshot_collection(db, collection_id, operator, f"{'启用' if status == 1 else '归档'}集合")

    # ── Items ──
    @staticmethod
    async def list_items(db: AsyncSession, collection_id: int) -> List[CollectionTestItem]:
        r = await db.execute(
            select(CollectionTestItem)
            .where(CollectionTestItem.collection_id == collection_id)
            .order_by(CollectionTestItem.sort_order)
        )
        return list(r.scalars().all())

    @staticmethod
    async def get_item_domains(db: AsyncSession, item_ids: List[int]) -> dict:
        """按测试项聚合其绑定指标的领域（多个去重后以「、」连接）"""
        if not item_ids:
            return {}
        r = await db.execute(
            select(TestItemIndicator.test_item_id, IndicatorDict.domain)
            .join(IndicatorDict, TestItemIndicator.indicator_id == IndicatorDict.id)
            .where(TestItemIndicator.test_item_id.in_(item_ids), IndicatorDict.domain != "")
        )
        result: dict = {}
        for row in r.all():
            result.setdefault(row[0], [])
            if row[1] not in result[row[0]]:
                result[row[0]].append(row[1])
        return {k: "、".join(v) for k, v in result.items()}

    @staticmethod
    async def list_items_with_domain(db: AsyncSession, collection_id: int) -> List[dict]:
        items = await CollectionService.list_items(db, collection_id)
        domains = await CollectionService.get_item_domains(db, [i.id for i in items])
        return [{**i.to_dict(), "domain": domains.get(i.id, "")} for i in items]

    @staticmethod
    async def create_item(db: AsyncSession, collection_id: int, data: dict, operator: str = "") -> CollectionTestItem:
        obj = CollectionTestItem(collection_id=collection_id, **data)
        db.add(obj)
        await db.flush()
        from app.services.version_snapshot_service import VersionSnapshotService
        await VersionSnapshotService.snapshot_collection(db, collection_id, operator, f"添加测试项 {data.get('name', '')}")
        return obj

    @staticmethod
    async def update_item(db: AsyncSession, item_id: int, data: dict, operator: str = "") -> CollectionTestItem:
        r = await db.execute(select(CollectionTestItem).where(CollectionTestItem.id == item_id))
        obj = r.scalar_one_or_none()
        if not obj:
            raise NotFoundError("测试项不存在")
        for k, v in data.items():
            if v is not None:
                setattr(obj, k, v)
        await db.flush()
        from app.services.version_snapshot_service import VersionSnapshotService
        await VersionSnapshotService.snapshot_collection(db, obj.collection_id, operator, f"更新测试项 {item_id}")
        return obj

    @staticmethod
    async def delete_item(db: AsyncSession, item_id: int, operator: str = ""):
        r = await db.execute(select(CollectionTestItem).where(CollectionTestItem.id == item_id))
        obj = r.scalar_one_or_none()
        if not obj:
            raise NotFoundError("测试项不存在")
        collection_id = obj.collection_id
        await db.delete(obj)
        await db.flush()
        from app.services.version_snapshot_service import VersionSnapshotService
        await VersionSnapshotService.snapshot_collection(db, collection_id, operator, f"删除测试项 {item_id}")

    # ── Test Item Indicators ──

    @staticmethod
    async def list_item_indicators(db: AsyncSession, item_id: int) -> List[dict]:
        r = await db.execute(
            select(
                TestItemIndicator.id,
                TestItemIndicator.test_item_id,
                TestItemIndicator.indicator_id,
                TestItemIndicator.unit,
                TestItemIndicator.judgment_rule,
                IndicatorDict.code.label("indicator_code"),
                IndicatorDict.name.label("indicator_name"),
                IndicatorDict.category,
                IndicatorDict.status.label("dict_status"),
                IndicatorDict.params,
                IndicatorDict.test_params,
            )
            .join(IndicatorDict, TestItemIndicator.indicator_id == IndicatorDict.id)
            .where(TestItemIndicator.test_item_id == item_id)
        )
        results = []
        for row in r.all():
            d = row._asdict()
            d["test_params"] = d.pop("test_params") or []
            d["params"] = d.get("params") or {}
            results.append(d)
        return results

    @staticmethod
    async def list_collection_available_indicators(db: AsyncSession, collection_id: int) -> List[dict]:
        r = await db.execute(
            select(
                IndicatorDict.id,
                IndicatorDict.code,
                IndicatorDict.name,
                IndicatorDict.category,
                IndicatorDict.unit,
                IndicatorDict.status,
                IndicatorDict.params,
            )
            .select_from(CollectionTestItem)
            .join(TestItemIndicator, CollectionTestItem.id == TestItemIndicator.test_item_id)
            .join(IndicatorDict, TestItemIndicator.indicator_id == IndicatorDict.id)
            .where(
                CollectionTestItem.collection_id == collection_id,
                IndicatorDict.status == 1,
            )
            .distinct()
            .order_by(IndicatorDict.code)
        )
        results = []
        for row in r.all():
            d = row._asdict()
            results.append(d)
        return results

    @staticmethod
    async def batch_add_item_indicators(db: AsyncSession, item_id: int, indicators: List[dict]):
        r = await db.execute(select(CollectionTestItem).where(CollectionTestItem.id == item_id))
        if not r.scalar_one_or_none():
            raise NotFoundError("测试项不存在")
        objs = []
        for ind in indicators:
            obj = TestItemIndicator(test_item_id=item_id, **ind)
            db.add(obj)
            objs.append(obj)
        await db.flush()
        return objs

    @staticmethod
    async def delete_item_indicator(db: AsyncSession, indicator_id: int):
        r = await db.execute(select(TestItemIndicator).where(TestItemIndicator.id == indicator_id))
        obj = r.scalar_one_or_none()
        if not obj:
            raise NotFoundError("绑定记录不存在")
        await db.delete(obj)
        await db.flush()
