"""
WebSocket 连接管理器 — 支持 Redis PubSub 跨实例广播
对应 design.md §12
"""
import asyncio
import json
import time
from typing import Dict, Set, Optional, Callable

from fastapi import WebSocket
from redis.asyncio import Redis

from app.config import get_settings
from app.core.redis import get_redis_pool

settings = get_settings()

WS_CHANNEL_PREFIX = "ws:"


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self._heartbeat_interval = 25
        self._idle_timeout = 300
        self._last_active: Dict[int, float] = {}
        self._redis_pubsub_task: Optional[asyncio.Task] = None
        self._redis_pool = None

    async def connect(self, channel: str, websocket: WebSocket):
        await websocket.accept()
        if channel not in self.active_connections:
            self.active_connections[channel] = set()
        self.active_connections[channel].add(websocket)
        self._last_active[id(websocket)] = time.time()

    def disconnect(self, channel: str, websocket: WebSocket):
        if channel in self.active_connections:
            self.active_connections[channel].discard(websocket)
            if not self.active_connections[channel]:
                del self.active_connections[channel]
        self._last_active.pop(id(websocket), None)

    async def broadcast(self, channel: str, event: str, data: dict):
        """本地广播（单实例内所有连接）"""
        payload = json.dumps({"event": event, "data": data})
        if channel in self.active_connections:
            stale = set()
            for ws in self.active_connections[channel]:
                try:
                    await ws.send_text(payload)
                except Exception:
                    stale.add(ws)
            for ws in stale:
                self.disconnect(channel, ws)

    async def broadcast_all(self, event: str, data: dict):
        """广播到所有连接"""
        for channel in list(self.active_connections.keys()):
            await self.broadcast(channel, event, data)

    async def send_personal(self, websocket: WebSocket, event: str, data: dict):
        try:
            await websocket.send_text(json.dumps({"event": event, "data": data}))
        except Exception:
            pass

    async def heartbeat(self, websocket: WebSocket):
        """发送心跳 ping"""
        while True:
            try:
                await asyncio.sleep(self._heartbeat_interval)
                await websocket.send_text(json.dumps({"event": "ping"}))
            except Exception:
                break

    def update_activity(self, websocket: WebSocket):
        self._last_active[id(websocket)] = time.time()

    async def cleanup_idle(self):
        """清理空闲超时连接"""
        while True:
            await asyncio.sleep(60)
            now = time.time()
            for channel in list(self.active_connections.keys()):
                stale = set()
                for ws in self.active_connections[channel]:
                    last = self._last_active.get(id(ws), 0)
                    if now - last > self._idle_timeout:
                        stale.add(ws)
                for ws in stale:
                    self.disconnect(channel, ws)

    # ── Redis PubSub ──
    async def publish_redis(self, channel: str, event: str, data: dict):
        """发布事件到 Redis PubSub（跨实例广播）"""
        pool = get_redis_pool()
        async with Redis(connection_pool=pool) as r:
            payload = json.dumps({"event": event, "data": data, "channel": channel})
            await r.publish(f"{WS_CHANNEL_PREFIX}{channel}", payload)

    async def _redis_subscriber(self):
        """后台任务：订阅 Redis PubSub，转发到本地连接（断线自动重连）"""
        while True:
            try:
                pool = get_redis_pool()
                async with Redis(connection_pool=pool) as r:
                    pubsub = r.pubsub()
                    await pubsub.psubscribe(f"{WS_CHANNEL_PREFIX}*")

                    async for message in pubsub.listen():
                        if message["type"] != "pmessage":
                            continue
                        try:
                            payload = json.loads(message["data"])
                            event = payload.get("event")
                            data = payload.get("data")
                            channel = payload.get("channel", "")
                            if channel:
                                await self.broadcast(channel, event, data)
                        except (json.JSONDecodeError, KeyError):
                            continue
            except asyncio.CancelledError:
                raise
            except Exception:
                await asyncio.sleep(3)

    async def start_redis_listener(self):
        if self._redis_pubsub_task is None or self._redis_pubsub_task.done():
            self._redis_pubsub_task = asyncio.create_task(self._redis_subscriber())
            # Also start cleanup task
            asyncio.create_task(self.cleanup_idle())

    async def stop_redis_listener(self):
        if self._redis_pubsub_task and not self._redis_pubsub_task.done():
            self._redis_pubsub_task.cancel()
            try:
                await self._redis_pubsub_task
            except asyncio.CancelledError:
                pass

    # ── Channel helpers ──
    @staticmethod
    def get_channel_for_station(station_id: int) -> str:
        return f"station:{station_id}"

    @staticmethod
    def get_channel_for_slot(slot_id: int) -> str:
        return f"slot:{slot_id}"

    @staticmethod
    def get_channel_global() -> str:
        return "global"


_manager: Optional[ConnectionManager] = None


def get_manager() -> ConnectionManager:
    global _manager
    if _manager is None:
        _manager = ConnectionManager()
    return _manager
