from typing import List, Optional
from fastapi import Depends, Request
from redis.asyncio import Redis
from time import time

from app.config import ROLE_HIERARCHY
from app.core.exceptions import AuthError, ForbiddenError
from app.core.redis import get_redis
from app.config import get_settings
from app.services.auth_service import _redis_get

settings = get_settings()

_CACHE_TTL = 30
_user_cache: dict[str, tuple[float, dict]] = {}


async def get_current_user(
    request: Request,
    redis: Redis = Depends(get_redis),
) -> dict:
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise AuthError("未登录")
    now = time()
    cached = _user_cache.get(session_id)
    if cached and now - cached[0] < _CACHE_TTL:
        return cached[1]
    data = await _redis_get(redis, f"session:{session_id}")
    if not data:
        _user_cache.pop(session_id, None)
        raise AuthError("会话已过期，请重新登录")
    import json
    user = json.loads(data)
    _user_cache[session_id] = (now, user)
    request.state.user = user
    return user


def require_roles(min_role: str):
    async def role_checker(user: dict = Depends(get_current_user)):
        user_role_level = ROLE_HIERARCHY.get(user.get("role", "operator"), 0)
        min_level = ROLE_HIERARCHY.get(min_role, 0)
        if user_role_level < min_level:
            raise ForbiddenError(f"需要 {min_role} 及以上权限")
        return user
    return role_checker


def require_domain_access(required_domain: str):
    """检查用户是否具有指定领域的访问权限"""
    async def domain_checker(user: dict = Depends(get_current_user)):
        if user.get("role") == "super_admin":
            return user
        user_domains = user.get("domains", []) or []
        if required_domain in user_domains:
            return user
        raise ForbiddenError(f"无 {required_domain} 领域访问权限")
    return domain_checker


def require_domain_access_optional():
    """获取当前用户，如果有 domain 则验证领域权限（用于可选领域参数的接口）"""
    async def domain_checker(
        request: Request,
        user: dict = Depends(get_current_user),
    ):
        domain = request.query_params.get("domain")
        if domain:
            if user.get("role") == "super_admin":
                return user
            user_domains = user.get("domains", []) or []
            if domain in user_domains:
                return user
            raise ForbiddenError(f"无 {domain} 领域访问权限")
        return user
    return domain_checker


require_process = require_roles("process")
require_developer = require_roles("developer")
require_super_admin = require_roles("super_admin")
