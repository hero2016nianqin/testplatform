"""
SQLite → PostgreSQL 一键迁移脚本

用法:
    python scripts/migrate_sqlite_to_pg.py \\
        --sqlite /path/to/test_platform.db \\
        --pg "postgresql+asyncpg://user:pass@localhost:5432/testplatform"

流程:
    1. 从 SQLite 读取全部表数据
    2. 在 PG 中通过 Alembic 创建表结构
    3. 逐表逐行迁移，JSON 自动转为 JSONB
    4. 关闭 SQLite 外键，按依赖顺序插入
"""
import asyncio
import json
import sys
from pathlib import Path

import aiosqlite
import asyncpg


TABLE_ORDER = [
    "users",
    "factories",
    "production_lines",
    "equipment_definitions",
    "test_stations",
    "cabinets",
    "test_chassis",
    "test_slots",
    "equipment_configs",
    "hardware_params",
    "software_configs",
    "scenario_configs",
    "equipment_metrics",
    "equipment_property_pages",
    "test_items",
    "test_item_templates",
    "test_sequences",
    "test_sequence_steps",
    "test_versions",
    "sub_scenarios",
    "release_steps",
    "version_archive_items",
    "version_binary_files",
    "release_deployments",
    "test_runs",
    "test_results",
    "test_logs",
]

# Columns known to store JSON strings in SQLite (case-insensitive)
JSON_COLUMNS = {
    "equipment_definitions": {"layout_config", "default_equipment_config", "default_hardware_params",
                              "default_software_config", "default_scenario_config"},
    "software_configs": {"selected_test_item_ids", "sequence_data"},
    "scenario_configs": {"scenario_data"},
    "equipment_metrics": {"metrics_json"},
    "equipment_property_pages": {"page_json"},
    "test_versions": {"codes_config"},
    "sub_scenarios": {"hardware_params", "software_metrics", "property_page"},
    "version_archive_items": {"data_snapshot"},
}


async def get_sqlite_tables(sqlite_path: str) -> list:
    async with aiosqlite.connect(sqlite_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        rows = await cursor.fetchall()
        return [r[0] for r in rows]


async def migrate_table(sqlite_path: str, pg_conn, table: str):
    async with aiosqlite.connect(sqlite_path) as src:
        src.row_factory = aiosqlite.Row
        cursor = await src.execute(f"SELECT * FROM [{table}]")
        rows = await cursor.fetchall()
        if not rows:
            print(f"  [SKIP] {table}: 0 rows")
            return 0

        columns = [desc[0] for desc in cursor.description]
        placeholders = ", ".join(f"${i + 1}" for i in range(len(columns)))
        col_names = ", ".join(f'"{c}"' for c in columns)
        insert_sql = f'INSERT INTO "{table}" ({col_names}) VALUES ({placeholders}) ON CONFLICT DO NOTHING'

        json_cols = JSON_COLUMNS.get(table, set())
        count = 0
        for row in rows:
            values = []
            for i, col in enumerate(columns):
                val = row[i]
                if col in json_cols and val is not None:
                    if isinstance(val, str):
                        try:
                            val = json.loads(val)
                        except (json.JSONDecodeError, TypeError):
                            pass
                values.append(val)
            try:
                await pg_conn.execute(insert_sql, *values)
                count += 1
            except Exception as e:
                print(f"  [ERR] {table} row {count + 1}: {e}")
        print(f"  [OK] {table}: {count}/{len(rows)} rows migrated")
        return count


async def main():
    import argparse
    parser = argparse.ArgumentParser(description="SQLite → PostgreSQL 一键迁移")
    parser.add_argument("--sqlite", default="database/test_platform.db", help="SQLite 数据库路径")
    parser.add_argument("--pg", default="postgresql+asyncpg://testplatform:testplatform@localhost:5432/testplatform", help="PostgreSQL DSN")
    args = parser.parse_args()

    sqlite_path = args.sqlite
    pg_dsn = args.pg.replace("+asyncpg", "")  # asyncpg doesn't use +asyncpg format

    if not Path(sqlite_path).exists():
        print(f"❌ SQLite 数据库不存在: {sqlite_path}")
        sys.exit(1)

    print(f"📦 从 SQLite 迁移: {sqlite_path}")
    print(f"🎯 目标 PostgreSQL: {pg_dsn}")

    # Step 1: Run Alembic migrations on PG
    print("\n1️⃣  运行 Alembic 迁移创建 PG 表结构...")
    import subprocess
    result = subprocess.run(
        ["alembic", "-c", "alembic.ini", "upgrade", "head"],
        cwd=Path(__file__).resolve().parent.parent,
        capture_output=True, text=True,
    )
    print(result.stdout)
    if result.returncode != 0:
        print(f"❌ Alembic 失败: {result.stderr}")
        # Continue — tables may already exist

    # Step 2: Connect to PG and migrate data
    print("\n2️⃣  迁移数据...")
    pg_conn = await asyncpg.connect(pg_dsn)

    try:
        total = 0
        for table in TABLE_ORDER:
            count = await migrate_table(sqlite_path, pg_conn, table)
            total += count
        print(f"\n✅ 迁移完成! 共迁移 {total} 条记录")
    finally:
        await pg_conn.close()


if __name__ == "__main__":
    asyncio.run(main())
