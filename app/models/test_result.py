from datetime import datetime
from app import db


class TestResult(db.Model):
    __tablename__ = 'test_results'

    id = db.Column(db.Integer, primary_key=True)
    test_item_id = db.Column(db.Integer, db.ForeignKey('test_items.id'),
                             nullable=False, index=True)
    test_run_id = db.Column(db.Integer, db.ForeignKey('test_runs.id'),
                            nullable=False, index=True)
    operator = db.Column(db.String(100), nullable=False, index=True)
    serial_number = db.Column(db.String(200), index=True)
    actual_value = db.Column(db.Float, nullable=False)
    passed = db.Column(db.Boolean, nullable=False)
    deviation = db.Column(db.Float, default=0.0)
    duration_ms = db.Column(db.Integer, default=0)
    remark = db.Column(db.Text, default='')
    tested_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
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
