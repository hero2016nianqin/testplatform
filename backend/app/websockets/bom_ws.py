from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, List, Optional
from collections import defaultdict
import json
from datetime import datetime

from redis.asyncio import Redis

from app.core.redis import get_redis_pool
from app.services.auth_service import AuthService

router = APIRouter(prefix="/ws", tags=["WebSocket"])

# 在线用户存储：room_key -> {user_id: {user_id, user_name, connected_at, websocket}}
# 在线用户列表仅用于展示（丢失可接受），编辑锁已移至 Redis（跨实例共享 + 自动过期）。
online_users: Dict[str, Dict[int, dict]] = defaultdict(dict)

HEARTBEAT_INTERVAL = 30
EDIT_LOCK_TTL = 120  # 秒，编辑锁有效期（2 分钟，输入时自动续期）

# 锁粒度：与后端乐观锁（测试项级 CAS）保持一致，避免"单元格可编辑、保存却冲突"的错位。
def make_cell_key(test_item_id: int) -> str:
    return f"item:{test_item_id}"


def _lock_key(room_key: str, cell_key: str) -> str:
    return f"bom:lock:{room_key}:{cell_key}"


async def _redis() -> Redis:
    return Redis(connection_pool=get_redis_pool())


async def acquire_edit_lock(room_key: str, cell_key: str, user_id: int, user_name: str) -> Optional[dict]:
    """原子获取测试项级编辑锁（SET NX EX）。
    返回 None 表示成功；返回他人占用者信息表示失败。
    若锁属于当前用户自己（同一用户重复点击/切换参数），视为成功并刷新 TTL，避免自身误拒绝。"""
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
        # 已存在：若属于自己则刷新 TTL 并视为成功
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
    """释放编辑锁（仅限锁持有者）。"""
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
    """输入自动续期：若锁属于当前用户则刷新 TTL（2 分钟滑动窗口），返回是否成功。"""
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
    """断开连接时清理该用户持有的所有编辑锁。"""
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
    """获取房间内所有正在编辑的测试项锁（供初始同步与 HTTP 接口）。"""
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
    """清理指定用户的编辑锁（供外部调用）。"""
    await release_user_editing(room_key, user_id)


@router.websocket("/bom/{bom_code}/{version}")
async def bom_websocket(
    websocket: WebSocket,
    bom_code: str,
    version: int,
    user_id: Optional[int] = None,  # 兼容旧客户端参数；以 session 鉴权为准
    user_name: Optional[str] = None,
):
    """
    BOM 协同编辑 WebSocket 连接
    - Session 鉴权（cookie session_id），拒绝伪造身份
    - 维护在线用户列表
    - 同步实时编辑状态（测试项级锁，Redis 存储，跨实例共享）
    - 广播用户加入/离开
    - 心跳保活
    """
    # ── 鉴权：以服务端 session 为准，忽略客户端自报身份 ──
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

    # 注册用户
    online_users[room_key][user_id] = {
        "user_id": user_id,
        "user_name": user_name,
        "connected_at": datetime.utcnow().isoformat(),
        "websocket": websocket,
    }

    # 发送当前编辑状态给新加入者（过滤掉自己持有的锁，避免本人界面误提醒）
    try:
        cells = await get_editing_cells(room_key)
        cells = {k: v for k, v in cells.items() if v.get("user_id") != user_id}
        await websocket.send_text(json.dumps({
            "type": "editing_sync",
            "editing_cells": cells,
            "timestamp": datetime.utcnow().isoformat(),
        }))
    except Exception:
        cells = {}

    # 广播用户加入
    await broadcast_online_users(room_key, f"用户 {user_name} 加入编辑")

    try:
        while True:
            data = await websocket.receive_text()
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
                            # 仅广播给房间内其他用户（exclude 发起者），避免编辑者自己界面误显示"X 正在编辑"
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
                    # 输入自动续期：仅当锁属于自己时刷新 TTL（他人/无锁则忽略）
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
        # 清理该用户的编辑锁（Redis）
        await release_user_editing(room_key, user_id)
        await broadcast_to_room(room_key, {
            "type": "user_stopped_editing_all",
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat(),
        })

        # 清理在线用户
        if user_id in online_users.get(room_key, {}):
            del online_users[room_key][user_id]
            await broadcast_online_users(room_key, f"用户 {user_name} 离开编辑")


async def broadcast_online_users(room_key: str, message: str = ""):
    """广播当前在线用户列表"""
    users = [
        {
            "user_id": u["user_id"],
            "user_name": u["user_name"],
            "connected_at": u["connected_at"],
        }
        for u in online_users.get(room_key, {}).values()
    ]

    msg = {
        "type": "online_users",
        "users": users,
        "count": len(users),
        "message": message,
        "timestamp": datetime.utcnow().isoformat(),
    }

    await broadcast_to_room(room_key, msg)


async def broadcast_to_room(room_key: str, message: dict, exclude: int = None):
    """向房间内所有用户广播消息（可排除某用户）"""
    dead_connections = []

    for uid, conn_info in online_users.get(room_key, {}).items():
        if exclude and uid == exclude:
            continue
        ws = conn_info["websocket"]
        try:
            await ws.send_text(json.dumps(message))
        except Exception:
            dead_connections.append(uid)

    for uid in dead_connections:
        if uid in online_users.get(room_key, {}):
            del online_users[room_key][uid]
            await release_user_editing(room_key, uid)


def get_online_users(room_key: str) -> List[dict]:
    """获取房间内在线用户列表（供 HTTP 接口调用）"""
    return [
        {
            "user_id": u["user_id"],
            "user_name": u["user_name"],
            "connected_at": u["connected_at"],
        }
        for u in online_users.get(room_key, {}).values()
    ]
