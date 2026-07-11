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
    TestStation, TestChassis, TestSlot, Cabinet,
    EquipmentConfig, HardwareParam, SoftwareConfig, ScenarioConfig,
    EquipmentDefinition,
    EquipmentMetrics, EquipmentPropertyPage,
)
from app.models import TestItem
from app.models.test_sequence import TestItemTemplate, TestSequence, TestSequenceStep
from app.auth import process_required, login_required, get_current_user

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
    user = get_current_user()
    line = ProductionLine(factory_id=factory_id, name=name,
                          code=data.get('code', '').strip(),
                          description=data.get('description', ''),
                          scenario=data.get('scenario', ''),
                          created_by=user.get('display_name', '') if user else '',
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
    for field in ['name', 'code', 'description', 'scenario', 'sort_order', 'factory_id']:
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


# ==================== 装备定义管理 ====================

@station_bp.route('/definitions', methods=['GET'])
@login_required
def list_definitions():
    """获取所有装备定义"""
    defs = EquipmentDefinition.query.order_by(
        EquipmentDefinition.name).all()
    return jsonify({'code': 0, 'data': [d.to_dict() for d in defs],
                    'total': len(defs)})


@station_bp.route('/definitions/<int:def_id>', methods=['GET'])
@login_required
def get_definition(def_id):
    """获取单个装备定义详情"""
    d = EquipmentDefinition.query.get_or_404(def_id)
    return jsonify({'code': 0, 'data': d.to_dict()})


@station_bp.route('/definitions', methods=['POST'])
@process_required
def create_definition():
    """创建装备定义"""
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    if not name:
        return jsonify({'code': 1, 'message': '名称不能为空'}), 400
    if EquipmentDefinition.query.filter_by(name=name).first():
        return jsonify({'code': 1, 'message': '名称已存在'}), 409
    d = EquipmentDefinition(
        name=name,
        code=data.get('code', '').strip(),
        description=data.get('description', ''),
        current_version=data.get('current_version', '1.0.0'),
        default_equipment_config=data.get('default_equipment_config', {}),
        default_hardware_params=data.get('default_hardware_params', []),
        default_software_config=data.get('default_software_config', {}),
        default_scenario_config=data.get('default_scenario_config', {}),
        layout_config=data.get('layout_config'),
    )
    db.session.add(d)
    db.session.commit()
    return jsonify({'code': 0, 'data': d.to_dict(), 'message': '创建成功'})


@station_bp.route('/definitions/<int:def_id>', methods=['PUT'])
@process_required
def update_definition(def_id):
    """更新装备定义"""
    d = EquipmentDefinition.query.get_or_404(def_id)
    data = request.get_json() or {}
    for field in ['name', 'code', 'description']:
        if field in data:
            setattr(d, field, data[field])
    if 'current_version' in data:
        d.current_version = data['current_version']
    if 'default_equipment_config' in data:
        d.default_equipment_config = data['default_equipment_config']
    if 'default_hardware_params' in data:
        d.default_hardware_params = data['default_hardware_params']
    if 'default_software_config' in data:
        d.default_software_config = data['default_software_config']
    if 'default_scenario_config' in data:
        d.default_scenario_config = data['default_scenario_config']
    if 'layout_config' in data:
        d.layout_config = data['layout_config']
    d.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'code': 0, 'data': d.to_dict(), 'message': '已更新'})


@station_bp.route('/definitions/<int:def_id>', methods=['DELETE'])
@process_required
def delete_definition(def_id):
    """删除装备定义"""
    d = EquipmentDefinition.query.get_or_404(def_id)
    db.session.delete(d)
    db.session.commit()
    return jsonify({'code': 0, 'message': '已删除'})


# ==================== 版本检查与更新 ====================

@station_bp.route('/<int:station_id>/version-check', methods=['GET'])
@login_required
def check_station_version(station_id):
    """检查装备版本：对比已部署版本与定义的最新版本"""
    station = TestStation.query.get_or_404(station_id)
    needs_update = station.deployed_version != station.latest_version
    return jsonify({
        'code': 0,
        'data': {
            'station_id': station.id,
            'name': station.name,
            'deployed_version': station.deployed_version,
            'latest_version': station.latest_version,
            'needs_update': needs_update,
        },
    })


