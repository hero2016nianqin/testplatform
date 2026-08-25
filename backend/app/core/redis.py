from typing import AsyncIterator, Optional
from redis.asyncio import Redis, ConnectionPool

from app.config import get_settings

settings = get_settings()

_pool: Optional[ConnectionPool] = None


def get_redis_pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        _pool = ConnectionPool.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_keepalive=True,
            retry_on_timeout=True,
            max_connections=settings.REDIS_MAX_CONNECTIONS,
        )
    return _pool


def reset_redis_pool():
    """Celery fork 子进程重置连接池，避免使用父进程的已关闭 event loop 连接"""
    global _pool
    _pool = None


async def get_redis() -> AsyncIterator[Redis]:
    pool = get_redis_pool()
    r = Redis(connection_pool=pool)
    try:
        yield r
    finally:
        await r.aclose()
