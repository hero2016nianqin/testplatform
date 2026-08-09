"""评审功能数据库补丁（幂等）：
1. 为 bom_config 表补充 approver_id / approver_name 列
2. 创建 bom_review_event 表（评审事件时间线）

兼容 SQLite 与 PostgreSQL。
用法: python -m scripts.migrate_review_fields
"""
import asyncio
from sqlalchemy import text
from app.core.database import engine


async def _table_columns(conn, table: str) -> set[str]:
    if str(engine.url).startswith("postgres"):
        r = await conn.execute(text(
            "SELECT column_name FROM information_schema.columns WHERE table_name = :t"
        ), {"t": table})
        return {row[0] for row in r.fetchall()}
    r = await conn.execute(text(f"PRAGMA table_info({table})"))
    return {row[1] for row in r.fetchall()}


async def _table_exists(conn, table: str) -> bool:
    if str(engine.url).startswith("postgres"):
        r = await conn.execute(text(
            "SELECT to_regclass(:t) IS NOT NULL"
        ), {"t": table})
        return bool(r.scalar())
    r = await conn.execute(text(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'"))
    return r.scalar() is not None


async def migrate():
    is_pg = str(engine.url).startswith("postgres")
    async with engine.begin() as conn:
        cols = await _table_columns(conn, "bom_config")
        if "approver_id" not in cols:
            await conn.execute(text("ALTER TABLE bom_config ADD COLUMN approver_id INTEGER"))
            print("+ bom_config.approver_id")
        else:
            print("= bom_config.approver_id (exists)")
        if "approver_name" not in cols:
            await conn.execute(text("ALTER TABLE bom_config ADD COLUMN approver_name VARCHAR(100)"))
            print("+ bom_config.approver_name")
        else:
            print("= bom_config.approver_name (exists)")
        if "change_summary" not in cols:
            await conn.execute(text("ALTER TABLE bom_config ADD COLUMN change_summary TEXT"))
            print("+ bom_config.change_summary")
        else:
            print("= bom_config.change_summary (exists)")

        if await _table_exists(conn, "bom_review_event"):
            print("= bom_review_event (exists)")
        else:
            await conn.execute(text("""
                CREATE TABLE bom_review_event (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bom_config_id INTEGER NOT NULL,
                    action VARCHAR(20) NOT NULL,
                    operator_id INTEGER,
                    operator_name VARCHAR(100) DEFAULT '',
                    comment TEXT,
                    test_item_id INTEGER,
                    test_item_name VARCHAR(200) DEFAULT '',
                    indicator_id INTEGER,
                    param_key VARCHAR(100),
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """))
            await conn.execute(text(
                "CREATE INDEX ix_bom_review_event_config ON bom_review_event (bom_config_id)"
                if is_pg else
                "CREATE INDEX IF NOT EXISTS ix_bom_review_event_config ON bom_review_event (bom_config_id)"
            ))
            await conn.execute(text(
                "CREATE INDEX ix_bom_review_event_created ON bom_review_event (created_at)"
                if is_pg else
                "CREATE INDEX IF NOT EXISTS ix_bom_review_event_created ON bom_review_event (created_at)"
            ))
            print("+ bom_review_event (created)")
    print("迁移完成")


if __name__ == "__main__":
    asyncio.run(migrate())
