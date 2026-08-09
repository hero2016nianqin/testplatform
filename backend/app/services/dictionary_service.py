import ast
from typing import Optional, List

from sqlalchemy import select, func, delete as sa_delete, JSON
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.metrics import IndicatorDict, TestItemIndicator, BomIndicator
from app.core.exceptions import NotFoundError, ConflictError
from app.utils.pagination import paginate
from app.utils.param_validator import FormatValidator

DEFAULT_INDICATOR_SCRIPT = '''# 指标导出转换脚本
#
# 入参: indicator_data (dict)
#       结构:
#         {
#             "code": "TX_PWR",     # 指标编码
#             "name": "发射功率",     # 指标名称
#             "freq": 2450,          # 硬件参数（类型取决于配置的格式）
#             "power": 20,
#         }
# 输出: result (dict) — 以指标编码为 key 的配置片段
#
# 注意: 已配置的硬件参数会自动合并到输出中

def convert(indicator):
    code = indicator.get("code", "")
    name = indicator.get("name", "")
    result = {"name": name, "code": code}
    for k, v in indicator.items():
        if k not in ("code", "name"):
            result[k] = v
    return {code: result}

result = convert(indicator_data)
'''

DEFAULT_DOMAINS = ["功放", "双工器", "算法", "TRX", "电源", "单板软件", "装备"]


