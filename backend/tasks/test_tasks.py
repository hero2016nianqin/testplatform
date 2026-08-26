"""
测试执行异步任务
对应 design.md §7.2 — 支持传统模式 + 序列模式
"""
import asyncio
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tasks.celery_app import celery_app
from app.models.test_run import TestRun
from app.models.station import TestSlot
from app.models.station_config import SoftwareConfig
from app.config import (
    SLOT_STATUS_TESTING, SLOT_STATUS_IDLE,
    RUN_STATUS_FAILED,
)
from app.ws.handlers import notify_run_failed


@celery_app.task(bind=True, max_retries=3, default_retry_delay=5)
def execute_test_run(self, run_id: int):
    """异步执行测试批次（传统模式）— 委托给 TestExecutor"""
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from app.config import get_settings
    settings = get_settings()

    async def _run():
        from app.core.redis import reset_redis_pool
        reset_redis_pool()
        engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)
        session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with session_factory() as db:
            r = await db.execute(select(TestRun).where(TestRun.id == run_id))
            run = r.scalar_one_or_none()
            if not run:
                return {"error": "批次不存在"}

            try:
                r2 = await db.execute(select(SoftwareConfig).where(SoftwareConfig.station_id == run.station_id))
                sw_cfg = r2.scalar_one_or_none()

                from app.services.test_executor import TestExecutor
                result = await TestExecutor._execute_traditional_mode(
                    db=db,
                    run=run,
                    station_id=run.station_id,
                    slot_id=run.slot_id,
                    serial_number=run.serial_number,
                    operator=run.operator,
                    sw_cfg=sw_cfg,
                )
                await db.commit()
                return result
            except Exception as e:
                run.status = RUN_STATUS_FAILED
                run.ended_at = datetime.utcnow()
                r = await db.execute(select(TestSlot).where(TestSlot.id == run.slot_id))
                slot = r.scalar_one_or_none()
                if slot and slot.status == SLOT_STATUS_TESTING:
                    slot.status = SLOT_STATUS_IDLE
                    slot.current_batch_id = None
                    slot.serial_number = None
                await db.commit()
                await notify_run_failed(run.station_id, {
                    "batch_id": run.batch_id,
                    "error": str(e)[:200],
                    "slot_id": run.slot_id,
                })
                raise
        await engine.dispose()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_run())
    finally:
        loop.close()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=5)
def execute_sequence_run(self, run_id: int):
    """异步执行序列模式测试批次 — 委托给 TestExecutor"""
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from app.config import get_settings
    settings = get_settings()

    async def _run():
        from app.core.redis import reset_redis_pool
        reset_redis_pool()
        engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)
        session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with session_factory() as db:
            r = await db.execute(select(TestRun).where(TestRun.id == run_id))
            run = r.scalar_one_or_none()
            if not run:
                return {"error": "批次不存在"}

            try:
                sequence_id = run.sequence_id or 0
                if not sequence_id:
                    r2 = await db.execute(select(SoftwareConfig).where(SoftwareConfig.station_id == run.station_id))
                    sw_cfg = r2.scalar_one_or_none()
                    if sw_cfg and sw_cfg.sequence_id and sw_cfg.sequence_id > 0:
                        sequence_id = sw_cfg.sequence_id

                from app.services.test_executor import TestExecutor
                result = await TestExecutor._execute_sequence_mode(
                    db=db,
                    run=run,
                    station_id=run.station_id,
                    slot_id=run.slot_id,
                    serial_number=run.serial_number,
                    operator=run.operator,
                    sequence_id=sequence_id,
                    selected_item_ids=run.selected_item_ids or [],
                )
                await db.commit()
                return result
            except Exception as e:
                run.status = RUN_STATUS_FAILED
                run.ended_at = datetime.utcnow()
                r = await db.execute(select(TestSlot).where(TestSlot.id == run.slot_id))
                slot = r.scalar_one_or_none()
                if slot and slot.status == SLOT_STATUS_TESTING:
                    slot.status = SLOT_STATUS_IDLE
                    slot.current_batch_id = None
                    slot.serial_number = None
                await db.commit()
                await notify_run_failed(run.station_id, {
                    "batch_id": run.batch_id,
                    "error": str(e)[:200],
                    "slot_id": run.slot_id,
                })
                raise
        await engine.dispose()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_run())
    finally:
        loop.close()
