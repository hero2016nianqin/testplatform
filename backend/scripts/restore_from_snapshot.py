"""从 indicator_version_snapshot 快照恢复主表数据（开发环境 SQLite）

背景：BOM/指标主表被清空，但版本快照表保留了历史完整配置。
本脚本按"每个实体取最新版本快照"重建：
  indicator_dict ← indicator 快照
  test_item_collection / collection_test_item ← collection 快照
  bom_config / bom_indicator / test_item_indicator ← bom 快照
用法: APP_ENV=dev python -m scripts.restore_from_snapshot
"""
import asyncio, json
from sqlalchemy import delete as sa_delete, select
from app.core.database import AsyncSessionLocal
from app.models.metrics import (
    IndicatorDict, TestItemCollection, CollectionTestItem,
    TestItemIndicator, BomConfig, BomIndicator,
)


def _load(data):
    return json.loads(data) if isinstance(data, str) else data


async def _latest_by_entity(db, etype):
    """按 entity_id 取 version 最大的快照。"""
    from sqlalchemy import text
    rows = (await db.execute(text(
        "SELECT entity_id, version, snapshot_data FROM indicator_version_snapshot WHERE entity_type=:t ORDER BY version DESC"
    ), {"t": etype})).fetchall()
    best = {}
    for entity_id, version, data in rows:
        if entity_id not in best:
            best[entity_id] = _load(data)
    return best


async def restore():
    async with AsyncSessionLocal() as db:
        ind_best = await _latest_by_entity(db, "indicator")
        coll_best = await _latest_by_entity(db, "collection")
        bom_best = await _latest_by_entity(db, "bom")
        print(f"最新快照: indicator={len(ind_best)} collection={len(coll_best)} bom={len(bom_best)}")

        # 清空主表
        for m in [BomIndicator, BomConfig, TestItemIndicator, CollectionTestItem, TestItemCollection, IndicatorDict]:
            await db.execute(sa_delete(m))

        # 1. 指标字典
        for data in ind_best.values():
            d = data.get("indicator") or {}
            db.add(IndicatorDict(
                id=d["id"],
                code=d.get("code", ""), name=d.get("name", ""),
                category=d.get("category", ""), domain=d.get("domain", ""),
                unit=d.get("unit", ""), hardware_model=d.get("hardware_model", ""),
                test_rule=d.get("test_rule", ""), params=d.get("params") or {},
                test_params=d.get("test_params") or [], script_source=d.get("script_source", ""),
                status=d.get("status", 1), description=d.get("description", ""),
            ))

        # 2. 集合 + 测试项
        item_to_proc_station = {}
        for data in coll_best.values():
            c = data.get("collection") or {}
            db.add(TestItemCollection(
                id=c["id"], name=c.get("name", ""), code=c.get("code", ""),
                product_type=c.get("product_type", ""), description=c.get("description", ""),
                status=c.get("status", 1),
            ))
            for it in data.get("items", []) or []:
                db.add(CollectionTestItem(
                    id=it["id"], collection_id=it["collection_id"], name=it.get("name", ""),
                    station=it.get("station", ""), process_name=it.get("process_name", ""),
                    test_type=it.get("test_type", ""), sort_order=it.get("sort_order", 0),
                    service_address=it.get("service_address"), timeout_seconds=it.get("timeout_seconds"),
                    block_type=it.get("block_type", "normal"), parallel_enabled=it.get("parallel_enabled", 0),
                    status=it.get("status", 1), item_revision=it.get("item_revision", 0),
                    owner_id=it.get("owner_id"), owner_name=it.get("owner_name"),
                    owner_manual=it.get("owner_manual", 0),
                ))
                item_to_proc_station.setdefault(
                    (str(it.get("process_name", "")), str(it.get("station", "") or it.get("station_name", ""))), []
                ).append(it["id"])

        # 3. BOM + 指标 + 测试项-指标绑定（BomIndicator 按 id 去重，最新快照优先）
        ti_indicator_seen = set()
        bi_seen = set()
        for data in bom_best.values():
            bc = data.get("bom_config") or {}
            db.add(BomConfig(
                id=bc["id"], bom_code=bc.get("bom_code", ""), bom_name=bc.get("bom_name", ""),
                collection_id=bc.get("collection_id"),
            ))
            for ind in data.get("indicators", []) or []:
                if ind["id"] in bi_seen:
                    continue
                bi_seen.add(ind["id"])
                db.add(BomIndicator(
                    id=ind["id"], bom_config_id=bc["id"], indicator_id=ind["indicator_id"],
                    unit=ind.get("unit", ""), judgment_rule=ind.get("judgment_rule", "合格"),
                    test_stage=ind.get("test_stage", ""), remark=ind.get("remark", ""),
                    status=ind.get("status", 1), process_name=ind.get("process_name", ""),
                    station_name=ind.get("station_name", ""), params=ind.get("params") or [],
                ))
                # 测试项绑定：按 (process, station) 匹配集合测试项
                key = (str(ind.get("process_name", "")), str(ind.get("station_name", "")))
                for tid in item_to_proc_station.get(key, []):
                    if (tid, ind["indicator_id"]) not in ti_indicator_seen:
                        ti_indicator_seen.add((tid, ind["indicator_id"]))
                        db.add(TestItemIndicator(test_item_id=tid, indicator_id=ind["indicator_id"]))

        await db.commit()

        # 报告
        for m, name in [(IndicatorDict, "indicator_dict"), (TestItemCollection, "test_item_collection"),
                        (CollectionTestItem, "collection_test_item"), (BomConfig, "bom_config"),
                        (BomIndicator, "bom_indicator"), (TestItemIndicator, "test_item_indicator")]:
            n = (await db.execute(select(m.id).limit(1))).scalars().all()
            cnt = (await db.execute(select(__import__('sqlalchemy').func.count()).select_from(m))).scalar()
            print(f"  {name}: {cnt}")
    print("恢复完成")


if __name__ == "__main__":
    asyncio.run(restore())
