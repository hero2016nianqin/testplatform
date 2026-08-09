"""
数据库初始化脚本
用法: python -m scripts.init_db
"""
import asyncio
from app.core.database import engine, Base, AsyncSessionLocal
from app.models import *


async def init_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("All tables created successfully.")


async def drop_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    print("All tables dropped successfully.")


if __name__ == "__main__":
    import sys
    if "--drop" in sys.argv:
        asyncio.run(drop_database())
    asyncio.run(init_database())
