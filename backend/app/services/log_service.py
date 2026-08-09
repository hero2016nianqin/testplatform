from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError


class LogService:

    @staticmethod
    async def query_logs(
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        level: Optional[str] = None,
        run_id: Optional[int] = None,
        slot_id: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> tuple[list, int]:
        stmt = text("""
            SELECT id, run_id, slot_id, level, message, created_at
            FROM test_logs
            WHERE 1=1
            {filters}
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
        """)
        count_stmt = text("""
            SELECT COUNT(*) FROM test_logs WHERE 1=1 {filters}
        """)

        filters = ""
        params = {}
        if level:
            filters += " AND level = :level"
            params["level"] = level
        if run_id:
            filters += " AND run_id = :run_id"
            params["run_id"] = run_id
        if slot_id:
            filters += " AND slot_id = :slot_id"
            params["slot_id"] = slot_id
        if start_date:
            filters += " AND created_at >= :start_date"
            params["start_date"] = start_date
        if end_date:
            filters += " AND created_at <= :end_date"
            params["end_date"] = end_date

        count_sql = text(str(count_stmt).format(filters=filters))
        r = await db.execute(count_sql, params)
        total = r.scalar() or 0

        params["limit"] = page_size
        params["offset"] = (page - 1) * page_size
        sql = text(str(stmt).format(filters=filters))
        r = await db.execute(sql, params)
        rows = r.fetchall()

        items = [
            {
                "id": row[0], "run_id": row[1], "slot_id": row[2],
                "level": row[3], "message": row[4],
                "created_at": row[5].isoformat() if row[5] else None,
            }
            for row in rows
        ]
        return items, total

    @staticmethod
    async def get_stats(db: AsyncSession, days: int = 30) -> dict:
        since = (datetime.utcnow() - timedelta(days=days)).isoformat()
        total_stmt = text("SELECT COUNT(*) FROM test_logs WHERE created_at >= :since")
        info_stmt = text("SELECT COUNT(*) FROM test_logs WHERE created_at >= :since AND level = 'INFO'")
        warn_stmt = text("SELECT COUNT(*) FROM test_logs WHERE created_at >= :since AND level = 'WARN'")
        error_stmt = text("SELECT COUNT(*) FROM test_logs WHERE created_at >= :since AND level = 'ERROR'")

        total = (await db.execute(total_stmt, {"since": since})).scalar() or 0
        info = (await db.execute(info_stmt, {"since": since})).scalar() or 0
        warn = (await db.execute(warn_stmt, {"since": since})).scalar() or 0
        err = (await db.execute(error_stmt, {"since": since})).scalar() or 0

        return {"total": total, "info_count": info, "warn_count": warn, "error_count": err}
