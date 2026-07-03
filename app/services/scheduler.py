import logging
from datetime import datetime

logger = logging.getLogger(__name__)

_scheduler = None


class TestScheduler:
    def __init__(self, app):
        self.app = app
        self._jobs = {}

    def add_periodic_task(self, task_id: str, interval_seconds: int,
                          task_func, **kwargs):
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
        logger.info(
            f'Scheduled task "{task_id}" every {interval_seconds}s.')
        return scheduler

    def add_cron_task(self, task_id: str, cron_expr: str,
                      task_func, **kwargs):
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
        if task_id in self._jobs:
            self._jobs[task_id].shutdown(wait=False)
            del self._jobs[task_id]
            logger.info(f'Removed scheduled task "{task_id}".')

    def shutdown_all(self):
        for task_id, scheduler in self._jobs.items():
            scheduler.shutdown(wait=False)
        self._jobs.clear()
        logger.info('All schedulers shut down.')


def init_scheduler(app):
    global _scheduler
    _scheduler = TestScheduler(app)

    def cleanup_expired_runs():
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

    _scheduler.add_periodic_task(
        task_id='cleanup-expired-runs',
        interval_seconds=3600,
        task_func=cleanup_expired_runs,
    )

    return _scheduler


def get_scheduler() -> TestScheduler:
    global _scheduler
    return _scheduler
