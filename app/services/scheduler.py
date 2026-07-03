"""
后台任务调度器模块

基于 APScheduler 提供定时任务和周期任务调度能力。
目前包含：
- 周期性清理过期（长时间 running 状态）的测试批次
- 可通过 add_periodic_task / add_cron_task 扩展新的定时任务
"""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# 全局调度器引用，供其他模块获取
_scheduler = None


class TestScheduler:
    """
    测试平台调度器，封装 APScheduler 提供简单易用的任务调度接口。
    支持 interval（周期执行）和 cron（定时执行）两种触发方式。
    """

    def __init__(self, app):
        self.app = app
        self._jobs = {}

    def add_periodic_task(self, task_id: str, interval_seconds: int,
                          task_func, **kwargs):
        """
        添加周期性执行的任务。

        Args:
            task_id: 任务唯一标识
            interval_seconds: 执行间隔（秒）
            task_func: 要执行的任务函数
            **kwargs: 传递给 APScheduler add_job 的额外参数
        """
        from apscheduler.schedulers.background import BackgroundScheduler
        scheduler = BackgroundScheduler(timezone=self.app.config.get(
            'SCHEDULER_TIMEZONE', 'Asia/Shanghai'))

        scheduler.add_job(
            func=task_func,
            trigger='interval',
            seconds=interval_seconds,
            id=task_id,
            replace_existing=True,
            **kwargs
        )
        scheduler.start()
        self._jobs[task_id] = scheduler
        logger.info(f'Scheduled task "{task_id}" every {interval_seconds}s.')
        return scheduler

    def add_cron_task(self, task_id: str, cron_expr: str,
                      task_func, **kwargs):
        """
        添加定时执行的 cron 任务。

        Args:
            task_id: 任务唯一标识
            cron_expr: cron 表达式（5段式：分 时 日 月 周）
            task_func: 要执行的任务函数
            **kwargs: 传递给 APScheduler add_job 的额外参数

        Raises:
            ValueError: cron 表达式格式不正确时抛出
        """
        from apscheduler.schedulers.background import BackgroundScheduler
        scheduler = BackgroundScheduler(timezone=self.app.config.get(
            'SCHEDULER_TIMEZONE', 'Asia/Shanghai'))

        parts = cron_expr.strip().split()
        if len(parts) != 5:
            raise ValueError(
                'Cron expression must have 5 fields: '
                'minute hour day month day_of_week')

        scheduler.add_job(
            func=task_func,
            trigger='cron',
            minute=parts[0], hour=parts[1], day=parts[2],
            month=parts[3], day_of_week=parts[4],
            id=task_id,
            replace_existing=True,
            **kwargs
        )
        scheduler.start()
        self._jobs[task_id] = scheduler
        logger.info(f'Scheduled cron task "{task_id}" ({cron_expr}).')
        return scheduler

    def remove_task(self, task_id: str):
        """移除指定的定时任务"""
        if task_id in self._jobs:
            self._jobs[task_id].shutdown(wait=False)
            del self._jobs[task_id]
            logger.info(f'Removed scheduled task "{task_id}".')

    def shutdown_all(self):
        """停止所有定时任务"""
        for task_id, scheduler in self._jobs.items():
            scheduler.shutdown(wait=False)
        self._jobs.clear()
        logger.info('All schedulers shut down.')


def init_scheduler(app):
    """
    初始化调度器，注册系统级定时任务。

    当前注册的任务：
    - cleanup-expired-runs: 每小时清理一次 running 状态超过1小时的批次

    Args:
        app: Flask 应用实例

    Returns:
        TestScheduler 实例
    """
    global _scheduler
    _scheduler = TestScheduler(app)

    def cleanup_expired_runs():
        """清理超时未完成的测试批次，将其标记为 failed"""
        with app.app_context():
            from app import db
            from app.models import TestRun
            cutoff = datetime.utcnow()
            expired = TestRun.query.filter(
                TestRun.status == 'running',
                TestRun.started_at < cutoff
            ).all()
            for run in expired:
                run.status = 'failed'
            if expired:
                db.session.commit()
                logger.info(
                    f'Cleaned up {len(expired)} stale test runs.')

    # 每小时执行一次清理任务
    _scheduler.add_periodic_task(
        task_id='cleanup-expired-runs',
        interval_seconds=3600,
        task_func=cleanup_expired_runs,
    )

    return _scheduler


def get_scheduler() -> TestScheduler:
    """获取全局调度器实例"""
    global _scheduler
    return _scheduler
