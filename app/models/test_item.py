from datetime import datetime
from app import db


class TestItem(db.Model):
    __tablename__ = 'test_items'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, index=True)
    description = db.Column(db.Text, default='')
    expected_value = db.Column(db.Float, nullable=False)
    min_value = db.Column(db.Float, nullable=False)
    max_value = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(50), default='')
    category = db.Column(db.String(100), default='general', index=True)
    is_active = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow,
                           onupdate=datetime.utcnow)

    results = db.relationship('TestResult', backref='test_item', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'expected_value': self.expected_value,
            'min_value': self.min_value,
            'max_value': self.max_value,
            'unit': self.unit,
            'category': self.category,
            'is_active': self.is_active,
            'sort_order': self.sort_order,
        }

    def __repr__(self):
        return f'<TestItem {self.name}>'
