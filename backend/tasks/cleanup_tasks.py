"""
过期数据清理任务
对应 design.md §9 — 清理过期测试记录
"""
import asyncio
from datetime import datetime, timedelta

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from tasks.celery_app import celery_app
from app.core.database import AsyncSessionLocal
from app.config import RUN_STATUS_PENDING


def run_sync(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def cleanup_expired_runs(self, keep_days: int = 90):
    """
    清理过期测试批次和结果
    对应 design.md §9 — 过期数据清理
    """
    async def _cleanup():
        cutoff = datetime.utcnow() - timedelta(days=keep_days)  # datetime 对象，PG timestamp 需要

        async with AsyncSessionLocal() as db:
            # 1. Find expired runs
            r = await db.execute(
                text("""
                    SELECT id FROM test_runs
                    WHERE created_at < :cutoff AND status = :status
                """),
                {"cutoff": cutoff, "status": RUN_STATUS_PENDING},
            )
            expired_ids = [row[0] for row in r.fetchall()]

            if not expired_ids:
                return {"status": "no_expired_runs", "deleted": 0}

            # 2. Delete results first
            await db.execute(
                text("DELETE FROM test_results WHERE test_run_id = ANY(:ids)"),
                {"ids": expired_ids},
            )

            # 3. Delete runs
            await db.execute(
                text("DELETE FROM test_runs WHERE id = ANY(:ids)"),
                {"ids": expired_ids},
            )

            await db.commit()

            return {
                "status": "cleaned",
                "deleted_runs": len(expired_ids),
                "cutoff_date": cutoff,
            }

    try:
        return run_sync(_cleanup())
    except Exception as exc:
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def cleanup_old_sessions(self, max_age_hours: int = 48):
    """清理过期 Redis Session（兜底）使用 SCAN 避免阻塞"""
    async def _cleanup():
        from app.core.redis import get_redis_pool
        from redis.asyncio import Redis

        pool = get_redis_pool()
        async with Redis(connection_pool=pool) as r:
            deleted = 0
            async for key in r.scan_iter("session:*"):
                ttl = await r.ttl(key)
                if ttl < 0:
                    await r.delete(key)
                    deleted += 1
            return {"status": "cleaned", "deleted_sessions": deleted}

    try:
        return run_sync(_cleanup())
    except Exception as exc:
        raise self.retry(exc=exc)
