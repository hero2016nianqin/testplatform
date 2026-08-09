"""
测试相关 API
对应 design.md §4.2, §5.1, §5.2, §7.2, §12
"""
from fastapi import APIRouter, Depends, Query, UploadFile
from app.utils.rate_limiter import rate_limit
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps.db_deps import get_db
from app.deps.auth_deps import require_developer, require_process
from app.core.response import success, paginated
from app.schemas.test_item import TestItemCreateReq, TestItemUpdateReq, TestItemResp
from app.schemas.test_sequence import (
    TemplateCreateReq, TemplateUpdateReq, TemplateResp,
    SequenceCreateReq, SequenceUpdateReq,
    SequenceResp, SequenceDetailResp, StepResp,
)
from app.schemas.test_run import RunCreateReq, RunUpdateReq, ResultSubmitReq, RunResp
from app.schemas.test_result import ResultResp
from app.services.test_service import TestService

router = APIRouter(tags=["测试"])

svc = TestService()


# ── Test Items ──
@router.get("/items", dependencies=[Depends(rate_limit("test_items", 60, 60))])
async def list_test_items(
    category: str = Query(None),
    db: AsyncSession = Depends(get_db),
):
    items = await svc.list_items(db, category)
    return success(data=[TestItemResp(**i.to_dict()) for i in items])


@router.post("/items", dependencies=[Depends(require_developer)])
async def create_test_item(req: TestItemCreateReq, db: AsyncSession = Depends(get_db)):
    item = await svc.create_item(db, req.model_dump())
    return success(data=TestItemResp(**item.to_dict()), message="测试项创建成功")


@router.put("/items/{item_id}", dependencies=[Depends(require_developer)])
async def update_test_item(item_id: int, req: TestItemUpdateReq, db: AsyncSession = Depends(get_db)):
    item = await svc.update_item(db, item_id, req.model_dump(exclude_none=True))
    return success(data=TestItemResp(**item.to_dict()), message="测试项更新成功")


@router.delete("/items/{item_id}", dependencies=[Depends(require_developer)])
async def delete_test_item(item_id: int, db: AsyncSession = Depends(get_db)):
    await svc.delete_item(db, item_id)
    return success(message="测试项已删除")


# ── Templates ──
@router.get("/templates", dependencies=[Depends(rate_limit("templates", 60, 60))])
async def list_templates(
    category: str = Query(None),
    db: AsyncSession = Depends(get_db),
):
    templates = await svc.list_templates(db, category)
    return success(data=[TemplateResp(**t.to_dict()) for t in templates])


@router.post("/templates", dependencies=[Depends(require_developer)])
async def create_template(req: TemplateCreateReq, db: AsyncSession = Depends(get_db)):
    t = await svc.create_template(db, req.model_dump())
    return success(data=TemplateResp(**t.to_dict()), message="模板创建成功")


@router.put("/templates/{template_id}", dependencies=[Depends(require_developer)])
async def update_template(template_id: int, req: TemplateUpdateReq, db: AsyncSession = Depends(get_db)):
    t = await svc.update_template(db, template_id, req.model_dump(exclude_none=True))
    return success(data=TemplateResp(**t.to_dict()), message="模板更新成功")


@router.delete("/templates/{template_id}", dependencies=[Depends(require_developer)])
async def delete_template(template_id: int, db: AsyncSession = Depends(get_db)):
    await svc.delete_template(db, template_id)
    return success(message="模板已删除")


# ── Sequences ──
@router.get("/sequences", dependencies=[Depends(rate_limit("sequences", 60, 60))])
async def list_sequences(db: AsyncSession = Depends(get_db)):
    seqs = await svc.list_sequences(db)
    return success(data=[SequenceResp(**s.to_dict()) for s in seqs])


@router.get("/sequences/{sequence_id}")
async def get_sequence(sequence_id: int, db: AsyncSession = Depends(get_db)):
    seq = await svc.get_sequence(db, sequence_id)
    steps = []
    for step in seq._steps:
        t = step._template
        steps.append(StepResp(
            id=step.id,
            sequence_id=step.sequence_id,
            step_order=step.step_order,
            timeout_seconds=step.timeout_seconds,
            template_id=step.template_id,
            template_name=t.name if t else "",
            template_service_address=t.service_address if t else "",
            template_is_critical=t.is_critical if t else False,
            template_category=t.category if t else "",
        ))
    return success(data=SequenceDetailResp(**seq.to_dict(), steps=steps))


@router.post("/sequences", dependencies=[Depends(require_developer)])
async def create_sequence(req: SequenceCreateReq, db: AsyncSession = Depends(get_db)):
    seq = await svc.create_sequence(db, req.model_dump())
    return success(data=SequenceResp(**seq.to_dict()), message="序列创建成功")


