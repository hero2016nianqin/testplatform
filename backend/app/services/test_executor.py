"""
异步测试执行引擎 — 支持传统模式（基于 TestItem）和序列模式（基于 TestSequence）
对应 design.md §7.2 (Fig. 传统模式 + 序列模式), §12 WebSocket 事件
"""
import asyncio
import os
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.test_run import TestRun
from app.models.test_item import TestItem
from app.models.test_sequence import TestSequence, TestSequenceStep, TestItemTemplate
from app.models.station_config import SoftwareConfig
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


class TestExecutor:

    @staticmethod
    async def execute_slot_scan(
        db: AsyncSession,
        station_id: int,
        slot_id: int,
        serial_number: str,
        operator: str,
        sequence_id: Optional[int] = None,
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

        # 2. 获取 Redis 分布式锁（非阻塞，失败则拒绝）
        acquired, lock_token = await acquire_slot_lock(slot_id, ttl=10)
        if not acquired:
            raise BusinessException(409, "槽位正在测试中，请稍后再试")

        try:
            # 3. 创建 PENDING 批次
            from app.services.test_service import TestService
            run = await TestService.create_pending_run(db, {
                "station_id": station_id,
                "slot_id": slot_id,
                "serial_number": serial_number,
                "operator": operator,
                "sequence_id": sequence_id or 0,
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
        station_id: int,
        slot_id: int,
        serial_number: str,
        operator: str,
        sequence_id: int,
    ) -> dict:
        """序列模式 — 按 TestSequence + TestItemTemplate 执行"""
        from sqlalchemy import select

        r = await db.execute(select(TestSequence).where(TestSequence.id == sequence_id))
        seq = r.scalar_one_or_none()
        if not seq:
            raise NotFoundError("测试序列不存在")

        r = await db.execute(
            select(TestSequenceStep).where(TestSequenceStep.sequence_id == sequence_id)
            .order_by(TestSequenceStep.step_order)
        )
        steps = list(r.scalars().all())

        # Create TestRun
        run = TestRun(
            batch_id=generate_batch_id(),
            serial_number=serial_number,
            operator=operator,
            status=RUN_STATUS_RUNNING,
            station_id=station_id,
            slot_id=slot_id,
            sequence_id=sequence_id,
            sequence_name=seq.name,
            started_at=__import__('datetime').datetime.utcnow(),
        )
        db.add(run)
        await db.flush()

        # Update slot
        r = await db.execute(select(TestSlot).where(TestSlot.id == slot_id))
        slot = r.scalar_one_or_none()
        if slot:
            slot.status = SLOT_STATUS_TESTING
            slot.current_batch_id = run.batch_id
            slot.serial_number = serial_number
        await db.flush()

        # Notify run_started
        await notify_run_started(station_id, {
            "batch_id": run.batch_id,
            "operator": operator,
            "serial_number": serial_number,
            "run_id": run.id,
            "slot_id": slot_id,
        })

        # Execute each step
        total = len(steps)
        passed_count = 0
        failed_count = 0
        stopped = False
        log_items = []

        for step in steps:
            if stopped:
                break

            r = await db.execute(select(TestItemTemplate).where(TestItemTemplate.id == step.template_id))
            template = r.scalar_one_or_none()
            if not template:
                continue

            await asyncio.sleep(0.5)  # Simulate test execution delay

            # Simulate result (in production, call actual service)
            actual_value = 0.0
            import random
            passed = random.random() > 0.1  # 90% pass rate

            from app.models.test_result import TestResult
            result = TestResult(
                test_item_id=template.id,
                test_run_id=run.id,
                operator=operator,
                serial_number=serial_number,
                actual_value=actual_value,
                passed=passed,
                deviation=0.0,
                duration_ms=500,
            )
            db.add(result)
            log_items.append({
                "name": template.name,
                "expected": getattr(step, 'expected_value', "-"),
                "actual": actual_value,
                "passed": passed,
            })

            if passed:
                passed_count += 1
            else:
                failed_count += 1

            await db.flush()

            is_critical = template.is_critical
            await notify_item_tested(station_id, {
                "item_name": template.name,
                "passed": passed,
                "actual_value": actual_value,
                "slot_id": slot_id,
                "run_id": run.id,
                "is_critical": is_critical,
            })

            # Critical item failure → stop
            if is_critical and not passed:
                stopped = True
                run.status = RUN_STATUS_FAILED
                run.ended_at = __import__('datetime').datetime.utcnow()
                if slot:
                    slot.status = SLOT_STATUS_FAIL
                    slot.current_batch_id = None
                    slot.serial_number = None
                await db.flush()

                # Save log on critical failure
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
                    "error": f"关键项失败: {template.name}",
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

    @staticmethod
    async def _execute_traditional_mode(
        db: AsyncSession,
        station_id: int,
        slot_id: int,
        serial_number: str,
        operator: str,
        sw_cfg: Optional[SoftwareConfig],
    ) -> dict:
        """传统模式 — 基于 SoftwareConfig.selected_test_item_ids"""
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

        run = TestRun(
            batch_id=generate_batch_id(),
            serial_number=serial_number,
            operator=operator,
            status=RUN_STATUS_RUNNING,
            station_id=station_id,
            slot_id=slot_id,
            started_at=__import__('datetime').datetime.utcnow(),
        )
        db.add(run)
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
            await asyncio.sleep(0.3)

            actual_value = item.expected_value
            import random
            passed = random.random() > 0.1

            from app.models.test_result import TestResult
            result = TestResult(
                test_item_id=item.id,
                test_run_id=run.id,
                operator=operator,
                serial_number=serial_number,
                actual_value=actual_value,
                passed=passed,
                deviation=actual_value - item.expected_value if passed else 999.0,
                duration_ms=300,
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
