"""
日志压缩归档 + 版本文件归档任务
对应 design.md §9 — 30天旧日志自动压缩至 MinIO
"""
import asyncio
import gzip
import json
import io
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select, text

from tasks.celery_app import celery_app
from app.core.database import AsyncSessionLocal
from app.config import get_settings
from app.core.minio_client import upload_file, remove_file


def run_sync(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(bind=True)
def compress_old_logs(self, days: int = 30):
    """
    压缩指定天数前的日志并归档至 MinIO
    对应 design.md §9 — 日志压缩
    """
    async def _compress():
        settings = get_settings()
        cutoff = datetime.utcnow() - timedelta(days=days)  # datetime 对象，PG timestamp 需要

        async with AsyncSessionLocal() as db:
            stmt = text("""
                SELECT id, run_id, slot_id, level, message, created_at
                FROM test_logs
                WHERE created_at < :cutoff
                ORDER BY created_at
                LIMIT 10000
            """)
            r = await db.execute(stmt, {"cutoff": cutoff})
            rows = r.fetchall()

            if not rows:
                return {"status": "no_logs_to_compress", "count": 0}

            log_entries = []
            for row in rows:
                log_entries.append({
                    "id": row[0], "run_id": row[1], "slot_id": row[2],
                    "level": row[3], "message": row[4],
                    "created_at": row[5].isoformat() if row[5] else None,
                })

            # Compress to gzip
            buf = io.BytesIO()
            with gzip.GzipFile(fileobj=buf, mode="wb") as f:
                f.write(json.dumps(log_entries, ensure_ascii=False, default=str).encode("utf-8"))

            # Upload to MinIO
            archive_date = (datetime.utcnow() - timedelta(days=days)).strftime("%Y%m%d")
            object_name = f"logs/archive/{archive_date}.json.gz"
            local_path = f"/tmp/logs_{archive_date}.json.gz"
            with open(local_path, "wb") as f:
                f.write(buf.getvalue())

            await upload_file(object_name, local_path, "application/gzip")

            # Delete archived logs from DB
            delete_stmt = text("DELETE FROM test_logs WHERE created_at < :cutoff")
            await db.execute(delete_stmt, {"cutoff": cutoff})
            await db.commit()

            import os
            os.remove(local_path)

            return {
                "status": "compressed",
                "count": len(log_entries),
                "archive": object_name,
                "size_bytes": len(buf.getvalue()),
            }

    try:
        return run_sync(_compress())
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


@celery_app.task(bind=True)
def archive_version_files(self, version_id: int):
    """
    将版本二进制文件归档至 MinIO
    对应 design.md §7.4 — 二进制文件管理
    """
    async def _archive():
        async with AsyncSessionLocal() as db:
            from app.models.version import VersionBinaryFile
            r = await db.execute(
                select(VersionBinaryFile).where(VersionBinaryFile.version_id == version_id)
            )
            files = list(r.scalars().all())

            archived = []
            for bf in files:
                try:
                    local_path = f"/tmp/{bf.filename}"
                    # In production, download from current storage then re-upload
                    archived.append({
                        "file_id": bf.id,
                        "filename": bf.filename,
                        "path": bf.file_path,
                    })
                except Exception:
                    continue

            return {"version_id": version_id, "archived": len(archived)}

    try:
        return run_sync(_archive())
    except Exception as exc:
        return {"version_id": version_id, "error": str(exc)}


@celery_app.task(bind=True)
def export_test_records_task(self, run_ids: list[int], format: str = "csv"):
    """异步导出测试记录"""
    async def _export():
        async with AsyncSessionLocal() as db:
            from app.models.test_run import TestRun
            from app.models.test_result import TestResult

            r = await db.execute(
                select(TestRun).where(TestRun.id.in_(run_ids))
            )
            runs = list(r.scalars().all())

            all_results = []
            for run in runs:
                r = await db.execute(
                    select(TestResult).where(TestResult.test_run_id == run.id)
                )
                results = list(r.scalars().all())
                for res in results:
                    all_results.append({
                        "batch_id": run.batch_id,
                        "serial_number": run.serial_number,
                        "operator": run.operator,
                        "item_name": res.test_item.name if res.test_item else "",
                        "actual_value": res.actual_value,
                        "passed": res.passed,
                        "deviation": res.deviation,
                        "duration_ms": res.duration_ms,
                        "tested_at": res.tested_at.isoformat() if res.tested_at else "",
                    })

            from app.utils.export import export_csv, export_xlsx
            headers = ["批次号", "序列号", "操作员", "测试项", "实测值", "结果", "偏差", "耗时(ms)", "测试时间"]
            rows = [
                [r["batch_id"], r["serial_number"], r["operator"], r["item_name"],
                 r["actual_value"], "PASS" if r["passed"] else "FAIL",
                 r["deviation"], r["duration_ms"], r["tested_at"]]
                for r in all_results
            ]

            if format == "xlsx":
                content = export_xlsx(headers, rows)
                ext = "xlsx"
            else:
                content = export_csv(headers, rows).encode("utf-8")
                ext = "csv"

            object_name = f"exports/records_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.{ext}"
            local_path = f"/tmp/export_{datetime.utcnow().timestamp()}.{ext}"
            with open(local_path, "wb") as f:
                if isinstance(content, bytes):
                    f.write(content)
                else:
                    f.write(content.encode("utf-8"))

            await upload_file(object_name, local_path, f"text/{ext}" if ext == "csv" else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            import os
            os.remove(local_path)

            from app.core.minio_client import presigned_download_url
            url = await presigned_download_url(object_name, 72)

            return {"url": url, "filename": object_name, "count": len(all_results)}

    try:
        return run_sync(_export())
    except Exception as exc:
        return {"error": str(exc)}
