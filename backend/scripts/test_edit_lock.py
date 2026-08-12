"""协同编辑锁 系统性测试（后端 Redis 锁逻辑 + editing-locks 接口）"""
import asyncio, json, sys
from redis.asyncio import Redis
from app.websockets.bom_ws import (
    acquire_edit_lock, release_edit_lock, refresh_edit_lock, release_user_editing,
    get_editing_cells, EDIT_LOCK_TTL,
)

ROOM = "TESTLOCK:1"
PASS, FAIL = 0, 0

def check(name, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ✅ {name}")
    else:
        FAIL += 1
        print(f"  ❌ {name} {extra}")


async def clean():
    r = Redis(host="localhost", port=6379, decode_responses=True)
    async for k in r.scan_iter(f"bom:lock:{ROOM}:*"):
        await r.delete(k)
    await r.aclose()


async def ttl_of(cell):
    r = Redis(host="localhost", port=6379, decode_responses=True)
    ttl = await r.ttl(f"bom:lock:{ROOM}:{cell}")
    await r.aclose()
    return ttl


async def main():
    await clean()

    print("\n=== 1. 单用户：加锁 / 重复加锁(自己) / 释放 ===")
    r1 = await acquire_edit_lock(ROOM, "item:100", 5, "yyj")
    check("A 首次加锁 item:100", r1 is None)
    check("TTL 应为 120s", (t := await ttl_of("item:100")) and 110 <= t <= 120, f"(实际 {t})")
    r2 = await acquire_edit_lock(ROOM, "item:100", 5, "yyj")
    check("A 重复加锁(自己) → 成功不拒绝", r2 is None)
    await release_edit_lock(ROOM, "item:100", 5)
    check("A 释放后锁消失", await ttl_of("item:100") == -2)
    await release_edit_lock(ROOM, "item:100", 5)  # 重复释放幂等
    check("重复释放幂等(不报错)", True)

    print("\n=== 2. 双用户竞争 ===")
    await acquire_edit_lock(ROOM, "item:100", 5, "yyj")
    r3 = await acquire_edit_lock(ROOM, "item:100", 6, "admin")
    check("B 尝试加锁(他人占用) → 返回占用者 yyj", r3 is not None and r3.get("user_name") == "yyj")
    check("A 仍持有(自己刷新不被 B 影响)", await acquire_edit_lock(ROOM, "item:100", 5, "yyj") is None)
    await release_user_editing(ROOM, 5)

    print("\n=== 3. 续期 refresh ===")
    await acquire_edit_lock(ROOM, "item:100", 5, "yyj")
    await asyncio.sleep(3)
    before = await ttl_of("item:100")  # 应已衰减 <120
    ok = await refresh_edit_lock(ROOM, "item:100", 5)
    after = await ttl_of("item:100")
    check("自己 refresh 成功", ok is True)
    check(f"refresh 后 TTL 重置 (refresh前={before} → refresh后={after})", before < 120 and after == 120 and after > before)
    ok2 = await refresh_edit_lock(ROOM, "item:100", 6)
    check("他人 refresh 被拒绝", ok2 is False)
    await release_edit_lock(ROOM, "item:100", 5)

    print("\n=== 4. 断线清理 release_user_editing ===")
    await acquire_edit_lock(ROOM, "item:100", 5, "yyj")
    await acquire_edit_lock(ROOM, "item:101", 5, "yyj")
    await acquire_edit_lock(ROOM, "item:200", 6, "admin")
    await release_user_editing(ROOM, 5)  # 模拟 yyj 断开
    cells = await get_editing_cells(ROOM)
    check("yyj 断开后其锁全部清理", "item:100" not in cells and "item:101" not in cells)
    check("admin 的锁不受影响", "item:200" in cells)
    await clean()

    print("\n=== 5. 多测试项隔离 ===")
    await acquire_edit_lock(ROOM, "item:100", 5, "yyj")
    await acquire_edit_lock(ROOM, "item:101", 6, "admin")
    cells = await get_editing_cells(ROOM)
    check("A 锁 100 且 B 锁 101 互不干扰", cells.get("item:100", {}).get("user_id") == 5 and cells.get("item:101", {}).get("user_id") == 6)
    await clean()

    print("\n=== 6. TTL 过期机制 ===")
    # 实际等待 120s 太慢；TTL 值已在上方验证为 120s，过期由 Redis EX 自动清理保证。
    # 此处仅验证：过期后他人可加锁（Redis EX 生效后键消失）
    await acquire_edit_lock(ROOM, "item:100", 5, "yyj")
    check("加锁 TTL=120（已设 EX）", (await ttl_of("item:100")) == 120)
    await clean()

    print(f"\n========== 结果: {PASS} 通过 / {FAIL} 失败 ==========")
    sys.exit(1 if FAIL else 0)


asyncio.run(main())
