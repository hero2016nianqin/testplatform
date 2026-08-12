"""协同编辑锁 双用户 WebSocket 端到端测试
场景：yyj 与 超级管理员(admin) 同一房间；覆盖编辑中/竞争/离开释放/广播通知。
"""
import asyncio, json, sys
import websockets
from redis.asyncio import Redis

ROOM_BOM = "TESTE2E3"
URI = f"ws://localhost:8000/ws/bom/{ROOM_BOM}/1?user_id=0&user_name=test"
PASS, FAIL = 0, 0

def check(name, cond, extra=""):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  ✅ {name}")
    else: FAIL += 1; print(f"  ❌ {name} {extra}")


async def setup():
    r = Redis(host="localhost", port=6379, decode_responses=True)
    await r.setex("session:t_yyj", 3600, json.dumps({"id": 5, "username": "yyj", "display_name": "yyj", "role": "super_admin", "domains": []}))
    await r.setex("session:t_admin", 3600, json.dumps({"id": 1, "username": "admin", "display_name": "超级管理员", "role": "super_admin", "domains": []}))
    async for k in r.scan_iter(f"bom:lock:{ROOM_BOM}:*"):
        await r.delete(k)
    await r.aclose()


async def redis_lock(cell):
    r = Redis(host="localhost", port=6379, decode_responses=True)
    raw = await r.get(f"bom:lock:{ROOM_BOM}:1:{cell}")
    await r.aclose()
    return json.loads(raw) if raw else None


async def recv_until(ws, want_type, timeout=3):
    loop = asyncio.get_event_loop()
    deadline = loop.time() + timeout
    try:
        while True:
            remaining = deadline - loop.time()
            if remaining <= 0: return None
            raw = await asyncio.wait_for(ws.recv(), remaining)
            msg = json.loads(raw)
            if msg.get("type") == want_type: return msg
    except asyncio.TimeoutError:
        return None


async def main():
    await setup()

    print("\n=== 场景1：yyj 编辑中，admin 竞争同一测试项 ===")
    ws_yyj = await websockets.connect(URI, additional_headers={"cookie": "session_id=t_yyj"})
    await ws_yyj.send(json.dumps({"type": "start_editing", "data": {"test_item_id": 100, "indicator_id": 1, "param_key": "x"}}))
    await asyncio.sleep(0.4)
    lock = await redis_lock("item:100")
    check("yyj 获得 item:100 锁", lock is not None and lock["user_name"] == "yyj")

    ws_admin = await websockets.connect(URI, additional_headers={"cookie": "session_id=t_admin"})
    await ws_admin.send(json.dumps({"type": "start_editing", "data": {"test_item_id": 100, "indicator_id": 2, "param_key": "y"}}))
    rej = await recv_until(ws_admin, "editing_rejected")
    check("admin 竞争 item:100 被拒绝(提示 yyj)", rej is not None and rej.get("occupied_by", {}).get("user_name") == "yyj")

    await ws_admin.send(json.dumps({"type": "start_editing", "data": {"test_item_id": 200, "indicator_id": 3, "param_key": "z"}}))
    await asyncio.sleep(0.4)
    lock2 = await redis_lock("item:200")
    check("admin 可编辑另一测试项 200", lock2 is not None and lock2["user_name"] == "超级管理员")

    print("\n=== 场景2：yyj 离开（关闭 WS），admin 保持连接 ===")
    await ws_yyj.close()
    await asyncio.sleep(1)
    check("yyj 断开后 item:100 锁释放", await redis_lock("item:100") is None)
    check("admin 的 item:200 锁保留", await redis_lock("item:200") is not None)
    # admin 应收到 user_stopped_editing_all
    evt = await recv_until(ws_admin, "user_stopped_editing_all", timeout=3)
    check("admin 收到 user_stopped_editing_all 广播", evt is not None and evt.get("user_id") == 5)

    print("\n=== 场景3：yyj 离开后，admin 重新编辑 item:100 → 应成功 ===")
    await ws_admin.send(json.dumps({"type": "start_editing", "data": {"test_item_id": 100, "indicator_id": 2, "param_key": "y"}}))
    await asyncio.sleep(0.4)
    lock = await redis_lock("item:100")
    check("admin 重新获得 item:100（幽灵锁定消除）", lock is not None and lock["user_name"] == "超级管理员")

    print("\n=== 场景4：admin 自己重复编辑(同测试项其它参数) → 不被拒绝 ===")
    await ws_admin.send(json.dumps({"type": "start_editing", "data": {"test_item_id": 100, "indicator_id": 9, "param_key": "w"}}))
    rej2 = await recv_until(ws_admin, "editing_rejected", timeout=2)
    check("admin 重复编辑自己持有的测试项不被拒绝", rej2 is None)

    await ws_admin.close()
    await asyncio.sleep(1)
    check("admin 断开后所有锁释放", await redis_lock("item:100") is None and await redis_lock("item:200") is None)

    r = Redis(host="localhost", port=6379, decode_responses=True)
    async for k in r.scan_iter(f"bom:lock:{ROOM_BOM}:*"):
        await r.delete(k)
    await r.aclose()

    print(f"\n========== 结果: {PASS} 通过 / {FAIL} 失败 ==========")
    sys.exit(1 if FAIL else 0)


asyncio.run(main())
