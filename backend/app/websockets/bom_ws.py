from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, List, Optional
import json
import asyncio
from datetime import datetime

from redis.asyncio import Redis

from app.core.redis import get_redis_pool
from app.services.auth_service import AuthService

router = APIRouter(prefix="/ws", tags=["WebSocket"])

# ── 进程本地 websocket 连接表（无法序列化到 Redis） ──
# room_key -> {user_id: WebSocket}
_local_connections: Dict[str, Dict[int, WebSocket]] = {}

HEARTBEAT_INTERVAL = 30
EDIT_LOCK_TTL = 120  # 秒
BOM_CHANNEL_PREFIX = "bom:broadcast:"
ONLINE_USERS_KEY_PREFIX = "bom:online:"


def make_cell_key(test_item_id: int) -> str:
    return f"item:{test_item_id}"


def _lock_key(room_key: str, cell_key: str) -> str:
    return f"bom:lock:{room_key}:{cell_key}"


def _online_key(room_key: str) -> str:
    return f"{ONLINE_USERS_KEY_PREFIX}{room_key}"


def _channel_name(room_key: str) -> str:
    return f"{BOM_CHANNEL_PREFIX}{room_key}"


async def _redis() -> Redis:
    return Redis(connection_pool=get_redis_pool())


# ── 在线用户 Redis 操作 ──

async def _add_online_user(room_key: str, user_id: int, user_name: str):
    """将用户加入在线列表（Redis Hash，field=user_id，TTL 5 分钟，连接时续期）"""
    r = await _redis()
    try:
        key = _online_key(room_key)
        payload = json.dumps({
            "user_id": user_id,
            "user_name": user_name,
            "connected_at": datetime.utcnow().isoformat(),
        }, ensure_ascii=False)
        await r.hset(key, str(user_id), payload)
        await r.expire(key, 300)
    finally:
        await r.aclose()


async def _remove_online_user(room_key: str, user_id: int):
    r = await _redis()
    try:
        key = _online_key(room_key)
        await r.hdel(key, str(user_id))
        # 如果房间空了，删除 key
        if await r.hlen(key) == 0:
            await r.delete(key)
    finally:
        await r.aclose()


async def _refresh_online_ttl(room_key: str):
    r = await _redis()
    try:
        key = _online_key(room_key)
        await r.expire(key, 300)
    finally:
        await r.aclose()


async def get_online_users(room_key: str) -> List[dict]:
    """获取房间内在线用户列表（Redis，跨实例）"""
    r = await _redis()
    try:
        key = _online_key(room_key)
        all_vals = await r.hvals(key)
        return [json.loads(v) for v in all_vals]
    finally:
        await r.aclose()


# ── 编辑锁操作（已有，保持不变） ──

async def acquire_edit_lock(room_key: str, cell_key: str, user_id: int, user_name: str) -> Optional[dict]:
    r = await _redis()
    try:
        key = _lock_key(room_key, cell_key)
        payload = json.dumps({
            "user_id": user_id,
            "user_name": user_name,
            "cell_key": cell_key,
            "started_at": datetime.utcnow().isoformat(),
        }, ensure_ascii=False)
        ok = await r.set(key, payload, nx=True, ex=EDIT_LOCK_TTL)
        if ok:
            return None
        raw = await r.get(key)
        if raw:
            data = json.loads(raw)
            if data.get("user_id") == user_id:
                await r.expire(key, EDIT_LOCK_TTL)
                return None
            return data
        return None
    finally:
        await r.aclose()


async def release_edit_lock(room_key: str, cell_key: str, user_id: int):
    r = await _redis()
    try:
        key = _lock_key(room_key, cell_key)
        raw = await r.get(key)
        if raw:
            data = json.loads(raw)
            if data.get("user_id") == user_id:
                await r.delete(key)
    finally:
        await r.aclose()


async def refresh_edit_lock(room_key: str, cell_key: str, user_id: int) -> bool:
    r = await _redis()
    try:
        key = _lock_key(room_key, cell_key)
        raw = await r.get(key)
        if raw:
            data = json.loads(raw)
            if data.get("user_id") == user_id:
                await r.expire(key, EDIT_LOCK_TTL)
                return True
        return False
    finally:
        await r.aclose()


