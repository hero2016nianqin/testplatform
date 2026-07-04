"""
测试执行器服务模块

管理一次测试执行的完整生命周期：开始批次 → 逐项执行 → 完成/失败。
通过 SocketIO 实时推送执行进度到前端，支持回调机制通知调用方。
"""

import json
import time
import uuid
from datetime import datetime
from typing import List, Optional, Callable

from app import db, socketio
from app.models import TestItem, TestResult, TestRun


class TestExecutor:
    """
    测试执行器，封装单次测试批次的执行逻辑。

    使用示例:
        executor = TestExecutor(operator='张三', serial_number='SN001')
        run = executor.start_run()
        result = executor.execute_item(item, actual_value=4.95)
        run = executor.complete_run()
    """

    def __init__(self, operator: str, serial_number: str = '',
                 product_type: str = '', config_id: Optional[int] = None,
                 station_id: Optional[int] = None,
                 slot_id: Optional[int] = None,
                 task_order: str = ''):
        self.operator = operator
        self.serial_number = serial_number
        self.product_type = product_type
        self.config_id = config_id
        self.station_id = station_id
        self.slot_id = slot_id
        self.task_order = task_order
        self.test_run = None
        self._progress_callback = None

    def on_progress(self, callback: Callable):
        """
        注册进度回调函数，每次状态变化时触发。
        回调签名: callback(event_name: str, data: dict)
        """
        self._progress_callback = callback

    def _emit_progress(self, event: str, data: dict):
        """
        通过 SocketIO 推送进度事件，同时调用注册的回调。

        Args:
            event: 事件名称（run_started / item_tested / run_completed / run_failed）
            data: 事件数据字典
        """
        data['batch_id'] = self.test_run.batch_id if self.test_run else None
        socketio.emit(event, data, room=self.test_run.batch_id
                     if self.test_run else None)
        if self._progress_callback:
            self._progress_callback(event, data)

    def start_run(self) -> TestRun:
        """
        启动新的测试批次，生成唯一批次号并持久化到数据库。

        Returns:
            创建的 TestRun 实例
        """
        # 生成唯一批次号：时间戳 + 随机8位hex
        batch_id = datetime.utcnow().strftime('%Y%m%d%H%M%S') + '-' + \
                   uuid.uuid4().hex[:8]

        self.test_run = TestRun(
            batch_id=batch_id,
            operator=self.operator,
            serial_number=self.serial_number,
            product_type=self.product_type,
            task_order=self.task_order,
            status='running',
            started_at=datetime.utcnow(),
            station_id=self.station_id,
            slot_id=self.slot_id,
        )
        db.session.add(self.test_run)
        db.session.commit()

        # 通知前端批次已启动
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
        """
        执行单个测试项，判定合格/不合格并记录结果。

        Args:
            test_item: 要执行的测试项对象
            actual_value: 实测值
            remark: 备注信息（可选）
            duration_ms: 测试耗时（毫秒）

        Returns:
            创建的 TestResult 实例

        Raises:
            RuntimeError: 未调用 start_run 时抛出
        """
        if not self.test_run:
            raise RuntimeError('Test run not started. Call start_run() first.')

        # 判定：实测值是否在 [min_value, max_value] 范围内
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

        # 更新批次统计计数
        self.test_run.total_items += 1
        if passed:
            self.test_run.passed_items += 1
        else:
            self.test_run.failed_items += 1
        db.session.commit()

        # 通知前端单项测试完成
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
        """
        将当前批次标记为已完成。

        Returns:
            更新后的 TestRun 实例
        """
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
        """
        将当前批次标记为失败（异常中断时使用）。

        Args:
            error_message: 错误描述

        Returns:
            更新后的 TestRun 实例
        """
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
        """根据批次号查询测试批次"""
        return TestRun.query.filter_by(batch_id=batch_id).first()

    @staticmethod
    def get_results_for_run(run_id: int) -> List[TestResult]:
        """获取指定批次的所有测试结果"""
        return TestResult.query.filter_by(test_run_id=run_id).all()

    @staticmethod
    def get_active_items() -> List[TestItem]:
        """获取所有启用的测试项（按排序序号排列）"""
        return TestItem.query.filter_by(is_active=True)\
            .order_by(TestItem.sort_order).all()
