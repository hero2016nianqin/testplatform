"""
WebSocket 事件处理器 — 支持 Redis PubSub 跨实例广播
对应 design.md §12 — 4 事件: run_started/item_tested/run_completed/run_failed
"""
from app.config import (
    WS_EVENT_RUN_STARTED, WS_EVENT_ITEM_TESTED,
    WS_EVENT_RUN_COMPLETED, WS_EVENT_RUN_FAILED,
)
from app.ws.manager import get_manager

manager = get_manager()


async def notify_run_started(station_id: int, data: dict):
    channel = manager.get_channel_for_station(station_id)
    await manager.publish_redis(channel, WS_EVENT_RUN_STARTED, data)


async def notify_item_tested(station_id: int, data: dict):
    channel = manager.get_channel_for_station(station_id)
    await manager.publish_redis(channel, WS_EVENT_ITEM_TESTED, data)


async def notify_run_completed(station_id: int, data: dict):
    channel = manager.get_channel_for_station(station_id)
    await manager.publish_redis(channel, WS_EVENT_RUN_COMPLETED, data)


async def notify_run_failed(station_id: int, data: dict):
    channel = manager.get_channel_for_station(station_id)
    await manager.publish_redis(channel, WS_EVENT_RUN_FAILED, data)
