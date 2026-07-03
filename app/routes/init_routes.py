from datetime import datetime
from flask import Blueprint, request, jsonify

from app import db
from app.models import TestItem, TestConfig, TestResult, TestRun
from config.config_manager import ConfigManager

init_bp = Blueprint('init', __name__)


@init_bp.route('/status', methods=['GET'])
def init_status():
    item_count = TestItem.query.count()
    config_count = TestConfig.query.count()
    run_count = TestRun.query.count()
    result_count = TestResult.query.count()

    return jsonify({
        'code': 0,
        'data': {
            'initialized': item_count > 0,
            'test_items': item_count,
            'configs': config_count,
            'test_runs': run_count,
            'test_results': result_count,
        }
    })


@init_bp.route('/sample', methods=['POST'])
def init_sample_data():
    if TestItem.query.count() > 0:
        return jsonify({
            'code': 1,
            'message': 'System already initialized. '
                       'Use reset if you want to re-initialize.'
        }), 400

    sample_items = [
        TestItem(name='Voltage Output', description='Output voltage test',
                 expected_value=5.0, min_value=4.8, max_value=5.2,
                 unit='V', category='electrical', sort_order=1),
        TestItem(name='Current Draw', description='Current consumption test',
                 expected_value=1.0, min_value=0.9, max_value=1.1,
                 unit='A', category='electrical', sort_order=2),
        TestItem(name='Frequency', description='Signal frequency test',
                 expected_value=60.0, min_value=59.5, max_value=60.5,
                 unit='Hz', category='signal', sort_order=3),
        TestItem(name='Temperature Rise',
                 description='Temperature rise after 30min operation',
                 expected_value=45.0, min_value=0, max_value=65.0,
                 unit='°C', category='thermal', sort_order=4),
        TestItem(name='Insulation Resistance',
                 description='Insulation resistance test',
                 expected_value=100.0, min_value=50.0, max_value=500.0,
                 unit='MΩ', category='safety', sort_order=5),
        TestItem(name='Noise Level', description='Acoustic noise test',
                 expected_value=30.0, min_value=0, max_value=45.0,
                 unit='dB', category='acoustic', sort_order=6),
    ]

    for item in sample_items:
        db.session.add(item)
    db.session.commit()

    return jsonify({
        'code': 0,
        'data': {
            'items_created': len(sample_items),
            'message': 'Sample data initialized successfully'
        }
    })


@init_bp.route('/reset', methods=['POST'])
def reset_system():
    confirm = request.args.get('confirm', 'false').lower() == 'true'
    if not confirm:
        return jsonify({
            'code': 1,
            'message': 'Please confirm with ?confirm=true'
        }), 400

    TestResult.query.delete()
    TestRun.query.delete()
    TestItem.query.delete()
    TestConfig.query.delete()
    db.session.commit()

    return jsonify({
        'code': 0,
        'message': 'System has been reset. All data cleared.'
    })


@init_bp.route('/import-defaults', methods=['POST'])
def import_default_config():
    if 'file' not in request.files:
        return jsonify({'code': 1, 'message': 'No file'}), 400

    file = request.files['file']
    ext = file.filename.rsplit('.', 1)[-1].lower()

    try:
        parsed = ConfigManager.parse_import_file(file, ext)
    except Exception as e:
        return jsonify({'code': 1, 'message': str(e)}), 400

    validated = ConfigManager.validate_config_data(parsed)
    if validated['error_count'] > 0:
        return jsonify({
            'code': 1,
            'data': validated,
            'message': 'Validation errors'
        }), 400

    for item_data in validated['validated']:
        item = TestItem(**item_data)
        db.session.add(item)
    db.session.commit()

    return jsonify({
        'code': 0,
        'data': validated,
        'message': f'Imported {validated["valid_count"]} items'
    })