@station_bp.route('/<int:station_id>/update-version', methods=['POST'])
@process_required
def update_station_version(station_id):
    """将装备更新到最新版本"""
    station = TestStation.query.get_or_404(station_id)
    if not station.definition_id:
        return jsonify({'code': 1, 'message': '该装备无关联定义，无法更新版本'}), 400
    definition = EquipmentDefinition.query.get(station.definition_id)
    if not definition:
        return jsonify({'code': 1, 'message': '关联定义已删除'}), 404

    old_version = station.deployed_version
    station.deployed_version = definition.current_version
    station.latest_version = definition.current_version
    station.updated_at = datetime.utcnow()
    db.session.commit()

    return jsonify({
        'code': 0,
        'data': {'old_version': old_version, 'new_version': station.deployed_version},
        'message': f'版本已从 {old_version} 更新到 {station.deployed_version}',
    })


# ==================== 工站管理 ====================

@station_bp.route('', methods=['GET'])
@login_required
def list_stations():
    """获取工站列表，可按线体/创建人筛选"""
    line_id = request.args.get('line_id', type=int)
    scope = request.args.get('scope', 'all')
    user = get_current_user()
    query = TestStation.query
    if line_id:
        query = query.filter_by(line_id=line_id)
    if scope == 'mine' and user:
        query = query.filter_by(created_by=user.get('display_name', ''))
    stations = query.order_by(TestStation.sort_order).all()
    result = []
    for s in stations:
        d = s.to_dict()
        d['location'] = f"{s.line.factory.name if s.line and s.line.factory else '?'}-{s.line.name if s.line else '?'}"
        result.append(d)
    return jsonify({
        'code': 0,
        'data': result,
        'total': len(result),
    })


@station_bp.route('', methods=['POST'])
@process_required
def create_station():
    """创建测试工站（装备部署实例）"""
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    if not name:
        return jsonify({'code': 1, 'message': '装备名称不能为空'}), 400
    if TestStation.query.filter_by(name=name).first():
        return jsonify({'code': 1, 'message': '装备名称已存在'}), 409

    definition_id = data.get('definition_id')
    deployed_version = '1.0.0'
    latest_version = '1.0.0'

    if definition_id:
        definition = EquipmentDefinition.query.get(definition_id)
        if definition:
            deployed_version = definition.current_version
            latest_version = definition.current_version
            if not name:
                name = definition.name

    user = get_current_user()
    station = TestStation(
        name=name,
        code=data.get('code', '').strip(),
        line_id=data.get('line_id'),
        definition_id=definition_id,
        description=data.get('description', ''),
        deployed_version=deployed_version,
        latest_version=latest_version,
        process_type=data.get('process_type', ''),
        workstation=data.get('workstation', ''),
        actuator=data.get('actuator', ''),
        hardware_code=data.get('hardware_code', ''),
        software_code=data.get('software_code', ''),
        created_by=user.get('display_name', '') if user else '',
        sort_order=data.get('sort_order', 0),
    )
    db.session.add(station)
    db.session.flush()

    # 自动创建默认配置和层级（按定义模板或默认布局）
    _create_station_full(station)
    db.session.commit()
    return jsonify({'code': 0, 'data': station.to_dict(),
                    'message': '装备创建成功'})


@station_bp.route('/lines', methods=['GET'])
@login_required
def list_all_lines():
    """获取全部线体列表，支持按创建人筛选"""
    scope = request.args.get('scope', 'all')
    user = get_current_user()
    query = ProductionLine.query.order_by(ProductionLine.sort_order)
    if scope == 'mine' and user:
        query = query.filter_by(created_by=user.get('display_name', ''))
    lines = query.all()
    # 关联厂区名称
    result = []
    for l in lines:
        d = l.to_dict()
        d['factory_name'] = l.factory.name if l.factory else ''
        result.append(d)
    return jsonify({'code': 0, 'data': result, 'total': len(result)})


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
    for field in ['name', 'description', 'has_settings', 'sort_order',
                  'definition_id', 'deployed_version', 'latest_version',
                  'process_type', 'workstation', 'actuator',
                  'hardware_code', 'software_code']:
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


