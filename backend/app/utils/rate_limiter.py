"""
Redis-based rate limiter (sliding window)
Usage: @router.get("/path", dependencies=[Depends(rate_limit("api", max_requests=100, window_seconds=60))])
"""
import time
from typing import Optional
from fastapi import Request, Depends
from redis.asyncio import Redis

from app.core.exceptions import BusinessException
from app.core.redis import get_redis


def rate_limit(
    prefix: str = "rl",
    max_requests: int = 100,
    window_seconds: int = 60,
):
    """Rate limiter dependency factory.

    Usage:
        @router.get("/items", dependencies=[Depends(rate_limit("items", 100, 60))])
    """
    async def _rate_limiter(request: Request, r: Redis = Depends(get_redis)):
        forwarded = request.headers.get("X-Forwarded-For", "")
        client_ip = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "unknown")
        key = f"{prefix}:{client_ip}"
        now = int(time.time())
        window_key = f"{key}:{now - (now % window_seconds)}"

        try:
            current = await r.get(window_key)
            if current is None:
                await r.setex(window_key, window_seconds + 1, 1)
                current_count = 1
            else:
                current_count = await r.incr(window_key)
                await r.expire(window_key, window_seconds + 1)

            if int(current_count) > max_requests:
                raise BusinessException(
                    code=429,
                    message=f"请求过于频繁，{window_seconds}秒内最多{max_requests}次",
                )
        except BusinessException:
            raise
        except Exception:
            pass  # Redis down — allow through

    return _rate_limiter
