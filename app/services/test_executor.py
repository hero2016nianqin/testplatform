import json
import time
import uuid
from datetime import datetime
from typing import List, Optional, Callable

from app import db, socketio
from app.models import TestItem, TestResult, TestRun


class TestExecutor:
    def __init__(self, operator: str, serial_number: str = '',
                 product_type: str = '', config_id: Optional[int] = None):
        self.operator = operator
        self.serial_number = serial_number
        self.product_type = product_type
        self.config_id = config_id
        self.test_run = None
        self._progress_callback = None

    def on_progress(self, callback: Callable):
        self._progress_callback = callback

    def _emit_progress(self, event: str, data: dict):
        data['batch_id'] = self.test_run.batch_id if self.test_run else None
        socketio.emit(event, data, room=self.test_run.batch_id
                     if self.test_run else None)
        if self._progress_callback:
            self._progress_callback(event, data)

    def start_run(self) -> TestRun:
        batch_id = datetime.utcnow().strftime('%Y%m%d%H%M%S') + '-' + \
                   uuid.uuid4().hex[:8]

        self.test_run = TestRun(
            batch_id=batch_id,
            operator=self.operator,
            serial_number=self.serial_number,
            product_type=self.product_type,
            status='running',
            started_at=datetime.utcnow(),
        )
        db.session.add(self.test_run)
        db.session.commit()

        self._emit_progress('run_started', {
            'batch_id': batch_id,
            'operator': self.operator,
            'serial_number': self.serial_number,
            'started_at': self.test_run.started_at.isoformat(),
        })
        return self.test_run

    def execute_item(self, test_item: TestItem,
                     actual_value: float, remark: str = '',
                     duration_ms: int = 0) -> TestResult:
        if not self.test_run:
            raise RuntimeError('Test run not started. Call start_run() first.')

        passed = test_item.min_value <= actual_value <= test_item.max_value
        deviation = actual_value - test_item.expected_value

        result = TestResult(
            test_item_id=test_item.id,
            test_run_id=self.test_run.id,
            operator=self.operator,
            serial_number=self.serial_number,
            actual_value=actual_value,
            passed=passed,
            deviation=deviation,
            duration_ms=duration_ms,
            remark=remark,
            tested_at=datetime.utcnow(),
        )
        db.session.add(result)
        db.session.commit()

        self.test_run.total_items += 1
        if passed:
            self.test_run.passed_items += 1
        else:
            self.test_run.failed_items += 1
        db.session.commit()

        self._emit_progress('item_tested', {
            'test_item_id': test_item.id,
            'item_name': test_item.name,
            'actual_value': actual_value,
            'expected_value': test_item.expected_value,
            'min_value': test_item.min_value,
            'max_value': test_item.max_value,
            'passed': passed,
            'deviation': deviation,
            'total': self.test_run.total_items,
            'passed_count': self.test_run.passed_items,
            'failed_count': self.test_run.failed_items,
        })
        return result

    def complete_run(self) -> TestRun:
        if not self.test_run:
            raise RuntimeError('No active test run.')

        self.test_run.status = 'completed'
        self.test_run.ended_at = datetime.utcnow()
        db.session.commit()

        self._emit_progress('run_completed', {
            'batch_id': self.test_run.batch_id,
            'total_items': self.test_run.total_items,
            'passed_items': self.test_run.passed_items,
            'failed_items': self.test_run.failed_items,
            'ended_at': self.test_run.ended_at.isoformat(),
        })
        return self.test_run

    def fail_run(self, error_message: str = '') -> TestRun:
        if not self.test_run:
            raise RuntimeError('No active test run.')

        self.test_run.status = 'failed'
        self.test_run.ended_at = datetime.utcnow()
        db.session.commit()

        self._emit_progress('run_failed', {
            'batch_id': self.test_run.batch_id,
            'error': error_message,
            'ended_at': self.test_run.ended_at.isoformat(),
        })
        return self.test_run

    @staticmethod
    def get_run_by_batch(batch_id: str) -> Optional[TestRun]:
        return TestRun.query.filter_by(batch_id=batch_id).first()

    @staticmethod
    def get_results_for_run(run_id: int) -> List[TestResult]:
        return TestResult.query.filter_by(test_run_id=run_id).all()

    @staticmethod
    def get_active_items() -> List[TestItem]:
        return TestItem.query.filter_by(is_active=True)\
            .order_by(TestItem.sort_order).all()
