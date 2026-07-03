"""
系统初始化 API 路由模块

提供系统状态查询、示例数据初始化、系统重置和默认配置导入功能。
用于首次部署时的快速初始化，或需要清空数据重新开始时的操作。
"""

from datetime import datetime
from flask import Blueprint, request, jsonify

from app import db
from app.models import TestItem, TestConfig, TestResult, TestRun
from config.config_manager import ConfigManager

# 初始化管理蓝图，URL 前缀为 /api/init
init_bp = Blueprint('init', __name__)


@init_bp.route('/status', methods=['GET'])
def init_status():
    """
    获取系统初始化状态。
    返回各数据表的记录数，以及是否已初始化的标志。
    """
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
    """
    创建一组示例测试项，方便快速开始使用。
    如果系统已初始化（有测试项存在），则返回错误提示，
    建议先重置再初始化。
    """
    if TestItem.query.count() > 0:
        return jsonify({
            'code': 1,
            'message': 'System already initialized. '
                       'Use reset if you want to re-initialize.'
        }), 400

    # 预定义的示例测试项，覆盖电气、信号、热学、安全、声学等类别
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
    """
    重置系统，清空所有数据。
    需要传入 ?confirm=true 确认操作，防止误触。
    """
    confirm = request.args.get('confirm', 'false').lower() == 'true'
    if not confirm:
        return jsonify({
            'code': 1,
            'message': 'Please confirm with ?confirm=true'
        }), 400

    # 按依赖顺序删除：先删结果，再删批次，最后删基础数据
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
    """
    通过上传配置文件来初始化系统。
    文件格式支持: CSV, XLSX, JSON, XML
    导入前会做数据校验，确保必填字段和数值正确。
    """
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