@station_bp.route('/<int:station_id>/detail', methods=['GET'])
@login_required
def station_detail(station_id):
    """获取工站完整层级：工站 → 机柜 → 机框 → 槽位"""
    station = TestStation.query.get_or_404(station_id)
    cabinets = Cabinet.query.filter_by(station_id=station_id) \
        .order_by(Cabinet.sort_order).all()
    cab_data = []
    for cab in cabinets:
        cd = cab.to_dict()
        chassis_list = cab.chassis_list.order_by(TestChassis.sort_order).all()
        cd['chassis'] = []
        for ch in chassis_list:
            chd = ch.to_dict()
            chd['slots'] = [s.to_dict() for s in
                            ch.slots.order_by(TestSlot.sort_order).all()]
            cd['chassis'].append(chd)
        cab_data.append(cd)
    return jsonify({
        'code': 0,
        'data': {
            'station': station.to_dict(),
            'cabinets': cab_data,
        }
    })


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
    # handle test_mode string (radio button value)
    if 'test_mode' in data:
        mode = data['test_mode']
        config.test_mode_normal = (mode == 'normal')
        config.test_mode_verify = (mode == 'verify')
        config.test_mode_calibration = (mode == 'calibration')
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


@station_bp.route('/<int:station_id>/hardware/batch', methods=['PUT'])
@login_required
def batch_update_hardware_params(station_id):
    """批量更新硬件参数（全量替换：删除旧参数写入新参数）"""
    data = request.get_json() or {}
    params = data.get('params', [])
    HardwareParam.query.filter_by(station_id=station_id).delete()
    for idx, p in enumerate(params):
        param = HardwareParam(
            station_id=station_id,
            param_name=p.get('param_name', '').strip(),
            param_value=p.get('param_value', ''),
            group_name='deployed',
            sort_order=idx,
        )
        if param.param_name:
            db.session.add(param)
    db.session.commit()
    return jsonify({'code': 0, 'message': f'已保存 {len(params)} 个参数'})


# ==================== 软件参数配置 ====================

@station_bp.route('/<int:station_id>/software', methods=['GET'])
@login_required
def get_software_config(station_id):
    """获取软件参数"""
    project_filter = request.args.get('project', '').strip()
    q = SoftwareConfig.query.filter_by(station_id=station_id)
    if project_filter:
        config = q.filter_by(project_name=project_filter).first()
    else:
        config = q.first()
    if not config:
        config = SoftwareConfig(station_id=station_id, project_name=project_filter or '')
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
    data = request.get_json() or {}
    project_name = data.get('project_name', '').strip()
    config = SoftwareConfig.query.filter_by(station_id=station_id)
    if project_name:
        config = config.filter_by(project_name=project_name).first()
    else:
        config = config.first()
    if not config:
        config = SoftwareConfig(station_id=station_id, project_name=project_name)
        db.session.add(config)
    for field in ['dut_version', 'dut_firmware_version',
                  'dut_hardware_version', 'project_name',
                  'process_type', 'workstation', 'selected_code', 'bom_code']:
        if field in data:
            setattr(config, field, data[field])
    if 'sequence_id' in data:
        config.sequence_id = int(data['sequence_id']) or 0
    if 'selected_test_item_ids' in data:
        config.selected_test_item_ids = json.dumps(
            data['selected_test_item_ids'], ensure_ascii=False)
    config.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'code': 0, 'data': config.to_dict(),
                    'message': '软件参数已更新'})


# ==================== 装备级指标配置 ====================

@station_bp.route('/<int:station_id>/metrics', methods=['GET'])
@login_required
def get_equipment_metrics(station_id):
    """获取装备级指标配置（发布时从版本实例化，不可见于产线，开发人员专用）"""
    eq_metrics = EquipmentMetrics.query.filter_by(station_id=station_id).first()
    if not eq_metrics:
        eq_metrics = EquipmentMetrics(station_id=station_id)
        db.session.add(eq_metrics)
        db.session.commit()
    return jsonify({'code': 0, 'data': eq_metrics.to_dict()})


