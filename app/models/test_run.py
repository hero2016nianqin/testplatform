"""
测试批次模型

记录一次完整的测试执行批次，包含批次号、操作员、被测产品信息、
整体执行状态（pending/running/completed/failed）以及通过/失败统计。
"""

from datetime import datetime
from app import db


class TestRun(db.Model):
    """测试批次表 - 跟踪一次测试执行的全生命周期"""

    __tablename__ = 'test_runs'

    # 主键，自增 ID
    id = db.Column(db.Integer, primary_key=True)
    # 批次号（全局唯一），格式：yyyyMMddHHmmss-随机8位hex
    batch_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    # 产品型号，用于区分不同产品的测试标准
    product_type = db.Column(db.String(100), default='')
    # 任务令号（工单号）
    task_order = db.Column(db.String(100), default='', index=True)
    # 被测产品序列号
    serial_number = db.Column(db.String(200), index=True)
    # 操作员姓名
    operator = db.Column(db.String(100), nullable=False, index=True)
    # 执行状态: pending(待执行) / running(执行中) / completed(已完成) / failed(已失败)
    status = db.Column(db.String(20), default='pending', index=True)
    # 总测试项数量
    total_items = db.Column(db.Integer, default=0)
    # 通过项数量
    passed_items = db.Column(db.Integer, default=0)
    # 失败项数量
    failed_items = db.Column(db.Integer, default=0)
    # 开始时间
    started_at = db.Column(db.DateTime, nullable=True)
    # 结束时间
    ended_at = db.Column(db.DateTime, nullable=True)
    # 关联的工站 ID 和槽位 ID（方便按装备/槽位查询）
    station_id = db.Column(db.Integer, db.ForeignKey('test_stations.id'),
                           nullable=True, index=True)
    slot_id = db.Column(db.Integer, db.ForeignKey('test_slots.id'),
                        nullable=True, index=True)
    # 记录创建时间
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 关联的测试结果列表（一对多关系）
    results = db.relationship('TestResult', backref='test_run', lazy='dynamic')

    def to_dict(self):
        """序列化为字典"""
        return {
            'id': self.id,
            'batch_id': self.batch_id,
            'product_type': self.product_type,
            'task_order': self.task_order,
            'serial_number': self.serial_number,
            'operator': self.operator,
            'status': self.status,
            'total_items': self.total_items,
            'passed_items': self.passed_items,
            'failed_items': self.failed_items,
            'started_at': self.started_at.isoformat()
                          if self.started_at else None,
            'ended_at': self.ended_at.isoformat()
                        if self.ended_at else None,
            'created_at': self.created_at.isoformat()
                          if self.created_at else None,
        }

    def __repr__(self):
        return f'<TestRun {self.batch_id} [{self.status}]>'
