"""
日志管理 API
对应 design.md §5.1, §5.2, §6.1
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps.db_deps import get_db
from app.core.response import success, paginated
from app.schemas.log import LogQueryParams, LogResp, LogStatsResp
from app.services.log_service import LogService

router = APIRouter(tags=["日志"])

svc = LogService()


@router.get("")
async def list_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    level: str = Query(None),
    run_id: int = Query(None),
    slot_id: int = Query(None),
    start_date: str = Query(None),
    end_date: str = Query(None),
    db: AsyncSession = Depends(get_db),
):
    items, total = await svc.query_logs(db, page, page_size, level, run_id, slot_id, start_date, end_date)
    return paginated(items, total, page, page_size)


@router.get("/stats")
async def log_stats(
    days: int = Query(30, ge=1),
    db: AsyncSession = Depends(get_db),
):
    stats = await svc.get_stats(db, days)
    return success(data=stats)


@router.get("/export")
async def export_logs(
    level: str = Query(None),
    start_date: str = Query(None),
    end_date: str = Query(None),
    db: AsyncSession = Depends(get_db),
):
    items, _ = await svc.query_logs(db, 1, 10000, level, start_date=start_date, end_date=end_date)
    from app.utils.export import export_csv
    headers = ["ID", "级别", "消息", "运行ID", "槽位ID", "时间"]
    rows = [[i["id"], i["level"], i["message"], i["run_id"], i["slot_id"], i["created_at"]] for i in items]
    csv_content = export_csv(headers, rows)
    from fastapi.responses import Response
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=logs.csv"},
    )