@station_bp.route('/<int:station_id>/metrics', methods=['PUT'])
@login_required
def update_equipment_metrics(station_id):
    """更新装备级指标配置（每个装备独立修改，互不影响）"""
    data = request.get_json() or {}
    metrics = data.get('metrics', [])
    eq_metrics = EquipmentMetrics.query.filter_by(station_id=station_id).first()
    if not eq_metrics:
        eq_metrics = EquipmentMetrics(station_id=station_id)
        db.session.add(eq_metrics)
    eq_metrics.metrics_json = json.dumps(metrics, ensure_ascii=False)
    eq_metrics.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'code': 0, 'data': eq_metrics.to_dict(),
                    'message': '指标配置已更新'})


# ==================== 装备级属性页（可见，可现场修改） ====================

@station_bp.route('/<int:station_id>/property-page', methods=['GET'])
@login_required
def get_equipment_property_page(station_id):
    """获取装备级属性页（可见于产线，可现场修改）"""
    pp = EquipmentPropertyPage.query.filter_by(station_id=station_id).first()
    if not pp:
        pp = EquipmentPropertyPage(station_id=station_id)
        db.session.add(pp)
        db.session.commit()
    return jsonify({'code': 0, 'data': pp.to_dict()})


@station_bp.route('/<int:station_id>/property-page', methods=['PUT'])
@login_required
def update_equipment_property_page(station_id):
    """更新装备级属性页（现场工程师可修改）"""
    data = request.get_json() or {}
    page_data = data.get('page_data', {})
    pp = EquipmentPropertyPage.query.filter_by(station_id=station_id).first()
    if not pp:
        pp = EquipmentPropertyPage(station_id=station_id)
        db.session.add(pp)
    pp.page_json = json.dumps(page_data, ensure_ascii=False)
    pp.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'code': 0, 'data': pp.to_dict(),
                    'message': '属性页已更新'})


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
    """初始化示例厂区/线体/工站数据（启动时自动调用）"""
    if Factory.query.count() > 0:
        seed_templates_and_sequences()
        return

    # 创建示例厂区
    f1 = Factory(name='SMT 一厂', code='SMT01', description='SMT 表面贴装工厂',
                 sort_order=1)
    db.session.add(f1)
    f2 = Factory(name='组装厂', code='ASM01', description='整机组装工厂',
                 sort_order=2)
    db.session.add(f2)
    db.session.flush()

    # 创建示例线体
    lines_data = [
        (f1.id, 'SMT 线体 01', 'SMT-L01', '高速贴片线', 1),
        (f1.id, 'SMT 线体 02', 'SMT-L02', '多功能贴片线', 2),
        (f2.id, '组装线 01', 'ASM-L01', '主线组装', 1),
    ]
    lines = []
    for fid, name, code, desc, order in lines_data:
        line = ProductionLine(factory_id=fid, name=name, code=code,
                              description=desc, sort_order=order)
        db.session.add(line)
        lines.append(line)
    db.session.flush()

    # 创建装备定义（版本化模板）
    defs_data = [
        ('SPI 检测装备', 'SPI-01', '锡膏检测仪', '2.1.0',
         {"cabinets":[{"name":"机柜 1","chassis":[{"name":"机框 1","slot_count":4},{"name":"机框 2","slot_count":4}]}]}),
        ('贴片机测试站', 'SMT-T01', '贴片后电气测试', '1.5.0',
         {"cabinets":[{"name":"机柜 1","chassis":[{"name":"机框 1","slot_count":4},{"name":"机框 2","slot_count":4},{"name":"机框 3","slot_count":2}]}]}),
        ('功能测试站', 'FCT-01', '整机功能测试', '3.0.0',
         {"cabinets":[{"name":"机柜 1","chassis":[{"name":"机框 1","slot_count":8}]}]}),
    ]
    definitions = []
    for dname, dcode, ddesc, dver, dlayout in defs_data:
        d = EquipmentDefinition(name=dname, code=dcode, description=ddesc,
                                current_version=dver, layout_config=dlayout)
        db.session.add(d)
        definitions.append(d)
    db.session.flush()

    # 为 SMT 线体 01 部署装备
    station = TestStation(line_id=lines[0].id,
                          definition_id=definitions[0].id,
                          name='SPI 检测装备', code='SPI-01',
                          description='锡膏检测仪', sort_order=1,
                          deployed_version='2.0.0',
                          latest_version=definitions[0].current_version)
    db.session.add(station)
    db.session.flush()
    _create_station_full(station)

    station2 = TestStation(line_id=lines[0].id,
                           definition_id=definitions[1].id,
                           name='贴片机测试站', code='SMT-T01',
                           description='贴片后电气测试', sort_order=2,
                           deployed_version=definitions[1].current_version,
                           latest_version=definitions[1].current_version)
    db.session.add(station2)
    db.session.flush()
    _create_station_full(station2)

    # 为组装线部署装备
    station3 = TestStation(line_id=lines[2].id,
                           definition_id=definitions[2].id,
                           name='功能测试站', code='FCT-01',
                           description='整机功能测试', sort_order=1,
                           deployed_version='2.5.0',
                           latest_version=definitions[2].current_version)
    db.session.add(station3)
    db.session.flush()
    _create_station_full(station3)

    seed_templates_and_sequences()
    db.session.commit()


