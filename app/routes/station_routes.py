"""
工站/机框/槽位管理及配置 API 路由模块

提供测试工站层级结构的 CRUD，以及各配置项的管理接口。
配置分为四类：装备参数、硬件参数、软件参数、场景参数。
"""

import json
from datetime import datetime
from flask import Blueprint, request, jsonify
from sqlalchemy import or_

from app import db
from app.models.station import (
    Factory, ProductionLine,
    TestStation, TestChassis, TestSlot,
    EquipmentConfig, HardwareParam, SoftwareConfig, ScenarioConfig,
)
from app.models import TestItem
from app.auth import process_required, login_required

station_bp = Blueprint('stations', __name__)


# ==================== 厂区管理 ====================

@station_bp.route('/factories', methods=['GET'])
@login_required
def list_factories():
    """获取所有厂区列表"""
    factories = Factory.query.order_by(Factory.sort_order).all()
    return jsonify({'code': 0, 'data': [f.to_dict() for f in factories],
                    'total': len(factories)})


@station_bp.route('/factories', methods=['POST'])
@process_required
def create_factory():
    """创建厂区"""
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    if not name:
        return jsonify({'code': 1, 'message': '厂区名称不能为空'}), 400
    if Factory.query.filter_by(name=name).first():
        return jsonify({'code': 1, 'message': '厂区名称已存在'}), 409
    f = Factory(name=name, code=data.get('code', '').strip(),
                description=data.get('description', ''),
                sort_order=data.get('sort_order', 0))
    db.session.add(f)
    db.session.commit()
    return jsonify({'code': 0, 'data': f.to_dict(), 'message': '创建成功'})


@station_bp.route('/factories/<int:factory_id>', methods=['PUT'])
@process_required
def update_factory(factory_id):
    """更新厂区"""
    f = Factory.query.get_or_404(factory_id)
    data = request.get_json() or {}
    for field in ['name', 'code', 'description', 'sort_order']:
        if field in data:
            setattr(f, field, data[field])
    f.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'code': 0, 'data': f.to_dict(), 'message': '已更新'})


@station_bp.route('/factories/<int:factory_id>', methods=['DELETE'])
@process_required
def delete_factory(factory_id):
    """删除厂区（级联删除线体和装备）"""
    f = Factory.query.get_or_404(factory_id)
    db.session.delete(f)
    db.session.commit()
    return jsonify({'code': 0, 'message': '已删除'})


# ==================== 线体管理 ====================

@station_bp.route('/factories/<int:factory_id>/lines', methods=['GET'])
@login_required
def list_lines(factory_id):
    """获取厂区下的线体列表"""
    lines = ProductionLine.query.filter_by(factory_id=factory_id)\
        .order_by(ProductionLine.sort_order).all()
    return jsonify({'code': 0, 'data': [l.to_dict() for l in lines],
                    'total': len(lines)})


@station_bp.route('/lines', methods=['POST'])
@process_required
def create_line():
    """创建线体"""
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    factory_id = data.get('factory_id')
    if not name or not factory_id:
        return jsonify({'code': 1, 'message': '线体名称和厂区不能为空'}), 400
    if not Factory.query.get(factory_id):
        return jsonify({'code': 1, 'message': '厂区不存在'}), 404
    line = ProductionLine(factory_id=factory_id, name=name,
                          code=data.get('code', '').strip(),
                          description=data.get('description', ''),
                          sort_order=data.get('sort_order', 0))
    db.session.add(line)
    db.session.commit()
    return jsonify({'code': 0, 'data': line.to_dict(), 'message': '创建成功'})


@station_bp.route('/lines/<int:line_id>', methods=['PUT'])
@process_required
def update_line(line_id):
    """更新线体"""
    line = ProductionLine.query.get_or_404(line_id)
    data = request.get_json() or {}
    for field in ['name', 'code', 'description', 'sort_order', 'factory_id']:
        if field in data:
            setattr(line, field, data[field])
    line.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'code': 0, 'data': line.to_dict(), 'message': '已更新'})


@station_bp.route('/lines/<int:line_id>', methods=['DELETE'])
@process_required
def delete_line(line_id):
    """删除线体（级联删除装备）"""
    line = ProductionLine.query.get_or_404(line_id)
    db.session.delete(line)
    db.session.commit()
    return jsonify({'code': 0, 'message': '已删除'})


# ==================== 完整层级查询 ====================

