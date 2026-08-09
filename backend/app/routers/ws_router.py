"""
WebSocket 实时通信端点
对应 design.md §12 — 心跳/断线重连/4 事件广播
"""
import json
import asyncio
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

router = APIRouter(tags=["WebSocket"])

# BOM 协同编辑在线用户存储：bom_code:version -> {user_id: {user_name, connected_at, websocket}}
bom_online_users: dict[str, dict[int, dict]] = {}


@router.websocket("/ws/bom/{bom_code}/{version}")
async def bom_collaborative_websocket(
    websocket: WebSocket,
    bom_code: str,
    version: int,
    user_id: int = Query(...),
    user_name: str = Query(...),
):
    """
    BOM 协同编辑 WebSocket 连接
    - 维护在线用户列表
    - 广播用户加入/离开
    - 心跳保活
    """
    room_key = f"{bom_code}:{version}"
    
    await websocket.accept()
    
    # 注册用户
    if room_key not in bom_online_users:
        bom_online_users[room_key] = {}
    bom_online_users[room_key][user_id] = {
        "user_id": user_id,
        "user_name": user_name,
        "connected_at": datetime.utcnow().isoformat(),
        "websocket": websocket,
    }
    
    # 广播用户加入
    await broadcast_bom_online_users(room_key, f"用户 {user_name} 加入编辑")
    
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong", "timestamp": datetime.utcnow().isoformat()}))
                elif msg.get("type") == "cursor":
                    await broadcast_to_bom_room(room_key, {
                        "type": "cursor",
                        "user_id": user_id,
                        "user_name": user_name,
                        "data": msg.get("data"),
                    }, exclude=user_id)
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        pass
    finally:
        # 清理
        if user_id in bom_online_users.get(room_key, {}):
            del bom_online_users[room_key][user_id]
            await broadcast_bom_online_users(room_key, f"用户 {user_name} 离开编辑")


async def broadcast_bom_online_users(room_key: str, message: str = ""):
    """广播当前在线用户列表"""
    users = [
        {
            "user_id": u["user_id"],
            "user_name": u["user_name"],
            "connected_at": u["connected_at"],
        }
        for u in bom_online_users.get(room_key, {}).values()
    ]
    
    msg = {
        "type": "online_users",
        "users": users,
        "count": len(users),
        "message": message,
        "timestamp": datetime.utcnow().isoformat(),
    }
    
    await broadcast_to_bom_room(room_key, msg)


async def broadcast_to_bom_room(room_key: str, message: dict, exclude: int = None):
    """向房间内所有用户广播消息（可排除某用户）"""
    dead_connections = []
    
    for user_id, conn_info in bom_online_users.get(room_key, {}).items():
        if exclude and user_id == exclude:
            continue
        ws = conn_info["websocket"]
        try:
            await ws.send_text(json.dumps(message))
        except Exception:
            dead_connections.append(user_id)
    
    # 清理断开的连接
    for uid in dead_connections:
        if uid in bom_online_users.get(room_key, {}):
            del bom_online_users[room_key][uid]


# 供 HTTP 接口调用
def get_bom_online_users(room_key: str) -> list[dict]:
    """获取房间内在线用户列表（供 HTTP 接口调用）"""
    return [
        {
            "user_id": u["user_id"],
            "user_name": u["user_name"],
            "connected_at": u["connected_at"],
        }
        for u in bom_online_users.get(room_key, {}).values()
    ]


@router.get("/ws/bom/{bom_code}/{version}/online-users")
async def get_bom_online_users_http(bom_code: str, version: int):
    """获取 BOM 协同编辑在线用户列表（HTTP 接口）"""
    room_key = f"{bom_code}:{version}"
    users = get_bom_online_users(room_key)
    return {"users": users, "count": len(users)}


# ── 原有 station / global 实时事件 WebSocket（供 useWebSocket 使用） ──
from app.ws.manager import get_manager

_manager = get_manager()


@router.websocket("/ws/stations/{station_id}")
async def station_websocket(websocket: WebSocket, station_id: int):
    """工位级实时事件推送（run_started/item_tested/run_completed/run_failed）"""
    channel = _manager.get_channel_for_station(station_id)
    await _manager.connect(channel, websocket)
    heartbeat_task = asyncio.create_task(_manager.heartbeat(websocket))
    try:
        while True:
            data = await websocket.receive_text()
            _manager.update_activity(websocket)
            try:
                msg = json.loads(data)
                if msg.get("event") == "pong":
                    pass
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        pass
    finally:
        heartbeat_task.cancel()
        _manager.disconnect(channel, websocket)


@router.websocket("/ws/global")
async def global_websocket(websocket: WebSocket):
    """全局实时事件推送"""
    channel = _manager.get_channel_global()
    await _manager.connect(channel, websocket)
    heartbeat_task = asyncio.create_task(_manager.heartbeat(websocket))
    try:
        while True:
            data = await websocket.receive_text()
            _manager.update_activity(websocket)
            try:
                msg = json.loads(data)
                if msg.get("event") == "pong":
                    pass
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        pass
    finally:
        heartbeat_task.cancel()
        _manager.disconnect(channel, websocket)
