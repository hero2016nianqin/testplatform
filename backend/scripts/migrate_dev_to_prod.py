"""将开发环境(SQLite)业务数据复制到生产环境(PostgreSQL)。

- 业务主表/装备表/日志表：以 SQLite 为准，清空 PG 后按原 ID 复制
- users：合并（保留 PG 已有账号，仅插入 SQLite 中不存在的用户名）
用法: python -m scripts.migrate_dev_to_prod
"""
import asyncio
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

SQLITE_URL = "sqlite+aiosqlite:///../database/test_platform.db"
PG_URL = "postgresql+asyncpg://testplatform:testplatform123@localhost:5432/testplatform"

SQLITE = create_async_engine(SQLITE_URL)
PG = create_async_engine(PG_URL)

# PG 中为 Boolean 的列（SQLite 存 0/1 整数，需转 bool）
BOOL_COLUMNS = {
    "is_active", "is_critical", "has_settings", "passed",
    "auto_load_enabled", "debug_mode_enabled", "process_control_enabled",
    "test_mode_normal", "test_mode_verify", "test_mode_calibration",
    "barcode_verify_enabled",
}

# 以 SQLite 为准的表（清空 PG 后按 ID 复制）
# 复制顺序按外键依赖：先父表后子表
COPY_TABLES = [
    "indicator_dict", "test_item_collection",
    "bom_config", "collection_test_item",
    "factories", "production_lines", "equipment_definitions",
    "test_stations", "cabinets", "test_chassis", "test_slots",
    "equipment_configs", "equipment_metrics", "equipment_property_pages",
    "scenario_configs", "software_configs",
    "bom_indicator", "test_item_indicator",
    "param_change_log", "indicator_version_snapshot", "bom_review_event",
    "bom_domain_owner", "audit_log",
]


def _fix(value):
    """将 SQLite 的文本转成 PG/asyncpg 需要的类型：
    - 日期时间文本 → datetime 对象
    - JSON 文本原样保留（PG jsonb 列直接解析）
    """
    if isinstance(value, str):
        s = value.strip()
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f",
                    "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%d"):
            try:
                return datetime.strptime(s, fmt)
            except ValueError:
                continue
    return value


async def main():
    table_list = ", ".join(f'"{t}"' for t in COPY_TABLES)
    async with PG.begin() as pg:
        await pg.execute(text(f"TRUNCATE {table_list} CASCADE"))
        print("PG 业务表已清空")

    copied = {}
    async with SQLITE.connect() as s:
        for t in COPY_TABLES:
            cols = (await s.execute(text(f'SELECT * FROM "{t}" LIMIT 0'))).keys()
            rows = (await s.execute(text(f'SELECT * FROM "{t}"'))).fetchall()
            if not rows:
                copied[t] = 0
                continue
            placeholders = ",".join(":" + c for c in cols)
            col_str = ",".join(cols)
            async with PG.begin() as pg:
                for row in rows:
                    data = {c: _fix(v) for c, v in zip(cols, row)}
                    for bc in BOOL_COLUMNS:
                        if bc in data and isinstance(data[bc], int):
                            data[bc] = bool(data[bc])
                    await pg.execute(
                        text(f'INSERT INTO "{t}" ({col_str}) VALUES ({placeholders})'),
                        data,
                    )
            copied[t] = len(rows)
            print(f"  {t}: {len(rows)}")

    # users 合并：插入 SQLite 中存在、PG 中不存在的账号
    pg_users = set()
    async with PG.connect() as pg:
        r = await pg.execute(text("SELECT username FROM users"))
        pg_users = {row[0] for row in r.fetchall()}
    added_users = 0
    async with SQLITE.connect() as s:
        cols = (await s.execute(text('SELECT * FROM "users" LIMIT 0'))).keys()
        rows = (await s.execute(text('SELECT * FROM "users"'))).fetchall()
        async with PG.begin() as pg:
            for row in rows:
                data = dict(zip(cols, row))
                if data["username"] in pg_users:
                    continue
                # 不指定 id，由 PG 自增
                insert_cols = [c for c in cols if c != "id"]
                placeholders = ",".join(":" + c for c in insert_cols)
                col_str = ",".join(insert_cols)
                user_data = {c: _fix(data[c]) for c in insert_cols}
                for bc in BOOL_COLUMNS:
                    if bc in user_data and isinstance(user_data[bc], int):
                        user_data[bc] = bool(user_data[bc])
                await pg.execute(
                    text(f"INSERT INTO users ({col_str}) VALUES ({placeholders})"),
                    user_data,
                )
                added_users += 1
                pg_users.add(data["username"])
    print(f"  users 新增: {added_users}")

    await SQLITE.dispose()
    await PG.dispose()
    print("迁移完成:", copied, "users +" + str(added_users))


if __name__ == "__main__":
    asyncio.run(main())
