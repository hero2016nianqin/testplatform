"""
Celery 异步任务应用

为测试平台提供分布式异步任务能力，替代 APScheduler 的内嵌调度。
支持:
  - 定时清理过期测试批次 (celery beat)
  - 异步压缩旧日志文件
  - 可扩展其他后台任务

启动 worker:
  celery -A app.services.celery_app worker -l info

启动 beat (定时任务调度):
  celery -A app.services.celery_app beat -l info
"""

from celery import Celery

celery_app = Celery('test_platform')

# 配置从 Flask 配置中加载，由 create_app 调用时设置
celery_app.config_from_object({
    'broker_url': 'redis://localhost:6379/1',
    'result_backend': 'redis://localhost:6379/1',
    'task_serializer': 'json',
    'accept_content': ['json'],
    'result_serializer': 'json',
    'timezone': 'Asia/Shanghai',
    'enable_utc': True,
    'beat_schedule': {
        'cleanup-expired-runs': {
            'task': 'app.services.tasks.cleanup_expired_runs',
            'schedule': 3600.0,  # 每小时
        },
        'compress-old-logs': {
            'task': 'app.services.tasks.compress_old_logs',
            'schedule': 86400.0,  # 每天
        },
    },
})


def init_celery(app):
    """从 Flask 配置更新 Celery 配置"""
    celery_app.conf.update(
        broker_url=app.config.get('CELERY_BROKER_URL', 'redis://localhost:6379/1'),
        result_backend=app.config.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/1'),
    )
    # 将 Flask 应用上下文推入 Celery task
    class ContextTask(celery_app.Task):
        abstract = True

        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery_app.Task = ContextTask
    return celery_app
