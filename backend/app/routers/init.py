"""
系统初始化 API
对应 design.md §5.1, §5.2, §11
"""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps.db_deps import get_db
from app.deps.auth_deps import get_current_user, require_developer, require_super_admin
from app.core.response import success
from app.core.exceptions import BusinessException
from app.models.station import Factory

router = APIRouter(tags=["系统初始化"])


@router.post("", dependencies=[Depends(require_developer)])
async def initialize(db: AsyncSession = Depends(get_db)):
    """初始化系统（创建默认数据）"""
    r = await db.execute(select(Factory).limit(1))
    if r.scalar_one_or_none():
        raise BusinessException(400, "系统已初始化")
    from scripts.seed_data import seed
    await seed()
    return success(message="系统初始化成功")


@router.post("/reset", dependencies=[Depends(require_super_admin)])
async def reset(db: AsyncSession = Depends(get_db)):
    """重置系统（清空所有数据）"""
    from app.core.database import engine, Base
    from app.core.security import hash_password
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    # Re-create the super_admin user so login still works after reset
    from app.core.database import AsyncSessionLocal
    from app.models.user import User
    async with AsyncSessionLocal() as session:
        admin = User(
            username="admin", display_name="超级管理员",
            password_hash=hash_password("admin123"), role="super_admin",
            registration_status="active",
        )
        session.add(admin)
        await session.commit()
    return success(message="系统已重置")


@router.get("/status")
async def init_status(db: AsyncSession = Depends(get_db)):
    """查询系统初始化状态"""
    from app.models.user import User
    r = await db.execute(select(User).limit(1))
    user_exists = r.scalar_one_or_none() is not None
    r2 = await db.execute(select(Factory).limit(1))
    factory_exists = r2.scalar_one_or_none() is not None
    return success(data={
        "initialized": user_exists and factory_exists,
        "has_users": user_exists,
        "has_factories": factory_exists,
    })


@router.post("/sample", dependencies=[Depends(require_developer)])
async def init_sample_data(db: AsyncSession = Depends(get_db)):
    """创建示例数据"""
    from scripts.seed_data import seed
    await seed()
    return success(message="示例数据创建成功")