def seed_templates_and_sequences():
    if TestItemTemplate.query.count() > 0:
        return
    tpls = [
        ('电压测试', 'http://service-test:5001/test/voltage', True, 30, '电气'),
        ('电流测试', 'http://service-test:5001/test/current', False, 30, '电气'),
        ('频率测试', 'http://service-test:5001/test/frequency', False, 60, '射频'),
        ('温度测量', 'http://service-test:5001/test/temperature', True, 120, '环境'),
        ('绝缘测试', 'http://service-test:5001/test/insulation', True, 60, '安规'),
        ('噪声测试', 'http://service-test:5001/test/noise', False, 30, '声学'),
    ]
    for i, (name, addr, critical, timeout, cat) in enumerate(tpls):
        db.session.add(TestItemTemplate(
            name=name, service_address=addr,
            is_critical=critical, timeout_seconds=timeout,
            category=cat, sort_order=i,
        ))
    db.session.flush()
    all_tpls = TestItemTemplate.query.order_by(TestItemTemplate.sort_order).all()
    seq = TestSequence(name='FCT 标准测试序列', description='功能测试标准流程', version='1.0')
    db.session.add(seq)
    db.session.flush()
    for i, t in enumerate(all_tpls):
        db.session.add(TestSequenceStep(
            sequence_id=seq.id, template_id=t.id,
            step_order=i, timeout_seconds=t.timeout_seconds,
        ))


def _create_station_full(station):
    """为工站创建完整的默认配置和机框槽位"""
    db.session.add(EquipmentConfig(station_id=station.id))
    db.session.add(SoftwareConfig(station_id=station.id))
    db.session.add(ScenarioConfig(station_id=station.id))

    # 从定义模板获取层级布局，或使用默认布局
    layout = None
    if station.definition_id:
        defn = EquipmentDefinition.query.get(station.definition_id)
        if defn and defn.layout_config:
            layout = defn.layout_config

    if not layout:
        layout = {"cabinets": [{"name": "机柜 1", "chassis": [
            {"name": "机框 1", "slot_count": 4},
            {"name": "机框 2", "slot_count": 4},
        ]}]}

    for ci, cab_cfg in enumerate(layout.get('cabinets', []), 1):
        cabinet = Cabinet(station_id=station.id,
                          name=cab_cfg.get('name', f'机柜 {ci}'),
                          sort_order=ci)
        db.session.add(cabinet)
        db.session.flush()

        for chi, ch_cfg in enumerate(cab_cfg.get('chassis', []), 1):
            slot_cnt = ch_cfg.get('slot_count', 4)
            chassis = TestChassis(station_id=station.id,
                                  cabinet_id=cabinet.id,
                                  name=ch_cfg.get('name', f'机框 {chi}'),
                                  slot_count=slot_cnt, sort_order=chi)
            db.session.add(chassis)
            db.session.flush()
            for si in range(1, slot_cnt + 1):
                db.session.add(TestSlot(
                    chassis_id=chassis.id, name=f'槽位 {si}', sort_order=si))

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
            group_name=group, sort_order=order))
