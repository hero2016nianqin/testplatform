"""
测试项与测试执行 API 路由模块

提供测试项的 CRUD 操作、测试批次的启停管理、
以及测试结果的提交和查询接口。
所有接口返回统一的 JSON 格式：{code: 0, data: ..., message: ...}
"""

from datetime import datetime
from flask import Blueprint, request, jsonify

from app import db
from app.models import TestItem, TestResult, TestRun, TestStation
from app.models.test_sequence import TestItemTemplate, TestSequence, TestSequenceStep
from app.auth import login_required, process_required
from app.services.test_executor import TestExecutor

# 测试相关蓝图，URL 前缀为 /api/tests
test_bp = Blueprint('tests', __name__)


# ==================== 测试项管理 ====================

@test_bp.route('/items', methods=['GET'])
def list_test_items():
    """
    获取测试项列表。
    查询参数:
        category: 按分类筛选（可选）
        active_only: 是否只返回启用项（默认 true）
    """
    category = request.args.get('category')
    active_only = request.args.get('active_only', 'true').lower() == 'true'

    query = TestItem.query
    if active_only:
        query = query.filter_by(is_active=True)
    if category:
        query = query.filter_by(category=category)

    items = query.order_by(TestItem.sort_order).all()
    return jsonify({
        'code': 0,
        'data': [item.to_dict() for item in items],
        'total': len(items),
    })


@test_bp.route('/items', methods=['POST'])
@process_required
def create_test_item():
    """创建新的测试项（仅工艺工程师）"""
    data = request.get_json()
    if not data or 'name' not in data:
        return jsonify({'code': 1, 'message': 'name is required'}), 400

    item = TestItem(
        name=data['name'],
        description=data.get('description', ''),
        expected_value=float(data['expected_value']),
        min_value=float(data['min_value']),
        max_value=float(data['max_value']),
        unit=data.get('unit', ''),
        category=data.get('category', 'general'),
        sort_order=data.get('sort_order', 0),
    )
    db.session.add(item)
    db.session.commit()
    return jsonify({'code': 0, 'data': item.to_dict(), 'message': 'created'})


@test_bp.route('/items/<int:item_id>', methods=['PUT'])
@process_required
def update_test_item(item_id):
    """更新测试项的属性（包括启用/禁用状态，仅工艺工程师）"""
    item = TestItem.query.get_or_404(item_id)
    data = request.get_json()
    for field in ['name', 'description', 'unit', 'category']:
        if field in data:
            setattr(item, field, data[field])
    for field in ['expected_value', 'min_value', 'max_value', 'sort_order']:
        if field in data:
            setattr(item, field, float(data[field]))
    if 'is_active' in data:
        item.is_active = bool(data['is_active'])
    item.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'code': 0, 'data': item.to_dict(), 'message': 'updated'})


@test_bp.route('/items/<int:item_id>', methods=['DELETE'])
@process_required
def delete_test_item(item_id):
    """删除指定的测试项（仅工艺工程师）"""
    item = TestItem.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    return jsonify({'code': 0, 'message': 'deleted'})


# ==================== 测试批次管理 ====================

@test_bp.route('/runs', methods=['GET'])
def list_test_runs():
    """
    获取测试批次列表，支持分页和状态筛选。
    查询参数:
        page: 页码（默认1）
        per_page: 每页条数（默认20）
        status: 按状态筛选（pending/running/completed/failed）
    """
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    status = request.args.get('status')

    query = TestRun.query.order_by(TestRun.created_at.desc())
    if status:
        query = query.filter_by(status=status)

    pagination = query.paginate(page=page, per_page=per_page)
    return jsonify({
        'code': 0,
        'data': [run.to_dict() for run in pagination.items],
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
    })


