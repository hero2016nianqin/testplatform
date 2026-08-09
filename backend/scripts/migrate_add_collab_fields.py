import asyncio
import aiosqlite
import os

DB_PATH = "/Users/yyj/Documents/test_platform_flask所有功能ok_副本/database/test_platform.db"


async def migrate():
    async with aiosqlite.connect(DB_PATH) as db:
        # 1. collection_test_item 增加 item_revision, owner_id, owner_name
        await db.execute("""
            ALTER TABLE collection_test_item 
            ADD COLUMN item_revision INTEGER DEFAULT 0
        """)
        await db.execute("""
            ALTER TABLE collection_test_item 
            ADD COLUMN owner_id INTEGER
        """)
        await db.execute("""
            ALTER TABLE collection_test_item 
            ADD COLUMN owner_name VARCHAR(100)
        """)

        # 2. bom_indicator 增加 item_revision, owner_id, owner_name
        await db.execute("""
            ALTER TABLE bom_indicator 
            ADD COLUMN item_revision INTEGER DEFAULT 0
        """)
        await db.execute("""
            ALTER TABLE bom_indicator 
            ADD COLUMN owner_id INTEGER
        """)
        await db.execute("""
            ALTER TABLE bom_indicator 
            ADD COLUMN owner_name VARCHAR(100)
        """)

        # 3. 创建参数变更日志表
        await db.execute("""
            CREATE TABLE IF NOT EXISTS param_change_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bom_code VARCHAR(100) NOT NULL,
                bom_config_id INTEGER NOT NULL,
                bom_version INTEGER NOT NULL,
                test_item_id INTEGER NOT NULL,
                test_item_name VARCHAR(200) DEFAULT '',
                indicator_id INTEGER NOT NULL,
                indicator_code VARCHAR(50) DEFAULT '',
                indicator_name VARCHAR(200) DEFAULT '',
                param_key VARCHAR(100) DEFAULT '',
                param_name VARCHAR(200) DEFAULT '',
                old_value TEXT,
                new_value TEXT,
                operator_id INTEGER,
                operator_name VARCHAR(100) DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_param_change_log_bom_code ON param_change_log(bom_code)
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_param_change_log_config_id ON param_change_log(bom_config_id)
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_param_change_log_test_item ON param_change_log(test_item_id)
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_param_change_log_created_at ON param_change_log(created_at)
        """)

        await db.commit()
        print("Collaborative editing fields and param_change_log table created OK")


if __name__ == "__main__":
    asyncio.run(migrate())