@station_bp.route('/hierarchy', methods=['GET'])
@login_required
def get_hierarchy():
    """获取完整层级：厂区→线体→装备"""
    factories = Factory.query.order_by(Factory.sort_order).all()
    result = []
    for f in factories:
        fd = f.to_dict()
        lines = ProductionLine.query.filter_by(factory_id=f.id)\
            .order_by(ProductionLine.sort_order).all()
        fd['lines'] = []
        for l in lines:
            ld = l.to_dict()
            stations = TestStation.query.filter_by(line_id=l.id)\
                .order_by(TestStation.sort_order).all()
            ld['stations'] = [s.to_dict() for s in stations]
            fd['lines'].append(ld)
        result.append(fd)
    return jsonify({'code': 0, 'data': result, 'total': len(result)})


# ==================== 工站管理 ====================

@station_bp.route('', methods=['GET'])
@login_required
def list_stations():
    """获取所有测试工站列表"""
    stations = TestStation.query.order_by(TestStation.sort_order).all()
    return jsonify({
        'code': 0,
        'data': [s.to_dict() for s in stations],
        'total': len(stations),
    })


@station_bp.route('', methods=['POST'])
@process_required
def create_station():
    """创建测试工站"""
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    if not name:
        return jsonify({'code': 1, 'message': '工站名称不能为空'}), 400
    if TestStation.query.filter_by(name=name).first():
        return jsonify({'code': 1, 'message': '工站名称已存在'}), 409

    station = TestStation(
        name=name,
        description=data.get('description', ''),
        sort_order=data.get('sort_order', 0),
    )
    db.session.add(station)
    db.session.flush()  # 获取 id

    # 自动创建默认配置
    equip = EquipmentConfig(station_id=station.id)
    db.session.add(equip)
    sw = SoftwareConfig(station_id=station.id)
    db.session.add(sw)
    sc = ScenarioConfig(station_id=station.id)
    db.session.add(sc)

    db.session.commit()
    return jsonify({'code': 0, 'data': station.to_dict(),
                    'message': '工站创建成功'})


@station_bp.route('/<int:station_id>', methods=['GET'])
@login_required
def get_station(station_id):
    """获取工站完整信息（含所有配置）"""
    station = TestStation.query.get_or_404(station_id)
    result = station.to_dict()
    result['chassis'] = [c.to_dict() for c in
                         station.chassis.order_by(TestChassis.sort_order).all()]
    return jsonify({'code': 0, 'data': result})


@station_bp.route('/<int:station_id>', methods=['PUT'])
@process_required
def update_station(station_id):
    """更新工站基本信息"""
    station = TestStation.query.get_or_404(station_id)
    data = request.get_json() or {}
    for field in ['name', 'description', 'has_settings', 'sort_order']:
        if field in data:
            setattr(station, field, data[field])
    station.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'code': 0, 'data': station.to_dict(),
                    'message': '已更新'})


@station_bp.route('/<int:station_id>', methods=['DELETE'])
@process_required
def delete_station(station_id):
    """删除工站（级联删除所有关联数据）"""
    station = TestStation.query.get_or_404(station_id)
    db.session.delete(station)
    db.session.commit()
    return jsonify({'code': 0, 'message': '已删除'})


# ==================== 机框管理 ====================

@station_bp.route('/<int:station_id>/chassis', methods=['GET'])
@login_required
def list_chassis(station_id):
    """获取工站下的机框列表（含槽位）"""
    chassis_list = TestChassis.query.filter_by(station_id=station_id)\
        .order_by(TestChassis.sort_order).all()
    data = []
    for c in chassis_list:
        d = c.to_dict()
        d['slots'] = [s.to_dict() for s in
                      c.slots.order_by(TestSlot.sort_order).all()]
        data.append(d)
    return jsonify({'code': 0, 'data': data, 'total': len(data)})


@station_bp.route('/<int:station_id>/chassis', methods=['POST'])
@process_required
def create_chassis(station_id):
    """创建机框"""
    station = TestStation.query.get_or_404(station_id)
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    if not name:
        return jsonify({'code': 1, 'message': '机框名称不能为空'}), 400

    chassis = TestChassis(
        station_id=station_id,
        name=name,
        slot_count=data.get('slot_count', 1),
        sort_order=data.get('sort_order', 0),
    )
    db.session.add(chassis)
    db.session.flush()

    # 自动创建对应数量的槽位
    for i in range(1, chassis.slot_count + 1):
        slot = TestSlot(
            chassis_id=chassis.id,
            name=f'Slot {i}',
            sort_order=i,
        )
        db.session.add(slot)

    db.session.commit()
    return jsonify({'code': 0, 'data': chassis.to_dict(),
                    'message': '机框创建成功'})


