"""
Celery 定时任务定义

这些任务被 celery beat 定时触发，也可手动调用。
"""

import logging
from datetime import datetime

from app.services.celery_app import celery_app
from app import db
from app.models import TestRun

logger = logging.getLogger(__name__)


@celery_app.task
def cleanup_expired_runs():
    """
    清理超时未完成的测试批次（running 状态超过 1 小时）。
    每小时由 celery beat 触发一次。
    """
    from app import create_app
    app = create_app()
    with app.app_context():
        cutoff = datetime.utcnow()
        expired = TestRun.query.filter(
            TestRun.status == 'running',
            TestRun.started_at < cutoff
        ).all()
        for run in expired:
            run.status = 'failed'
        if expired:
            db.session.commit()
            logger.info(f'Cleaned up {len(expired)} stale test runs.')
        return len(expired)


@celery_app.task
def compress_old_logs():
    """
    压缩 30 天前的 .json 日志文件为 .gz 格式。
    每天由 celery beat 触发一次。
    """
    from app import create_app
    app = create_app()
    with app.app_context():
        from app.services.log_service import LogService
        log_folder = app.config.get('LOG_FOLDER', 'logs')
        service = LogService(log_folder)
        service.compress_old_logs(days_old=30)
        logger.info('Old logs compressed.')
        return True