@test_bp.route('/runs', methods=['POST'])
@login_required
def start_test_run():
    """
    启动一个新的测试批次。
    请求体:
        operator: 操作员（必填）
        serial_number: 序列号（可选）
        product_type: 产品型号（可选）
        config_id: 配置方案 ID（可选）
        sequence_id: 测试序列 ID（可选）
        sequence_name: 测试序列名称（可选）
    """
    data = request.get_json() or {}
    operator = data.get('operator', 'default')
    serial_number = data.get('serial_number', '')
    product_type = data.get('product_type', '')
    config_id = data.get('config_id')
    station_id = data.get('station_id')
    slot_id = data.get('slot_id')
    task_order = data.get('task_order', '')
    sequence_id = data.get('sequence_id', 0)
    sequence_name = data.get('sequence_name', '')

    executor = TestExecutor(
        operator=operator,
        serial_number=serial_number,
        product_type=product_type,
        config_id=config_id,
        station_id=station_id,
        slot_id=slot_id,
        task_order=task_order,
    )
    run = executor.start_run()
    if sequence_id:
        run.sequence_id = int(sequence_id)
        run.sequence_name = sequence_name
        db.session.commit()
    return jsonify({
        'code': 0,
        'data': run.to_dict(),
        'message': 'Test run started',
    })


@test_bp.route('/runs/<int:run_id>/results', methods=['POST'])
@login_required
def submit_result(run_id):
    """
    提交单个测试项的测试结果。
    请求体:
        test_item_id: 测试项 ID (支持 TestItem 或 TestItemTemplate)
        actual_value: 实测值
        is_critical: 是否关键项（可选）
        duration_ms: 耗时（毫秒，可选）
        remark: 备注（可选）
    """
    run = TestRun.query.get_or_404(run_id)
    if run.status != 'running':
        return jsonify({'code': 1, 'message': 'Test run is not active'}), 400

    data = request.get_json()
    test_item_id = data.get('test_item_id')
    actual_value = data.get('actual_value')
    is_critical = data.get('is_critical', False)
    client_passed = data.get('passed')

    if not test_item_id or actual_value is None:
        return jsonify({'code': 1, 'message': 'test_item_id and actual_value required'}), 400

    item = TestItem.query.get(test_item_id)
    item_name = ''
    if item:
        passed = item.min_value <= float(actual_value) <= item.max_value
        deviation = float(actual_value) - item.expected_value
        item_name = item.name
    else:
        # Try TestItemTemplate
        tmpl = TestItemTemplate.query.get(test_item_id)
        if not tmpl:
            return jsonify({'code': 1, 'message': 'Test item not found'}), 404
        item_name = tmpl.name
        # Template items: use client-provided passed flag, or eval from archived params
        if client_passed is not None:
            passed = bool(client_passed)
        else:
            passed = False
        deviation = float(actual_value) if passed else 0.0

    result = TestResult(
        test_item_id=test_item_id,
        test_run_id=run_id,
        operator=run.operator,
        serial_number=run.serial_number,
        actual_value=float(actual_value),
        passed=passed,
        deviation=deviation,
        duration_ms=data.get('duration_ms', 0),
        remark=data.get('remark', ''),
        tested_at=datetime.utcnow(),
    )
    db.session.add(result)

    run.total_items += 1
    if passed:
        run.passed_items += 1
    else:
        run.failed_items += 1
    db.session.commit()

    stop = is_critical and not passed
    if stop:
        run.status = 'failed'
        run.ended_at = datetime.utcnow()
        db.session.commit()

    return jsonify({
        'code': 0,
        'data': result.to_dict(),
        'message': 'PASS' if passed else 'FAIL',
        'is_critical': is_critical,
        'stop': stop,
    })


@test_bp.route('/runs/<run_id>', methods=['PUT'])
@login_required
def update_test_run(run_id):
    """
    更新测试批次状态（completed / failed）。
    支持按批次号或自增 ID 查询。
    """
    run = TestRun.query.filter(
        (TestRun.id == run_id) | (TestRun.batch_id == run_id)
    ).first_or_404()

    data = request.get_json()
    new_status = data.get('status')
    if new_status in ('completed', 'failed'):
        run.status = new_status
        run.ended_at = datetime.utcnow()
        db.session.commit()
        return jsonify({
            'code': 0,
            'data': run.to_dict(),
            'message': f'Run {new_status}',
        })

    return jsonify({'code': 1, 'message': f'Invalid status: {new_status}'}), 400


