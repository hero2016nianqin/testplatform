from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Dict, List, Set
from collections import defaultdict
import json
from datetime import datetime

router = APIRouter(prefix="/ws", tags=["WebSocket"])

# 在线用户存储：bom_code:version -> {user_id: {user_name, connected_at, websocket}}
online_users: Dict[str, Dict[int, dict]] = defaultdict(dict)

# 连接心跳间隔（秒）
HEARTBEAT_INTERVAL = 30


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
    
    # 广播用户加入
    await broadcast_online_users(room_key, f"用户 {user_name} 加入编辑")
    
    try:
        while True:
            # 接收消息（心跳或客户端消息）
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong", "timestamp": datetime.utcnow().isoformat()}))
                elif msg.get("type") == "cursor":
                    # 广播光标位置（可选功能）
                    await broadcast_to_room(room_key, {
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
        if user_id in online_users.get(room_key, {}):
            del online_users[room_key][user_id]
            # 广播用户离开
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