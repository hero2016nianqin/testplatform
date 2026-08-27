"""
异步测试执行引擎 — BOM测试序列执行（基于 SoftwareConfig.sequence_data）
"""
import asyncio
import os
import json
from typing import Optional
import httpx

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.test_run import TestRun
from app.models.test_item import TestItem
from app.models.station_config import SoftwareConfig, EquipmentConfig
from app.models.station import TestSlot
from app.core.exceptions import NotFoundError, BusinessException
from app.core.database import AsyncSessionLocal
from app.utils.batch_id import generate_batch_id
from app.config import (
    SLOT_STATUS_TESTING, SLOT_STATUS_PASS, SLOT_STATUS_FAIL, SLOT_STATUS_IDLE,
    RUN_STATUS_RUNNING, RUN_STATUS_COMPLETED, RUN_STATUS_FAILED,
)
from app.ws.handlers import notify_run_started, notify_item_tested, notify_run_completed, notify_run_failed
from app.services.run_log_saver import save_run_log
from app.utils.slot_lock import acquire_slot_lock, release_slot_lock, is_slot_locked


def _build_service_url(base_url: str, relative_path: str) -> str:
    """拼接基础 URL 和相对路径"""
    if not base_url or not relative_path:
        return ""
    base = base_url.rstrip("/")
    path = relative_path.lstrip("/")
    return f"{base}/{path}"


async def _call_test_service(url: str, payload: dict, timeout: float = 30.0) -> dict:
    """调用测试微服务，返回标准化结果"""
    if not url:
        return {"passed": False, "actual_value": 0.0, "error": "未配置服务地址"}
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            # 标准化响应格式
            return {
                "passed": data.get("passed", False),
                "actual_value": data.get("actual_value", 0.0),
                "deviation": data.get("deviation", 0.0),
                "duration_ms": data.get("duration_ms", 0),
                "error": data.get("error"),
            }
    except httpx.TimeoutException:
        return {"passed": False, "actual_value": 0.0, "error": f"请求超时 ({timeout}s)"}
    except httpx.HTTPStatusError as e:
        return {"passed": False, "actual_value": 0.0, "error": f"HTTP {e.response.status_code}: {e.response.text[:200]}"}
    except Exception as e:
        return {"passed": False, "actual_value": 0.0, "error": f"调用异常: {type(e).__name__}: {e}"}


