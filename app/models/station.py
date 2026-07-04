"""
工站/机框/槽位模型及各项配置模型

层级结构: 厂区(Factory) → 线体(Line) → 装备(TestStation) → 机框(Chassis) → 槽位(Slot)
每个装备（测试工站）包含四类配置：装备参数、硬件参数、软件参数、场景参数
"""

from datetime import datetime
from app import db


class Factory(db.Model):
    """厂区 - 最顶层组织单元"""
    __tablename__ = 'factories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    code = db.Column(db.String(50), unique=True, nullable=True, comment='厂区编码')
    description = db.Column(db.Text, default='')
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow,
                           onupdate=datetime.utcnow)

    lines = db.relationship('ProductionLine', backref='factory',
                            lazy='dynamic', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'code': self.code,
            'description': self.description,
            'sort_order': self.sort_order,
            'line_count': self.lines.count(),
        }

    def __repr__(self):
        return f'<Factory {self.name}>'


class ProductionLine(db.Model):
    """线体 - 属于厂区，包含多个装备"""
    __tablename__ = 'production_lines'

    id = db.Column(db.Integer, primary_key=True)
    factory_id = db.Column(db.Integer, db.ForeignKey('factories.id'),
                           nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(50), nullable=True, comment='线体编码')
    description = db.Column(db.Text, default='')
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow,
                           onupdate=datetime.utcnow)

    stations = db.relationship('TestStation', backref='line',
                               lazy='dynamic', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'factory_id': self.factory_id,
            'name': self.name,
            'code': self.code,
            'description': self.description,
            'sort_order': self.sort_order,
            'station_count': self.stations.count(),
            'factory_name': self.factory.name if self.factory else '',
        }

    def __repr__(self):
        return f'<ProductionLine {self.name}>'


class TestStation(db.Model):
    """测试工站（装备） - 属于线体，包含机框和槽位"""
    __tablename__ = 'test_stations'

    id = db.Column(db.Integer, primary_key=True)
    line_id = db.Column(db.Integer, db.ForeignKey('production_lines.id'),
                        nullable=True, index=True)
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    code = db.Column(db.String(50), nullable=True, comment='装备编码')
    description = db.Column(db.Text, default='')
    # 是否有设置标记（调出设置界面）
    has_settings = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow,
                           onupdate=datetime.utcnow)

    chassis = db.relationship('TestChassis', backref='station',
                              lazy='dynamic', cascade='all, delete-orphan')
    equipment_config = db.relationship('EquipmentConfig', uselist=False,
                                       backref='station', cascade='all, delete-orphan')
    hardware_params = db.relationship('HardwareParam', backref='station',
                                      cascade='all, delete-orphan')
    software_config = db.relationship('SoftwareConfig', uselist=False,
                                      backref='station', cascade='all, delete-orphan')
    scenario_config = db.relationship('ScenarioConfig', uselist=False,
                                      backref='station', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'line_id': self.line_id,
            'name': self.name,
            'code': self.code,
            'description': self.description,
            'has_settings': self.has_settings,
            'sort_order': self.sort_order,
            'chassis_count': self.chassis.count(),
            'line_name': self.line.name if self.line else '',
            'factory_name': self.line.factory.name if self.line and self.line.factory else '',
        }

    def __repr__(self):
        return f'<TestStation {self.name}>'