@router.put("/sequences/{sequence_id}", dependencies=[Depends(require_developer)])
async def update_sequence(sequence_id: int, req: SequenceUpdateReq, db: AsyncSession = Depends(get_db)):
    seq = await svc.update_sequence(db, sequence_id, req.model_dump(exclude_none=True))
    return success(data=SequenceResp(**seq.to_dict()), message="序列更新成功")


@router.delete("/sequences/{sequence_id}", dependencies=[Depends(require_developer)])
async def delete_sequence(sequence_id: int, db: AsyncSession = Depends(get_db)):
    await svc.delete_sequence(db, sequence_id)
    return success(message="序列已删除")


# ── Test Runs ──
@router.get("/runs", dependencies=[Depends(rate_limit("runs", 60, 60))])
async def list_runs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100000),
    status: str = Query(None),
    operator: str = Query(None),
    station_id: int = Query(None),
    start_date: str = Query(None),
    end_date: str = Query(None),
    db: AsyncSession = Depends(get_db),
):
    runs, total = await svc.list_runs(db, page, page_size, status, operator, station_id, start_date, end_date)
    items = [RunResp(**r.to_dict()) for r in runs]
    return paginated(items, total, page, page_size)


@router.post("/runs", dependencies=[Depends(rate_limit("create_run", 30, 60))])
async def create_run(req: RunCreateReq, db: AsyncSession = Depends(get_db)):
    run = await svc.create_run(db, req.model_dump())
    return success(data=RunResp(**run.to_dict()), message="批次创建成功")


@router.put("/runs/{run_id}", dependencies=[Depends(rate_limit("update_run", 60, 60))])
async def update_run(run_id: int, req: RunUpdateReq, db: AsyncSession = Depends(get_db)):
    run = await svc.update_run(db, run_id, req.model_dump(exclude_none=True))
    return success(data=RunResp(**run.to_dict()), message="批次更新成功")


@router.post("/runs/{run_id}/results", dependencies=[Depends(rate_limit("submit_result", 60, 60))])
async def submit_result(run_id: int, req: ResultSubmitReq, db: AsyncSession = Depends(get_db)):
    result = await svc.submit_result(db, run_id, req.model_dump())
    return success(data=result, message="测试结果已提交")


@router.post("/scan")
async def scan_test(
    station_id: int = Query(...),
    slot_id: int = Query(...),
    serial_number: str = Query(""),
    operator: str = Query(""),
    sequence_id: int = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """扫码即测 — 单个槽位扫码立即启动测试"""
    from app.services.test_executor import TestExecutor
    result = await TestExecutor.execute_slot_scan(
        db, station_id, slot_id, serial_number, operator, sequence_id,
    )
    return success(data=result, message="测试已启动")


# ── Records ──
@router.get("/records", dependencies=[Depends(rate_limit("records", 30, 60))])
async def get_records(
    level: str = Query("R1"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    operator: str = Query(None),
    serial_number: str = Query(None),
    status: str = Query(None),
    station_id: int = Query(None),
    batch_id: str = Query(None),
    start_date: str = Query(None),
    end_date: str = Query(None),
    db: AsyncSession = Depends(get_db),
):
    items, total = await svc.get_records(db, level, page, page_size, operator, serial_number, status, station_id, batch_id, start_date, end_date)
    return paginated(items, total, page, page_size)


# ── Config Import / Export ──
@router.post("/configs/import", dependencies=[Depends(require_developer)])
async def import_config(
    file: UploadFile,
    format: str = Query("json"),
    dry_run: bool = Query(False, description="仅校验不写入"),
    db: AsyncSession = Depends(get_db),
):
    """导入配置文件 (CSV/XLSX/JSON/XML)"""
    from app.services.config_service import ConfigService
    parsed = await ConfigService.parse_import(file, format.lower())
    validated = ConfigService.validate_items(parsed["items"])
    if validated["errors"]:
        return success(code=1, data=validated, message="部分数据校验失败")
    if not dry_run:
        count = await ConfigService.import_items(db, validated["validated"])
        return success(data={"imported": count, **validated}, message=f"成功导入{count}条")
    return success(data=validated, message=f"校验通过 {validated['valid_count']} 条")


@router.get("/configs/export", dependencies=[Depends(require_process)])
async def export_config(
    format: str = Query("json"),
    db: AsyncSession = Depends(get_db),
):
    """导出测试项配置 (JSON/CSV/XLSX)"""
    from app.services.config_service import ConfigService
    from fastapi.responses import Response
    content, media_type = await ConfigService.export_items(db, format.lower())
    filename = f"test_items.{format}"
    return Response(content=content, media_type=media_type, headers={"Content-Disposition": f'attachment; filename="{filename}"'})