async def release_user_editing(room_key: str, user_id: int):
    r = await _redis()
    try:
        prefix = f"bom:lock:{room_key}:"
        async for key in r.scan_iter(prefix + "*"):
            raw = await r.get(key)
            if raw:
                data = json.loads(raw)
                if data.get("user_id") == user_id:
                    await r.delete(key)
    finally:
        await r.aclose()


async def get_editing_cells(room_key: str) -> Dict[str, dict]:
    r = await _redis()
    try:
        result: Dict[str, dict] = {}
        prefix = f"bom:lock:{room_key}:"
        async for key in r.scan_iter(prefix + "*"):
            raw = await r.get(key)
            if raw:
                cell_key = key[len(prefix):]
                result[cell_key] = json.loads(raw)
        return result
    finally:
        await r.aclose()


async def clear_user_editing(room_key: str, user_id: int):
    await release_user_editing(room_key, user_id)


# ── 跨实例广播 ──

async def broadcast_to_room(room_key: str, message: dict, exclude: int = None):
    """向房间内所有用户广播消息 — 通过 Redis PubSub 实现跨实例"""
    # 1. 发布到 Redis PubSub，所有 worker 都能收到
    r = await _redis()
    try:
        channel = _channel_name(room_key)
        payload = json.dumps(message, ensure_ascii=False)
        await r.publish(channel, payload)
    finally:
        await r.aclose()

    # 2. 同时发给本进程的本地连接（排除指定用户）
    for uid, ws in _local_connections.get(room_key, {}).items():
        if exclude and uid == exclude:
            continue
        try:
            await ws.send_text(json.dumps(message, ensure_ascii=False))
        except Exception:
            pass


async def broadcast_online_users(room_key: str, message: str = ""):
    """广播当前在线用户列表"""
    users = await get_online_users(room_key)
    msg = {
        "type": "online_users",
        "users": users,
        "count": len(users),
        "message": message,
        "timestamp": datetime.utcnow().isoformat(),
    }
    await broadcast_to_room(room_key, msg)


# ── Redis PubSub 订阅者（每个 worker 进程启动一次） ──

_pubsub_tasks: Dict[str, asyncio.Task] = {}


async def _subscribe_room(room_key: str):
    """订阅一个房间的 Redis PubSub 频道，将消息转发给本地连接"""
    r = await _redis()
    pubsub = r.pubsub()
    channel = _channel_name(room_key)
    await pubsub.subscribe(channel)

    try:
        async for msg in pubsub.listen():
            if msg["type"] == "message":
                data = msg["data"]
                if isinstance(data, bytes):
                    data = data.decode()
                # 转发给本进程的本地连接
                for uid, ws in _local_connections.get(room_key, {}).items():
                    try:
                        await ws.send_text(data)
                    except Exception:
                        pass
    except Exception:
        pass
    finally:
        await pubsub.unsubscribe(channel)
        await r.aclose()


def _ensure_subscribed(room_key: str):
    """确保房间的 PubSub 订阅已启动"""
    if room_key not in _pubsub_tasks or _pubsub_tasks[room_key].done():
        _pubsub_tasks[room_key] = asyncio.create_task(_subscribe_room(room_key))


# ── WebSocket 端点 ──

