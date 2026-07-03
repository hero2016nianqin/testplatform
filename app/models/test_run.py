from datetime import datetime
from app import db


class TestRun(db.Model):
    __tablename__ = 'test_runs'

    id = db.Column(db.Integer, primary_key=True)
    batch_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    product_type = db.Column(db.String(100), default='')
    serial_number = db.Column(db.String(200), index=True)
    operator = db.Column(db.String(100), nullable=False, index=True)
    status = db.Column(
        db.String(20), default='pending', index=True
    )
    total_items = db.Column(db.Integer, default=0)
    passed_items = db.Column(db.Integer, default=0)
    failed_items = db.Column(db.Integer, default=0)
    started_at = db.Column(db.DateTime, nullable=True)
    ended_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    results = db.relationship('TestResult', backref='test_run', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'batch_id': self.batch_id,
            'product_type': self.product_type,
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
