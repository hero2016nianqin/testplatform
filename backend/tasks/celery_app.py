"""
Celery 异步任务 app 实例
对应 design.md §9 — 测试执行/版本部署/日志归档/过期清理
"""
from celery import Celery
from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "test_platform",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_track_published=True,
    result_expires=3600 * 24 * 7,
    worker_concurrency=settings.CELERY_WORKER_CONCURRENCY,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_soft_time_limit=3600,
    task_time_limit=4200,
    beat_schedule={
        "cleanup-expired-runs-daily": {
            "task": "tasks.cleanup_tasks.cleanup_expired_runs",
            "schedule": 86400.0,
        },
        "compress-old-logs-daily": {
            "task": "tasks.archive_tasks.compress_old_logs",
            "schedule": 86400.0,
        },
    },
)

celery_app.autodiscover_tasks(["tasks"])