@router.websocket("/bom/{bom_code}/{version}")
async def bom_websocket(
    websocket: WebSocket,
    bom_code: str,
    version: int,
    user_id: Optional[int] = None,
    user_name: Optional[str] = None,
):
    """
    BOM 协同编辑 WebSocket 连接
    - Session 鉴权（cookie session_id）
    - 在线用户列表存 Redis（跨实例）
    - 编辑锁存 Redis（跨实例）
    - 广播走 Redis PubSub（跨实例）
    - 本地 websocket 连接表用于消息投递
    """
    # ── 鉴权 ──
    session_id = websocket.cookies.get("session_id")
    if not session_id:
        await websocket.close(code=1008, reason="未登录")
        return
    r = await _redis()
    try:
        user = await AuthService.get_current_user(r, session_id)
    except Exception:
        user = None
    finally:
        await r.aclose()
    if not user:
        await websocket.close(code=1008, reason="会话无效")
        return
    user_id = user["id"]
    user_name = user.get("display_name") or user.get("username") or ""

    room_key = f"{bom_code}:{version}"

    await websocket.accept()

    # ── 注册连接 ──
    _local_connections.setdefault(room_key, {})[user_id] = websocket
    await _add_online_user(room_key, user_id, user_name)
    _ensure_subscribed(room_key)

    # 发送当前编辑状态给新加入者
    try:
        cells = await get_editing_cells(room_key)
        cells = {k: v for k, v in cells.items() if v.get("user_id") != user_id}
        await websocket.send_text(json.dumps({
            "type": "editing_sync",
            "editing_cells": cells,
            "timestamp": datetime.utcnow().isoformat(),
        }))
    except Exception:
        pass

    # 广播用户加入
    await broadcast_online_users(room_key, f"用户 {user_name} 加入编辑")

    try:
        while True:
            data = await websocket.receive_text()
            # 续期在线状态
            await _refresh_online_ttl(room_key)
            try:
                msg = json.loads(data)
                msg_type = msg.get("type")

                if msg_type == "ping":
                    await websocket.send_text(json.dumps({
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat(),
                    }))

                elif msg_type == "cursor":
                    await broadcast_to_room(room_key, {
                        "type": "cursor",
                        "user_id": user_id,
                        "user_name": user_name,
                        "data": msg.get("data"),
                    }, exclude=user_id)

                elif msg_type == "start_editing":
                    cell_info = msg.get("data")
                    if cell_info:
                        test_item_id = cell_info.get("test_item_id")
                        if test_item_id is None:
                            continue
                        cell_key = make_cell_key(test_item_id)
                        existing = await acquire_edit_lock(room_key, cell_key, user_id, user_name)
                        if existing:
                            await websocket.send_text(json.dumps({
                                "type": "editing_rejected",
                                "cell_key": cell_key,
                                "occupied_by": existing,
                                "message": f"该测试项正在被 {existing.get('user_name', '')} 编辑，请稍后再试",
                            }))
                        else:
                            await broadcast_to_room(room_key, {
                                "type": "user_started_editing",
                                "cell_key": cell_key,
                                "test_item_id": test_item_id,
                                "user": {
                                    "user_id": user_id,
                                    "user_name": user_name,
                                    "test_item_id": test_item_id,
                                    "started_at": datetime.utcnow().isoformat(),
                                },
                                "timestamp": datetime.utcnow().isoformat(),
                            }, exclude=user_id)

                elif msg_type == "refresh_editing":
                    cell_info = msg.get("data")
                    if cell_info and cell_info.get("test_item_id") is not None:
                        cell_key = make_cell_key(cell_info["test_item_id"])
                        await refresh_edit_lock(room_key, cell_key, user_id)

                elif msg_type == "stop_editing":
                    cell_info = msg.get("data")
                    if cell_info:
                        test_item_id = cell_info.get("test_item_id")
                        if test_item_id is None:
                            continue
                        cell_key = make_cell_key(test_item_id)
                        await release_edit_lock(room_key, cell_key, user_id)
                        await broadcast_to_room(room_key, {
                            "type": "user_stopped_editing",
                            "cell_key": cell_key,
                            "test_item_id": test_item_id,
                            "user_id": user_id,
                            "timestamp": datetime.utcnow().isoformat(),
                        })

            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        pass
    finally:
        # 清理编辑锁
        await release_user_editing(room_key, user_id)
        await broadcast_to_room(room_key, {
            "type": "user_stopped_editing_all",
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat(),
        })

        # 清理本地连接
        local = _local_connections.get(room_key, {})
        local.pop(user_id, None)
        if not local:
            _local_connections.pop(room_key, None)
            # 房间空了，取消订阅
            task = _pubsub_tasks.pop(room_key, None)
            if task:
                task.cancel()

        # 清理 Redis 在线列表
        await _remove_online_user(room_key, user_id)
        await broadcast_online_users(room_key, f"用户 {user_name} 离开编辑")
