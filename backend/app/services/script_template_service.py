import configparser
import json as builtin_json
import os
import tempfile
import time
import traceback
import uuid
from typing import Optional, List
from datetime import datetime, timedelta
from app.schemas.metrics import BomExportItem

from sqlalchemy import select, func, delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.metrics import ScriptTemplate, IndicatorDict, TestItemCollection, BomConfig
from app.services.bom_config_service import BomConfigService
from app.services.dictionary_service import DictionaryService
from app.core.exceptions import NotFoundError
from app.utils.pagination import paginate
from app.config import get_settings


class ScriptTemplateService:

    @staticmethod
    async def list(
        db: AsyncSession,
        *,
        page: int = 1,
        page_size: int = 20,
        keyword: str = "",
        status: Optional[int] = None,
    ):
        stmt = select(ScriptTemplate)
        if keyword:
            stmt = stmt.where(ScriptTemplate.name.ilike(f"%{keyword}%"))
        if status is not None:
            stmt = stmt.where(ScriptTemplate.status == status)
        stmt = stmt.order_by(ScriptTemplate.id.desc())
        return await paginate(db, stmt, page, page_size)

    @staticmethod
    async def list_active(db: AsyncSession) -> List[ScriptTemplate]:
        r = await db.execute(
            select(ScriptTemplate).where(ScriptTemplate.status == 1).order_by(ScriptTemplate.name)
        )
        return list(r.scalars().all())

    @staticmethod
    async def get(db: AsyncSession, script_id: int) -> ScriptTemplate:
        r = await db.execute(select(ScriptTemplate).where(ScriptTemplate.id == script_id))
        obj = r.scalar_one_or_none()
        if not obj:
            raise NotFoundError("脚本模板不存在")
        return obj

    @staticmethod
    async def create(db: AsyncSession, data: dict, operator: str = "") -> ScriptTemplate:
        existing = await db.execute(
            select(ScriptTemplate).where(ScriptTemplate.name == data.get("name"))
        )
        if existing.scalar_one_or_none():
            from app.core.exceptions import ConflictError
            raise ConflictError("脚本名称已存在")
        obj = ScriptTemplate(**data, created_by=operator, updated_by=operator)
        db.add(obj)
        await db.flush()
        await db.refresh(obj)
        return obj

    @staticmethod
    async def update(db: AsyncSession, script_id: int, data: dict, operator: str = "") -> ScriptTemplate:
        obj = await ScriptTemplateService.get(db, script_id)
        if "name" in data and data["name"] != obj.name:
            existing = await db.execute(
                select(ScriptTemplate).where(ScriptTemplate.name == data["name"], ScriptTemplate.id != script_id)
            )
            if existing.scalar_one_or_none():
                from app.core.exceptions import ConflictError
                raise ConflictError("脚本名称已存在")
        for k, v in data.items():
            if v is not None:
                setattr(obj, k, v)
        obj.updated_by = operator
        await db.flush()
        await db.refresh(obj)
        return obj

    @staticmethod
    async def delete(db: AsyncSession, script_id: int):
        obj = await ScriptTemplateService.get(db, script_id)
        await db.delete(obj)
        await db.flush()

    @staticmethod
    async def toggle_status(db: AsyncSession, script_id: int, status: int, operator: str = "") -> ScriptTemplate:
        obj = await ScriptTemplateService.get(db, script_id)
        obj.status = status
        obj.updated_by = operator
        await db.flush()
        await db.refresh(obj)
        return obj

    # ── Execute ──

    @staticmethod
    async def execute_script(
        db: AsyncSession,
        script_id: int,
        *,
        indicator_ids: Optional[List[int]] = None,
        collection_ids: Optional[List[int]] = None,
        bom_config_ids: Optional[List[int]] = None,
        export_all: bool = False,
        operator: str = "",
    ) -> dict:
        script = await ScriptTemplateService.get(db, script_id)
        if script.status != 1:
            raise ValueError("脚本已禁用，无法执行")

        indicator_data = await ScriptTemplateService._collect_indicator_data(
            db, indicator_ids=indicator_ids, collection_ids=collection_ids,
            bom_config_ids=bom_config_ids, export_all=export_all,
        )

        start = time.time()
        try:
            result = ScriptTemplateService._run_sandbox(script.source_code, indicator_data)
            execution_time_ms = int((time.time() - start) * 1000)
        except Exception as e:
            raise RuntimeError(f"脚本执行失败: {e}\n{traceback.format_exc()}")

        settings = get_settings()
        export_dir = os.path.join(settings.UPLOAD_FOLDER, "script_exports")
        os.makedirs(export_dir, exist_ok=True)

        ext = "json" if script.output_format == "json" else "ini"
        file_id = str(uuid.uuid4())[:8]
        file_name = f"{script.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file_id}.{ext}"
        file_path = os.path.join(export_dir, file_name)

        if script.output_format == "json":
            content = builtin_json.dumps(result, ensure_ascii=False, indent=2, default=str)
        else:
            content = ScriptTemplateService._dict_to_ini(result)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        file_size = os.path.getsize(file_path)

        return {
            "file_id": file_id,
            "file_name": file_name,
            "file_size": file_size,
            "download_url": f"/api/v1/metrics/script-exports/{file_name}",
            "execution_time_ms": execution_time_ms,
        }

    @staticmethod
    async def _fetch_params(db: AsyncSession, indicator_id: int) -> list:
        r = await db.execute(select(IndicatorDict).where(IndicatorDict.id == indicator_id))
        indicator = r.scalar_one_or_none()
        if not indicator:
            return []
        return list(indicator.test_params or [])

    @staticmethod
    async def _collect_indicator_data(
        db: AsyncSession,
        *,
        indicator_ids: Optional[List[int]] = None,
        collection_ids: Optional[List[int]] = None,
        bom_config_ids: Optional[List[int]] = None,
        export_all: bool = False,
    ) -> list:
        if export_all:
            r = await db.execute(
                select(IndicatorDict).order_by(IndicatorDict.code)
            )
            items = r.scalars().all()
            result = []
            for it in items:
                d = {
                    "indicator_id": it.id,
                    "indicator_code": it.code,
                    "indicator_name": it.name,
                    "unit": it.unit,
                    "category": it.category,
                    "status": it.status,
                    "test_params": await ScriptTemplateService._fetch_params(db, it.id),
                }
                result.append(d)
            return result

        seen = set()
        result = []

        if indicator_ids:
            r = await db.execute(
                select(IndicatorDict).where(IndicatorDict.id.in_(indicator_ids))
            )
            for it in r.scalars().all():
                if it.id not in seen:
                    seen.add(it.id)
                    d = {
                        "indicator_id": it.id,
                        "indicator_code": it.code,
                        "indicator_name": it.name,
                        "unit": it.unit,
                        "category": it.category,
                        "status": it.status,
                        "test_params": await ScriptTemplateService._fetch_params(db, it.id),
                    }
                    result.append(d)

        return result

    @staticmethod
    def _run_sandbox(source_code: str, indicator_data: list) -> dict:
        restricted_globals = {
            "__builtins__": {
                "abs": abs, "all": all, "any": any, "bool": bool,
                "dict": dict, "enumerate": enumerate, "float": float,
                "int": int, "isinstance": isinstance, "len": len,
                "list": list, "max": max, "min": min, "range": range,
                "round": round, "sorted": sorted, "str": str,
                "sum": sum, "tuple": tuple, "type": type, "zip": zip,
                "map": map, "filter": filter, "reversed": reversed,
                "set": set, "frozenset": frozenset, "object": object,
                "True": True, "False": False, "None": None,
                "Exception": Exception, "ValueError": ValueError,
                "KeyError": KeyError, "TypeError": TypeError,
                "IndexError": IndexError, "StopIteration": StopIteration,
                "print": print,
            },
            "json": builtin_json,
            "configparser": configparser,
            "indicator_data": indicator_data,
        }
        local_vars = {}
        exec(source_code, restricted_globals, local_vars)
        result = local_vars.get("result")
        if result is None:
            raise ValueError("脚本未定义 result 变量")
        return result

    @staticmethod
    def _dict_to_ini(data: dict) -> str:
        lines = []
        for section, values in data.items():
            lines.append(f"[{section}]")
            if isinstance(values, dict):
                for k, v in values.items():
                    lines.append(f"{k} = {v}")
            elif isinstance(values, list):
                for v in values:
                    lines.append(f"{v}")
            lines.append("")
        return "\n".join(lines)

    @staticmethod
    def execute_indicator_script(indicator_data: dict, source_code: str, timeout: int = 10) -> dict:
        """Execute a single indicator's Python conversion script in sandbox."""
        import signal
        restricted_globals = {
            "__builtins__": {
                "abs": abs, "all": all, "any": any, "bool": bool,
                "dict": dict, "enumerate": enumerate, "float": float,
                "int": int, "isinstance": isinstance, "len": len,
                "list": list, "max": max, "min": min, "range": range,
                "round": round, "sorted": sorted, "str": str,
                "sum": sum, "tuple": tuple, "type": type, "zip": zip,
                "map": map, "filter": filter, "reversed": reversed,
                "set": set, "frozenset": frozenset, "object": object,
                "True": True, "False": False, "None": None,
                "Exception": Exception, "ValueError": ValueError,
                "KeyError": KeyError, "TypeError": TypeError,
                "IndexError": IndexError, "StopIteration": StopIteration,
                "print": print,
            },
            "json": builtin_json,
            "configparser": configparser,
            "indicator_data": indicator_data,
        }
        local_vars = {}
        exec(source_code, restricted_globals, local_vars)
        result = local_vars.get("result")
        if result is None:
            raise ValueError("脚本未定义 result 变量")
        return result

    @staticmethod
    async def export_all_indicators(
        db: AsyncSession,
        output_format: str = "json",
    ) -> dict:
        """Export all active indicators using per-indicator scripts."""
        import time, uuid, os
        from datetime import datetime
        from app.config import get_settings
        from app.models.metrics import IndicatorDict

        r = await db.execute(
            select(IndicatorDict).where(IndicatorDict.status == 1)
        )
        all_indicators = r.scalars().all()

        total_start = time.time()
        fragments = {}
        logs = []
        succeeded = 0
        failed = 0

        for ind in all_indicators:
            indicator_data = {
                "code": ind.code,
                "name": ind.name,
                "min": None,
                "max": None,
                "unit": ind.unit or "",
                "params": ind.params or {},
                "test_params": await ScriptTemplateService._fetch_params(db, ind.id),
            }

            script_source = DictionaryService.get_default_script()
            script_name = f"默认模板 ({ind.code})"

            ind_start = time.time()
            try:
                fragment = ScriptTemplateService.execute_indicator_script(indicator_data, script_source)
                elapsed = int((time.time() - ind_start) * 1000)
                if isinstance(fragment, dict):
                    fragments.update(fragment)
                logs.append(BomExportItem(
                    indicator_code=ind.code, indicator_name=ind.name,
                    script_name=script_name, status="success", execution_time_ms=elapsed,
                ))
                succeeded += 1
            except Exception as e:
                elapsed = int((time.time() - ind_start) * 1000)
                logs.append(BomExportItem(
                    indicator_code=ind.code, indicator_name=ind.name,
                    script_name=script_name, status="failed", execution_time_ms=elapsed, error=str(e),
                ))
                failed += 1

        total_elapsed = int((time.time() - total_start) * 1000)
        settings = get_settings()
        export_dir = os.path.join(settings.UPLOAD_FOLDER, "script_exports")
        os.makedirs(export_dir, exist_ok=True)
        ext = output_format
        file_id = str(uuid.uuid4())[:8]
        file_name = f"AllIndicators_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file_id}.{ext}"
        file_path = os.path.join(export_dir, file_name)

        if output_format == "json":
            content = builtin_json.dumps(fragments, ensure_ascii=False, indent=2, default=str)
        else:
            content = ScriptTemplateService._dict_to_ini(fragments)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        file_size = os.path.getsize(file_path)

        return {
            "file_id": file_id,
            "file_name": file_name,
            "file_size": file_size,
            "download_url": f"/api/v1/metrics/script-exports/{file_name}",
            "execution_time_ms": total_elapsed,
            "total_indicators": succeeded + failed,
            "succeeded": succeeded,
            "failed": failed,
            "logs": [l.model_dump() for l in logs],
        }

    @staticmethod
    async def export_bom_config(
        db: AsyncSession,
        config_id: int,
        output_format: str = "json",
    ) -> dict:
        """Export a BOM config using per-indicator scripts, aggregate all fragments.
        
        Data source: IndicatorDict.params JSON (BOM and test items no longer store override limits/params).
        """
        import time, uuid, os
        from datetime import datetime
        from app.config import get_settings
        from app.models.metrics import BomConfig, CollectionTestItem, TestItemIndicator, BomIndicator

        config = await BomConfigService.get(db, config_id)
        collection_id = config.collection_id

        # Pre-load all BomIndicators for this config, keyed by indicator_id
        bom_ind_r = await db.execute(
            select(BomIndicator).where(
                BomIndicator.bom_config_id == config_id, BomIndicator.status == 1
            )
        )
        bom_indicator_map = {bi.indicator_id: bi for bi in bom_ind_r.scalars().all()}

        # Load collection items
        item_r = await db.execute(
            select(CollectionTestItem)
            .where(CollectionTestItem.collection_id == collection_id)
            .order_by(CollectionTestItem.sort_order)
        )
        test_items = item_r.scalars().all()

        total_start = time.time()
        fragments = {}
        logs = []
        succeeded = 0
        failed = 0

        for item in test_items:
            item_data = {
                "item_name": item.name,
                "station": item.station,
                "test_type": item.test_type,
                "sort_order": item.sort_order,
                "service_address": item.service_address or "",
                "timeout_seconds": item.timeout_seconds,
                "block_type": item.block_type,
                "parallel_enabled": bool(item.parallel_enabled),
                "indicators": [],
            }

            ind_r = await db.execute(
                select(TestItemIndicator)
                .where(TestItemIndicator.test_item_id == item.id)
            )
            item_indicators = ind_r.scalars().all()

            for ti_ind in item_indicators:
                indicator = await DictionaryService.get(db, ti_ind.indicator_id)

                merged_unit = ""
                bom_ind = bom_indicator_map.get(ti_ind.indicator_id)
                if bom_ind and bom_ind.unit:
                    merged_unit = bom_ind.unit
                elif ti_ind.unit:
                    merged_unit = ti_ind.unit
                else:
                    merged_unit = indicator.unit or ""

                indicator_data = {
                    "code": indicator.code,
                    "name": indicator.name,
                    "min": None,
                    "max": None,
                    "unit": merged_unit,
                    "params": indicator.params or {},
                    "test_params": await ScriptTemplateService._fetch_params(db, indicator.id),
                }

                script_source = DictionaryService.get_default_script()
                script_name = f"默认模板 ({indicator.code})"

                ind_start = time.time()
                try:
                    fragment = ScriptTemplateService.execute_indicator_script(indicator_data, script_source)
                    elapsed = int((time.time() - ind_start) * 1000)
                    item_data["indicators"].append(fragment)
                    logs.append(BomExportItem(
                        indicator_code=indicator.code,
                        indicator_name=indicator.name,
                        script_name=script_name,
                        status="success",
                        execution_time_ms=elapsed,
                    ))
                    succeeded += 1
                except Exception as e:
                    elapsed = int((time.time() - ind_start) * 1000)
                    logs.append(BomExportItem(
                        indicator_code=indicator.code,
                        indicator_name=indicator.name,
                        script_name=script_name,
                        status="failed",
                        execution_time_ms=elapsed,
                        error=str(e),
                    ))
                    failed += 1

            fragments[item.name] = item_data

        total_elapsed = int((time.time() - total_start) * 1000)

        settings = get_settings()
        export_dir = os.path.join(settings.UPLOAD_FOLDER, "script_exports")
        os.makedirs(export_dir, exist_ok=True)

        ext = output_format
        file_id = str(uuid.uuid4())[:8]
        bom_code_safe = config.bom_code.replace("/", "_")
        file_name = f"BOM_{bom_code_safe}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file_id}.{ext}"
        file_path = os.path.join(export_dir, file_name)

        if output_format == "json":
            content = builtin_json.dumps(fragments, ensure_ascii=False, indent=2, default=str)
        else:
            content = ScriptTemplateService._dict_to_ini(fragments)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        file_size = os.path.getsize(file_path)

        return {
            "file_id": file_id,
            "file_name": file_name,
            "file_size": file_size,
            "download_url": f"/api/v1/metrics/script-exports/{file_name}",
            "execution_time_ms": total_elapsed,
            "total_indicators": succeeded + failed,
            "succeeded": succeeded,
            "failed": failed,
            "logs": [l.model_dump() for l in logs],
        }

    @staticmethod
    def cleanup_expired_exports():
        settings = get_settings()
        export_dir = os.path.join(settings.UPLOAD_FOLDER, "script_exports")
        if not os.path.isdir(export_dir):
            return
        cutoff = datetime.now() - timedelta(days=7)
        for fname in os.listdir(export_dir):
            fpath = os.path.join(export_dir, fname)
            if os.path.isfile(fpath):
                mtime = datetime.fromtimestamp(os.path.getmtime(fpath))
                if mtime < cutoff:
                    os.remove(fpath)
