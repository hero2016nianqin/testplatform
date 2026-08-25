"""
WebSocket 事件处理器 — 支持 Redis PubSub 跨实例广播
对应 design.md §12 — 4 事件: run_started/item_tested/run_completed/run_failed
"""
from app.config import (
    WS_EVENT_RUN_STARTED, WS_EVENT_ITEM_TESTED,
    WS_EVENT_RUN_COMPLETED, WS_EVENT_RUN_FAILED,
)


def _safe_notify(coro_fn):
    """在 Celery fork 子进程中，manager 的 Redis 连接可能绑定到已关闭的 event loop。
    用 try/except 包裹，确保 WebSocket 通知失败不影响测试执行。"""
    import asyncio
    async def wrapper(*args, **kwargs):
        try:
            from app.ws.manager import get_manager
            mgr = get_manager()
            channel = mgr.get_channel_for_station(args[0])
            await mgr.publish_redis(channel, coro_fn, *args[1:])
        except Exception:
            pass
    return wrapper


async def notify_run_started(station_id: int, data: dict):
    try:
        from app.ws.manager import get_manager
        mgr = get_manager()
        channel = mgr.get_channel_for_station(station_id)
        await mgr.publish_redis(channel, WS_EVENT_RUN_STARTED, data)
    except Exception:
        pass


async def notify_item_tested(station_id: int, data: dict):
    try:
        from app.ws.manager import get_manager
        mgr = get_manager()
        channel = mgr.get_channel_for_station(station_id)
        await mgr.publish_redis(channel, WS_EVENT_ITEM_TESTED, data)
    except Exception:
        pass


async def notify_run_completed(station_id: int, data: dict):
    try:
        from app.ws.manager import get_manager
        mgr = get_manager()
        channel = mgr.get_channel_for_station(station_id)
        await mgr.publish_redis(channel, WS_EVENT_RUN_COMPLETED, data)
    except Exception:
        pass


async def notify_run_failed(station_id: int, data: dict):
    try:
        from app.ws.manager import get_manager
        mgr = get_manager()
        channel = mgr.get_channel_for_station(station_id)
        await mgr.publish_redis(channel, WS_EVENT_RUN_FAILED, data)
    except Exception:
        pass