class TestChassis(db.Model):
    """机框 - 属于工站，包含多个槽位"""
    __tablename__ = 'test_chassis'

    id = db.Column(db.Integer, primary_key=True)
    station_id = db.Column(db.Integer, db.ForeignKey('test_stations.id'),
                           nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    slot_count = db.Column(db.Integer, default=1)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    slots = db.relationship('TestSlot', backref='chassis',
                            lazy='dynamic', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'station_id': self.station_id,
            'name': self.name,
            'slot_count': self.slot_count,
            'sort_order': self.sort_order,
            'slot_count_actual': self.slots.count(),
        }

    def __repr__(self):
        return f'<TestChassis {self.name}>'


class TestSlot(db.Model):
    """槽位 - 最小测试单元"""
    __tablename__ = 'test_slots'

    id = db.Column(db.Integer, primary_key=True)
    chassis_id = db.Column(db.Integer, db.ForeignKey('test_chassis.id'),
                           nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    # 槽位状态: idle/testing/pass/fail/disabled
    status = db.Column(db.String(20), default='idle', index=True)
    # 当前正在此槽位测试的批次号
    current_batch_id = db.Column(db.String(50), nullable=True)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'chassis_id': self.chassis_id,
            'name': self.name,
            'status': self.status,
            'current_batch_id': self.current_batch_id,
            'sort_order': self.sort_order,
        }

    def __repr__(self):
        return f'<TestSlot {self.name} [{self.status}]>'


# ==================== 装备参数 ====================

class EquipmentConfig(db.Model):
    """装备参数配置 - 每个工站一条"""
    __tablename__ = 'equipment_configs'

    id = db.Column(db.Integer, primary_key=True)
    station_id = db.Column(db.Integer, db.ForeignKey('test_stations.id'),
                           nullable=False, unique=True)

    # ---- 公共属性 ----
    auto_load_enabled = db.Column(db.Boolean, default=False)
    debug_mode_enabled = db.Column(db.Boolean, default=False)
    equipment_ip = db.Column(db.String(50), default='192.168.1.100')
    equipment_service_address = db.Column(db.String(200), default='')
    process_control_enabled = db.Column(db.Boolean, default=True)

    # ---- 通用属性 ----
    test_mode_normal = db.Column(db.Boolean, default=True, comment='正常测试')
    test_mode_verify = db.Column(db.Boolean, default=False, comment='验证测试')
    test_mode_calibration = db.Column(db.Boolean, default=False, comment='校准测试')
    barcode_verify_enabled = db.Column(db.Boolean, default=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow,
                           onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'station_id': self.station_id,
            # 公共属性
            'auto_load_enabled': self.auto_load_enabled,
            'debug_mode_enabled': self.debug_mode_enabled,
            'equipment_ip': self.equipment_ip,
            'equipment_service_address': self.equipment_service_address,
            'process_control_enabled': self.process_control_enabled,
            # 通用属性
            'test_mode_normal': self.test_mode_normal,
            'test_mode_verify': self.test_mode_verify,
            'test_mode_calibration': self.test_mode_calibration,
            'barcode_verify_enabled': self.barcode_verify_enabled,
        }


# ==================== 硬件参数 ====================

class HardwareParam(db.Model):
    """硬件参数 - key-value 对形式，每个工站多条"""
    __tablename__ = 'hardware_params'

    id = db.Column(db.Integer, primary_key=True)
    station_id = db.Column(db.Integer, db.ForeignKey('test_stations.id'),
                           nullable=False, index=True)
    # 参数名（左侧显示）
    param_name = db.Column(db.String(200), nullable=False)
    # 参数值（右侧显示）
    param_value = db.Column(db.String(500), default='')
    # 分组标签
    group_name = db.Column(db.String(100), default='default')
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'station_id': self.station_id,
            'param_name': self.param_name,
            'param_value': self.param_value,
            'group_name': self.group_name,
            'sort_order': self.sort_order,
        }


# ==================== 软件参数 ====================

class SoftwareConfig(db.Model):
    """软件参数配置 - 每个工站一条"""
    __tablename__ = 'software_configs'

    id = db.Column(db.Integer, primary_key=True)
    station_id = db.Column(db.Integer, db.ForeignKey('test_stations.id'),
                           nullable=False, unique=True)
    # 被测物版本信息
    dut_version = db.Column(db.String(100), default='')
    dut_firmware_version = db.Column(db.String(100), default='')
    dut_hardware_version = db.Column(db.String(100), default='')
    # 可勾选的测试项目 ID 集合 (JSON 数组)
    selected_test_item_ids = db.Column(db.Text, default='[]')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow,
                           onupdate=datetime.utcnow)

    def to_dict(self):
        import json
        return {
            'id': self.id,
            'station_id': self.station_id,
            'dut_version': self.dut_version,
            'dut_firmware_version': self.dut_firmware_version,
            'dut_hardware_version': self.dut_hardware_version,
            'selected_test_item_ids': json.loads(
                self.selected_test_item_ids or '[]'),
        }


# ==================== 场景参数 ====================

class ScenarioConfig(db.Model):
    """场景参数配置 - 每个工站一条"""
    __tablename__ = 'scenario_configs'

    id = db.Column(db.Integer, primary_key=True)
    station_id = db.Column(db.Integer, db.ForeignKey('test_stations.id'),
                           nullable=False, unique=True)
    # 场景参数以 JSON 格式存储（灵活扩展）
    scenario_data = db.Column(db.Text, default='{}')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow,
                           onupdate=datetime.utcnow)

    def to_dict(self):
        import json
        return {
            'id': self.id,
            'station_id': self.station_id,
            'scenario_data': json.loads(self.scenario_data or '{}'),
        }
