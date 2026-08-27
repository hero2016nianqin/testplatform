"""
压力测试脚本 — 测试平台核心接口（支持CSRF）
测试场景: 并发扫码、API负载、数据库压力
"""
import asyncio
import aiohttp
import time
import json
import statistics
from dataclasses import dataclass, field
from typing import List

BASE_URL = "http://localhost:8000/api/v1"
STATION_ID = 5
SLOT_IDS = [1, 2, 3, 4]

@dataclass
class TestResult:
    name: str
    total: int = 0
    success: int = 0
    failed: int = 0
    times: List[float] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    @property
    def avg_ms(self):
        return statistics.mean(self.times) * 1000 if self.times else 0

    @property
    def p95_ms(self):
        return sorted(self.times)[int(len(self.times) * 0.95)] * 1000 if self.times else 0

    @property
    def max_ms(self):
        return max(self.times) * 1000 if self.times else 0

    def summary(self):
        return (f"{self.name}: {self.success}/{self.total} 成功 | "
                f"平均 {self.avg_ms:.0f}ms | P95 {self.p95_ms:.0f}ms | 最大 {self.max_ms:.0f}ms | "
                f"失败 {self.failed}")


async def login(session: aiohttp.ClientSession, username: str, password: str) -> str:
    """登录获取session和CSRF token"""
    async with session.post(f"{BASE_URL}/auth/login",
                           json={"username": username, "password": password}) as resp:
        data = await resp.json()
        if data.get("code") == 0:
            # 从cookie获取csrf_token
            csrf_token = ""
            for cookie in session.cookie_jar:
                if cookie.key == "csrf_token":
                    csrf_token = cookie.value
                    break
            return csrf_token
    return ""


async def test_api(session: aiohttp.ClientSession, method: str, url: str,
                   result: TestResult, csrf_token: str = "", **kwargs) -> bool:
    """测试单个API请求"""
    start = time.monotonic()
    try:
        headers = kwargs.pop("headers", {})
        if method.upper() in ("POST", "PUT", "DELETE", "PATCH") and csrf_token:
            headers["X-CSRF-Token"] = csrf_token

        async with session.request(method, url, headers=headers, **kwargs) as resp:
            elapsed = time.monotonic() - start
            result.times.append(elapsed)
            result.total += 1
            if resp.status == 200:
                data = await resp.json()
                if data.get("code") == 0:
                    result.success += 1
                    return True
                else:
                    result.failed += 1
                    result.errors.append(data.get("message", "unknown")[:50])
            else:
                result.failed += 1
                text = await resp.text()
                result.errors.append(f"HTTP {resp.status}: {text[:50]}")
    except Exception as e:
        elapsed = time.monotonic() - start
        result.times.append(elapsed)
        result.total += 1
        result.failed += 1
        result.errors.append(str(e)[:80])
    return False


# ── 场景1: 并发读取API ──

async def test_concurrent_reads(concurrency: int = 20, requests_per_user: int = 10):
    print(f"\n{'='*60}")
    print(f"场景1: 并发读取 ({concurrency} 用户 x {requests_per_user} 请求)")
    print(f"{'='*60}")

    result = TestResult("并发读取")

    async def user_task(uid: int):
        async with aiohttp.ClientSession() as session:
            await login(session, "admin", "admin123")
            for _ in range(requests_per_user):
                await test_api(session, "GET", f"{BASE_URL}/stations/{STATION_ID}", result)

    start = time.monotonic()
    tasks = [user_task(i) for i in range(concurrency)]
    await asyncio.gather(*tasks)
    total_time = time.monotonic() - start

    print(f"  {result.summary()}")
    print(f"  总耗时: {total_time:.1f}s | QPS: {result.total/total_time:.1f}")
    return result


# ── 场景2: 并发扫码测试 ──

async def test_concurrent_scan(concurrency: int = 4):
    print(f"\n{'='*60}")
    print(f"场景2: 并发扫码 ({concurrency} 槽位同时扫码)")
    print(f"{'='*60}")

    result = TestResult("并发扫码")
    slots = SLOT_IDS[:concurrency]

    async def scan_task(uid: int, slot_id: int):
        async with aiohttp.ClientSession() as session:
            csrf = await login(session, "admin", "admin123")
            url = (f"{BASE_URL}/tests/scan?station_id={STATION_ID}"
                   f"&slot_id={slot_id}&serial_number=STRESS{uid:03d}"
                   f"&operator=admin&selected_item_ids=")
            await test_api(session, "POST", url, result, csrf_token=csrf)

    start = time.monotonic()
    tasks = [scan_task(i, slots[i]) for i in range(concurrency)]
    await asyncio.gather(*tasks)
    total_time = time.monotonic() - start

    print(f"  {result.summary()}")
    print(f"  总耗时: {total_time:.1f}s")
    if result.errors:
        print(f"  错误: {result.errors[:5]}")
    return result


