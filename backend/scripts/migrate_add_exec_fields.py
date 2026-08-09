"""
迁移脚本: 为 collection_test_item 表添加自动化执行配置字段
用法: python -m scripts.migrate_add_exec_fields
"""
import asyncio
from sqlalchemy import text
from app.core.database import engine


async def migrate():
    async with engine.connect() as conn:
        existing = set()
        r = await conn.execute(text("PRAGMA table_info(collection_test_item)"))
        for row in r.fetchall():
            existing.add(row[1])

        adds = []
        if "service_address" not in existing:
            adds.append("ADD COLUMN service_address VARCHAR(500) DEFAULT ''")
        if "timeout_seconds" not in existing:
            adds.append("ADD COLUMN timeout_seconds INTEGER")
        if "block_type" not in existing:
            adds.append("ADD COLUMN block_type VARCHAR(20) DEFAULT 'normal'")
        if "parallel_enabled" not in existing:
            adds.append("ADD COLUMN parallel_enabled INTEGER DEFAULT 0")

        for stmt in adds:
            await conn.execute(text(f"ALTER TABLE collection_test_item {stmt}"))
            print(f"  + {stmt}")

        await conn.commit()
        print("Migration complete.")


if __name__ == "__main__":
    asyncio.run(migrate())
