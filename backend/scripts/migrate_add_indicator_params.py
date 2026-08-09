import asyncio
import sys
from sqlalchemy import text
from app.core.database import async_session_factory


async def migrate():
    async with async_session_factory() as db:
        conn = await db.connection()
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS indicator_param (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                indicator_id INTEGER NOT NULL REFERENCES indicator_dict(id),
                param_key VARCHAR(80) NOT NULL,
                param_name VARCHAR(100) DEFAULT '',
                param_value VARCHAR(500) DEFAULT '',
                param_type VARCHAR(20) DEFAULT '通用测试参数',
                remark TEXT DEFAULT '',
                status INTEGER DEFAULT 1
            )
        """))
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS bom_indicator_param (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bom_indicator_id INTEGER NOT NULL REFERENCES bom_indicator(id),
                param_key VARCHAR(80) NOT NULL,
                param_name VARCHAR(100) DEFAULT '',
                param_value VARCHAR(500) DEFAULT '',
                param_type VARCHAR(20) DEFAULT '通用测试参数',
                remark TEXT DEFAULT ''
            )
        """))
        await db.commit()
        print("Tables indicator_param / bom_indicator_param created OK")


if __name__ == "__main__":
    asyncio.run(migrate())
