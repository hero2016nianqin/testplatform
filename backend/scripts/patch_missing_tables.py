"""数据库补表脚本（幂等）：为已有数据库补齐缺失的表。

现有数据库可能因历史原因缺少部分表（如权限系统的 audit_log / user_domain）。
create_all(checkfirst=True) 仅创建不存在的表，不会影响已有数据。

用法: python -m scripts.patch_missing_tables
"""
import asyncio
from app.core.database import engine, Base
import app.models  # noqa: F401  确保所有 ORM 模型注册到 Base.metadata


async def patch():
    async with engine.begin() as conn:
        before = set()
        r = await conn.exec_driver_sql(
            "SELECT name FROM sqlite_master WHERE type='table'" if str(engine.url).startswith("sqlite")
            else "SELECT tablename FROM pg_tables WHERE schemaname='public'"
        )
        before = {row[0] for row in r.fetchall()}
        await conn.run_sync(Base.metadata.create_all)
        after = set()
        r = await conn.exec_driver_sql(
            "SELECT name FROM sqlite_master WHERE type='table'" if str(engine.url).startswith("sqlite")
            else "SELECT tablename FROM pg_tables WHERE schemaname='public'"
        )
        after = {row[0] for row in r.fetchall()}
    added = sorted(after - before)
    if added:
        print("已补齐缺失表:", ", ".join(added))
    else:
        print("无缺失表，无需操作")


if __name__ == "__main__":
    asyncio.run(patch())