class TestExecutor:

    @staticmethod
    async def execute_slot_scan(
        db: AsyncSession,
        station_id: int,
        slot_id: int,
        serial_number: str,
        operator: str,
        sequence_id: Optional[int] = None,
        selected_item_ids: Optional[list] = None,
    ) -> dict:
        """扫码即测入口 — 验证槽位 → 创建 PENDING 批次 → 分发 Celery 任务"""
        from sqlalchemy import select

        # 1. 校验槽位
        r = await db.execute(select(TestSlot).where(TestSlot.id == slot_id))
        slot = r.scalar_one_or_none()
        if not slot:
            raise NotFoundError("槽位不存在")
        if slot.status == SLOT_STATUS_TESTING:
            raise BusinessException(400, "槽位正在测试中")

        # 2. 获取 Redis 分布式锁（非阻塞，失败则拒绝；TTL 10分钟覆盖最长测试时间）
        acquired, lock_token = await acquire_slot_lock(slot_id, ttl=600)
        if not acquired:
            raise BusinessException(409, "槽位正在测试中，请稍后再试")

        # 将 lock_token 存入 Redis 以便 Celery 任务完成后释放
        from redis.asyncio import Redis
        from app.core.redis import get_redis_pool
        pool = get_redis_pool()
        async with Redis(connection_pool=pool) as r:
            await r.set(f"slot_lock_token:{slot_id}", lock_token, ex=600)

        try:
            # 3. 创建 PENDING 批次
            from app.services.test_service import TestService
            run = await TestService.create_pending_run(db, {
                "station_id": station_id,
                "slot_id": slot_id,
                "serial_number": serial_number,
                "operator": operator,
                "sequence_id": sequence_id or 0,
                "selected_item_ids": selected_item_ids or [],
            })
            await db.commit()

            # 4. 判断模式并分发 Celery 任务
            r2 = await db.execute(
                select(SoftwareConfig).where(SoftwareConfig.station_id == station_id)
            )
            sw_cfg = r2.scalar_one_or_none()
            use_sequence = sequence_id or (sw_cfg and sw_cfg.sequence_id and sw_cfg.sequence_id > 0)

            if use_sequence:
                from tasks.test_tasks import execute_sequence_run
                execute_sequence_run.delay(run.id)
            else:
                from tasks.test_tasks import execute_test_run
                execute_test_run.delay(run.id)

            return {
                "run_id": run.id,
                "batch_id": run.batch_id,
                "slot_id": slot_id,
                "status": "pending",
                "message": "测试已分发到后台执行",
            }
        except Exception:
            await release_slot_lock(slot_id, lock_token)
            raise

    @staticmethod
    async def _execute_sequence_mode(
        db: AsyncSession,
        run: TestRun,
        station_id: int,
        slot_id: int,
        serial_number: str,
        operator: str,
        sequence_id: int,
        selected_item_ids: Optional[list] = None,
    ) -> dict:
        """序列模式 — 优先使用 BOM 部署的 sequence_data，回退到全局 TestSequence"""
        from sqlalchemy import select

        # Get equipment base URL
        r = await db.execute(select(EquipmentConfig).where(EquipmentConfig.station_id == station_id))
        equip_cfg = r.scalar_one_or_none()
        base_url = equip_cfg.equipment_service_address if equip_cfg else ""

        # Get SoftwareConfig — BOM-deployed sequence_data is required
        r = await db.execute(select(SoftwareConfig).where(SoftwareConfig.station_id == station_id))
        sw_cfg = r.scalar_one_or_none()
        sequence_data = sw_cfg.sequence_data if sw_cfg and sw_cfg.sequence_data else []

        if not sequence_data or not isinstance(sequence_data, list) or len(sequence_data) == 0:
            raise BusinessException(400, "该工位未部署BOM测试序列，请先在版本管理中发布部署版本")

        steps_to_run = sequence_data
        if selected_item_ids:
            steps_to_run = [s for s in sequence_data if (s.get("test_item_id") or s.get("id")) in selected_item_ids]
            if not steps_to_run:
                raise BusinessException(400, "勾选的测试项在当前序列中未找到")
        seq_name = "BOM测试序列"
        is_bom_sequence = True

        # Update existing TestRun to RUNNING
        run.status = RUN_STATUS_RUNNING
        run.sequence_id = sequence_id
        run.sequence_name = seq_name
        run.started_at = __import__('datetime').datetime.utcnow()
        await db.flush()

        # Update slot
        r = await db.execute(select(TestSlot).where(TestSlot.id == slot_id))
        slot = r.scalar_one_or_none()
        if slot:
            slot.status = SLOT_STATUS_TESTING
            slot.current_batch_id = run.batch_id
            slot.serial_number = serial_number
        await db.flush()

        await notify_run_started(station_id, {
            "batch_id": run.batch_id,
            "operator": operator,
            "serial_number": serial_number,
            "run_id": run.id,
            "slot_id": slot_id,
        })

        # Execute each step
        total = len(steps_to_run)
        passed_count = 0
        failed_count = 0
        stopped = False
        log_items = []

        for idx, step_data in enumerate(steps_to_run):
            if stopped:
                break

            # BOM sequence: step_data is a dict from sequence_data
            test_item_id = step_data.get("test_item_id", 0)
            test_item_name = step_data.get("test_item_name", step_data.get("template_name", f"测试项{idx+1}"))
            relative_path = step_data.get("service_address", "") or step_data.get("template_service_address", "")
            timeout = float(step_data.get("timeout_seconds") or 30)
            is_critical = step_data.get("is_critical", step_data.get("template_is_critical", False))
            block_type = step_data.get("block_type", "must_test" if is_critical else "normal")
            params = step_data.get("params", {})

            # 跳过已有结果的测试项（防止重试时重复）
            from app.models.test_result import TestResult
            existing = await db.execute(
                select(TestResult.id).where(
                    TestResult.test_run_id == run.id,
                    TestResult.test_item_id == test_item_id,
                )
            )
            if existing.scalar_one_or_none():
                continue

            service_url = _build_service_url(base_url, relative_path)

            payload = {
                "serial_number": serial_number,
                "station_id": station_id,
                "slot_id": slot_id,
                "test_item_id": test_item_id,
                "test_item_name": test_item_name,
                "params": params,
            }

            svc_result = await _call_test_service(service_url, payload, timeout=timeout)

            passed = svc_result.get("passed", False)
            raw_value = svc_result.get("actual_value", 0.0)
            deviation = svc_result.get("deviation", 0.0)
            duration_ms = svc_result.get("duration_ms", 0)
            error_msg = svc_result.get("error")

            # actual_value must be numeric for DB; store original in remark if non-numeric
            remark = ""
            try:
                actual_value = float(raw_value)
            except (TypeError, ValueError):
                actual_value = 1.0 if passed else 0.0
                remark = str(raw_value)

            from app.models.test_result import TestResult
            result = TestResult(
                test_item_id=test_item_id,
                test_run_id=run.id,
                operator=operator,
                serial_number=serial_number,
                actual_value=actual_value,
                passed=passed,
                deviation=deviation,
                duration_ms=duration_ms,
                remark=remark + (f" | {error_msg}" if error_msg else ""),
            )
            db.add(result)
            log_items.append({
                "name": test_item_name,
                "actual": actual_value,
                "passed": passed,
                "error": error_msg,
            })

            if passed:
                passed_count += 1
            else:
                failed_count += 1

            await db.flush()

            await notify_item_tested(station_id, {
                "item_name": test_item_name,
                "passed": passed,
                "actual_value": actual_value,
                "slot_id": slot_id,
                "run_id": run.id,
                "is_critical": is_critical,
            })

            if is_critical and not passed:
                stopped = True
                run.status = RUN_STATUS_FAILED
                run.ended_at = __import__('datetime').datetime.utcnow()
                run.total_items = total
                run.passed_items = passed_count
                run.failed_items = failed_count
                if slot:
                    slot.status = SLOT_STATUS_FAIL
                    slot.current_batch_id = None
                    slot.serial_number = None
                await db.flush()

                try:
                    from app.config import get_settings
                    settings = get_settings()
                    base_dir = settings.LOG_FOLDER
                    if not os.path.isabs(base_dir):
                        base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), base_dir)
                    slot_info = slot.name if slot else ""
                    save_run_log(
                        base_dir=base_dir, station_id=station_id,
                        serial_number=serial_number, batch_id=run.batch_id,
                        status="failed", total=total, passed=passed_count, failed=failed_count,
                        items=log_items, slot_info=slot_info,
                    )
                except Exception:
                    pass

                await notify_run_failed(station_id, {
                    "batch_id": run.batch_id,
                    "error": f"关键项失败: {test_item_name}",
                    "slot_id": slot_id,
                })
                break

        if not stopped:
            run.status = RUN_STATUS_COMPLETED if failed_count == 0 else RUN_STATUS_FAILED
            run.ended_at = __import__('datetime').datetime.utcnow()
            run.total_items = total
            run.passed_items = passed_count
            run.failed_items = failed_count

            if slot:
                slot.status = SLOT_STATUS_PASS if run.status == RUN_STATUS_COMPLETED else SLOT_STATUS_IDLE
                slot.current_batch_id = None
                slot.serial_number = None
            await db.flush()

            try:
                from app.config import get_settings
                settings = get_settings()
                base_dir = settings.LOG_FOLDER
                if not os.path.isabs(base_dir):
                    base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), base_dir)
                slot_info = slot.name if slot else ""
                save_run_log(
                    base_dir=base_dir, station_id=station_id,
                    serial_number=serial_number, batch_id=run.batch_id,
                    status=run.status, total=total, passed=passed_count, failed=failed_count,
                    items=log_items, slot_info=slot_info,
                )
            except Exception:
                pass

            if run.status == RUN_STATUS_COMPLETED:
                await notify_run_completed(station_id, {
                    "batch_id": run.batch_id,
                    "total": total,
                    "passed": passed_count,
                    "failed": failed_count,
                    "slot_id": slot_id,
                })
            else:
                await notify_run_failed(station_id, {
                    "batch_id": run.batch_id,
                    "error": f"{failed_count}/{total} 项失败",
                    "slot_id": slot_id,
                })

        return {"run_id": run.id, "batch_id": run.batch_id, "status": run.status}

    @staticmethod
    async def _execute_traditional_mode(
        db: AsyncSession,
        run: TestRun,
        station_id: int,
        slot_id: int,
        serial_number: str,
        operator: str,
        sw_cfg: Optional[SoftwareConfig],
    ) -> dict:
        """传统模式 — 基于 SoftwareConfig.selected_test_item_ids，调用真实服务"""
        from sqlalchemy import select

        selected_ids = []
        if sw_cfg and sw_cfg.selected_test_item_ids:
            selected_ids = sw_cfg.selected_test_item_ids

        if not selected_ids:
            raise BusinessException(400, "未配置测试项，请先在软件配置中选择测试项")

        r = await db.execute(
            select(TestItem).where(TestItem.id.in_(selected_ids), TestItem.is_active == True)
            .order_by(TestItem.sort_order)
        )
        items = list(r.scalars().all())

        if not items:
            raise BusinessException(400, "选中的测试项均已禁用")

        # Get equipment base URL
        r = await db.execute(select(EquipmentConfig).where(EquipmentConfig.station_id == station_id))
        equip_cfg = r.scalar_one_or_none()
        base_url = equip_cfg.equipment_service_address if equip_cfg else ""

        # Update existing TestRun to RUNNING
        run.status = RUN_STATUS_RUNNING
        run.started_at = __import__('datetime').datetime.utcnow()
        await db.flush()

        r = await db.execute(select(TestSlot).where(TestSlot.id == slot_id))
        slot = r.scalar_one_or_none()
        if slot:
            slot.status = SLOT_STATUS_TESTING
            slot.current_batch_id = run.batch_id
            slot.serial_number = serial_number
        await db.flush()

        await notify_run_started(station_id, {
            "batch_id": run.batch_id,
            "operator": operator,
            "serial_number": serial_number,
            "run_id": run.id,
            "slot_id": slot_id,
        })

        total = len(items)
        passed_count = 0
        failed_count = 0
        log_items = []

        for item in items:
            # Get service address
            relative_path = item.service_address or ""
            service_url = _build_service_url(base_url, relative_path)

            # Prepare payload
            payload = {
                "serial_number": serial_number,
                "station_id": station_id,
                "slot_id": slot_id,
                "test_item_id": item.id,
                "test_item_name": item.name,
                "params": item.params or {},
            }

            # Call actual service
            svc_result = await _call_test_service(service_url, payload, timeout=30.0)

            passed = svc_result.get("passed", False)
            raw_value = svc_result.get("actual_value", 0.0)
            deviation = svc_result.get("deviation", 0.0)
            duration_ms = svc_result.get("duration_ms", 0)
            error_msg = svc_result.get("error")

            remark = ""
            try:
                actual_value = float(raw_value)
            except (TypeError, ValueError):
                actual_value = 1.0 if passed else 0.0
                remark = str(raw_value)

            from app.models.test_result import TestResult
            result = TestResult(
                test_item_id=item.id,
                test_run_id=run.id,
                operator=operator,
                serial_number=serial_number,
                actual_value=actual_value,
                passed=passed,
                deviation=deviation,
                duration_ms=duration_ms,
                remark=remark + (f" | {error_msg}" if error_msg else ""),
            )
            db.add(result)
            log_items.append({
                "name": item.name,
                "expected": item.expected_value,
                "actual": actual_value,
                "passed": passed,
            })

            if passed:
                passed_count += 1
            else:
                failed_count += 1

            await db.flush()

            await notify_item_tested(station_id, {
                "item_name": item.name,
                "passed": passed,
                "actual_value": actual_value,
                "slot_id": slot_id,
                "run_id": run.id,
            })

        run.status = RUN_STATUS_COMPLETED if failed_count == 0 else RUN_STATUS_FAILED
        run.ended_at = __import__('datetime').datetime.utcnow()
        run.total_items = total
        run.passed_items = passed_count
        run.failed_items = failed_count

        if slot:
            slot.status = SLOT_STATUS_PASS if run.status == RUN_STATUS_COMPLETED else SLOT_STATUS_IDLE
            slot.current_batch_id = None
            slot.serial_number = None
        await db.flush()

        # Save log file to disk
        try:
            from app.config import get_settings
            settings = get_settings()
            base_dir = settings.LOG_FOLDER
            if not os.path.isabs(base_dir):
                base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), base_dir)
            slot_info = slot.name if slot else ""
            save_run_log(
                base_dir=base_dir, station_id=station_id,
                serial_number=serial_number, batch_id=run.batch_id,
                status=run.status, total=total, passed=passed_count, failed=failed_count,
                items=log_items, slot_info=slot_info,
            )
        except Exception:
            pass

        if run.status == RUN_STATUS_COMPLETED:
            await notify_run_completed(station_id, {
                "batch_id": run.batch_id,
                "total": total,
                "passed": passed_count,
                "failed": failed_count,
                "slot_id": slot_id,
            })
        else:
            await notify_run_failed(station_id, {
                "batch_id": run.batch_id,
                "error": f"{failed_count}/{total} 项失败",
                "slot_id": slot_id,
            })

        return {"run_id": run.id, "batch_id": run.batch_id, "status": run.status}
