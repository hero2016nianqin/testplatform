"""
迁移脚本: 创建 script_template 表
用法: python -m scripts.migrate_add_script_templates
"""
import asyncio
from sqlalchemy import text
from app.core.database import engine


async def migrate():
    async with engine.connect() as conn:
        existing_tables = set()
        r = await conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
        for row in r.fetchall():
            existing_tables.add(row[0])

        if "script_template" not in existing_tables:
            await conn.execute(text("""
                CREATE TABLE script_template (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(100) NOT NULL UNIQUE,
                    description TEXT DEFAULT '',
                    source_code TEXT NOT NULL,
                    output_format VARCHAR(10) DEFAULT 'json',
                    status INTEGER DEFAULT 1,
                    created_by VARCHAR(50) DEFAULT '',
                    updated_by VARCHAR(50) DEFAULT '',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """))
            await conn.execute(text("CREATE INDEX ix_script_template_name ON script_template(name)"))
            print("  + created table script_template")
        else:
            print("  - table script_template already exists")

        await conn.commit()
        print("Migration complete")


if __name__ == "__main__":
    asyncio.run(migrate())
