from datetime import datetime
from app import db


class TestVersion(db.Model):
    __tablename__ = 'test_versions'

    id = db.Column(db.Integer, primary_key=True)
    version = db.Column(db.String(50), nullable=False, index=True)
    project_name = db.Column(db.String(200), default='', index=True)
    description = db.Column(db.Text, default='')
    status = db.Column(db.String(30), default='draft', index=True)
    created_by = db.Column(db.String(100), default='')
    sequence_id = db.Column(db.Integer, default=0, comment='关联测试序列 ID')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    steps = db.relationship('ReleaseStep', backref='version', lazy='dynamic',
                            cascade='all, delete-orphan', order_by='ReleaseStep.stage, ReleaseStep.step_order')
    archive_items = db.relationship('VersionArchiveItem', backref='version', lazy='dynamic',
                                     cascade='all, delete-orphan')
    deployments = db.relationship('ReleaseDeployment', backref='version', lazy='dynamic',
                                   cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'version': self.version,
            'project_name': self.project_name,
            'description': self.description,
            'status': self.status,
            'created_by': self.created_by,
            'sequence_id': self.sequence_id or 0,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class ReleaseStep(db.Model):
    __tablename__ = 'release_steps'

    id = db.Column(db.Integer, primary_key=True)
    version_id = db.Column(db.Integer, db.ForeignKey('test_versions.id'), nullable=False, index=True)
    stage = db.Column(db.Integer, nullable=False)
    step_order = db.Column(db.Integer, nullable=False)
    step_name = db.Column(db.String(100), nullable=False)
    approver_role = db.Column(db.String(50), default='')
    assigned_to = db.Column(db.String(100), default='')
    status = db.Column(db.String(20), default='pending')
    approved_by = db.Column(db.String(100), default='')
    approved_at = db.Column(db.DateTime, nullable=True)
    comment = db.Column(db.Text, default='')

    def to_dict(self):
        return {
            'id': self.id,
            'version_id': self.version_id,
            'stage': self.stage,
            'step_order': self.step_order,
            'step_name': self.step_name,
            'approver_role': self.approver_role,
            'assigned_to': self.assigned_to,
            'status': self.status,
            'approved_by': self.approved_by,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'comment': self.comment,
        }


class VersionArchiveItem(db.Model):
    __tablename__ = 'version_archive_items'

    id = db.Column(db.Integer, primary_key=True)
    version_id = db.Column(db.Integer, db.ForeignKey('test_versions.id'), nullable=False, index=True)
    type = db.Column(db.String(50), nullable=False)
    item_id = db.Column(db.Integer, nullable=True)
    data_snapshot = db.Column(db.Text, default='{}')

    def to_dict(self):
        return {
            'id': self.id,
            'version_id': self.version_id,
            'type': self.type,
            'item_id': self.item_id,
            'data_snapshot': self.data_snapshot,
        }


class ReleaseDeployment(db.Model):
    __tablename__ = 'release_deployments'

    id = db.Column(db.Integer, primary_key=True)
    version_id = db.Column(db.Integer, db.ForeignKey('test_versions.id'), nullable=False, index=True)
    factory_id = db.Column(db.Integer, nullable=True)
    factory_name = db.Column(db.String(200), default='')
    line_id = db.Column(db.Integer, nullable=True)
    line_name = db.Column(db.String(200), default='')
    station_id = db.Column(db.Integer, nullable=True)
    station_name = db.Column(db.String(200), default='')
    assigned_to = db.Column(db.String(100), default='')
    status = db.Column(db.String(20), default='pending')
    approved_by = db.Column(db.String(100), default='')
    approved_at = db.Column(db.DateTime, nullable=True)
    comment = db.Column(db.Text, default='')
    deployed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'version_id': self.version_id,
            'factory_id': self.factory_id,
            'factory_name': self.factory_name,
            'line_id': self.line_id,
            'line_name': self.line_name,
            'station_id': self.station_id,
            'station_name': self.station_name,
            'assigned_to': self.assigned_to,
            'status': self.status,
            'approved_by': self.approved_by,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'comment': self.comment,
            'deployed_at': self.deployed_at.isoformat() if self.deployed_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