@station_bp.route('/chassis/<int:chassis_id>', methods=['PUT'])
@process_required
def update_chassis(chassis_id):
    """更新机框"""
    chassis = TestChassis.query.get_or_404(chassis_id)
    data = request.get_json() or {}
    for field in ['name', 'sort_order']:
        if field in data:
            setattr(chassis, field, data[field])
    if 'slot_count' in data:
        new_count = int(data['slot_count'])
        current = chassis.slots.count()
        if new_count > current:
            for i in range(current + 1, new_count + 1):
                slot = TestSlot(
                    chassis_id=chassis.id,
                    name=f'Slot {i}',
                    sort_order=i,
                )
                db.session.add(slot)
        chassis.slot_count = new_count
    db.session.commit()
    return jsonify({'code': 0, 'data': chassis.to_dict(),
                    'message': '已更新'})


@station_bp.route('/chassis/<int:chassis_id>', methods=['DELETE'])
@process_required
def delete_chassis(chassis_id):
    """删除机框"""
    chassis = TestChassis.query.get_or_404(chassis_id)
    db.session.delete(chassis)
    db.session.commit()
    return jsonify({'code': 0, 'message': '已删除'})


# ==================== 槽位管理 ====================

@station_bp.route('/slots/<int:slot_id>', methods=['PUT'])
@login_required
def update_slot(slot_id):
    """更新槽位状态"""
    slot = TestSlot.query.get_or_404(slot_id)
    data = request.get_json() or {}
    if 'status' in data:
        slot.status = data['status']
    if 'current_batch_id' in data:
        slot.current_batch_id = data['current_batch_id']
    db.session.commit()
    return jsonify({'code': 0, 'data': slot.to_dict(),
                    'message': '已更新'})


# ==================== 装备参数配置 ====================

@station_bp.route('/<int:station_id>/equipment', methods=['GET'])
@login_required
def get_equipment_config(station_id):
    """获取装备参数"""
    config = EquipmentConfig.query.filter_by(station_id=station_id).first()
    if not config:
        config = EquipmentConfig(station_id=station_id)
        db.session.add(config)
        db.session.commit()
    return jsonify({'code': 0, 'data': config.to_dict()})


@station_bp.route('/<int:station_id>/equipment', methods=['PUT'])
@process_required
def update_equipment_config(station_id):
    """更新装备参数"""
    config = EquipmentConfig.query.filter_by(station_id=station_id).first()
    if not config:
        config = EquipmentConfig(station_id=station_id)
        db.session.add(config)
    data = request.get_json() or {}
    for field in [
        'auto_load_enabled', 'debug_mode_enabled',
        'equipment_ip', 'equipment_service_address',
        'process_control_enabled',
        'test_mode_normal', 'test_mode_verify', 'test_mode_calibration',
        'barcode_verify_enabled',
    ]:
        if field in data:
            if isinstance(getattr(config, field), bool):
                setattr(config, field, bool(data[field]))
            else:
                setattr(config, field, data[field])
    config.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'code': 0, 'data': config.to_dict(),
                    'message': '装备参数已更新'})


# ==================== 硬件参数配置 ====================

@station_bp.route('/<int:station_id>/hardware', methods=['GET'])
@login_required
def list_hardware_params(station_id):
    """获取硬件参数列表（按分组）"""
    params = HardwareParam.query.filter_by(station_id=station_id)\
        .order_by(HardwareParam.group_name, HardwareParam.sort_order).all()
    groups = {}
    for p in params:
        g = p.group_name or 'default'
        if g not in groups:
            groups[g] = []
        groups[g].append(p.to_dict())
    return jsonify({
        'code': 0,
        'data': {
            'groups': groups,
            'items': [p.to_dict() for p in params],
            'total': len(params),
        }
    })


@station_bp.route('/<int:station_id>/hardware', methods=['POST'])
@process_required
def add_hardware_param(station_id):
    """添加硬件参数"""
    data = request.get_json() or {}
    param = HardwareParam(
        station_id=station_id,
        param_name=data.get('param_name', '').strip(),
        param_value=data.get('param_value', ''),
        group_name=data.get('group_name', 'default'),
        sort_order=data.get('sort_order', 0),
    )
    if not param.param_name:
        return jsonify({'code': 1, 'message': '参数名不能为空'}), 400
    db.session.add(param)
    db.session.commit()
    return jsonify({'code': 0, 'data': param.to_dict(),
                    'message': '已添加'})


@station_bp.route('/hardware/<int:param_id>', methods=['PUT'])
@process_required
def update_hardware_param(param_id):
    """更新硬件参数"""
    param = HardwareParam.query.get_or_404(param_id)
    data = request.get_json() or {}
    for field in ['param_name', 'param_value', 'group_name', 'sort_order']:
        if field in data:
            setattr(param, field, data[field])
    db.session.commit()
    return jsonify({'code': 0, 'data': param.to_dict(),
                    'message': '已更新'})


