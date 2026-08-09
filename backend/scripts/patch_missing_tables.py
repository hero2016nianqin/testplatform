"""数据库补表脚本（幂等）：为已有数据库补齐缺失的表。

现有数据库可能因历史原因缺少部分表（如权限系统的 audit_log / user_domain）。
create_all(checkfirst=True) 仅创建不存在的表，不会影响已有数据。

用法: python -m scripts.patch_missing_tables
"""
import asyncio
from sqlalchemy import text
from app.core.database import engine, Base
import app.models  # noqa: F401  确保所有 ORM 模型注册到 Base.metadata


async def _columns(conn, table: str) -> set[str]:
    if str(engine.url).startswith("postgres"):
        r = await conn.execute(text(
            "SELECT column_name FROM information_schema.columns WHERE table_name = :t"
        ), {"t": table})
        return {row[0] for row in r.fetchall()}
    r = await conn.execute(text(f"PRAGMA table_info({table})"))
    return {row[1] for row in r.fetchall()}


async def _patch_columns(conn):
    """为已有表补充新增列（幂等，兼容 SQLite/PostgreSQL）。"""
    # users.department
    cols = await _columns(conn, "users")
    if "department" not in cols:
        await conn.execute(text("ALTER TABLE users ADD COLUMN department VARCHAR(100) DEFAULT ''"))
        print("+ users.department")


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
    # 补充列
    async with engine.begin() as conn:
        await _patch_columns(conn)


if __name__ == "__main__":
    asyncio.run(patch())
