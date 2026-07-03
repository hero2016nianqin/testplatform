"""
测试结果模型

记录每条测试项的实际测量结果，包含实测值、合格判定、偏差量、
测试耗时和备注。关联到对应的测试项和测试批次。
"""

from datetime import datetime
from app import db


class TestResult(db.Model):
    """测试结果表 - 存储每次测试的详细测量数据"""

    __tablename__ = 'test_results'

    # 主键，自增 ID
    id = db.Column(db.Integer, primary_key=True)
    # 关联的测试项 ID（外键）
    test_item_id = db.Column(db.Integer, db.ForeignKey('test_items.id'),
                             nullable=False, index=True)
    # 关联的测试批次 ID（外键）
    test_run_id = db.Column(db.Integer, db.ForeignKey('test_runs.id'),
                            nullable=False, index=True)
    # 操作员姓名，用于追溯测试责任人
    operator = db.Column(db.String(100), nullable=False, index=True)
    # 被测产品序列号
    serial_number = db.Column(db.String(200), index=True)
    # 实际测量值
    actual_value = db.Column(db.Float, nullable=False)
    # 是否通过（True = PASS, False = FAIL）
    passed = db.Column(db.Boolean, nullable=False)
    # 与标准值的偏差（actual_value - expected_value）
    deviation = db.Column(db.Float, default=0.0)
    # 该测试项耗时（毫秒）
    duration_ms = db.Column(db.Integer, default=0)
    # 备注信息，记录异常情况或额外说明
    remark = db.Column(db.Text, default='')
    # 测试时间
    tested_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        """序列化为字典，包含关联的测试项名称和标准值"""
        return {
            'id': self.id,
            'test_item_id': self.test_item_id,
            'test_run_id': self.test_run_id,
            'operator': self.operator,
            'serial_number': self.serial_number,
            'actual_value': self.actual_value,
            'passed': self.passed,
            'deviation': self.deviation,
            'duration_ms': self.duration_ms,
            'remark': self.remark,
            'item_name': self.test_item.name if self.test_item else None,
            'expected_value': self.test_item.expected_value
                             if self.test_item else None,
            'tested_at': self.tested_at.isoformat()
                         if self.tested_at else None,
        }

    def __repr__(self):
        return f'<TestResult {self.test_item_id} {"PASS" if self.passed else "FAIL"}>'
