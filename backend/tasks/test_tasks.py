"""
测试执行异步任务
对应 design.md §7.2 — 支持传统模式 + 序列模式
"""
import asyncio
import random
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tasks.celery_app import celery_app
from app.core.database import AsyncSessionLocal
from app.models.test_run import TestRun
from app.models.test_item import TestItem
from app.models.test_sequence import TestSequence, TestSequenceStep, TestItemTemplate
from app.models.test_result import TestResult
from app.models.station import TestSlot
from app.models.station_config import SoftwareConfig
from app.config import (
    SLOT_STATUS_TESTING, SLOT_STATUS_PASS, SLOT_STATUS_FAIL,
    RUN_STATUS_RUNNING, RUN_STATUS_COMPLETED, RUN_STATUS_FAILED,
)
from app.ws.handlers import (
    notify_run_started, notify_item_tested,
    notify_run_completed, notify_run_failed,
)


def run_sync(coro):
    """在 Celery worker 中运行异步代码"""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=5)
def execute_test_run(self, run_id: int):
    """异步执行测试批次（传统模式）"""
    async def _run():
        async with AsyncSessionLocal() as db:
            r = await db.execute(select(TestRun).where(TestRun.id == run_id))
            run = r.scalar_one_or_none()
            if not run:
                return {"error": "批次不存在"}
            if run.status != RUN_STATUS_PENDING:
                return {"error": f"批次状态异常: {run.status}"}

            run.status = RUN_STATUS_RUNNING
            run.started_at = datetime.utcnow()

            # Update slot
            if run.slot_id:
                r = await db.execute(select(TestSlot).where(TestSlot.id == run.slot_id))
                slot = r.scalar_one_or_none()
                if slot:
                    slot.status = SLOT_STATUS_TESTING
                    slot.current_batch_id = run.batch_id
            await db.flush()

            station_id = run.station_id or 0
            await notify_run_started(station_id, {
                "batch_id": run.batch_id, "operator": run.operator,
                "serial_number": run.serial_number, "run_id": run.id,
            })

            # Get test items from software config
            if run.station_id:
                r = await db.execute(
                    select(SoftwareConfig).where(SoftwareConfig.station_id == run.station_id)
                )
                sw = r.scalar_one_or_none()
                item_ids = sw.selected_test_item_ids if sw and sw.selected_test_item_ids else []
            else:
                item_ids = []

            if item_ids:
                r = await db.execute(
                    select(TestItem).where(TestItem.id.in_(item_ids), TestItem.is_active == True)
                    .order_by(TestItem.sort_order)
                )
                items = list(r.scalars().all())
            else:
                r = await db.execute(
                    select(TestItem).where(TestItem.is_active == True).order_by(TestItem.sort_order)
                )
                items = list(r.scalars().all())

            total = len(items)
            passed_count = 0
            failed_count = 0

            for item in items:
                import asyncio as _asyncio
                _asyncio.sleep(0.5)

                actual_value = item.expected_value + (random.random() - 0.5) * 0.1
                passed = item.min_value <= actual_value <= item.max_value

                result = TestResult(
                    test_item_id=item.id,
                    test_run_id=run.id,
                    operator=run.operator,
                    serial_number=run.serial_number,
                    actual_value=actual_value,
                    passed=passed,
                    deviation=actual_value - item.expected_value,
                    duration_ms=500,
                )
                db.add(result)

                if passed:
                    passed_count += 1
                else:
                    failed_count += 1

                await db.flush()

                await notify_item_tested(station_id, {
                    "item_name": item.name, "passed": passed,
                    "actual_value": actual_value, "slot_id": run.slot_id,
                    "run_id": run.id,
                })

            run.status = RUN_STATUS_COMPLETED if failed_count == 0 else RUN_STATUS_FAILED
            run.ended_at = datetime.utcnow()
            run.total_items = total
            run.passed_items = passed_count
            run.failed_items = failed_count

            if run.slot_id:
                r = await db.execute(select(TestSlot).where(TestSlot.id == run.slot_id))
                slot = r.scalar_one_or_none()
                if slot:
                    slot.status = SLOT_STATUS_PASS if run.status == RUN_STATUS_COMPLETED else SLOT_STATUS_IDLE
                    slot.current_batch_id = None

            await db.commit()

            if run.status == RUN_STATUS_COMPLETED:
                await notify_run_completed(station_id, {
                    "batch_id": run.batch_id, "total": total,
                    "passed": passed_count, "failed": failed_count,
                })
            else:
                await notify_run_failed(station_id, {
                    "batch_id": run.batch_id,
                    "error": f"{failed_count}/{total} 项失败",
                })

            return {"run_id": run.id, "status": run.status, "passed": passed_count, "failed": failed_count}

    try:
        return run_sync(_run())
    except Exception as exc:
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=5)
def execute_sequence_run(self, run_id: int):
    """异步执行序列模式测试批次"""
    async def _run():
        async with AsyncSessionLocal() as db:
            r = await db.execute(select(TestRun).where(TestRun.id == run_id))
            run = r.scalar_one_or_none()
            if not run:
                return {"error": "批次不存在"}

            run.status = RUN_STATUS_RUNNING
            run.started_at = datetime.utcnow()

            if run.slot_id:
                r = await db.execute(select(TestSlot).where(TestSlot.id == run.slot_id))
                slot = r.scalar_one_or_none()
                if slot:
                    slot.status = SLOT_STATUS_TESTING
                    slot.current_batch_id = run.batch_id
            await db.flush()

            station_id = run.station_id or 0
            await notify_run_started(station_id, {
                "batch_id": run.batch_id, "operator": run.operator,
                "serial_number": run.serial_number, "run_id": run.id,
            })

            seq_id = run.sequence_id
            r = await db.execute(
                select(TestSequence).where(TestSequence.id == seq_id)
            )
            seq = r.scalar_one_or_none()

            steps = []
            if seq:
                r = await db.execute(
                    select(TestSequenceStep).where(TestSequenceStep.sequence_id == seq_id)
                    .order_by(TestSequenceStep.step_order)
                )
                steps = list(r.scalars().all())

            total = len(steps)
            passed_count = 0
            failed_count = 0
            stopped = False

            for step in steps:
                if stopped:
                    break

                r = await db.execute(select(TestItemTemplate).where(TestItemTemplate.id == step.template_id))
                template = r.scalar_one_or_none()
                if not template:
                    continue

                import asyncio as _asyncio
                _asyncio.sleep(0.5)

                actual_value = round(random.uniform(0, 100), 2)
                passed = random.random() > 0.1

                result = TestResult(
                    test_item_id=template.id,
                    test_run_id=run.id,
                    operator=run.operator,
                    serial_number=run.serial_number,
                    actual_value=actual_value,
                    passed=passed,
                    deviation=0.0,
                    duration_ms=step.timeout_seconds * 1000 if step.timeout_seconds else 60000,
                )
                db.add(result)

                if passed:
                    passed_count += 1
                else:
                    failed_count += 1

                await db.flush()

                await notify_item_tested(station_id, {
                    "item_name": template.name, "passed": passed,
                    "actual_value": actual_value, "slot_id": run.slot_id,
                    "run_id": run.id, "is_critical": template.is_critical,
                })

                if template.is_critical and not passed:
                    stopped = True
                    run.status = RUN_STATUS_FAILED
                    run.ended_at = datetime.utcnow()
                    if run.slot_id:
                        r = await db.execute(select(TestSlot).where(TestSlot.id == run.slot_id))
                        slot = r.scalar_one_or_none()
                        if slot:
                            slot.status = SLOT_STATUS_FAIL
                            slot.current_batch_id = None
                    await db.commit()
                    await notify_run_failed(station_id, {
                        "batch_id": run.batch_id,
                        "error": f"关键项失败: {template.name}",
                    })
                    return {"run_id": run.id, "status": "failed", "stopped_by_critical": True}

            if not stopped:
                run.status = RUN_STATUS_COMPLETED if failed_count == 0 else RUN_STATUS_FAILED
                run.ended_at = datetime.utcnow()
                run.total_items = total
                run.passed_items = passed_count
                run.failed_items = failed_count

                if run.slot_id:
                    r = await db.execute(select(TestSlot).where(TestSlot.id == run.slot_id))
                    slot = r.scalar_one_or_none()
                    if slot:
                        slot.status = SLOT_STATUS_PASS if run.status == RUN_STATUS_COMPLETED else SLOT_STATUS_IDLE
                        slot.current_batch_id = None

                await db.commit()

                if run.status == RUN_STATUS_COMPLETED:
                    await notify_run_completed(station_id, {
                        "batch_id": run.batch_id, "total": total,
                        "passed": passed_count, "failed": failed_count,
                    })
                else:
                    await notify_run_failed(station_id, {
                        "batch_id": run.batch_id,
                        "error": f"{failed_count}/{total} 项失败",
                    })

            return {"run_id": run.id, "status": run.status}

    try:
        return run_sync(_run())
    except Exception as exc:
        raise self.retry(exc=exc)
