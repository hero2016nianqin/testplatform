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
    process_type = db.Column(db.String(200), default='', comment='工序(多个用逗号分隔)')
    workstation = db.Column(db.String(200), default='', comment='工位(多个用逗号分隔)')
    codes_config = db.Column(db.Text, default='[]', comment='被测编码配置JSON: [{code, process_type, workstation, sequence_id}]')
    type = db.Column(db.String(30), default='standard', comment='版本类型: standard/multi_process/product_family')
    bom_code = db.Column(db.String(200), default='', comment='BOM编码(多工序版本)')
    tps_name = db.Column(db.String(200), default='', comment='TPS名称(多工序版本)')
    domain_tags = db.Column(db.String(500), default='', comment='领域标签')
    inherit_from_id = db.Column(db.Integer, db.ForeignKey('test_versions.id'), nullable=True, comment='继承自哪个版本')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    steps = db.relationship('ReleaseStep', backref='version', lazy='dynamic',
                            cascade='all, delete-orphan', order_by='ReleaseStep.stage, ReleaseStep.step_order')
    archive_items = db.relationship('VersionArchiveItem', backref='version', lazy='dynamic',
                                     cascade='all, delete-orphan')
    deployments = db.relationship('ReleaseDeployment', backref='version', lazy='dynamic',
                                   cascade='all, delete-orphan')
    sub_scenarios = db.relationship('SubScenario', backref='version', lazy='dynamic',
                                     cascade='all, delete-orphan', order_by='SubScenario.sort_order')

    def to_dict(self):
        import json
        codes = []
        try:
            codes = json.loads(self.codes_config or '[]')
        except (json.JSONDecodeError, TypeError):
            codes = []
        try:
            ss_list = [s.to_dict() for s in self.sub_scenarios.order_by(SubScenario.sort_order).all()]
        except Exception:
            ss_list = []
        return {
            'id': self.id,
            'version': self.version,
            'project_name': self.project_name,
            'description': self.description,
            'status': self.status,
            'created_by': self.created_by,
            'sequence_id': self.sequence_id or 0,
            'process_type': self.process_type or '',
            'workstation': self.workstation or '',
            'codes_config': codes,
            'type': self.type or 'standard',
            'bom_code': self.bom_code or '',
            'tps_name': self.tps_name or '',
            'domain_tags': self.domain_tags or '',
            'inherit_from_id': self.inherit_from_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'sub_scenarios': ss_list,
        }


class SubScenario(db.Model):
    """子场景 - 多工序版本中的每个工序-工位组合"""
    __tablename__ = 'sub_scenarios'

    id = db.Column(db.Integer, primary_key=True)
    version_id = db.Column(db.Integer, db.ForeignKey('test_versions.id'), nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False, comment='子场景名称, 如 FT-MP1')
    description = db.Column(db.Text, default='')
    sort_order = db.Column(db.Integer, default=0)
    process_type = db.Column(db.String(100), default='', comment='工序类型(可从名称解析)')
    workstation = db.Column(db.String(100), default='', comment='工位(可从名称解析)')
    sequence_id = db.Column(db.Integer, default=0, comment='关联测试序列 ID')
    hardware_params = db.Column(db.Text, default='{}', comment='硬件参数JSON')
    software_metrics = db.Column(db.Text, default='[]', comment='软件指标JSON数组')
    property_page = db.Column(db.Text, default='{}', comment='属性页JSON')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        import json
        def _load(v, default=None):
            if isinstance(v, str) and v:
                try: return json.loads(v)
                except: return default if default else v
            return v if v else default
        return {
            'id': self.id,
            'version_id': self.version_id,
            'name': self.name,
            'description': self.description or '',
            'sort_order': self.sort_order or 0,
            'process_type': self.process_type or '',
            'workstation': self.workstation or '',
            'sequence_id': self.sequence_id or 0,
            'hardware_params': _load(self.hardware_params, '{}'),
            'software_metrics': _load(self.software_metrics, '[]'),
            'property_page': _load(self.property_page, '{}'),
            'created_at': self.created_at.isoformat() if self.created_at else None,
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


class VersionBinaryFile(db.Model):
    """版本二进制文件 - 存储固件等二进制文件"""
    __tablename__ = 'version_binary_files'

    id = db.Column(db.Integer, primary_key=True)
    version_id = db.Column(db.Integer, db.ForeignKey('test_versions.id'),
                           nullable=False, index=True)
    filename = db.Column(db.String(200), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer, default=0)
    description = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'version_id': self.version_id,
            'filename': self.filename,
            'file_size': self.file_size,
            'description': self.description,
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
