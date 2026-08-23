"""
槽位分布式锁 — 基于 Redis，防止同一槽位并发启动多个测试
"""
import time
from contextlib import asynccontextmanager
from typing import AsyncIterator

from redis.asyncio import Redis

from app.core.redis import get_redis_pool

# 键前缀 & 默认 TTL
_LOCK_PREFIX = "slot_lock:"
_DEFAULT_TTL = 600  # 10 分钟，覆盖最长测试时间


async def acquire_slot_lock(slot_id: int, ttl: int = _DEFAULT_TTL) -> tuple[bool, str]:
    """尝试获取槽位锁。返回 (成功, lock_token)"""
    pool = get_redis_pool()
    async with Redis(connection_pool=pool) as r:
        lock_key = f"{_LOCK_PREFIX}{slot_id}"
        lock_token = f"{slot_id}:{time.time_ns()}"
        # SET NX EX 原子操作
        acquired = await r.set(lock_key, lock_token, nx=True, ex=ttl)
        return bool(acquired), lock_token


async def release_slot_lock(slot_id: int, lock_token: str) -> bool:
    """释放槽位锁（仅当 token 匹配时才释放）"""
    pool = get_redis_pool()
    async with Redis(connection_pool=pool) as r:
        lock_key = f"{_LOCK_PREFIX}{slot_id}"
        # Lua 脚本保证原子性：比对 token 后删除
        script = """
        if redis.call('get', KEYS[1]) == ARGV[1] then
            return redis.call('del', KEYS[1])
        else
            return 0
        end
        """
        result = await r.eval(script, 1, lock_key, lock_token)
        return bool(result)


async def is_slot_locked(slot_id: int) -> bool:
    """检查槽位是否被锁定"""
    pool = get_redis_pool()
    async with Redis(connection_pool=pool) as r:
        lock_key = f"{_LOCK_PREFIX}{slot_id}"
        return bool(await r.exists(lock_key))


@asynccontextmanager
async def slot_lock(slot_id: int, ttl: int = _DEFAULT_TTL) -> AsyncIterator[str]:
    """上下文管理器：自动获取/释放槽位锁"""
    acquired, token = await acquire_slot_lock(slot_id, ttl)
    if not acquired:
        raise RuntimeError(f"槽位 {slot_id} 正在测试中，请稍后再试")
    try:
        yield token
    finally:
        await release_slot_lock(slot_id, token)
