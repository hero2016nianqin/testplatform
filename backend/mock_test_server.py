"""
模拟测试装备服务
真实生产环境中，这就是实际的装备 HTTP 接口。
测试平台会拼接 equipment_service_address + service_address 调用此服务。
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import random
import time

app = FastAPI(title="Mock Test Equipment")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.post("/api/test/temperature")
async def test_temperature(payload: dict):
    """查询温度 — 模拟从设备读取温度值"""
    time.sleep(0.5)
    temp = round(random.uniform(25.0, 45.0), 1)
    passed = 15.0 <= temp <= 60.0
    return {
        "passed": passed,
        "actual_value": temp,
        "deviation": 0.0,
        "duration_ms": 500,
        "params": payload.get("params", {}),
    }


@app.post("/api/test/voltage")
async def test_voltage(payload: dict):
    """查询电压 — 模拟从设备读取电压值"""
    time.sleep(0.3)
    voltage = round(random.uniform(3.2, 3.5), 2)
    passed = 3.0 <= voltage <= 3.6
    return {
        "passed": passed,
        "actual_value": voltage,
        "deviation": 0.0,
        "duration_ms": 300,
        "params": payload.get("params", {}),
    }


@app.post("/api/test/current")
async def test_current(payload: dict):
    """查询电流 — 模拟从设备读取电流值"""
    time.sleep(0.3)
    current = round(random.uniform(0.5, 2.0), 2)
    passed = 0.1 <= current <= 5.0
    return {
        "passed": passed,
        "actual_value": current,
        "deviation": 0.0,
        "duration_ms": 300,
        "params": payload.get("params", {}),
    }


@app.post("/api/test/query_version")
async def test_query_version(payload: dict):
    """查询版本 — 模拟获取设备固件版本"""
    time.sleep(0.2)
    return {
        "passed": True,
        "actual_value": "v2.3.1-build.20260824",
        "deviation": 0.0,
        "duration_ms": 200,
        "params": payload.get("params", {}),
    }


@app.post("/api/test/power")
async def test_power(payload: dict):
    """查询功耗 — 模拟从设备读取功耗值(W)"""
    time.sleep(0.4)
    params = payload.get("params", {})
    threshold_max = float(params.get("threshold_max", 80))
    channel = params.get("channel", "1")
    power = round(random.uniform(15.0, 75.0), 1)
    passed = power <= threshold_max
    return {
        "passed": passed,
        "actual_value": power,
        "deviation": 0.0,
        "duration_ms": 400,
        "params": params,
    }


@app.post("/api/test/version")
async def test_version(payload: dict):
    """查询版本 — 校验设备版本号是否匹配期望值"""
    time.sleep(0.2)
    params = payload.get("params", {})
    expected_version = params.get("expected_version", "V2.1.0")
    actual_version = "V2.1.0-rc3.build.20260827"
    passed = expected_version in actual_version or actual_version.startswith(expected_version)
    return {
        "passed": passed,
        "actual_value": actual_version,
        "deviation": 0.0,
        "duration_ms": 200,
        "params": params,
    }


@app.post("/api/test/start-work")
async def test_start_work(payload: dict):
    """查询开工 — 模拟开工自检流程"""
    time.sleep(0.3)
    params = payload.get("params", {})
    check_items = params.get("check_items", "版本,序列号,时间")
    items = [s.strip() for s in check_items.split(",")]
    results = {item: "PASS" for item in items}
    passed = all(v == "PASS" for v in results.values())
    return {
        "passed": passed,
        "actual_value": str(results),
        "deviation": 0.0,
        "duration_ms": 300,
        "params": params,
    }


@app.post("/api/test/{path:path}")
async def test_fallback(path: str, payload: dict):
    """通用兜底 — 所有未定义的测试项都返回通过"""
    time.sleep(0.1)
    return {
        "passed": True,
        "actual_value": f"mock-{path}",
        "deviation": 0.0,
        "duration_ms": 100,
        "params": payload.get("params", {}),
    }


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "mock-test-equipment"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