class DictionaryService:

    @staticmethod
    async def list(
        db: AsyncSession,
        *,
        page: int = 1,
        page_size: int = 20,
        keyword: str = "",
        category: str = "",
        status: Optional[int] = None,
    ):
        stmt = select(IndicatorDict).where(IndicatorDict.id > 0)
        if keyword:
            stmt = stmt.where(
                IndicatorDict.name.ilike(f"%{keyword}%")
                | IndicatorDict.code.ilike(f"%{keyword}%")
            )
        if category:
            stmt = stmt.where(IndicatorDict.category == category)
        if status is not None:
            stmt = stmt.where(IndicatorDict.status == status)
        stmt = stmt.order_by(IndicatorDict.id.desc())
        return await paginate(db, stmt, page, page_size)

    @staticmethod
    async def get(db: AsyncSession, indicator_id: int) -> IndicatorDict:
        r = await db.execute(
            select(IndicatorDict).where(IndicatorDict.id == indicator_id)
        )
        obj = r.scalar_one_or_none()
        if not obj:
            raise NotFoundError("指标不存在")
        return obj

    @staticmethod
    async def create(db: AsyncSession, data: dict) -> IndicatorDict:
        obj = IndicatorDict(**data)
        db.add(obj)
        await db.flush()
        return obj

    @staticmethod
    async def update(db: AsyncSession, indicator_id: int, data: dict, operator: str = "") -> IndicatorDict:
        obj = await DictionaryService.get(db, indicator_id)
        changed_fields = [k for k in data if k != "status" and data[k] is not None and getattr(obj, k, None) != data[k]]
        for k, v in data.items():
            if v is not None:
                setattr(obj, k, v)
        await db.flush()
        await db.refresh(obj)
        if changed_fields:
            summary = ", ".join(changed_fields[:5])
            from app.services.version_snapshot_service import VersionSnapshotService
            await VersionSnapshotService.snapshot_indicator(db, indicator_id, operator, f"更新字段: {summary}")
        return obj

    @staticmethod
    async def delete(db: AsyncSession, indicator_id: int, force: bool = False):
        obj = await DictionaryService.get(db, indicator_id)
        # Check references before deleting
        ti_r = await db.execute(
            select(func.count()).select_from(TestItemIndicator)
            .where(TestItemIndicator.indicator_id == indicator_id)
        )
        ti_count = ti_r.scalar() or 0
        bi_r = await db.execute(
            select(func.count()).select_from(BomIndicator)
            .where(BomIndicator.indicator_id == indicator_id)
        )
        bi_count = bi_r.scalar() or 0
        total = ti_count + bi_count
        if total > 0 and not force:
            raise ConflictError(
                f"当前指标已被 {ti_count} 个测试项、{bi_count} 个BOM配置引用，无法删除，请先解绑全部关联后再操作"
            )
        if total > 0 and force:
            # Force: also remove references
            await db.execute(
                sa_delete(TestItemIndicator).where(TestItemIndicator.indicator_id == indicator_id)
            )
        obj.status = 0
        await db.flush()

    @staticmethod
    async def get_references(db: AsyncSession, indicator_id: int) -> dict:
        """Get all collections and BOM configs that reference this indicator."""
        from sqlalchemy import select as sa_select
        from app.models.metrics import CollectionTestItem, TestItemCollection, BomConfig

        # Find all test items that bind this indicator
        ti_r = await db.execute(
            sa_select(CollectionTestItem).join(
                TestItemIndicator,
                CollectionTestItem.id == TestItemIndicator.test_item_id
            ).where(TestItemIndicator.indicator_id == indicator_id)
        )
        test_items = ti_r.scalars().all()

        # Also find BOM indicators referencing this indicator
        bi_r = await db.execute(
            sa_select(BomConfig).join(
                BomIndicator,
                BomConfig.id == BomIndicator.bom_config_id
            ).where(BomIndicator.indicator_id == indicator_id)
        )
        bom_configs = bi_r.scalars().all()

        # Group test items by collection
        collection_ids = set()
        for ti in test_items:
            collection_ids.add(ti.collection_id)

        collections = []
        for cid in collection_ids:
            coll_r = await db.execute(sa_select(TestItemCollection).where(TestItemCollection.id == cid))
            coll = coll_r.scalar_one_or_none()
            if coll:
                items_in_coll = [ti for ti in test_items if ti.collection_id == cid]
                collections.append({
                    "id": coll.id,
                    "name": coll.name,
                    "code": coll.code,
                    "test_items": [{"id": ti.id, "name": ti.name} for ti in items_in_coll],
                })

        return {
            "collections": collections,
            "bom_configs": [{"id": b.id, "bom_code": b.bom_code, "bom_name": b.bom_name} for b in bom_configs],
        }

    @staticmethod
    async def batch_update(db: AsyncSession, updates: List[dict]) -> List[IndicatorDict]:
        objs = []
        for item in updates:
            iid = item.get("id")
            if not iid:
                continue
            r = await db.execute(select(IndicatorDict).where(IndicatorDict.id == iid))
            obj = r.scalar_one_or_none()
            if obj:
                for k, v in item.items():
                    if k != "id" and v is not None:
                        setattr(obj, k, v)
                objs.append(obj)
        await db.flush()
        return objs

    @staticmethod
    async def list_categories(db: AsyncSession) -> List[str]:
        r = await db.execute(
            select(IndicatorDict.category)
            .where(IndicatorDict.category != "", IndicatorDict.status == 1)
            .distinct()
            .order_by(IndicatorDict.category)
        )
        return [row[0] for row in r.all()]

    @staticmethod
    async def list_domains(db: AsyncSession) -> dict:
        """返回内置默认领域列表 + 字典库中自定义的领域。"""
        r = await db.execute(
            select(IndicatorDict.domain)
            .where(IndicatorDict.domain != "")
            .distinct()
            .order_by(IndicatorDict.domain)
        )
        custom = [row[0] for row in r.all()]
        merged = []
        seen = set()
        for d in DEFAULT_DOMAINS + custom:
            if d not in seen:
                seen.add(d)
                merged.append(d)
        return {"defaults": DEFAULT_DOMAINS, "custom": custom, "domains": merged}

    @staticmethod
    async def list_all_active(db: AsyncSession) -> List[IndicatorDict]:
        r = await db.execute(
            select(IndicatorDict).where(IndicatorDict.status == 1).order_by(IndicatorDict.code)
        )
        return list(r.scalars().all())

    # ── Per-param CRUD (test_params) ──

    @staticmethod
    def _validate_param_type(param: dict):
        fmt = param.get("type") or param.get("format") or "text"
        # Accept both dict format names and BOM format names
        valid_types = {"number", "range", "percent", "enum", "expr", "array", "text", "string", "boolean", "list"}
        if fmt not in valid_types:
            raise ValueError(f"参数类型必须是: {', '.join(valid_types)}")
        value = param.get("value") or param.get("param_value") or ""
        if fmt in ("number", "range", "percent"):
            if value != "" and value is not None:
                try:
                    float(str(value))
                except (ValueError, TypeError):
                    raise ValueError("number/range/percent 类型参数值必须是数字")
        elif fmt in ("array", "list"):
            if value != "" and value is not None:
                val = str(value)
                if "，" in val:
                    raise ValueError("array/list 类型参数请使用英文逗号分隔")
        elif fmt in ("boolean",):
            if value != "" and value is not None:
                if str(value).lower() not in ("true", "false", "1", "0"):
                    raise ValueError("boolean 类型参数值必须是 true 或 false")

    @staticmethod
    async def add_param(db: AsyncSession, indicator_id: int, data: dict) -> IndicatorDict:
        obj = await DictionaryService.get(db, indicator_id)
        params = list(obj.test_params or [])
        if any(p.get("key") == data["param_key"] or p.get("param_key") == data["param_key"] for p in params):
            raise ValueError(f"参数 Key '{data['param_key']}' 已存在")
        new_param = {
            "key": data["param_key"],
            "name": data.get("param_name", ""),
            "value": data.get("param_value", ""),
            "type": data.get("param_type", "text"),
            "remark": data.get("remark", ""),
        }
        DictionaryService._validate_param_type(new_param)
        params.append(new_param)
        obj.test_params = params
        await db.flush()
        await db.refresh(obj)
        return obj

    @staticmethod
    async def update_param(db: AsyncSession, indicator_id: int, param_key: str, data: dict) -> IndicatorDict:
        obj = await DictionaryService.get(db, indicator_id)
        params = list(obj.test_params or [])
        found = False
        for p in params:
            if p.get("key") == param_key or p.get("param_key") == param_key:
                if "param_name" in data:
                    p["name"] = data["param_name"]
                if "param_value" in data:
                    p["value"] = data["param_value"]
                if "param_type" in data:
                    p["type"] = data["param_type"]
                if "remark" in data:
                    p["remark"] = data["remark"]
                DictionaryService._validate_param_type(p)
                found = True
                break
        if not found:
            raise NotFoundError(f"参数 '{param_key}' 不存在")
        obj.test_params = params
        await db.flush()
        await db.refresh(obj)
        return obj

    @staticmethod
    async def delete_param(db: AsyncSession, indicator_id: int, param_key: str) -> IndicatorDict:
        obj = await DictionaryService.get(db, indicator_id)
        params = list(obj.test_params or [])
        new_params = [p for p in params if p.get("key") != param_key and p.get("param_key") != param_key]
        if len(new_params) == len(params):
            raise NotFoundError(f"参数 '{param_key}' 不存在")
        obj.test_params = new_params
        await db.flush()
        await db.refresh(obj)
        return obj

    # ── Per-indicator Script ──

    @staticmethod
    def get_default_script() -> str:
        return DEFAULT_INDICATOR_SCRIPT

    @staticmethod
    async def get_script(db: AsyncSession, indicator_id: int) -> str:
        obj = await DictionaryService.get(db, indicator_id)
        return obj.script_source or DEFAULT_INDICATOR_SCRIPT

    @staticmethod
    async def update_script(db: AsyncSession, indicator_id: int, source_code: str, operator: str = "") -> IndicatorDict:
        obj = await DictionaryService.get(db, indicator_id)
        # Validate syntax
        try:
            ast.parse(source_code)
        except SyntaxError as e:
            raise ValueError(f"Python 语法错误: 第 {e.lineno} 行: {e.msg}")
        obj.script_source = source_code
        await db.flush()
        await db.refresh(obj)
        return obj

    @staticmethod
    async def reset_script(db: AsyncSession, indicator_id: int, operator: str = "") -> IndicatorDict:
        obj = await DictionaryService.get(db, indicator_id)
        obj.script_source = ""
        await db.flush()
        await db.refresh(obj)
        return obj

    @staticmethod
    def validate_script(source_code: str) -> dict:
        if not source_code:
            return {"valid": False, "message": "代码为空"}
        try:
            ast.parse(source_code)
            return {"valid": True, "message": "语法正确"}
        except SyntaxError as e:
            return {
                "valid": False,
                "message": f"第 {e.lineno} 行: {e.msg}",
                "lineno": e.lineno,
                "offset": e.offset,
                "text": e.text,
            }

    # ── Sandbox Script Preview ──

    @staticmethod
    def _run_script_sync(source_code: str, input_data: dict) -> dict:
        """Execute script synchronously in a restricted sandbox."""
        import sys, io, json

        code = compile(source_code, '<sandbox>', 'exec')
        safe_builtins = {
            'True': True, 'False': False, 'None': None,
            'int': int, 'float': float, 'str': str, 'bool': bool,
            'list': list, 'dict': dict, 'tuple': tuple, 'set': set,
            'len': len, 'range': range, 'map': map, 'filter': filter,
            'min': min, 'max': max, 'sum': sum, 'abs': abs,
            'sorted': sorted, 'reversed': reversed, 'enumerate': enumerate,
            'zip': zip, 'isinstance': isinstance, 'type': type,
            'round': round, 'format': format, 'any': any, 'all': all,
            'print': print,
        }
        safe_globals = {'__builtins__': safe_builtins, 'indicator_data': input_data}
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            exec(code, safe_globals)
            stdout_output = sys.stdout.getvalue()
            result = safe_globals.get('result')
            return {'success': True, 'result': result, 'stdout': stdout_output}
        except Exception as e:
            import traceback
            return {'success': False, 'error': str(e), 'traceback': traceback.format_exc()}
        finally:
            sys.stdout = old_stdout

    @staticmethod
    async def preview_script(db: AsyncSession, indicator_id: int, source_code: str, input_data: dict) -> dict:
        """Run script in sandbox with 10s timeout and return preview result."""
        import asyncio, concurrent.futures
        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor() as pool:
            try:
                result = await asyncio.wait_for(
                    loop.run_in_executor(pool, DictionaryService._run_script_sync, source_code, input_data),
                    timeout=10,
                )
                return result
            except asyncio.TimeoutError:
                return {'success': False, 'error': '脚本执行超时（10秒限制）', 'traceback': ''}
