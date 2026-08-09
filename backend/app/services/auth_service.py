import json
import logging
from datetime import datetime
from time import time
from typing import Optional, Dict, List

from sqlalchemy import select, delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from app.models.user import User
from app.models.registration import AccountRegistration
from app.models.permission import UserDomain, AuditLog
from app.core.security import hash_password, verify_password, generate_session_id
from app.core.exceptions import AuthError, ForbiddenError, NotFoundError, ConflictError
from app.config import ROLE_HIERARCHY, ROLE_LABELS, get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_IS_DEV = settings.APP_ENV == "dev"
_memory_sessions: Dict[str, dict] = {}
_memory_ttl: Dict[str, float] = {}


async def _redis_setex(redis: Redis, key: str, ttl: int, value: str):
    try:
        await redis.setex(key, ttl, value)
    except Exception as e:
        if _IS_DEV:
            logger.warning("Redis unavailable, falling back to memory (dev only): %s", e)
            _memory_sessions[key] = json.loads(value)
            _memory_ttl[key] = time() + ttl
        else:
            raise AuthError("会话服务不可用，请稍后重试") from e


async def _redis_get(redis: Redis, key: str) -> Optional[str]:
    try:
        return await redis.get(key)
    except Exception as e:
        if _IS_DEV:
            logger.warning("Redis unavailable, reading from memory fallback: %s", e)
            data = _memory_sessions.get(key)
            if not data:
                return None
            if _memory_ttl.get(key, 0) < time():
                _memory_sessions.pop(key, None)
                _memory_ttl.pop(key, None)
                return None
            return json.dumps(data, ensure_ascii=False)
        else:
            raise AuthError("会话服务不可用") from e


async def _redis_delete(redis: Redis, key: str):
    try:
        await redis.delete(key)
    except Exception as e:
        if _IS_DEV:
            _memory_sessions.pop(key, None)
            _memory_ttl.pop(key, None)
        else:
            raise AuthError("会话服务不可用") from e


def _get_user_domains(user: dict, db_domains: list = None) -> List[str]:
    """获取用户的域列表（从会话数据或数据库）"""
    if db_domains is not None:
        return db_domains
    return user.get("domains", [])


