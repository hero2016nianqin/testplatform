"""
配置管理 API 路由模块

提供配置方案的 CRUD、激活切换、导入（支持 CSV/XLSX/JSON/XML）、
导出和应用功能。配置方案可以保存当前测试项的完整快照，
方便在不同产线或产品型号之间切换测试参数。

权限说明：所有接口仅工艺工程师（process role）可访问。
"""

import os
import json
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app

from app import db
from app.models import TestItem, TestConfig
from app.auth import process_required
from config.config_manager import ConfigManager, ConfigImportError

# 配置管理蓝图，URL 前缀为 /api/configs
config_bp = Blueprint('configs', __name__)


@config_bp.route('', methods=['GET'])
@process_required
def list_configs():
    """获取所有配置方案列表"""
    configs = TestConfig.query.order_by(TestConfig.updated_at.desc()).all()
    return jsonify({
        'code': 0,
        'data': [c.to_dict() for c in configs],
        'total': len(configs),
    })


@config_bp.route('', methods=['POST'])
@process_required
def create_config():
    """
    创建新的配置方案。
    请求体:
        name: 方案名称（必填，唯一）
        description: 描述（可选）
        config_data: 配置数据 JSON（可选）
        version: 版本号（默认 1.0）
    """
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    if not name:
        return jsonify({'code': 1, 'message': 'name is required'}), 400

    if TestConfig.query.filter_by(name=name).first():
        return jsonify({'code': 1, 'message': 'Config name already exists'}), 409

    config = TestConfig(
        name=name,
        description=data.get('description', ''),
        config_data=json.dumps(data.get('config_data', {}),
                               ensure_ascii=False),
        version=data.get('version', '1.0'),
    )
    db.session.add(config)
    db.session.commit()
    return jsonify({'code': 0, 'data': config.to_dict(),
                    'message': 'created'})


@config_bp.route('/<int:config_id>', methods=['GET'])
@process_required
def get_config(config_id):
    """获取指定配置方案的详细信息（包含 config_data）"""
    config = TestConfig.query.get_or_404(config_id)
    return jsonify({
        'code': 0,
        'data': {**config.to_dict(),
                 'config_data': json.loads(config.config_data or '{}')},
    })


@config_bp.route('/<int:config_id>/activate', methods=['POST'])
@process_required
def activate_config(config_id):
    """
    激活指定的配置方案。
    先将所有方案设为未激活，再将目标方案设为激活。
    系统中同时只有一个激活的方案。
    """
    TestConfig.query.filter_by(is_active=True).update(
        {'is_active': False})
    config = TestConfig.query.get_or_404(config_id)
    config.is_active = True
    config.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'code': 0, 'data': config.to_dict(),
                    'message': 'activated'})


@config_bp.route('/<int:config_id>', methods=['DELETE'])
@process_required
def delete_config(config_id):
    """删除指定的配置方案"""
    config = TestConfig.query.get_or_404(config_id)
    db.session.delete(config)
    db.session.commit()
    return jsonify({'code': 0, 'message': 'deleted'})


@config_bp.route('/import', methods=['POST'])
@process_required
def import_config():
    """
    导入配置文件。
    支持格式: CSV, XLSX, JSON, XML
    请求参数:
        file: 上传的文件
        preview_only: 如果为 true 则只验证不保存（可选）
    导入规则: 同名测试项更新，新名称新增。
    """
    if 'file' not in request.files:
        return jsonify({'code': 1, 'message': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'code': 1, 'message': 'Empty filename'}), 400

    # 根据文件扩展名选择解析方式
    ext = file.filename.rsplit('.', 1)[-1].lower()
    if ext not in ConfigManager.SUPPORTED_FORMATS:
        return jsonify({
            'code': 1,
            'message': f'Unsupported format: {ext}'
        }), 400

    try:
        parsed = ConfigManager.parse_import_file(file, ext)
    except ConfigImportError as e:
        return jsonify({'code': 1, 'message': str(e)}), 400

    # 校验数据：检查必填字段和数值有效性
    validated = ConfigManager.validate_config_data(parsed)

    if validated['error_count'] > 0 and validated['valid_count'] == 0:
        return jsonify({
            'code': 1,
            'message': 'All rows failed validation',
            'data': validated,
        }), 400

    # 预览模式：只返回校验结果，不写入数据库
    if request.form.get('preview_only', 'false').lower() == 'true':
        return jsonify({
            'code': 0,
            'data': validated,
            'message': 'Preview (not saved)',
        })

    # 写入数据库：同名更新，不同名新增
    for item_data in validated['validated']:
        existing = TestItem.query.filter_by(name=item_data['name']).first()
        if existing:
            for key, val in item_data.items():
                setattr(existing, key, val)
            existing.updated_at = datetime.utcnow()
        else:
            item = TestItem(**item_data)
            db.session.add(item)
    db.session.commit()

    return jsonify({
        'code': 0,
        'data': validated,
        'message': f'Imported {validated["valid_count"]} items '
                   f'({validated["error_count"]} errors)',
    })


@config_bp.route('/export', methods=['GET'])
@process_required
def export_config():
    """
    导出测试项为配置文件。
    查询参数:
        format: 导出格式（json/csv/xlsx，默认 json）
        category: 分类筛选（可选）
    """
    export_format = request.args.get('format', 'json')
    category = request.args.get('category')

    query = TestItem.query.filter_by(is_active=True)
    if category:
        query = query.filter_by(category=category)
    items = query.all()

    if not items:
        return jsonify({'code': 1, 'message': 'No items to export'}), 404

    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    os.makedirs(upload_folder, exist_ok=True)
    timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
    filename = f'test_config_export_{timestamp}.{export_format}'
    filepath = os.path.join(upload_folder, filename)

    cm = ConfigManager()
    export_method = getattr(cm, f'export_to_{export_format}', None)
    if not export_method:
        return jsonify({
            'code': 1,
            'message': f'Unsupported export format: {export_format}'
        }), 400

    try:
        export_method(items, filepath)
        return jsonify({
            'code': 0,
            'data': {'filename': filename, 'path': filepath},
            'message': f'Exported to {filename}',
        })
    except Exception as e:
        return jsonify({'code': 1, 'message': str(e)}), 500


@config_bp.route('/apply/<int:config_id>', methods=['POST'])
@process_required
def apply_config(config_id):
    """
    应用指定配置方案到系统。
    将所有现有测试项禁用，然后根据配置方案中的数据重新创建/更新测试项。
    """
    config = TestConfig.query.get_or_404(config_id)
    config_data = json.loads(config.config_data or '{}')

    items_config = config_data.get('items', [])
    if not items_config:
        return jsonify({'code': 1, 'message': 'Config has no items'}), 400

    # 先禁用所有现有测试项
    TestItem.query.update({'is_active': False})
    imported = 0
    for item_data in items_config:
        existing = TestItem.query.filter_by(
            name=item_data.get('name')).first()
        if existing:
            for key, val in item_data.items():
                if hasattr(existing, key):
                    setattr(existing, key, val)
            existing.is_active = True
            existing.updated_at = datetime.utcnow()
        else:
            new_item = TestItem(**item_data, is_active=True)
            db.session.add(new_item)
        imported += 1
    db.session.commit()

    config.is_active = True
    config.updated_at = datetime.utcnow()
    db.session.commit()

    return jsonify({
        'code': 0,
        'message': f'Applied config "{config.name}" with {imported} items',
    })
