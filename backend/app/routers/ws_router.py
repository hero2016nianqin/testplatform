"""
WebSocket 实时通信端点
对应 design.md §12 — 心跳/断线重连/4 事件广播
"""
import asyncio
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

router = APIRouter(tags=["WebSocket"])

# ── BOM 协同编辑 WebSocket (新版：支持编辑状态同步) ──

from app.websockets.bom_ws import (
    online_users as bom_online_users,
    broadcast_to_room as broadcast_bom_room,
    get_online_users as get_bom_online_users,
    get_editing_cells as get_bom_editing_cells,
)

# 保持兼容旧导入
bom_online_users_dict: dict[str, dict[int, dict]] = {}

# 兼容旧版导出函数
def get_bom_online_users(room_key: str) -> list[dict]:
    from app.websockets.bom_ws import get_online_users
    return get_online_users(room_key)

# 供旧代码调用
def broadcast_bom_online_users(room_key: str, message: str = ""):
    import asyncio
    from app.websockets.bom_ws import broadcast_online_users
    asyncio.create_task(broadcast_online_users(room_key, message))

async def broadcast_to_bom_room(room_key: str, message: dict, exclude: int = None):
    from app.websockets.bom_ws import broadcast_to_room
    await broadcast_to_room(room_key, message, exclude)


@router.websocket("/ws/bom/{bom_code}/{version}")
async def bom_collaborative_websocket(
    websocket: WebSocket,
    bom_code: str,
    version: int,
    user_id: int = Query(...),
    user_name: str = Query(...),
):
    """
    BOM 协同编辑 WebSocket 连接（新版：支持编辑状态同步）
    - 维护在线用户列表
    - 同步实时编辑状态（谁在改哪个参数）
    - 广播用户加入/离开
    - 心跳保活
    """
    from app.websockets.bom_ws import bom_websocket
    await bom_websocket(websocket, bom_code, version, user_id, user_name)


@router.get("/ws/bom/{bom_code}/{version}/online-users")
async def get_bom_online_users_http(bom_code: str, version: int):
    """获取 BOM 协同编辑在线用户列表（HTTP 接口）"""
    from app.websockets.bom_ws import get_online_users
    room_key = f"{bom_code}:{version}"
    users = get_online_users(room_key)
    return {"users": users, "count": len(users)}


@router.get("/ws/bom/{bom_code}/{version}/editing-cells")
async def get_bom_editing_cells_http(bom_code: str, version: int):
    """获取 BOM 协同编辑中正在被编辑的单元格状态（HTTP 接口）"""
    from app.websockets.bom_ws import get_editing_cells
    room_key = f"{bom_code}:{version}"
    cells = await get_editing_cells(room_key)
    return {"editing_cells": cells, "count": len(cells)}


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