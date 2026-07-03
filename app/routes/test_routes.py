from datetime import datetime
from flask import Blueprint, request, jsonify

from app import db
from app.models import TestItem, TestResult, TestRun
from app.services.test_executor import TestExecutor

test_bp = Blueprint('tests', __name__)


@test_bp.route('/items', methods=['GET'])
def list_test_items():
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
def create_test_item():
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
def update_test_item(item_id):
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
def delete_test_item(item_id):
    item = TestItem.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    return jsonify({'code': 0, 'message': 'deleted'})


@test_bp.route('/runs', methods=['GET'])
def list_test_runs():
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
def start_test_run():
    data = request.get_json() or {}
    operator = data.get('operator', 'default')
    serial_number = data.get('serial_number', '')
    product_type = data.get('product_type', '')
    config_id = data.get('config_id')

    executor = TestExecutor(
        operator=operator,
        serial_number=serial_number,
        product_type=product_type,
        config_id=config_id,
    )
    run = executor.start_run()
    return jsonify({
        'code': 0,
        'data': run.to_dict(),
        'message': 'Test run started',
    })


@test_bp.route('/runs/<int:run_id>/results', methods=['POST'])
def submit_result(run_id):
    run = TestRun.query.get_or_404(run_id)
    if run.status != 'running':
        return jsonify({'code': 1, 'message': 'Test run is not active'}), 400

    data = request.get_json()
    test_item_id = data.get('test_item_id')
    actual_value = data.get('actual_value')

    if not test_item_id or actual_value is None:
        return jsonify({'code': 1, 'message': 'test_item_id and actual_value required'}), 400

    item = TestItem.query.get(test_item_id)
    if not item:
        return jsonify({'code': 1, 'message': 'Test item not found'}), 404

    passed = item.min_value <= float(actual_value) <= item.max_value
    deviation = float(actual_value) - item.expected_value

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

    return jsonify({
        'code': 0,
        'data': result.to_dict(),
        'message': 'PASS' if passed else 'FAIL',
    })


@test_bp.route('/runs/<run_id>', methods=['PUT'])
def update_test_run(run_id):
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
    run = TestRun.query.filter(
        (TestRun.id == run_id) | (TestRun.batch_id == run_id)
    ).first_or_404()

    results = TestResult.query.filter_by(test_run_id=run.id).all()
    return jsonify({
        'code': 0,
        'data': [r.to_dict() for r in results],
        'total': len(results),
    })


@test_bp.route('/categories', methods=['GET'])
def list_categories():
    categories = db.session.query(TestItem.category).distinct().all()
    return jsonify({
        'code': 0,
        'data': [c[0] for c in categories if c[0]],
    })
