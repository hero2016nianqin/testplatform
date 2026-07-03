from datetime import datetime
from app import db


class TestConfig(db.Model):
    __tablename__ = 'test_configs'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, unique=True)
    description = db.Column(db.Text, default='')
    config_data = db.Column(db.Text, default='{}')
    version = db.Column(db.String(50), default='1.0')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow,
                           onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'version': self.version,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat()
                          if self.created_at else None,
            'updated_at': self.updated_at.isoformat()
                          if self.updated_at else None,
        }

    def __repr__(self):
        return f'<TestConfig {self.name} v{self.version}>'
