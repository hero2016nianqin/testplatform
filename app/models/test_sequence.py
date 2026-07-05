from datetime import datetime
from app import db


class TestItemTemplate(db.Model):
    __tablename__ = 'test_item_templates'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, index=True)
    description = db.Column(db.Text, default='')
    service_address = db.Column(db.String(500), default='')
    is_critical = db.Column(db.Boolean, default=False)
    timeout_seconds = db.Column(db.Integer, default=60)
    category = db.Column(db.String(100), default='general', index=True)
    is_active = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow,
                           onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'service_address': self.service_address,
            'is_critical': self.is_critical,
            'timeout_seconds': self.timeout_seconds,
            'category': self.category,
            'is_active': self.is_active,
            'sort_order': self.sort_order,
        }


class TestSequence(db.Model):
    __tablename__ = 'test_sequences'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, index=True)
    description = db.Column(db.Text, default='')
    version = db.Column(db.String(50), default='1.0')
    is_active = db.Column(db.Boolean, default=True)
    created_by = db.Column(db.String(100), default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow,
                           onupdate=datetime.utcnow)

    steps = db.relationship('TestSequenceStep', backref='sequence',
                            lazy='dynamic',
                            cascade='all, delete-orphan',
                            order_by='TestSequenceStep.step_order')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'version': self.version,
            'is_active': self.is_active,
            'created_by': self.created_by,
            'step_count': self.steps.count(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def to_dict_with_steps(self):
        d = self.to_dict()
        d['steps'] = [s.to_dict() for s in self.steps]
        return d


class TestSequenceStep(db.Model):
    __tablename__ = 'test_sequence_steps'

    id = db.Column(db.Integer, primary_key=True)
    sequence_id = db.Column(db.Integer, db.ForeignKey('test_sequences.id'),
                            nullable=False, index=True)
    template_id = db.Column(db.Integer, db.ForeignKey('test_item_templates.id'),
                            nullable=False)
    step_order = db.Column(db.Integer, nullable=False)
    timeout_seconds = db.Column(db.Integer, default=60)

    template = db.relationship('TestItemTemplate')

    def to_dict(self):
        t = self.template
        return {
            'id': self.id,
            'sequence_id': self.sequence_id,
            'step_order': self.step_order,
            'timeout_seconds': self.timeout_seconds,
            'template_id': self.template_id,
            'template_name': t.name if t else '',
            'template_service_address': t.service_address if t else '',
            'template_is_critical': t.is_critical if t else False,
            'template_category': t.category if t else '',
        }
