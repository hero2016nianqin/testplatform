"""
后台任务调度器模块

生产环境使用 Celery + Redis 提供分布式任务调度：
  - cleanup-expired-runs: 每小时清理超时批次（Celery Beat）
  - compress-old-logs: 每天压缩旧日志（Celery Beat）

保留 TestScheduler 类兼容旧代码，但 init_scheduler 现在配置 Celery。
"""

import logging

logger = logging.getLogger(__name__)

_scheduler = None


class TestScheduler:
    """
    测试平台调度器（兼容接口）。
    生产环境请使用 Celery Beat 替代 APScheduler。
    """

    def __init__(self, app):
        self.app = app
        self._jobs = {}

    def add_periodic_task(self, task_id, interval_seconds, task_func, **kwargs):
        logger.info(
            f'TestScheduler.add_periodic_task is deprecated. '
            f'Use Celery Beat instead. ({task_id})'
        )
        return None

    def add_cron_task(self, task_id, cron_expr, task_func, **kwargs):
        logger.info(
            f'TestScheduler.add_cron_task is deprecated. '
            f'Use Celery Beat instead. ({task_id})'
        )
        return None

    def remove_task(self, task_id):
        pass

    def shutdown_all(self):
        self._jobs.clear()


def init_scheduler(app):
    """
    初始化调度器。
    - 配置 Celery 应用（从 Flask 配置读取 Redis URL）
    - 保留 TestScheduler 实例供 get_scheduler() 调用

    Args:
        app: Flask 应用实例

    Returns:
        TestScheduler 实例
    """
    global _scheduler
    _scheduler = TestScheduler(app)

    # 初始化 Celery — 从 Flask 配置注入 Redis URL
    from app.services.celery_app import init_celery
    init_celery(app)

    logger.info('Scheduler initialized (Celery Beat). '
                'Run: celery -A app.services.celery_app worker -l info')
    return _scheduler


def get_scheduler():
    """获取全局调度器实例"""
    global _scheduler
    return _scheduler