@test_bp.route('/runs/<run_id>/results', methods=['GET'])
def get_run_results(run_id):
    """获取指定批次的所有测试结果"""
    run = TestRun.query.filter(
        (TestRun.id == run_id) | (TestRun.batch_id == run_id)
    ).first_or_404()

    results = TestResult.query.filter_by(test_run_id=run.id).all()
    return jsonify({
        'code': 0,
        'data': [r.to_dict() for r in results],
        'total': len(results),
    })


@test_bp.route('/records', methods=['GET'])
def get_test_records():
    """
    获取 R1/R2/R3 层级测试记录
    参数: station_id, status, date_from, date_to, serial, limit, offset
    """
    query = TestRun.query
    station_id = request.args.get('station_id', type=int)
    if station_id:
        query = query.filter_by(station_id=station_id)
    status = request.args.get('status')
    if status:
        query = query.filter_by(status=status)
    date_from = request.args.get('date_from')
    if date_from:
        query = query.filter(TestRun.created_at >= date_from)
    date_to = request.args.get('date_to')
    if date_to:
        query = query.filter(TestRun.created_at <= date_to + ' 23:59:59')
    serial = request.args.get('serial')
    if serial:
        query = query.filter(TestRun.serial_number.ilike(f'%{serial}%'))
    task_order = request.args.get('task_order')
    if task_order:
        query = query.filter(TestRun.task_order.ilike(f'%{task_order}%'))
    operator = request.args.get('operator')
    if operator:
        query = query.filter(TestRun.operator.ilike(f'%{operator}%'))

    limit = min(request.args.get('limit', 50, type=int), 200)
    offset = request.args.get('offset', 0, type=int)
    total = query.count()
    runs = query.order_by(TestRun.created_at.desc()).offset(offset).limit(limit).all()

    data = []
    for run in runs:
        run_dict = run.to_dict()
        station = TestStation.query.get(run.station_id)
        if station:
            line = station.line
            run_dict['station_name'] = station.name
            run_dict['process_type'] = station.process_type
            run_dict['workstation'] = station.workstation
            run_dict['line_name'] = line.name if line else None
            run_dict['factory_name'] = line.factory.name if line and line.factory else None
        else:
            run_dict['station_name'] = None
            run_dict['process_type'] = None
            run_dict['workstation'] = None
            run_dict['line_name'] = None
            run_dict['factory_name'] = None
        results = TestResult.query.filter_by(test_run_id=run.id).order_by(TestResult.id).all()
        r2_list = []
        for r in results:
            r2 = r.to_dict()
            # R3: detailed indicator info merged into r2
            item = TestItem.query.get(r.test_item_id)
            r2['item_detail'] = item.to_dict() if item else None
            r2_list.append(r2)
        data.append({
            'run': run_dict,
            'results': r2_list,
        })

    return jsonify({'code': 0, 'data': data, 'total': total})


@test_bp.route('/categories', methods=['GET'])
def list_categories():
    """获取所有测试项分类（去重）"""
    categories = db.session.query(TestItem.category).distinct().all()
    return jsonify({
        'code': 0,
        'data': [c[0] for c in categories if c[0]],
    })


# ==================== 测试项模板管理 ====================

@test_bp.route('/templates', methods=['GET'])
@login_required
def list_templates():
    category = request.args.get('category')
    active_only = request.args.get('active_only', 'true').lower() == 'true'
    q = TestItemTemplate.query
    if active_only:
        q = q.filter_by(is_active=True)
    if category:
        q = q.filter_by(category=category)
    items = q.order_by(TestItemTemplate.sort_order).all()
    return jsonify({'code': 0, 'data': [t.to_dict() for t in items]})


