"""
XXL-Job 回调 Handler
对应 design.md §9 — 统一管理定时清理/装备巡检/版本同步

XXL-Job Admin 通过 HTTP POST 调用 /api/v1/xxl-job/callback 触发任务
请求格式: {"jobName": "...", "params": {...}}
"""
import json
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.core.response import success
from app.config import get_settings

router = APIRouter(tags=["XXL-Job"])

# Map: XXL-Job job name → Celery task path
JOB_MAP = {
    "cleanup_expired_runs": "tasks.cleanup_tasks.cleanup_expired_runs",
    "compress_old_logs": "tasks.archive_tasks.compress_old_logs",
    "archive_version_files": "tasks.archive_tasks.archive_version_files",
    "cleanup_old_sessions": "tasks.cleanup_tasks.cleanup_old_sessions",
}


@router.post("/xxl-job/callback")
async def xxl_job_callback(request: Request):
    """
    XXL-Job 任务回调入口
    接收 XXL-Job Admin 的调度请求，执行对应 Celery 任务
    """
    try:
        body = await request.json()
    except Exception:
        body = {}

    job_name = body.get("jobName", body.get("job_name", ""))
    params = body.get("params", body.get("params", {}))

    if not job_name:
        return JSONResponse(status_code=400, content={"code": 400, "message": "缺少 jobName"})

    # Forward to Celery task
    import importlib
    task_path = JOB_MAP.get(job_name)
    if not task_path:
        return JSONResponse(status_code=404, content={
            "code": 404, "message": f"未知任务: {job_name}",
            "available": list(JOB_MAP.keys()),
        })

    try:
        module_path, func_name = task_path.rsplit(".", 1)
        module = importlib.import_module(module_path)
        task_func = getattr(module, func_name)

        kwargs = params if isinstance(params, dict) else {}
        result = task_func.delay(**kwargs)
        return success(data={
            "job_name": job_name,
            "task_id": result.id,
            "status": "dispatched",
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={
            "code": 500, "message": f"任务调度失败: {str(e)}",
        })


@router.get("/xxl-job/jobs")
async def list_jobs():
    """列出所有可用 XXL-Job 任务"""
    return success(data=[
        {"name": name, "task": path}
        for name, path in JOB_MAP.items()
    ])