class AuthService:

    @staticmethod
    async def login(db: AsyncSession, redis: Redis, username: str, password: str) -> tuple[dict, str]:
        result = await db.execute(select(User).where(User.username == username))
        user = result.scalar_one_or_none()
        if not user or not verify_password(password, user.password_hash):
            raise AuthError("用户名或密码错误")
        if not user.is_active:
            raise AuthError("账号已禁用")
        if user.registration_status == "pending":
            raise AuthError("账号待审核中，请联系管理员")

        user.last_login = datetime.utcnow()
        await db.flush()

        session_id = generate_session_id()
        user_data = {
            "id": user.id,
            "username": user.username,
            "display_name": user.display_name,
            "role": user.role,
            "role_label": ROLE_LABELS.get(user.role, user.role),
            "is_active": user.is_active,
            "domains": user.domains or [],
        }
        await _redis_setex(
            redis,
            f"session:{session_id}",
            settings.SESSION_TTL_SECONDS,
            json.dumps(user_data, ensure_ascii=False),
        )
        return user_data, session_id

    @staticmethod
    async def logout(redis: Redis, session_id: Optional[str]):
        if session_id:
            await _redis_delete(redis, f"session:{session_id}")

    @staticmethod
    async def get_current_user(redis: Redis, session_id: Optional[str]) -> dict:
        if not session_id:
            raise AuthError("未登录")
        data = await _redis_get(redis, f"session:{session_id}")
        if not data:
            raise AuthError("会话已过期")
        return json.loads(data)

    @staticmethod
    async def list_users(db: AsyncSession, page: int = 1, page_size: int = 20, *,
                         role_filter: str = None, status_filter: str = None) -> tuple[list[User], int]:
        stmt = select(User)
        if role_filter:
            stmt = stmt.where(User.role == role_filter)
        if status_filter == "active":
            stmt = stmt.where(User.is_active == True)
        elif status_filter == "inactive":
            stmt = stmt.where(User.is_active == False)
        stmt = stmt.order_by(User.id)
        result = await db.execute(stmt)
        all_users = result.scalars().all()
        total = len(all_users)
        users = all_users[(page - 1) * page_size: page * page_size]
        return list(users), total

    @staticmethod
    async def create_user(db: AsyncSession, username: str, display_name: str, password: str,
                          role: str = "operator", domains: List[str] = None,
                          created_by: str = None, is_active: bool = True,
                          department: str = "") -> User:
        existing = await db.execute(select(User).where(User.username == username))
        if existing.scalar_one_or_none():
            raise ConflictError("用户名已存在")
        user = User(
            username=username,
            display_name=display_name,
            password_hash=hash_password(password),
            role=role,
            is_active=is_active,
            domains=domains or [],
            department=department,
            created_by=created_by,
            registration_status="active",
        )
        db.add(user)
        await db.flush()
        return user

    @staticmethod
    async def update_user(db: AsyncSession, user_id: int, data: dict) -> User:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise NotFoundError("用户不存在")
        if "display_name" in data:
            user.display_name = data["display_name"]
        if "password" in data and data["password"]:
            user.password_hash = hash_password(data["password"])
        if "role" in data:
            user.role = data["role"]
        if "is_active" in data:
            user.is_active = data["is_active"]
        if "domains" in data:
            user.domains = data["domains"]
        if "department" in data:
            user.department = data.get("department") or ""
        await db.flush()
        return user

    @staticmethod
    async def delete_user(db: AsyncSession, user_id: int):
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise NotFoundError("用户不存在")
        await db.delete(user)
        await db.flush()

    @staticmethod
    async def reset_password(db: AsyncSession, user_id: int, new_password: str) -> User:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise NotFoundError("用户不存在")
        user.password_hash = hash_password(new_password)
        await db.flush()
        return user

    @staticmethod
    def check_role(user_role: str, min_role: str):
        user_level = ROLE_HIERARCHY.get(user_role, 0)
        min_level = ROLE_HIERARCHY.get(min_role, 0)
        if user_level < min_level:
            raise ForbiddenError(f"需要 {min_role} 及以上权限")

    @staticmethod
    async def check_domain_access(user: dict, required_domain: str) -> bool:
        """检查用户是否具有指定领域的访问权限"""
        if user.get("role") == "super_admin":
            return True
        if not required_domain:
            return True
        user_domains = user.get("domains", []) or []
        return required_domain in user_domains

    # ── Account Registration ──

    @staticmethod
    async def register(db: AsyncSession, username: str, display_name: str, password: str,
                        department: str, requested_role: str, requested_domains: List[str],
                        justification: str = None) -> AccountRegistration:
        existing_user = await db.execute(select(User).where(User.username == username))
        if existing_user.scalar_one_or_none():
            raise ConflictError("用户名已存在，请直接登录")
        existing_reg = await db.execute(select(AccountRegistration).where(AccountRegistration.username == username))
        if existing_reg.scalar_one_or_none():
            raise ConflictError("注册申请已提交，请等待审核")
        reg = AccountRegistration(
            username=username,
            display_name=display_name,
            password_hash=hash_password(password),
            department=department,
            requested_role=requested_role,
            requested_domains=requested_domains,
            justification=justification,
        )
        db.add(reg)
        await db.flush()
        return reg

    @staticmethod
    async def list_registrations(db: AsyncSession, status: str = "pending",
                                  page: int = 1, page_size: int = 20) -> tuple[List[AccountRegistration], int]:
        stmt = select(AccountRegistration)
        if status:
            stmt = stmt.where(AccountRegistration.status == status)
        stmt = stmt.order_by(AccountRegistration.created_at.desc())
        result = await db.execute(stmt)
        all_regs = result.scalars().all()
        total = len(all_regs)
        regs = all_regs[(page - 1) * page_size: page * page_size]
        return regs, total

    @staticmethod
    async def approve_registration(db: AsyncSession, reg_id: int, reviewer_id: int,
                                    reviewer_name: str, comment: str = None,
                                    approved_domains: List[str] = None) -> User:
        result = await db.execute(select(AccountRegistration).where(AccountRegistration.id == reg_id))
        reg = result.scalar_one_or_none()
        if not reg:
            raise NotFoundError("注册申请不存在")
        if reg.status != "pending":
            raise ConflictError("该申请已审核")

        # Validate requested role exists
        if reg.requested_role not in ROLE_HIERARCHY:
            raise ConflictError(f"请求的角色 {reg.requested_role} 不存在")

        # Determine final domains - use approved_domains if provided, else use requested_domains
        final_domains = approved_domains if approved_domains is not None else (reg.requested_domains or [])

        # Check if username is still available
        existing = await db.execute(select(User).where(User.username == reg.username))
        if existing.scalar_one_or_none():
            reg.status = "rejected"
            reg.review_comment = f"审核失败：用户名已存在 - {comment}"
            await db.flush()
            raise ConflictError("用户名已存在，审核失败")

        user = User(
            username=reg.username,
            display_name=reg.display_name,
            password_hash=reg.password_hash,
            role=reg.requested_role,
            is_active=True,
            domains=final_domains,
            created_by=reviewer_name,
            registration_status="active",
        )
        db.add(user)
        reg.status = "approved"
        reg.reviewer_id = reviewer_id
        reg.reviewed_at = datetime.utcnow()
        reg.review_comment = comment
        await db.flush()
        return user

    @staticmethod
    async def reject_registration(db: AsyncSession, reg_id: int, reviewer_id: int,
                                   comment: str = None) -> AccountRegistration:
        result = await db.execute(select(AccountRegistration).where(AccountRegistration.id == reg_id))
        reg = result.scalar_one_or_none()
        if not reg:
            raise NotFoundError("注册申请不存在")
        if reg.status != "pending":
            raise ConflictError("该申请已审核")
        reg.status = "rejected"
        reg.reviewer_id = reviewer_id
        reg.reviewed_at = datetime.utcnow()
        reg.review_comment = comment
        await db.flush()
        return reg

    # ── Domain Management ──

    @staticmethod
    async def update_user_domains(db: AsyncSession, user_id: int, domains: List[str]) -> User:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise NotFoundError("用户不存在")
        user.domains = domains
        await db.flush()
        return user

    @staticmethod
    async def get_user_domains(db: AsyncSession, user_id: int) -> List[str]:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise NotFoundError("用户不存在")
        return user.domains or []

    # ── Audit Log ──

    @staticmethod
    async def log_audit(db: AsyncSession, user_id: int, username: str, action: str,
                         resource_type: str = None, resource_id: str = None,
                         detail: dict = None, ip_address: str = None):
        entry = AuditLog(
            user_id=user_id,
            username=username,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            detail=detail,
            ip_address=ip_address,
        )
        db.add(entry)
        await db.flush()
        return entry

    @staticmethod
    async def list_audit_logs(db: AsyncSession, page: int = 1, page_size: int = 20,
                               action: str = None, resource_type: str = None,
                               user_id: int = None) -> tuple[List[AuditLog], int]:
        from app.utils.pagination import paginate
        stmt = select(AuditLog).order_by(AuditLog.created_at.desc())
        if action:
            stmt = stmt.where(AuditLog.action == action)
        if resource_type:
            stmt = stmt.where(AuditLog.resource_type == resource_type)
        if user_id:
            stmt = stmt.where(AuditLog.user_id == user_id)
        items, total, _, _ = await paginate(db, stmt, page, page_size)
        return items, total