# ── 场景3: 顺序扫码稳定性 ──

async def test_sequential_scan(count: int = 15):
    print(f"\n{'='*60}")
    print(f"场景3: 顺序扫码稳定性 ({count} 次连续扫码)")
    print(f"{'='*60}")

    result = TestResult("顺序扫码")
    slot_id = SLOT_IDS[0]

    async with aiohttp.ClientSession() as session:
        csrf = await login(session, "admin", "admin123")

        for i in range(count):
            await asyncio.sleep(3)  # 等待上一次测试完成
            url = (f"{BASE_URL}/tests/scan?station_id={STATION_ID}"
                   f"&slot_id={slot_id}&serial_number=SEQ{i:03d}"
                   f"&operator=admin&selected_item_ids=")
            await test_api(session, "POST", url, result, csrf_token=csrf)

    print(f"  {result.summary()}")
    success_rate = result.success / result.total * 100 if result.total else 0
    print(f"  成功率: {success_rate:.1f}%")
    return result


# ── 场景4: API响应时间基准 ──

async def test_api_benchmark(iterations: int = 100):
    print(f"\n{'='*60}")
    print(f"场景4: API响应时间基准 ({iterations} 次)")
    print(f"{'='*60}")

    endpoints = [
        ("GET", f"{BASE_URL}/stations/{STATION_ID}", "工站详情"),
        ("GET", f"{BASE_URL}/stations", "工站列表"),
        ("GET", f"{BASE_URL}/auth/me", "当前用户"),
        ("GET", f"{BASE_URL}/versions", "版本列表"),
        ("GET", f"{BASE_URL}/test-records?page=1&page_size=10", "测试记录"),
    ]

    async with aiohttp.ClientSession() as session:
        await login(session, "admin", "admin123")
        for method, url, name in endpoints:
            result = TestResult(name)
            for _ in range(iterations):
                await test_api(session, method, url, result)
            print(f"  {result.summary()}")


# ── 场景5: 混合负载 ──

async def test_mixed_workload(duration: int = 30):
    print(f"\n{'='*60}")
    print(f"场景5: 混合负载 ({duration}秒)")
    print(f"{'='*60}")

    read_result = TestResult("读取")
    write_result = TestResult("写入")
    stop_time = time.monotonic() + duration

    async def reader():
        async with aiohttp.ClientSession() as session:
            await login(session, "admin", "admin123")
            while time.monotonic() < stop_time:
                await test_api(session, "GET", f"{BASE_URL}/stations/{STATION_ID}", read_result)
                await asyncio.sleep(0.1)

    async def writer(uid: int):
        async with aiohttp.ClientSession() as session:
            csrf = await login(session, "admin", "admin123")
            slot_id = SLOT_IDS[uid % len(SLOT_IDS)]
            while time.monotonic() < stop_time:
                url = (f"{BASE_URL}/tests/scan?station_id={STATION_ID}"
                       f"&slot_id={slot_id}&serial_number=MIX{uid}"
                       f"&operator=admin&selected_item_ids=")
                await test_api(session, "POST", url, write_result, csrf_token=csrf)
                await asyncio.sleep(4)

    start = time.monotonic()
    tasks = [reader() for _ in range(5)] + [writer(i) for i in range(3)]
    await asyncio.gather(*tasks)
    total_time = time.monotonic() - start

    print(f"  {read_result.summary()}")
    print(f"  {write_result.summary()}")
    print(f"  总耗时: {total_time:.1f}s")


# ── 主函数 ──

async def main():
    print("=" * 60)
    print("  测试平台压力测试 (含CSRF支持)")
    print("=" * 60)

    await test_api_benchmark(iterations=50)
    await test_concurrent_reads(concurrency=20, requests_per_user=10)
    await test_concurrent_scan(concurrency=4)
    await test_sequential_scan(count=10)
    await test_mixed_workload(duration=20)

    print("\n" + "=" * 60)
    print("  压力测试完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
