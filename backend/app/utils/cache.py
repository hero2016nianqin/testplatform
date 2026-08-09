import json
from functools import wraps
from typing import Optional, Callable
from redis.asyncio import Redis

from app.core.redis import get_redis_pool


def redis_cache(prefix: str, ttl: int = 60):
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            pool = get_redis_pool()
            async with Redis(connection_pool=pool) as r:
                parts = [prefix]
                for k, v in kwargs.items():
                    if k not in ("db", "redis", "request"):
                        parts.append(f"{k}={v}")
                cache_key = ":".join(parts)
                cached = await r.get(cache_key)
                if cached is not None:
                    return json.loads(cached)
                result = await func(*args, **kwargs)
                await r.setex(cache_key, ttl, json.dumps(result, default=str))
                return result
        return wrapper
    return decorator


def invalidate_cache(prefix: str, pattern: Optional[str] = None):
    async def invalidator(*args, **kwargs):
        pool = get_redis_pool()
        async with Redis(connection_pool=pool) as r:
            key_pattern = f"{prefix}:*" if pattern is None else f"{prefix}:{pattern}" if pattern else f"{prefix}:*"
            keys = await r.keys(key_pattern)
            if keys:
                await r.delete(*keys)
    return invalidator
