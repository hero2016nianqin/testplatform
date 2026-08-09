from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Dict, List, Set, Optional
from collections import defaultdict
import json
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Any

router = APIRouter(prefix="/ws", tags=["WebSocket"])

# 在线用户存储：room_key -> {user_id: {user_id, user_name, connected_at, websocket}}
online_users: Dict[str, Dict[int, dict]] = defaultdict(dict)

# 正在编辑的单元格：room_key -> {cell_key: {user_id, user_name, test_item_id, indicator_id, param_key, started_at}}
editing_cells: Dict[str, Dict[str, dict]] = defaultdict(dict)

HEARTBEAT_INTERVAL = 30


@dataclass
class EditingInfo:
    user_id: int
    user_name: str
    test_item_id: int
    indicator_id: int
    param_key: str
    started_at: str

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def cell_key(self) -> str:
        return f"{self.test_item_id}:{self.indicator_id}:{self.param_key}"


def make_cell_key(test_item_id: int, indicator_id: int, param_key: str) -> str:
    return f"{test_item_id}:{indicator_id}:{param_key}"


@router.websocket("/bom/{bom_code}/{version}")
async def bom_websocket(
    websocket: WebSocket,
    bom_code: str,
    version: int,
    user_id: int = Query(...),
    user_name: str = Query(...),
):
    """
    BOM 协同编辑 WebSocket 连接
    - 维护在线用户列表
    - 同步实时编辑状态（谁在改哪个参数）
    - 广播用户加入/离开
    - 心跳保活
    """
    room_key = f"{bom_code}:{version}"

    await websocket.accept()

    # 注册用户
    online_users[room_key][user_id] = {
        "user_id": user_id,
        "user_name": user_name,
        "connected_at": datetime.utcnow().isoformat(),
        "websocket": websocket,
    }

    # 发送当前编辑状态给新加入者
    await websocket.send_text(json.dumps({
        "type": "editing_sync",
        "editing_cells": {
            k: v for k, v in editing_cells.get(room_key, {}).items()
        },
        "timestamp": datetime.utcnow().isoformat(),
    }))

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
                    # 广播光标位置
                    await broadcast_to_room(room_key, {
                        "type": "cursor",
                        "user_id": user_id,
                        "user_name": user_name,
                        "data": msg.get("data"),
                    }, exclude=user_id)

                elif msg_type == "start_editing":
                    # 用户开始编辑某个参数
                    cell_info = msg.get("data")
                    if cell_info:
                        cell_key = make_cell_key(
                            cell_info["test_item_id"],
                            cell_info["indicator_id"],
                            cell_info["param_key"],
                        )
                        # 检查是否已被他人编辑
                        existing = editing_cells[room_key].get(cell_key)
                        if existing and existing["user_id"] != user_id:
                            # 已被他人占用，拒绝并通知当前用户
                            await websocket.send_text(json.dumps({
                                "type": "editing_rejected",
                                "cell_key": cell_key,
                                "occupied_by": existing,
                                "message": f"该参数正在被 {existing['user_name']} 编辑，请稍后再试",
                            }))
                        else:
                            # 记录编辑状态并广播
                            info = EditingInfo(
                                user_id=user_id,
                                user_name=user_name,
                                test_item_id=cell_info["test_item_id"],
                                indicator_id=cell_info["indicator_id"],
                                param_key=cell_info["param_key"],
                                started_at=datetime.utcnow().isoformat(),
                            )
                            editing_cells[room_key][cell_key] = info.to_dict()
                            await broadcast_to_room(room_key, {
                                "type": "user_started_editing",
                                "cell_key": cell_key,
                                "user": info.to_dict(),
                                "timestamp": datetime.utcnow().isoformat(),
                            })

                elif msg_type == "stop_editing":
                    # 用户结束编辑
                    cell_info = msg.get("data")
                    if cell_info:
                        cell_key = make_cell_key(
                            cell_info["test_item_id"],
                            cell_info["indicator_id"],
                            cell_info["param_key"],
                        )
                        existing = editing_cells[room_key].get(cell_key)
                        if existing and existing["user_id"] == user_id:
                            del editing_cells[room_key][cell_key]
                            await broadcast_to_room(room_key, {
                                "type": "user_stopped_editing",
                                "cell_key": cell_key,
                                "user_id": user_id,
                                "timestamp": datetime.utcnow().isoformat(),
                            })

            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        pass
    finally:
        # 清理该用户的编辑状态
        if room_key in editing_cells:
            keys_to_delete = [
                k for k, v in editing_cells[room_key].items()
                if v.get("user_id") == user_id
            ]
            for k in keys_to_delete:
                del editing_cells[room_key][k]
                await broadcast_to_room(room_key, {
                    "type": "user_stopped_editing",
                    "cell_key": k,
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

    for user_id, conn_info in online_users.get(room_key, {}).items():
        if exclude and user_id == exclude:
            continue
        ws = conn_info["websocket"]
        try:
            await ws.send_text(json.dumps(message))
        except Exception:
            dead_connections.append(user_id)

    # 清理断开的连接
    for uid in dead_connections:
        if uid in online_users.get(room_key, {}):
            del online_users[room_key][uid]
            # 同时清理该用户的编辑状态
            if room_key in editing_cells:
                keys_to_delete = [
                    k for k, v in editing_cells[room_key].items()
                    if v.get("user_id") == uid
                ]
                for k in keys_to_delete:
                    del editing_cells[room_key][k]
                    await broadcast_to_room(room_key, {
                        "type": "user_stopped_editing",
                        "cell_key": k,
                        "user_id": uid,
                        "timestamp": datetime.utcnow().isoformat(),
                    })


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


def get_editing_cells(room_key: str) -> Dict[str, dict]:
    """获取房间内正在编辑的单元格状态（供 HTTP 接口调用）"""
    return editing_cells.get(room_key, {})


def clear_user_editing(room_key: str, user_id: int):
    """清理指定用户的编辑状态（供外部调用，如用户被踢出）"""
    if room_key in editing_cells:
        keys_to_delete = [
            k for k, v in editing_cells[room_key].items()
            if v.get("user_id") == user_id
        ]
        for k in keys_to_delete:
            del editing_cells[room_key][k]