@test_bp.route('/templates', methods=['POST'])
@process_required
def create_template():
    data = request.get_json() or {}
    if not data.get('name'):
        return jsonify({'code': 1, 'message': 'name is required'}), 400
    t = TestItemTemplate(
        name=data['name'],
        description=data.get('description', ''),
        service_address=data.get('service_address', ''),
        is_critical=data.get('is_critical', False),
        timeout_seconds=data.get('timeout_seconds', 60),
        category=data.get('category', 'general'),
        sort_order=data.get('sort_order', 0),
    )
    db.session.add(t)
    db.session.commit()
    return jsonify({'code': 0, 'data': t.to_dict()})


@test_bp.route('/templates/<int:template_id>', methods=['PUT'])
@process_required
def update_template(template_id):
    t = TestItemTemplate.query.get_or_404(template_id)
    data = request.get_json() or {}
    for field in ['name', 'description', 'service_address', 'category']:
        if field in data:
            setattr(t, field, data[field])
    for field in ['is_critical', 'is_active']:
        if field in data:
            setattr(t, field, bool(data[field]))
    for field in ['timeout_seconds', 'sort_order']:
        if field in data:
            setattr(t, field, int(data[field]))
    t.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'code': 0, 'data': t.to_dict()})


@test_bp.route('/templates/<int:template_id>', methods=['DELETE'])
@process_required
def delete_template(template_id):
    t = TestItemTemplate.query.get_or_404(template_id)
    db.session.delete(t)
    db.session.commit()
    return jsonify({'code': 0, 'message': 'deleted'})


# ==================== 测试序列管理 ====================

@test_bp.route('/sequences', methods=['GET'])
@login_required
def list_sequences():
    active_only = request.args.get('active_only', 'false').lower() == 'true'
    q = TestSequence.query.order_by(TestSequence.updated_at.desc())
    if active_only:
        q = q.filter_by(is_active=True)
    seqs = q.all()
    return jsonify({'code': 0, 'data': [s.to_dict() for s in seqs]})


@test_bp.route('/sequences', methods=['POST'])
@process_required
def create_sequence():
    data = request.get_json() or {}
    if not data.get('name'):
        return jsonify({'code': 1, 'message': 'name is required'}), 400
    seq = TestSequence(
        name=data['name'],
        description=data.get('description', ''),
        created_by=data.get('created_by', ''),
    )
    db.session.add(seq)
    db.session.flush()
    steps = data.get('steps', [])
    for i, s in enumerate(steps):
        db.session.add(TestSequenceStep(
            sequence_id=seq.id,
            template_id=s.get('template_id'),
            step_order=i,
            timeout_seconds=s.get('timeout_seconds', 60),
        ))
    db.session.commit()
    return jsonify({'code': 0, 'data': seq.to_dict_with_steps()})


@test_bp.route('/sequences/<int:sequence_id>', methods=['GET'])
@login_required
def get_sequence(sequence_id):
    seq = TestSequence.query.get_or_404(sequence_id)
    return jsonify({'code': 0, 'data': seq.to_dict_with_steps()})


@test_bp.route('/sequences/<int:sequence_id>', methods=['PUT'])
@process_required
def update_sequence(sequence_id):
    seq = TestSequence.query.get_or_404(sequence_id)
    data = request.get_json() or {}
    for field in ['name', 'description']:
        if field in data:
            setattr(seq, field, data[field])
    if 'is_active' in data:
        seq.is_active = bool(data['is_active'])
    if 'steps' in data:
        TestSequenceStep.query.filter_by(sequence_id=seq.id).delete()
        db.session.flush()
        for i, s in enumerate(data['steps']):
            db.session.add(TestSequenceStep(
                sequence_id=seq.id,
                template_id=s.get('template_id'),
                step_order=i,
                timeout_seconds=s.get('timeout_seconds', 60),
            ))
    seq.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'code': 0, 'data': seq.to_dict_with_steps()})


@test_bp.route('/sequences/<int:sequence_id>', methods=['DELETE'])
@process_required
def delete_sequence(sequence_id):
    seq = TestSequence.query.get_or_404(sequence_id)
    db.session.delete(seq)
    db.session.commit()
    return jsonify({'code': 0, 'message': 'deleted'})
