from typing import Optional, List
from datetime import datetime

from sqlalchemy import select, func, delete as sa_delete, update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.metrics import BomConfig, BomIndicator, BomDomainOwner, IndicatorDict, TestItemCollection, CollectionTestItem, TestItemIndicator, ParamChangeLog
from app.routers.ws_router import get_bom_online_users
from app.core.exceptions import NotFoundError
from app.utils.pagination import paginate
from app.services.collection_service import CollectionService


class BomConfigService:

    @staticmethod
    async def list(
        db: AsyncSession,
        *,
        page: int = 1,
        page_size: int = 20,
        keyword: str = "",
        status: Optional[int] = None,
    ):
        stmt = select(BomConfig)
        if keyword:
            stmt = stmt.where(
                BomConfig.bom_code.ilike(f"%{keyword}%")
                | BomConfig.bom_name.ilike(f"%{keyword}%")
            )
        if status is not None:
            stmt = stmt.where(BomConfig.status == status)
        stmt = stmt.order_by(BomConfig.id.desc())
        return await paginate(db, stmt, page, page_size)

    @staticmethod
    async def list_bom_codes(db: AsyncSession, keyword: str = "") -> List[dict]:
        stmt = select(BomConfig.bom_code, BomConfig.bom_name).distinct()
        if keyword:
            stmt = stmt.where(
                BomConfig.bom_code.ilike(f"%{keyword}%")
                | BomConfig.bom_name.ilike(f"%{keyword}%")
            )
        stmt = stmt.order_by(BomConfig.bom_code)
        r = await db.execute(stmt)
        return [{"bom_code": row[0], "bom_name": row[1]} for row in r.all()]

    @staticmethod
    async def list_grouped_by_code(
        db: AsyncSession,
        *,
        page: int = 1,
        page_size: int = 20,
        keyword: str = "",
        status: Optional[int] = None,
    ):
        """按 BOM 编码聚合：每个编码仅保留最新版本（version 最大），分页单位是编码而非版本。"""
        stmt = select(BomConfig)
        if keyword:
            stmt = stmt.where(
                BomConfig.bom_code.ilike(f"%{keyword}%")
                | BomConfig.bom_name.ilike(f"%{keyword}%")
            )
        if status is not None:
            stmt = stmt.where(BomConfig.status == status)
        rows = (await db.execute(stmt)).scalars().all()
        grouped: dict = {}
        for row in rows:
            cur = grouped.get(row.bom_code)
            if cur is None or (row.version, row.id) > (cur.version, cur.id):
                grouped[row.bom_code] = row
        items = list(grouped.values())
        items.sort(key=lambda x: x.id, reverse=True)
        total = len(items)
        start = (page - 1) * page_size
        page_items = items[start:start + page_size]
        return page_items, total, page, page_size

    @staticmethod
    async def list_by_code(db: AsyncSession, bom_code: str):
        """某 BOM 编码下的全部版本，按版本号降序。"""
        r = await db.execute(
            select(BomConfig)
            .where(BomConfig.bom_code == bom_code)
            .order_by(BomConfig.version.desc(), BomConfig.id.desc())
        )
        return r.scalars().all()

    @staticmethod
    async def get_domain_owners(db: AsyncSession, config_id: int) -> dict:
        obj = await BomConfigService.get(db, config_id)
        r = await db.execute(
            select(IndicatorDict.domain)
            .join(BomIndicator, BomIndicator.indicator_id == IndicatorDict.id)
            .where(BomIndicator.bom_config_id == config_id)
            .distinct()
        )
        domains = [row[0] for row in r.all() if row[0]]
        return {"domain_owners": obj.domain_owners or {}, "domains": domains}

    @staticmethod
    async def update_domain_owners(db: AsyncSession, config_id: int, domain_owners: dict):
        obj = await BomConfigService.get(db, config_id)
        cleaned = {}
        for k, v in (domain_owners or {}).items():
            key = str(k)
            val = BomConfigService._normalize_owners(str(v))
            if val:
                cleaned[key] = val
        obj.domain_owners = cleaned
        await db.flush()
        await db.refresh(obj)
        await BomConfigService.refresh_item_owners_by_domain(db, obj.bom_code, cleaned)
        return obj.domain_owners or {}

    @staticmethod
    async def get_domain_owners_by_bom_code(db: AsyncSession, bom_code: str) -> dict:
        """获取 BOM 编码级别的领域负责人配置"""
        from app.models.metrics import BomDomainOwner
        r = await db.execute(
            select(BomDomainOwner).where(BomDomainOwner.bom_code == bom_code)
        )
        obj = r.scalar_one_or_none()
        # Also get domains from indicators in this BOM code
        r2 = await db.execute(
            select(IndicatorDict.domain)
            .join(BomIndicator, BomIndicator.indicator_id == IndicatorDict.id)
            .join(BomConfig, BomIndicator.bom_config_id == BomConfig.id)
            .where(BomConfig.bom_code == bom_code)
            .distinct()
        )
        domains = [row[0] for row in r2.all() if row[0]]
        return {"domain_owners": obj.domain_owners if obj else {}, "domains": domains}

    @staticmethod
    def _normalize_owners(raw: str) -> str:
        """将负责人字符串按分号/逗号/空格拆分，去空后以英文逗号连接"""
        import re
        parts = re.split(r'[,;，；\s]+', str(raw or ''))
        return ','.join(p.strip() for p in parts if p.strip())

    @staticmethod
    async def update_domain_owners_by_bom_code(db: AsyncSession, bom_code: str, domain_owners: dict):
        """更新 BOM 编码级别的领域负责人配置"""
        from app.models.metrics import BomDomainOwner
        r = await db.execute(
            select(BomDomainOwner).where(BomDomainOwner.bom_code == bom_code)
        )
        obj = r.scalar_one_or_none()
        cleaned = {}
        for k, v in (domain_owners or {}).items():
            key = str(k)
            val = BomConfigService._normalize_owners(str(v))
            if val:
                cleaned[key] = val
        if obj:
            obj.domain_owners = cleaned
        else:
            obj = BomDomainOwner(bom_code=bom_code, domain_owners=cleaned)
            db.add(obj)
        await db.flush()
        await db.refresh(obj)
        await BomConfigService.refresh_item_owners_by_domain(db, bom_code, cleaned)
        return obj.domain_owners or {}

    @staticmethod
    async def refresh_item_owners_by_domain(db: AsyncSession, bom_code: str, domain_owners: dict):
        """领域负责人配置保存后，批量刷新本 BOM 编码下所有测试项的负责人。
        规则：测试项领域命中配置项则自动填充负责人；已被手动覆盖（owner_manual）的测试项不刷新。
        负责人支持逗号分隔的多值，取第一个可匹配用户。
        """
        from app.models.user import User
        if not domain_owners:
            return
        # 解析所有负责人为独立用户名集合
        all_owner_names = set()
        for owners in domain_owners.values():
            for o in owners.split(","):
                o = o.strip()
                if o:
                    all_owner_names.add(o)
        # 该 BOM 编码下的全部 BOM 配置 -> 涉及集合 -> 测试项
        r = await db.execute(
            select(BomConfig.collection_id).where(BomConfig.bom_code == bom_code, BomConfig.collection_id.isnot(None))
        )
        collection_ids = {row[0] for row in r.all()}
        if not collection_ids:
            return
        r = await db.execute(
            select(CollectionTestItem)
            .where(
                CollectionTestItem.collection_id.in_(collection_ids),
                CollectionTestItem.owner_manual == 0,
            )
        )
        items = r.scalars().all()
        if not items:
            return
        domains = await CollectionService.get_item_domains(db, [i.id for i in items])
        # 解析负责人字符串 -> 用户
        user_map: dict = {}
        if all_owner_names:
            ur = await db.execute(
                select(User.id, User.username, User.display_name).where(
                    (User.username.in_(all_owner_names)) | (User.display_name.in_(all_owner_names))
                )
            )
            for uid, uname, dname in ur.all():
                user_map[uname] = {"id": uid, "name": uname}
                user_map[dname] = {"id": uid, "name": uname}
        changed = 0
        for item in items:
            item_domain = domains.get(item.id, "")
            if not item_domain:
                continue
            # 测试项领域可能含多个，按配置命中优先；取第一个命中的领域负责人
            owner = ""
            for d in item_domain.split("、"):
                if d in domain_owners:
                    owner = domain_owners[d]
                    break
            if not owner:
                continue
            # 多个负责人取第一个可匹配用户的，否则取第一个
            owners_list = [o.strip() for o in owner.split(",") if o.strip()]
            resolved_owner = ""
            resolved_id = None
            for o in owners_list:
                if o in user_map:
                    resolved_owner = o
                    resolved_id = user_map[o]["id"]
                    break
            if not resolved_owner and owners_list:
                resolved_owner = owners_list[0]
            if resolved_owner:
                new_owner_id = resolved_id
                new_owner_name = resolved_owner
            else:
                new_owner_id = None
                new_owner_name = owner
            if item.owner_id != new_owner_id or (item.owner_name or "") != new_owner_name:
                item.owner_id = new_owner_id
                item.owner_name = new_owner_name
                changed += 1
        if changed:
            await db.flush()

    @staticmethod
    async def update_item_owner(db: AsyncSession, item_id: int, owner_name: str = "", operator: str = ""):
        """单行手动修改测试项负责人（手动覆盖自动填充规则）"""
        from app.models.user import User
        r = await db.execute(select(CollectionTestItem).where(CollectionTestItem.id == item_id))
        item = r.scalar_one_or_none()
        if not item:
            raise NotFoundError("测试项不存在")
        owner_name = BomConfigService._normalize_owners(owner_name)
        item.owner_manual = 1
        if owner_name:
            # 多个负责人取第一个可匹配用户的，否则取第一个
            owners_list = [o.strip() for o in owner_name.split(",") if o.strip()]
            resolved_owner = ""
            resolved_id = None
            for o in owners_list:
                ur = await db.execute(
                    select(User.id, User.username, User.display_name).where(
                        (User.username == o) | (User.display_name == o)
                    )
                )
                row = ur.first()
                if row:
                    resolved_owner = o
                    resolved_id = row.id
                    break
            if not resolved_owner and owners_list:
                resolved_owner = owners_list[0]
            if resolved_owner:
                item.owner_id = resolved_id
                item.owner_name = resolved_owner
            else:
                item.owner_id = None
                item.owner_name = owner_name
        else:
            item.owner_id = None
            item.owner_name = ""
        await db.flush()
        return item

    @staticmethod
    async def get(db: AsyncSession, config_id: int) -> BomConfig:
        r = await db.execute(select(BomConfig).where(BomConfig.id == config_id))
        obj = r.scalar_one_or_none()
        if not obj:
            raise NotFoundError("BOM配置不存在")
        return obj

    @staticmethod
    async def create(db: AsyncSession, data: dict) -> BomConfig:
        collection_id = data.get("collection_id")
        bom_code = data.get("bom_code", "")
        if collection_id:
            r = await db.execute(
                select(TestItemCollection.version).where(TestItemCollection.id == collection_id)
            )
            coll_ver = r.scalar_one_or_none()
            if coll_ver is not None:
                data["collection_version"] = coll_ver
        if bom_code:
            # Check unique constraint: only one non-archived/non-approved BOM per bom_code
            r = await db.execute(
                select(BomConfig).where(
                    BomConfig.bom_code == bom_code,
                    BomConfig.archived == False,
                    BomConfig.review_status != "approved"
                )
            )
            existing = r.scalar_one_or_none()
            if existing:
                raise ValueError(f"已存在未归档且未评审通过的 BOM 编码: {bom_code}")
            r = await db.execute(
                select(func.max(BomConfig.version)).where(BomConfig.bom_code == bom_code)
            )
            max_ver = r.scalar()
            data["version"] = (max_ver or 0) + 1
        obj = BomConfig(**data)
        db.add(obj)
        await db.flush()
        return obj

    @staticmethod
    async def update(db: AsyncSession, config_id: int, data: dict) -> BomConfig:
        obj = await BomConfigService.get(db, config_id)
        # 已发布或已归档的 BOM 仅允许修改名称/状态，禁止修改核心绑定与版本引用
        immutable_fields = {"bom_code", "collection_id", "collection_version", "version"}
        if (obj.archived or obj.review_status == "approved") and immutable_fields.intersection(data):
            raise ValueError("已发布或归档的 BOM 不能修改编码/绑定集合/版本引用")
        if "bom_code" in data and data["bom_code"] != obj.bom_code:
            new_bom_code = data["bom_code"]
            r = await db.execute(
                select(BomConfig).where(
                    BomConfig.bom_code == new_bom_code,
                    BomConfig.archived == False,
                    BomConfig.review_status != "approved",
                    BomConfig.id != config_id
                )
            )
            existing = r.scalar_one_or_none()
            if existing:
                raise ValueError(f"已存在未归档且未评审通过的 BOM 编码: {new_bom_code}")
        changed_collection = "collection_id" in data and data["collection_id"] != obj.collection_id
        for k, v in data.items():
            if v is not None:
                setattr(obj, k, v)
        if changed_collection and obj.collection_id:
            if obj.archived or obj.review_status == "approved":
                raise ValueError("已发布或归档的 BOM 不能修改绑定集合")
            r = await db.execute(
                select(TestItemCollection.version).where(TestItemCollection.id == obj.collection_id)
            )
            version = r.scalar_one_or_none()
            if version is not None:
                obj.collection_version = version
        await db.flush()
        await db.refresh(obj)
        return obj

    @staticmethod
    async def delete(db: AsyncSession, config_id: int):
        obj = await BomConfigService.get(db, config_id)
        if obj.archived or obj.review_status in ("approved", "pending"):
            raise ValueError("已发布/待评审/已归档的 BOM 不允许删除")
        await db.delete(obj)
        await db.flush()

    @staticmethod
    async def copy(db: AsyncSession, config_id: int, target_bom_code: str, target_bom_name: str) -> BomConfig:
        source = await BomConfigService.get(db, config_id)
        # Check unique constraint for target bom_code
        r = await db.execute(
            select(BomConfig).where(
                BomConfig.bom_code == target_bom_code,
                BomConfig.archived == False,
                BomConfig.review_status != "approved"
            )
        )
        existing = r.scalar_one_or_none()
        if existing:
            raise ValueError(f"已存在未归档且未评审通过的 BOM 编码: {target_bom_code}")
        
        r = await db.execute(
            select(func.max(BomConfig.version)).where(BomConfig.bom_code == target_bom_code)
        )
        max_ver = r.scalar()
        new_version = (max_ver or 0) + 1

        new_config = BomConfig(
            bom_code=target_bom_code,
            bom_name=target_bom_name,
            collection_id=source.collection_id,
            collection_version=source.collection_version,
            status=1,
            version=new_version,
        )
        db.add(new_config)
        await db.flush()

        indicators = await BomConfigService.list_indicators(db, config_id)
        for ind in indicators:
            bi = BomIndicator(
                bom_config_id=new_config.id,
                indicator_id=ind["indicator_id"],
                unit=ind["unit"],
                judgment_rule=ind["judgment_rule"],
                test_stage=ind["test_stage"],
                remark=ind["remark"],
                status=1,
                params=ind.get("params") or [],
            )
            db.add(bi)
            await db.flush()
        await db.flush()
        await db.refresh(new_config)
        return new_config

    # ── Indicators ──
    @staticmethod
    async def list_indicators(db: AsyncSession, config_id: int) -> List[dict]:
        r = await db.execute(
            select(
                BomIndicator.id,
                BomIndicator.bom_config_id,
                BomIndicator.indicator_id,
                BomIndicator.unit,
                BomIndicator.judgment_rule,
                BomIndicator.test_stage,
                BomIndicator.remark,
                BomIndicator.status,
                BomIndicator.process_name,
                BomIndicator.station_name,
                BomIndicator.params.label("bom_params"),
                IndicatorDict.code.label("indicator_code"),
                IndicatorDict.name.label("indicator_name"),
                IndicatorDict.category.label("category"),
                IndicatorDict.params.label("dict_params"),
            )
            .join(IndicatorDict, BomIndicator.indicator_id == IndicatorDict.id, isouter=True)
            .where(BomIndicator.bom_config_id == config_id)
            .order_by(BomIndicator.id)
        )
        rows = r.all()
        result = []
        for row in rows:
            d = row._asdict()
            d["params"] = d.pop("bom_params") or []
            d["dict_params"] = d.pop("dict_params") if d["dict_params"] is not None else {}
            result.append(d)
        return result

    @staticmethod
    async def get_full_indicators_by_config(
        db: AsyncSession, config_id: int
    ) -> List[dict]:
        """
        一次性获取某 BOM 配置下所有测试项的完整指标数据（字典参数 + BOM overrides 合并）。
        返回结构：[{test_item_id, test_item_name, process_name, station_name, sort_order,
                   indicators: [{indicator_id, indicator_code, indicator_name, category,
                                unit, judgment_rule, test_stage, remark, status,
                                process_name, station_name, params, _bom_indicator_id,
                                dict_params, has_override}]}]
        消除前端 N+1 请求。
        """
        from app.models.metrics import CollectionTestItem, TestItemIndicator, IndicatorDict, BomIndicator

        config = await BomConfigService.get(db, config_id)
        if not config.collection_id:
            return []

        # 1) 获取该集合版本下所有测试项
        items_stmt = (
            select(CollectionTestItem)
            .where(
                CollectionTestItem.collection_id == config.collection_id,
                CollectionTestItem.status == 1,
            )
            .order_by(CollectionTestItem.sort_order, CollectionTestItem.id)
        )
        items = (await db.execute(items_stmt)).scalars().all()

        if not items:
            return []

        item_ids = [it.id for it in items]

        # 2) 一次性获取这些测试项关联的所有指标（字典层参数 + 指标领域）
        ti_indicators_stmt = (
            select(
                TestItemIndicator.test_item_id,
                TestItemIndicator.indicator_id,
                TestItemIndicator.unit,
                TestItemIndicator.judgment_rule,
                IndicatorDict.code.label("indicator_code"),
                IndicatorDict.name.label("indicator_name"),
                IndicatorDict.category.label("category"),
                IndicatorDict.domain.label("indicator_domain"),
                IndicatorDict.test_params.label("dict_params"),
            )
            .join(IndicatorDict, TestItemIndicator.indicator_id == IndicatorDict.id)
            .where(TestItemIndicator.test_item_id.in_(item_ids))
        )
        ti_rows = (await db.execute(ti_indicators_stmt)).all()

        # 3) 获取该 BOM 的所有 overrides
        bom_indicators = await BomConfigService.list_indicators(db, config_id)
        bom_map = {bi["indicator_id"]: bi for bi in bom_indicators}

        # 4) 组装：按 test_item_id 分组，字段名保持与前端模板一致
        grouped: dict[int, dict] = {}
        for it in items:
            grouped[it.id] = {
                "id": it.id,
                "name": it.name,
                "process_name": it.process_name or "",
                "station_name": it.station or "",
                "station": it.station or "",
                "test_type": it.test_type or "",
                "sort_order": it.sort_order,
                "block_type": it.block_type or "normal",
                "service_address": it.service_address or "",
                "timeout_seconds": it.timeout_seconds,
                "parallel_enabled": bool(it.parallel_enabled),
                "status": it.status,
                "item_revision": it.item_revision,
                "owner_id": it.owner_id,
                "owner_name": it.owner_name,
                "owner_manual": bool(it.owner_manual),
                "domain": "",
                "indicators": [],
            }

        for row in ti_rows:
            test_item_id = row.test_item_id
            if test_item_id not in grouped:
                continue
            ind_data = {
                "indicator_id": row.indicator_id,
                "indicator_code": row.indicator_code,
                "indicator_name": row.indicator_name,
                "category": row.category,
                "unit": row.unit,
                "judgment_rule": row.judgment_rule,
                "test_stage": "",
                "remark": "",
                "status": 1,
                "process_name": "",
                "station_name": "",
                "params": [],
                "_bom_indicator_id": 0,
                "dict_params": row.dict_params or [],
                "has_override": False,
                "param_cols": [],
            }
            # 检查是否有 BOM override
            bom_override = bom_map.get(row.indicator_id)
            if bom_override:
                ind_data.update({
                    "_bom_indicator_id": bom_override["id"],
                    "params": bom_override["params"] or [],
                    "unit": bom_override["unit"] or ind_data["unit"],
                    "judgment_rule": bom_override["judgment_rule"] or ind_data["judgment_rule"],
                    "test_stage": bom_override["test_stage"] or "",
                    "remark": bom_override["remark"] or "",
                    "status": bom_override["status"],
                    "process_name": bom_override["process_name"] or "",
                    "station_name": bom_override["station_name"] or "",
                    "has_override": True,
                })
            # 每个指标生成权威参数列（统一 schema，BOM override 优先于字典层）
            ind_data["param_cols"] = BomConfigService._build_param_cols(ind_data)
            grouped[test_item_id]["indicators"].append(ind_data)
            # 聚合指标领域作为测试项 domain
            if row.indicator_domain:
                domains = grouped[test_item_id]["domain"]
                parts = domains.split("、") if domains else []
                if row.indicator_domain not in parts:
                    parts.append(row.indicator_domain)
                    grouped[test_item_id]["domain"] = "、".join(parts)

        # 5) 处理 BOM 独有的指标（不在集合中的）
        ti_indicator_ids = {row.indicator_id for row in ti_rows}
        for bi in bom_indicators:
            if bi["indicator_id"] not in ti_indicator_ids:
                # 找到该指标关联的任意测试项（或创建虚拟分组）
                # 简单起见：放到第一个测试项或创建"其它"分组
                target_item_id = item_ids[0] if item_ids else 0
                if target_item_id and target_item_id in grouped:
                    _bom_only = {
                        "indicator_id": bi["indicator_id"],
                        "indicator_code": bi["indicator_code"],
                        "indicator_name": bi["indicator_name"],
                        "category": bi["category"],
                        "unit": bi["unit"],
                        "judgment_rule": bi["judgment_rule"],
                        "test_stage": bi["test_stage"] or "",
                        "remark": bi["remark"] or "",
                        "status": bi["status"],
                        "process_name": bi["process_name"] or "",
                        "station_name": bi["station_name"] or "",
                        "params": bi["params"] or [],
                        "_bom_indicator_id": bi["id"],
                        "dict_params": [],
                        "has_override": True,
                        "param_cols": [],
                    }
                    _bom_only["param_cols"] = BomConfigService._build_param_cols(_bom_only)
                    grouped[target_item_id]["indicators"].append(_bom_only)

        # 6) 每个测试项计算统一参数列（该测试项所有指标的参数并集），
        #    前端矩阵视图 / 列头展示使用；行级渲染仍以 per-indicator param_cols 为准。
        # 转为列表，按 sort_order 排序
        result = list(grouped.values())
        result.sort(key=lambda x: x["sort_order"] or 0)
        for item in result:
            union: dict[str, dict] = {}
            for ind in item.get("indicators", []):
                for c in ind.get("param_cols", []):
                    union.setdefault(c["key"], c)
            item["param_cols"] = list(union.values())
        return result

    @staticmethod
    def _build_param_cols(ind_data: dict) -> list:
        """根据指标数据（BOM override 优先，否则字典层）生成统一参数列 schema。"""
        src_params = ind_data.get("params") or ind_data.get("dict_params") or []
        cols: list[dict] = []
        seen: set[str] = set()
        for p in src_params:
            key = p.get("param_key") or p.get("key")
            if not key or key in seen:
                continue
            seen.add(key)
            cols.append({
                "key": key,
                "label": p.get("param_name") or p.get("name") or key,
                "format": p.get("format") or p.get("type") or "string",
                "required": bool(p.get("required")),
                "remark": p.get("remark") or "",
                "unit": p.get("unit") or ind_data.get("unit") or "",
                "default": p.get("default") or p.get("default_value") or "",
                "minWidth": 140,
            })
        return cols

    @staticmethod
    async def preview_collection_upgrade(db: AsyncSession, config_id: int, snapshot_id: int) -> dict:
        """对比当前 BOM 引用的集合版本与目标快照，返回测试项级差异，供升级前预览。

        升级仅更新 BOM 对集合版本的引用，不影响集合本身；此预览帮助用户确认
        升级将带来的测试项新增/删除，避免静默切换。
        """
        from app.models.metrics import IndicatorVersionSnapshot
        config = await BomConfigService.get(db, config_id)
        r = await db.execute(
            select(IndicatorVersionSnapshot).where(
                IndicatorVersionSnapshot.id == snapshot_id,
                IndicatorVersionSnapshot.entity_type == "collection",
                IndicatorVersionSnapshot.entity_id == config.collection_id,
            )
        )
        target = r.scalar_one_or_none()
        if not target:
            raise NotFoundError("目标版本快照不存在或不属于当前集合")

        # 当前引用版本的快照（可能落后于集合实时版本）
        current = None
        if config.collection_version:
            r = await db.execute(
                select(IndicatorVersionSnapshot)
                .where(
                    IndicatorVersionSnapshot.entity_type == "collection",
                    IndicatorVersionSnapshot.entity_id == config.collection_id,
                    IndicatorVersionSnapshot.version == config.collection_version,
                )
                .order_by(IndicatorVersionSnapshot.created_at.desc())
                .limit(1)
            )
            current = r.scalar_one_or_none()

        current_items = (current.snapshot_data or {}).get("items", []) if current else []
        target_items = (target.snapshot_data or {}).get("items", [])

        def _key(it: dict):
            return (
                str(it.get("process_name") or ""),
                str(it.get("station") or it.get("station_name") or ""),
                str(it.get("name") or ""),
            )

        cur_keys = {_key(it) for it in current_items}
        tgt_keys = {_key(it) for it in target_items}

        added = [it for it in target_items if _key(it) not in cur_keys]
        removed = [it for it in current_items if _key(it) not in tgt_keys]

        return {
            "current_version": config.collection_version or 0,
            "target_version": target.version,
            "current_items": len(current_items),
            "target_items": len(target_items),
            "added": added,
            "removed": removed,
            "added_count": len(added),
            "removed_count": len(removed),
        }

    @staticmethod
    async def _ensure_editable(db: AsyncSession, config_id: int) -> BomConfig:
        """校验 BOM 处于可编辑状态（未归档、未评审/未待评审），返回 config。"""
        config = await BomConfigService.get(db, config_id)
        if config.archived or config.review_status in ("approved", "pending"):
            raise ValueError("仅未评审状态的 BOM 允许编辑")
        return config

    @staticmethod
    async def add_indicator(db: AsyncSession, config_id: int, data: dict, operator: str = "") -> BomIndicator:
        config = await BomConfigService._ensure_editable(db, config_id)
        indicator_id = data.get("indicator_id")
        bom_params = data.get("params")
        if bom_params is None:
            r = await db.execute(
                select(IndicatorDict.test_params).where(IndicatorDict.id == indicator_id)
            )
            row = r.scalar_one_or_none()
            bom_params = row or []
        data["params"] = bom_params
        # Auto-inherit process_name / station_name from collection test item
        if not data.get("process_name") and not data.get("station_name"):
            r = await db.execute(
                select(CollectionTestItem.process_name, CollectionTestItem.station)
                .join(TestItemIndicator, TestItemIndicator.test_item_id == CollectionTestItem.id)
                .where(
                    TestItemIndicator.indicator_id == indicator_id,
                    CollectionTestItem.collection_id == config.collection_id,
                )
                .limit(1)
            )
            row = r.one_or_none()
            if row:
                data.setdefault("process_name", row.process_name or "")
                data.setdefault("station_name", row.station or "")
        obj = BomIndicator(bom_config_id=config_id, **data)
        db.add(obj)
        await db.flush()
        return obj

    @staticmethod
    async def batch_add_indicators(db: AsyncSession, config_id: int, indicators: List[dict], operator: str = "") -> List[BomIndicator]:
        config = await BomConfigService._ensure_editable(db, config_id)
        objs = []
        for d in indicators:
            indicator_id = d.get("indicator_id")
            bom_params = d.get("params")
            if bom_params is None:
                r = await db.execute(
                    select(IndicatorDict.test_params).where(IndicatorDict.id == indicator_id)
                )
                row = r.scalar_one_or_none()
                bom_params = row or []
            d["params"] = bom_params
            # Auto-inherit process_name / station_name
            if not d.get("process_name") and not d.get("station_name"):
                r = await db.execute(
                    select(CollectionTestItem.process_name, CollectionTestItem.station)
                    .join(TestItemIndicator, TestItemIndicator.test_item_id == CollectionTestItem.id)
                    .where(
                        TestItemIndicator.indicator_id == indicator_id,
                        CollectionTestItem.collection_id == config.collection_id,
                    )
                    .limit(1)
                )
                row = r.one_or_none()
                if row:
                    d.setdefault("process_name", row.process_name or "")
                    d.setdefault("station_name", row.station or "")
            obj = BomIndicator(bom_config_id=config_id, **d)
            db.add(obj)
            objs.append(obj)
            await db.flush()
        await db.flush()
        return objs

    @staticmethod
    async def update_indicator(db: AsyncSession, indicator_id: int, data: dict, operator: str = "") -> BomIndicator:
        r = await db.execute(select(BomIndicator).where(BomIndicator.id == indicator_id))
        obj = r.scalar_one_or_none()
        if not obj:
            raise NotFoundError("指标记录不存在")

        await BomConfigService._ensure_editable(db, obj.bom_config_id)

        # 乐观锁：客户端携带了所属测试项 id + revision 则原子校验
        test_item_id = data.pop("test_item_id", None)
        client_revision = data.pop("item_revision", None)
        locked = test_item_id is not None and client_revision is not None
        if locked:
            acquired = await BomConfigService.check_item_revision_atomic(db, test_item_id, client_revision)
            if not acquired:
                from app.core.exceptions import ConcurrencyError
                raise ConcurrencyError("该指标已被他人更新，请刷新页面获取最新数据后重新编辑")

        try:
            nullable_fields = {"unit", "judgment_rule", "test_stage", "remark"}
            for k, v in data.items():
                if k in nullable_fields:
                    setattr(obj, k, v)
                elif v is not None:
                    setattr(obj, k, v)
            await db.flush()
        except BaseException:
            # 操作失败时补偿释放乐观锁版本
            if locked:
                await BomConfigService.rollback_item_revision(db, test_item_id)
            raise
        return obj

    @staticmethod
    async def batch_update_indicators(db: AsyncSession, ids: List[int], data: dict, operator: str = ""):
        config_ids = set()
        for iid in ids:
            try:
                r = await db.execute(select(BomIndicator).where(BomIndicator.id == iid))
                obj = r.scalar_one_or_none()
                if obj:
                    await BomConfigService._ensure_editable(db, obj.bom_config_id)
                    for k, v in data.items():
                        if v is not None:
                            setattr(obj, k, v)
                    config_ids.add(obj.bom_config_id)
            except NotFoundError:
                pass
        await db.flush()

    @staticmethod
    async def batch_update_indicator_status(db: AsyncSession, ids: List[int], status: int, operator: str = ""):
        config_ids = set()
        for iid in ids:
            try:
                r = await db.execute(select(BomIndicator).where(BomIndicator.id == iid))
                obj = r.scalar_one_or_none()
                if obj:
                    await BomConfigService._ensure_editable(db, obj.bom_config_id)
                    obj.status = status
                    config_ids.add(obj.bom_config_id)
            except NotFoundError:
                pass
        await db.flush()

    @staticmethod
    async def _record_review_event(db: AsyncSession, config_id: int, action: str, operator_id: int, operator_name: str, comment: str = "", **loc):
        """记录评审事件（时间线）。"""
        from app.models.metrics import BomReviewEvent
        db.add(BomReviewEvent(
            bom_config_id=config_id,
            action=action,
            operator_id=operator_id,
            operator_name=operator_name,
            comment=comment,
            test_item_id=loc.get("test_item_id"),
            test_item_name=loc.get("test_item_name") or "",
            indicator_id=loc.get("indicator_id"),
            param_key=loc.get("param_key"),
        ))
        await db.flush()

    @staticmethod
    async def get_review_events(db: AsyncSession, config_id: int) -> List[dict]:
        """查询 BOM 评审时间线（提交/通过/驳回/撤回/意见）。"""
        from app.models.metrics import BomReviewEvent
        r = await db.execute(
            select(BomReviewEvent)
            .where(BomReviewEvent.bom_config_id == config_id)
            .order_by(BomReviewEvent.created_at.asc())
        )
        return [e.to_dict() for e in r.scalars().all()]

    @staticmethod
    async def add_review_comments(db: AsyncSession, config_id: int, comments: List[dict], operator_id: int, operator_name: str):
        """驳回时记录逐条评审意见（可定位到测试项/指标/参数）。"""
        from app.models.metrics import BomReviewEvent
        for c in comments:
            db.add(BomReviewEvent(
                bom_config_id=config_id,
                action="comment",
                operator_id=operator_id,
                operator_name=operator_name,
                comment=c.get("comment", ""),
                test_item_id=c.get("test_item_id"),
                test_item_name=c.get("test_item_name") or "",
                indicator_id=c.get("indicator_id"),
                param_key=c.get("param_key"),
            ))
        await db.flush()
        return await BomConfigService.get_review_events(db, config_id)

    @staticmethod
    def _can_review(config: BomConfig, operator_id: int, role: str) -> bool:
        """审批权限：super_admin 或指定审批人；未指定审批人时任意 developer+ 可审。"""
        if role == "super_admin":
            return True
        if config.approver_id is None:
            return True
        return config.approver_id == operator_id

    @staticmethod
    async def submit_review(db: AsyncSession, config_id: int, operator_id: int, operator_name: str, change_summary: str = "", approver_id: Optional[int] = None) -> BomConfig:
        obj = await BomConfigService.get(db, config_id)
        if obj.review_status == "pending":
            raise ValueError("该 BOM 已提交评审，请勿重复提交")
        if obj.archived:
            raise ValueError("已归档的 BOM 不可提交评审")
        # 驳回修订闭环：rejected 状态允许重新提交
        obj.review_status = "pending"
        obj.review_operator = operator_name
        obj.reviewed_at = datetime.utcnow()
        obj.change_summary = change_summary
        if approver_id is not None:
            # 解析审批人姓名
            from app.models.user import User
            r = await db.execute(select(User.id, User.display_name, User.username).where(User.id == approver_id))
            approver_row = r.one_or_none()
            if approver_row:
                obj.approver_id = approver_row.id
                obj.approver_name = approver_row.display_name or approver_row.username
            else:
                obj.approver_id = None
                obj.approver_name = None
        await db.flush()
        await BomConfigService._record_review_event(
            db, config_id, "submit", operator_id, operator_name,
            f"提交评审：{change_summary or ''}",
            **({"approver": obj.approver_name} if obj.approver_name else {}),
        )
        await db.refresh(obj)
        return obj

    @staticmethod
    async def approve_review(db: AsyncSession, config_id: int, comment: str = "", operator_id: int = 0, operator_name: str = "", role: str = "") -> BomConfig:
        obj = await BomConfigService.get(db, config_id)
        if obj.review_status != "pending":
            raise ValueError("该 BOM 当前未处于待评审状态")
        if not BomConfigService._can_review(obj, operator_id, role):
            raise ValueError("仅指定审批人可执行评审操作")
        obj.review_status = "approved"
        obj.review_comment = comment
        obj.review_operator = operator_name
        obj.reviewed_at = datetime.utcnow()
        await db.flush()
        await BomConfigService._record_review_event(
            db, config_id, "approve", operator_id, operator_name, comment,
        )
        await db.refresh(obj)
        from app.services.version_snapshot_service import VersionSnapshotService
        await VersionSnapshotService.snapshot_bom_config(db, config_id, operator_name, obj.change_summary or "评审通过，版本发布")
        return obj

    @staticmethod
    async def reject_review(db: AsyncSession, config_id: int, comment: str = "", operator_id: int = 0, operator_name: str = "", role: str = "") -> BomConfig:
        obj = await BomConfigService.get(db, config_id)
        if obj.review_status != "pending":
            raise ValueError("该 BOM 当前未处于待评审状态")
        if not BomConfigService._can_review(obj, operator_id, role):
            raise ValueError("仅指定审批人可执行评审操作")
        obj.review_status = "rejected"
        obj.review_comment = comment
        obj.review_operator = operator_name
        obj.reviewed_at = datetime.utcnow()
        await db.flush()
        await BomConfigService._record_review_event(
            db, config_id, "reject", operator_id, operator_name, comment,
        )
        await db.refresh(obj)
        return obj

    @staticmethod
    async def withdraw_review(db: AsyncSession, config_id: int, operator_id: int = 0, operator_name: str = "") -> BomConfig:
        obj = await BomConfigService.get(db, config_id)
        if obj.review_status != "pending":
            raise ValueError("该 BOM 当前未处于待评审状态，无法撤回")
        obj.review_status = "none"
        obj.review_operator = operator_name
        obj.reviewed_at = None
        obj.review_comment = None
        await db.flush()
        await BomConfigService._record_review_event(
            db, config_id, "withdraw", operator_id, operator_name,
        )
        await db.refresh(obj)
        return obj

    @staticmethod
    async def archive_bom(db: AsyncSession, config_id: int, operator: str = "") -> BomConfig:
        obj = await BomConfigService.get(db, config_id)
        if obj.review_status != "approved":
            raise ValueError("仅评审通过的 BOM 可以归档")
        if obj.archived:
            raise ValueError("该 BOM 已归档")
        obj.archived = True
        obj.archived_at = datetime.utcnow()
        await db.flush()
        await db.refresh(obj)
        from app.services.version_snapshot_service import VersionSnapshotService
        await VersionSnapshotService.snapshot_bom_config(db, config_id, operator, "BOM 归档")
        return obj

    @staticmethod
    async def create_new_iteration(db: AsyncSession, config_id: int, operator: str = "") -> BomConfig:
        obj = await BomConfigService.get(db, config_id)
        if not obj.archived and obj.review_status != "approved":
            raise ValueError("仅已归档或已发布的 BOM 可以创建迭代版本")
        
        # Check unique constraint: only one non-archived/non-approved per bom_code
        r = await db.execute(
            select(BomConfig).where(
                BomConfig.bom_code == obj.bom_code,
                BomConfig.archived == False,
                BomConfig.review_status != "approved"
            )
        )
        existing = r.scalar_one_or_none()
        if existing and existing.id != config_id:
            raise ValueError(f"已存在未归档且未评审通过的 BOM 编码: {obj.bom_code}")
        
        r = await db.execute(
            select(func.max(BomConfig.version)).where(BomConfig.bom_code == obj.bom_code)
        )
        max_ver = r.scalar()
        next_version = (max_ver or 0) + 1
        new_obj = BomConfig(
            bom_code=obj.bom_code,
            bom_name=obj.bom_name,
            collection_id=obj.collection_id,
            collection_version=obj.collection_version,
            status=1,
            version=next_version,
            review_status="none",
            archived=False,
        )
        db.add(new_obj)
        await db.flush()
        indicators = await BomConfigService.list_indicators(db, config_id)
        for ind in indicators:
            bi = BomIndicator(
                bom_config_id=new_obj.id,
                indicator_id=ind["indicator_id"],
                unit=ind.get("unit", ""),
                process_name=ind.get("process_name", ""),
                station_name=ind.get("station_name", ""),
                judgment_rule=ind.get("judgment_rule", "合格"),
                test_stage=ind.get("test_stage", ""),
                remark=ind.get("remark", ""),
                status=1,
                params=ind.get("params") or [],
            )
            db.add(bi)
            await db.flush()
        await db.flush()
        await db.refresh(new_obj)
        # ── Snapshot for traceability ──
        from app.services.version_snapshot_service import VersionSnapshotService
        source_label = "已归档" if obj.archived else "已发布"
        summary = f"基于{source_label}版本 #{config_id} (v{obj.version}) 创建新迭代 v{new_obj.version}"
        await VersionSnapshotService.snapshot_bom_config(db, new_obj.id, operator, summary)
        return new_obj

    @staticmethod
    async def delete_indicator(db: AsyncSession, indicator_id: int, operator: str = ""):
        r = await db.execute(select(BomIndicator).where(BomIndicator.id == indicator_id))
        obj = r.scalar_one_or_none()
        if not obj:
            raise NotFoundError("指标记录不存在")
        config_id = obj.bom_config_id
        await BomConfigService._ensure_editable(db, config_id)
        await db.delete(obj)
        await db.flush()

    # ── Collaborative Editing: Optimistic Locking (atomic CAS) ──
    @staticmethod
    async def check_item_revision_atomic(
        db: AsyncSession,
        test_item_id: Optional[int],
        client_revision: Optional[int],
    ) -> bool:
        """
        测试项乐观锁：原子条件递增（CAS）。
        仅当 collection_test_item 当前 item_revision == client_revision 时递增并返回 True，
        否则返回 False（表示已被他人修改）。返回 True 代表本次已成功"占有"该行的写锁。
        若调用方未提供 revision（旧调用方/首次创建），跳过校验返回 True。
        """
        if not test_item_id or client_revision is None:
            return True

        result = await db.execute(
            sa_update(CollectionTestItem)
            .where(
                CollectionTestItem.id == test_item_id,
                CollectionTestItem.item_revision == client_revision,
            )
            .values(item_revision=CollectionTestItem.item_revision + 1)
        )
        return (result.rowcount or 0) > 0

    @staticmethod
    async def rollback_item_revision(
        db: AsyncSession,
        test_item_id: Optional[int],
    ):
        """回滚被 check_item_revision_atomic 递增的版本号（用于后续操作失败时补偿）"""
        if not test_item_id:
            return
        await db.execute(
            sa_update(CollectionTestItem)
            .where(CollectionTestItem.id == test_item_id)
            .values(item_revision=CollectionTestItem.item_revision - 1)
        )

    # ── Per-param CRUD within a BOM indicator ──
    @staticmethod
    async def add_param(db: AsyncSession, bom_indicator_id: int, param: dict, operator: str = "") -> list:
        r = await db.execute(select(BomIndicator).where(BomIndicator.id == bom_indicator_id))
        obj = r.scalar_one_or_none()
        if not obj:
            raise NotFoundError("BOM 指标记录不存在")
        await BomConfigService._ensure_editable(db, obj.bom_config_id)
        params = obj.params or []
        new_key = param.get("param_key", "")
        if any(p.get("param_key") == new_key for p in params):
            raise ValueError(f"参数 Key '{new_key}' 已存在")
        BomConfigService._validate_param_format(param, params)
        params.append(param)
        await db.execute(sa_update(BomIndicator).where(BomIndicator.id == bom_indicator_id).values(params=params))
        await db.flush()
        return params

    @staticmethod
    async def update_param(db: AsyncSession, bom_indicator_id: int, param_key: str, updates: dict, operator: str = "", operator_id: int = 0) -> list:
        r = await db.execute(select(BomIndicator).where(BomIndicator.id == bom_indicator_id))
        obj = r.scalar_one_or_none()
        if not obj:
            raise NotFoundError("BOM 指标记录不存在")

        await BomConfigService._ensure_editable(db, obj.bom_config_id)

        # 乐观锁：客户端携带了所属测试项 id + revision 则原子校验
        test_item_id = updates.pop("test_item_id", None)
        client_revision = updates.pop("item_revision", None)
        locked = test_item_id is not None and client_revision is not None
        if locked:
            acquired = await BomConfigService.check_item_revision_atomic(db, test_item_id, client_revision)
            if not acquired:
                from app.core.exceptions import ConcurrencyError
                raise ConcurrencyError("该参数已被他人更新，请刷新页面获取最新数据后重新编辑")

        try:
            params = obj.params or []
            found = False
            old_value = ""
            for p in params:
                if p.get("param_key") == param_key or p.get("key") == param_key:
                    old_value = str(p.get("param_value") or p.get("value") or "")
                    p.update({k: v for k, v in updates.items() if v is not None})
                    BomConfigService._validate_param_format(p, params)
                    found = True
                    break
            if not found:
                raise NotFoundError(f"参数 Key '{param_key}' 不存在")
            await db.execute(sa_update(BomIndicator).where(BomIndicator.id == bom_indicator_id).values(params=params))
            await db.flush()

            # 记录参数变更日志（补全审计覆盖，此前仅 batch-save 路径写入）
            from app.models.metrics import ParamChangeLog
            new_value = ""
            for p in params:
                if p.get("param_key") == param_key or p.get("key") == param_key:
                    new_value = str(p.get("param_value") or p.get("value") or "")
                    break
            change_log = ParamChangeLog(
                bom_code=obj.bom_code if hasattr(obj, "bom_code") else "",
                bom_config_id=obj.bom_config_id,
                bom_version=0,
                test_item_id=test_item_id or 0,
                test_item_name="",
                indicator_id=obj.indicator_id,
                indicator_code="",
                indicator_name="",
                param_key=param_key,
                param_name=param_key,
                old_value=old_value,
                new_value=new_value,
                operator_id=operator_id,
                operator_name=operator,
            )
            # 补充 BOM 版本与测试项名
            cfg = None
            if test_item_id:
                tr = await db.execute(select(CollectionTestItem).where(CollectionTestItem.id == test_item_id))
                ti = tr.scalar_one_or_none()
                if ti:
                    change_log.test_item_name = ti.name or ""
            from app.models.metrics import BomConfig as _BC
            cr = await db.execute(select(_BC).where(_BC.id == obj.bom_config_id))
            cfg = cr.scalar_one_or_none()
            if cfg:
                change_log.bom_code = cfg.bom_code or ""
                change_log.bom_version = cfg.version or 0
            db.add(change_log)

        except BaseException:
            if locked:
                await BomConfigService.rollback_item_revision(db, test_item_id)
            raise
        return params

    @staticmethod
    def _validate_param_format(param: dict, all_params: list):
        fmt = param.get("format") or param.get("type") or "string"
        # Accept both dict format names and BOM format names
        valid_types = {"number", "range", "percent", "enum", "expr", "array", "text", "string", "boolean", "list"}
        if fmt not in valid_types:
            raise ValueError(f"参数类型必须是: {', '.join(valid_types)}")
        value = param.get("param_value") or param.get("value")
        if fmt in ("number", "range", "percent"):
            if value is not None and value != "":
                try:
                    float(str(value))
                except (ValueError, TypeError):
                    raise ValueError(f"参数 {param.get('param_key', '')} 格式为数字，仅允许整数或小数")
        elif fmt in ("array", "list"):
            if value is not None and value != "":
                val = str(value)
                if "，" in val:
                    raise ValueError(f"参数 {param.get('param_key', '')} 格式为列表，请使用英文逗号分隔")
        elif fmt in ("boolean",):
            if value is not None and value != "":
                if str(value).lower() not in ("true", "false", "1", "0"):
                    raise ValueError(f"参数 {param.get('param_key', '')} 格式为布尔，仅支持 true 或 false")

    @staticmethod
    async def delete_param(db: AsyncSession, bom_indicator_id: int, param_key: str, operator: str = "") -> list:
        r = await db.execute(select(BomIndicator).where(BomIndicator.id == bom_indicator_id))
        obj = r.scalar_one_or_none()
        if not obj:
            raise NotFoundError("BOM 指标记录不存在")
        await BomConfigService._ensure_editable(db, obj.bom_config_id)
        params = obj.params or []
        new_params = [p for p in params if p.get("param_key") != param_key and p.get("key") != param_key]
        if len(new_params) == len(params):
            raise NotFoundError(f"参数 Key '{param_key}' 不存在")
        await db.execute(sa_update(BomIndicator).where(BomIndicator.id == bom_indicator_id).values(params=new_params))
        await db.flush()
        return new_params

    @staticmethod
    async def check_non_closed_version(db: AsyncSession, bom_code: str, exclude_config_id: int = 0) -> bool:
        r = await db.execute(
            select(BomConfig).where(
                BomConfig.bom_code == bom_code,
                BomConfig.archived == False,
                BomConfig.review_status != "approved",
                BomConfig.id != exclude_config_id,
            )
        )
        return r.scalar_one_or_none() is not None

    # ── Collaborative Editing: Batch Save with Optimistic Locking ──
    @staticmethod
    async def batch_save_indicator_params(
        db: AsyncSession,
        config_id: int,
        items: List[dict],
        operator_id: int,
        operator_name: str,
        is_super_admin: bool = False,
    ) -> dict:
        """
        批量保存指标参数，乐观锁并发控制 + 测试项级负责人权限校验
        items: [{indicator_id, param_key, param_value, item_revision, test_item_id, test_item_name}]
        返回: {success: [indicator_id], conflicts: [{indicator_id, current_revision, message}]}
        """
        from app.models.metrics import ParamChangeLog
        
        config = await BomConfigService.get(db, config_id)
        
        # 检查版本状态：仅未评审可编辑
        if config.archived or config.review_status in ("approved", "pending"):
            raise ValueError("仅未评审状态的 BOM 允许编辑")
        
        success_ids = []
        conflicts = []
        change_logs = []
        saved_details: list[dict] = []

        # 按测试项分组（乐观锁 & 权限均为测试项粒度）
        grouped: dict[int, list[dict]] = {}
        for item in items:
            grouped.setdefault(item.get("test_item_id") or 0, []).append(item)
        
        test_item_ids = [tid for tid in grouped if tid]
        test_item_map: dict = {}
        if test_item_ids:
            r = await db.execute(
                select(CollectionTestItem)
                .where(CollectionTestItem.id.in_(test_item_ids))
            )
            test_item_map = {ti.id: ti for ti in r.scalars().all()}
        
        for test_item_id, group_items in grouped.items():
            ti = test_item_map.get(test_item_id)
            if not ti:
                for item in group_items:
                    conflicts.append({
                        "indicator_id": item["indicator_id"],
                        "test_item_id": test_item_id,
                        "current_revision": item.get("item_revision", 0),
                        "message": "测试项不存在",
                    })
                continue
            
            # 权限检查：仅超管可编辑所有项；其他角色只能编辑自己负责（或无主）的测试项
            # 负责人可能仅有 owner_name（用户不存在时），需按名称兜底匹配
            owned_by_other = (
                (ti.owner_id is not None and ti.owner_id != operator_id)
                or (ti.owner_id is None and ti.owner_name and ti.owner_name != operator_name)
            )
            if not is_super_admin and owned_by_other:
                for item in group_items:
                    conflicts.append({
                        "indicator_id": item["indicator_id"],
                        "test_item_id": test_item_id,
                        "current_revision": item.get("item_revision", 0),
                        "message": f"该测试项由他人负责，无编辑权限",
                    })
                continue
            
            # 乐观锁：原子条件递增（CAS），消除 check-then-act 竞态窗口。
            # 仅当当前 item_revision == 客户端持有版本时递增成功并"占有"写锁，
            # 并发请求中只有一个能通过，其余会真正拿到空结果触发冲突。
            client_revision = group_items[0].get("item_revision", 0)
            revision_acquired = await BomConfigService.check_item_revision_atomic(db, test_item_id, client_revision)
            if not revision_acquired:
                # 刷新读取当前版本用于提示
                r_cur = await db.execute(select(CollectionTestItem.item_revision).where(CollectionTestItem.id == test_item_id))
                cur_revision = r_cur.scalar_one_or_none() or 0
                for item in group_items:
                    conflicts.append({
                        "indicator_id": item["indicator_id"],
                        "test_item_id": test_item_id,
                        "current_revision": cur_revision,
                        "message": "该测试项已被他人更新，请刷新页面获取最新数据后重新编辑",
                    })
                continue
            
            # 逐个指标更新参数
            group_success = True
            for item in group_items:
                indicator_id = item["indicator_id"]
                param_key = item["param_key"]
                param_value = item["param_value"]
                
                r = await db.execute(select(BomIndicator).where(BomIndicator.id == indicator_id))
                obj = r.scalar_one_or_none()
                if not obj:
                    conflicts.append({
                        "indicator_id": indicator_id,
                        "test_item_id": test_item_id,
                        "current_revision": ti.item_revision,
                        "message": "指标记录不存在",
                    })
                    group_success = False
                    continue
                
                params = obj.params or []
                found = False
                old_value = ""
                for p in params:
                    if p.get("param_key") == param_key or p.get("key") == param_key:
                        old_value = str(p.get("param_value") or p.get("value") or "")
                        p["param_value"] = param_value
                        p["value"] = param_value
                        found = True
                        break
                
                if not found:
                    conflicts.append({
                        "indicator_id": indicator_id,
                        "test_item_id": test_item_id,
                        "current_revision": ti.item_revision,
                        "message": f"参数 Key '{param_key}' 不存在",
                    })
                    group_success = False
                    continue
                
                # 更新参数（仅增加指标自身版本号，测试项版本号统一在组内递增一次）
                await db.execute(
                    sa_update(BomIndicator)
                    .where(BomIndicator.id == indicator_id)
                    .values(params=params, item_revision=BomIndicator.item_revision + 1)
                )
                
                # 记录变更日志
                change_logs.append(ParamChangeLog(
                    bom_code=config.bom_code,
                    bom_config_id=config.id,
                    bom_version=config.version,
                    test_item_id=test_item_id,
                    test_item_name=ti.name or item.get("test_item_name") or "",
                    indicator_id=obj.indicator_id,
                    indicator_code="",
                    indicator_name="",
                    param_key=param_key,
                    param_name=param_key,
                    old_value=old_value,
                    new_value=str(param_value),
                    operator_id=operator_id,
                    operator_name=operator_name,
                ))
                success_ids.append(indicator_id)
                saved_details.append({
                    "test_item_id": test_item_id,
                    "indicator_id": indicator_id,
                    "param_key": param_key,
                    "param_value": str(param_value),
                    "item_revision": ti.item_revision,
                })

            # 组内任一条失败则回滚本次占有的测试项版本号（乐观锁补偿），
            # 否则版本号已在 check_item_revision_atomic 递增，无需重复递增。
            if not group_success:
                await BomConfigService.rollback_item_revision(db, test_item_id)
        
        if change_logs:
            # 补充指标名称信息（从指标字典查询）
            dict_indicator_ids = [log.indicator_id for log in change_logs]
            r = await db.execute(
                select(IndicatorDict.id, IndicatorDict.code, IndicatorDict.name)
                .where(IndicatorDict.id.in_(dict_indicator_ids))
            )
            info_map = {row.id: row for row in r.all()}

            for log in change_logs:
                info = info_map.get(log.indicator_id)
                if info:
                    log.indicator_code = info.code or ""
                    log.indicator_name = info.name or ""

            db.add_all(change_logs)

        return {
            "success": success_ids,
            "conflicts": conflicts,
            "details": saved_details,
            "room_key": f"{config.bom_code}:{config.version}",
        }

    @staticmethod
    async def get_change_logs(
        db: AsyncSession,
        config_id: int,
        test_item_id: Optional[int] = None,
        indicator_id: Optional[int] = None,
    ) -> List[dict]:
        """查询参数变更日志"""
        from app.models.metrics import ParamChangeLog
        
        stmt = select(ParamChangeLog).where(ParamChangeLog.bom_config_id == config_id)
        if test_item_id:
            stmt = stmt.where(ParamChangeLog.test_item_id == test_item_id)
        if indicator_id:
            stmt = stmt.where(ParamChangeLog.indicator_id == indicator_id)
        stmt = stmt.order_by(ParamChangeLog.created_at.desc())
        
        r = await db.execute(stmt)
        logs = r.scalars().all()
        return [log.to_dict() for log in logs]

    @staticmethod
    async def get_online_users(
        db: AsyncSession,
        config_id: int,
    ) -> List[dict]:
        """获取当前在线用户（从 WebSocket 维护的内存集合获取）"""
        config = await BomConfigService.get(db, config_id)
        room_key = f"{config.bom_code}:{config.version}"
        return get_bom_online_users(f"{config.bom_code}:{config.version}")

    @staticmethod
    async def check_edit_permission(
        db: AsyncSession,
        config_id: int,
        indicator_ids: List[int],
        user_id: int,
        is_super_admin: bool,
    ) -> dict:
        """
        检查用户对指定指标的编辑权限
        返回: {allowed: [indicator_id], denied: [indicator_id], message: str}
        """
        if is_super_admin:
            return {"allowed": indicator_ids, "denied": []}
        
        r = await db.execute(
            select(BomIndicator.id, BomIndicator.owner_id)
            .where(BomIndicator.id.in_(indicator_ids))
        )
        rows = r.all()
        
        allowed = []
        denied = []
        for row in rows:
            if row.owner_id == user_id:
                allowed.append(row.id)
            else:
                denied.append(row.id)
        
        return {"allowed": allowed, "denied": denied}