@station_bp.route('/hardware/<int:param_id>', methods=['DELETE'])
@process_required
def delete_hardware_param(param_id):
    """删除硬件参数"""
    param = HardwareParam.query.get_or_404(param_id)
    db.session.delete(param)
    db.session.commit()
    return jsonify({'code': 0, 'message': '已删除'})


# ==================== 软件参数配置 ====================

@station_bp.route('/<int:station_id>/software', methods=['GET'])
@login_required
def get_software_config(station_id):
    """获取软件参数"""
    config = SoftwareConfig.query.filter_by(station_id=station_id).first()
    if not config:
        config = SoftwareConfig(station_id=station_id)
        db.session.add(config)
        db.session.commit()

    result = config.to_dict()
    # 附带所有测试项供勾选
    all_items = TestItem.query.filter_by(is_active=True)\
        .order_by(TestItem.sort_order).all()
    result['all_test_items'] = [item.to_dict() for item in all_items]
    return jsonify({'code': 0, 'data': result})


@station_bp.route('/<int:station_id>/software', methods=['PUT'])
@process_required
def update_software_config(station_id):
    """更新软件参数"""
    config = SoftwareConfig.query.filter_by(station_id=station_id).first()
    if not config:
        config = SoftwareConfig(station_id=station_id)
        db.session.add(config)
    data = request.get_json() or {}
    for field in ['dut_version', 'dut_firmware_version',
                  'dut_hardware_version']:
        if field in data:
            setattr(config, field, data[field])
    if 'selected_test_item_ids' in data:
        config.selected_test_item_ids = json.dumps(
            data['selected_test_item_ids'], ensure_ascii=False)
    config.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'code': 0, 'data': config.to_dict(),
                    'message': '软件参数已更新'})


# ==================== 场景参数配置 ====================

@station_bp.route('/<int:station_id>/scenario', methods=['GET'])
@login_required
def get_scenario_config(station_id):
    """获取场景参数"""
    config = ScenarioConfig.query.filter_by(station_id=station_id).first()
    if not config:
        config = ScenarioConfig(station_id=station_id)
        db.session.add(config)
        db.session.commit()
    return jsonify({'code': 0, 'data': config.to_dict()})


@station_bp.route('/<int:station_id>/scenario', methods=['PUT'])
@process_required
def update_scenario_config(station_id):
    """更新场景参数"""
    config = ScenarioConfig.query.filter_by(station_id=station_id).first()
    if not config:
        config = ScenarioConfig(station_id=station_id)
        db.session.add(config)
    data = request.get_json() or {}
    if 'scenario_data' in data:
        config.scenario_data = json.dumps(data['scenario_data'],
                                          ensure_ascii=False)
    config.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'code': 0, 'data': config.to_dict(),
                    'message': '场景参数已更新'})


# ==================== 种子数据 ====================

def seed_sample_stations():
    """初始化示例工站数据（启动时自动调用）"""
    if TestStation.query.count() > 0:
        return

    station = TestStation(name='SMT 测试工站 01', description='SMT产线1号测试工站',
                          sort_order=1)
    db.session.add(station)
    db.session.flush()

    # 默认配置
    db.session.add(EquipmentConfig(station_id=station.id))
    db.session.add(SoftwareConfig(station_id=station.id))
    db.session.add(ScenarioConfig(station_id=station.id))

    # 两个机框
    for ci in range(1, 3):
        chassis = TestChassis(station_id=station.id,
                              name=f'机框 {ci}', slot_count=4,
                              sort_order=ci)
        db.session.add(chassis)
        db.session.flush()
        for si in range(1, 5):
            db.session.add(TestSlot(
                chassis_id=chassis.id,
                name=f'槽位 {si}',
                sort_order=si,
            ))

    # 示例硬件参数
    hw_samples = [
        ('测试仪 IP', '192.168.1.100', '网络配置', 1),
        ('测试仪端口', '5025', '网络配置', 2),
        ('万用表 IP', '192.168.1.101', '仪器配置', 1),
        ('万用表型号', '34461A', '仪器配置', 2),
        ('电源 IP', '192.168.1.102', '仪器配置', 3),
        ('电源通道数', '2', '仪器配置', 4),
        ('GPIB 地址', '10', '通信配置', 1),
        ('串口波特率', '115200', '通信配置', 2),
    ]
    for name, val, group, order in hw_samples:
        db.session.add(HardwareParam(
            station_id=station.id, param_name=name, param_value=val,
            group_name=group, sort_order=order,
        ))

    db.session.commit()
