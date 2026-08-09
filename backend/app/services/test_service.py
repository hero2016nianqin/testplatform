from datetime import datetime
from typing import Optional, List

from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.test_item import TestItem
from app.models.test_sequence import TestItemTemplate, TestSequence, TestSequenceStep
from app.models.test_run import TestRun
from app.models.test_result import TestResult
from app.models.station import TestStation, TestSlot
from app.core.exceptions import NotFoundError, BusinessException
from app.utils.batch_id import generate_batch_id
from app.config import (
    SLOT_STATUS_TESTING, SLOT_STATUS_PASS, SLOT_STATUS_FAIL, SLOT_STATUS_IDLE,
    RUN_STATUS_RUNNING, RUN_STATUS_COMPLETED, RUN_STATUS_FAILED,
)


class TestService:

    # ── TestItem ──
    @staticmethod
    async def list_items(db: AsyncSession, category: Optional[str] = None) -> list[TestItem]:
        stmt = select(TestItem).order_by(TestItem.sort_order)
        if category:
            stmt = stmt.where(TestItem.category == category)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def create_item(db: AsyncSession, data: dict) -> TestItem:
        item = TestItem(**data)
        db.add(item)
        await db.flush()
        return item

    @staticmethod
    async def update_item(db: AsyncSession, item_id: int, data: dict) -> TestItem:
        r = await db.execute(select(TestItem).where(TestItem.id == item_id))
        item = r.scalar_one_or_none()
        if not item:
            raise NotFoundError("测试项不存在")
        for k, v in data.items():
            if v is not None:
                setattr(item, k, v)
        await db.flush()
        return item

    @staticmethod
    async def delete_item(db: AsyncSession, item_id: int):
        r = await db.execute(select(TestItem).where(TestItem.id == item_id))
        item = r.scalar_one_or_none()
        if not item:
            raise NotFoundError("测试项不存在")
        await db.delete(item)
        await db.flush()

    # ── TestItemTemplate ──
    @staticmethod
    async def list_templates(db: AsyncSession, category: Optional[str] = None) -> list[TestItemTemplate]:
        stmt = select(TestItemTemplate).where(TestItemTemplate.is_active == True).order_by(TestItemTemplate.sort_order)
        if category:
            stmt = stmt.where(TestItemTemplate.category == category)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def create_template(db: AsyncSession, data: dict) -> TestItemTemplate:
        t = TestItemTemplate(**data)
        db.add(t)
        await db.flush()
        return t

    @staticmethod
    async def update_template(db: AsyncSession, template_id: int, data: dict) -> TestItemTemplate:
        r = await db.execute(select(TestItemTemplate).where(TestItemTemplate.id == template_id))
        t = r.scalar_one_or_none()
        if not t:
            raise NotFoundError("模板不存在")
        for k, v in data.items():
            if v is not None:
                setattr(t, k, v)
        await db.flush()
        return t

    @staticmethod
    async def delete_template(db: AsyncSession, template_id: int):
        r = await db.execute(select(TestItemTemplate).where(TestItemTemplate.id == template_id))
        t = r.scalar_one_or_none()
        if not t:
            raise NotFoundError("模板不存在")
        t.is_active = False
        await db.flush()

    # ── TestSequence ──
    @staticmethod
    async def list_sequences(db: AsyncSession) -> list[TestSequence]:
        result = await db.execute(select(TestSequence).order_by(TestSequence.name))
        return list(result.scalars().all())

    @staticmethod
    async def get_sequence(db: AsyncSession, seq_id: int) -> TestSequence:
        r = await db.execute(
            select(TestSequence).where(TestSequence.id == seq_id)
        )
        seq = r.scalar_one_or_none()
        if not seq:
            raise NotFoundError("序列不存在")
        r = await db.execute(
            select(TestSequenceStep).where(TestSequenceStep.sequence_id == seq_id)
            .order_by(TestSequenceStep.step_order)
        )
        seq._steps = list(r.scalars().all())
        # load templates for each step
        for step in seq._steps:
            r = await db.execute(select(TestItemTemplate).where(TestItemTemplate.id == step.template_id))
            step._template = r.scalar_one_or_none()
        return seq

    @staticmethod
    async def create_sequence(db: AsyncSession, data: dict) -> TestSequence:
        steps_data = data.pop("steps", [])
        seq = TestSequence(**data)
        db.add(seq)
        await db.flush()
        for s in steps_data:
            db.add(TestSequenceStep(sequence_id=seq.id, **s))
        await db.flush()
        return seq

    @staticmethod
    async def update_sequence(db: AsyncSession, seq_id: int, data: dict) -> TestSequence:
        r = await db.execute(select(TestSequence).where(TestSequence.id == seq_id))
        seq = r.scalar_one_or_none()
        if not seq:
            raise NotFoundError("序列不存在")
        for k, v in data.items():
            if v is not None:
                setattr(seq, k, v)
        await db.flush()
        return seq

    @staticmethod
    async def delete_sequence(db: AsyncSession, seq_id: int):
        r = await db.execute(select(TestSequence).where(TestSequence.id == seq_id))
        seq = r.scalar_one_or_none()
        if not seq:
            raise NotFoundError("序列不存在")
        seq.is_active = False
        await db.flush()

    # ── TestRun ──
    @staticmethod
    async def create_run(db: AsyncSession, data: dict) -> TestRun:
        operator = data.get("operator", "")
        station_id = data.get("station_id")
        slot_id = data.get("slot_id")
        serial_number = data.get("serial_number", "")

        run = TestRun(
            batch_id=generate_batch_id(),
            product_type=data.get("product_type", ""),
            task_order=data.get("task_order", ""),
            serial_number=serial_number,
            operator=operator,
            status=RUN_STATUS_RUNNING,
            station_id=station_id,
            slot_id=slot_id,
            sequence_id=data.get("sequence_id", 0),
            sequence_name=data.get("sequence_name", ""),
            started_at=datetime.utcnow(),
        )
        db.add(run)
        await db.flush()

        # Update slot status
        r = await db.execute(select(TestSlot).where(TestSlot.id == slot_id))
        slot = r.scalar_one_or_none()
        if slot:
            slot.status = SLOT_STATUS_TESTING
            slot.current_batch_id = run.batch_id

        await db.flush()
        return run

    @staticmethod
    async def update_run(db: AsyncSession, run_id: int, data: dict) -> TestRun:
        r = await db.execute(select(TestRun).where(TestRun.id == run_id))
        run = r.scalar_one_or_none()
        if not run:
            raise NotFoundError("批次不存在")

        status = data.get("status")
        if status:
            run.status = status
            run.ended_at = datetime.utcnow()
            if "total_items" in data:
                run.total_items = data["total_items"]
            if "passed_items" in data:
                run.passed_items = data["passed_items"]
            if "failed_items" in data:
                run.failed_items = data["failed_items"]

            # Update slot status
            if run.slot_id:
                r = await db.execute(select(TestSlot).where(TestSlot.id == run.slot_id))
                slot = r.scalar_one_or_none()
                if slot:
                    slot.status = SLOT_STATUS_PASS if status == RUN_STATUS_COMPLETED else SLOT_STATUS_IDLE
                    if status in (RUN_STATUS_COMPLETED, RUN_STATUS_FAILED):
                        slot.current_batch_id = None

        await db.flush()
        return run

    @staticmethod
    async def submit_result(db: AsyncSession, run_id: int, data: dict) -> dict:
        r = await db.execute(select(TestRun).where(TestRun.id == run_id))
        run = r.scalar_one_or_none()
        if not run:
            raise NotFoundError("批次不存在")

        result = TestResult(
            test_item_id=data["test_item_id"],
            test_run_id=run_id,
            operator=data.get("operator", run.operator),
            serial_number=data.get("serial_number", run.serial_number),
            actual_value=data["actual_value"],
            passed=data["passed"],
            deviation=data.get("deviation", 0.0),
            duration_ms=data.get("duration_ms", 0),
            remark=data.get("remark", ""),
        )
        db.add(result)
        await db.flush()

        is_critical = data.get("is_critical", False)
        stop = is_critical and not data["passed"]

        run.passed_items = (run.passed_items or 0) + (1 if data["passed"] else 0)
        run.failed_items = (run.failed_items or 0) + (0 if data["passed"] else 1)
        run.total_items = (run.total_items or 0) + 1

        if stop:
            run.status = RUN_STATUS_FAILED
            run.ended_at = datetime.utcnow()
            if run.slot_id:
                r = await db.execute(select(TestSlot).where(TestSlot.id == run.slot_id))
                slot = r.scalar_one_or_none()
                if slot:
                    slot.status = SLOT_STATUS_FAIL
                    slot.current_batch_id = None

        await db.flush()

        return {
            "id": result.id,
            "stop": stop,
            "passed": data["passed"],
            "message": "关键项失败，测试终止" if stop else "",
        }

    @staticmethod
    async def list_runs(
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        operator: Optional[str] = None,
        station_id: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> tuple[list[TestRun], int]:
        stmt = select(TestRun)
        if status:
            stmt = stmt.where(TestRun.status == status)
        if operator:
            stmt = stmt.where(TestRun.operator.like(f"%{operator}%"))
        if station_id:
            stmt = stmt.where(TestRun.station_id == station_id)
        if start_date:
            stmt = stmt.where(TestRun.created_at >= start_date)
        if end_date:
            stmt = stmt.where(TestRun.created_at <= end_date)
        stmt = stmt.order_by(TestRun.created_at.desc())

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await db.execute(count_stmt)
        total = total_result.scalar() or 0

        result = await db.execute(stmt.offset((page - 1) * page_size).limit(page_size))
        runs = list(result.scalars().all())
        return runs, total

    # ── Records (R1/R2/R3) ──
    @staticmethod
    async def get_records(
        db: AsyncSession,
        level: str = "R1",
        page: int = 1,
        page_size: int = 20,
        operator: Optional[str] = None,
        serial_number: Optional[str] = None,
        status: Optional[str] = None,
        station_id: Optional[int] = None,
        batch_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> tuple[list[dict], int]:
        stmt = select(TestRun)
        if batch_id:
            stmt = stmt.where(TestRun.batch_id.like(f"%{batch_id}%"))
        if operator:
            stmt = stmt.where(TestRun.operator.like(f"%{operator}%"))
        if serial_number:
            stmt = stmt.where(TestRun.serial_number.like(f"%{serial_number}%"))
        if status:
            stmt = stmt.where(TestRun.status == status)
        if station_id:
            stmt = stmt.where(TestRun.station_id == station_id)
        if start_date:
            stmt = stmt.where(TestRun.created_at >= start_date)
        if end_date:
            stmt = stmt.where(TestRun.created_at <= end_date)
        stmt = stmt.order_by(TestRun.created_at.desc())

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await db.execute(count_stmt)
        total = total_result.scalar() or 0

        # Eager-load results + test_items to avoid N+1
        stmt = stmt.options(
            selectinload(TestRun.results).selectinload(TestResult.test_item)
        )
        result = await db.execute(stmt.offset((page - 1) * page_size).limit(page_size))
        runs = list(result.scalars().all())

        items = []
        for run in runs:
            item = run.to_dict()
            if level in ("R2", "R3"):
                item["results"] = [res.to_dict() for res in (run.results or [])]
            items.append(item)

        return items, total
