import os
import json
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app

from app import db
from app.models import TestItem, TestConfig
from config.config_manager import ConfigManager, ConfigImportError

config_bp = Blueprint('configs', __name__)


@config_bp.route('', methods=['GET'])
def list_configs():
    configs = TestConfig.query.order_by(TestConfig.updated_at.desc()).all()
    return jsonify({
        'code': 0,
        'data': [c.to_dict() for c in configs],
        'total': len(configs),
    })


@config_bp.route('', methods=['POST'])
def create_config():
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
def get_config(config_id):
    config = TestConfig.query.get_or_404(config_id)
    return jsonify({
        'code': 0,
        'data': {**config.to_dict(),
                 'config_data': json.loads(config.config_data or '{}')},
    })


@config_bp.route('/<int:config_id>/activate', methods=['POST'])
def activate_config(config_id):
    TestConfig.query.filter_by(is_active=True).update(
        {'is_active': False})
    config = TestConfig.query.get_or_404(config_id)
    config.is_active = True
    config.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'code': 0, 'data': config.to_dict(),
                    'message': 'activated'})


@config_bp.route('/<int:config_id>', methods=['DELETE'])
def delete_config(config_id):
    config = TestConfig.query.get_or_404(config_id)
    db.session.delete(config)
    db.session.commit()
    return jsonify({'code': 0, 'message': 'deleted'})


@config_bp.route('/import', methods=['POST'])
def import_config():
    if 'file' not in request.files:
        return jsonify({'code': 1, 'message': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'code': 1, 'message': 'Empty filename'}), 400

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

    validated = ConfigManager.validate_config_data(parsed)

    if validated['error_count'] > 0 and validated['valid_count'] == 0:
        return jsonify({
            'code': 1,
            'message': 'All rows failed validation',
            'data': validated,
        }), 400

    if request.form.get('preview_only', 'false').lower() == 'true':
        return jsonify({
            'code': 0,
            'data': validated,
            'message': 'Preview (not saved)',
        })

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
def export_config():
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
def apply_config(config_id):
    config = TestConfig.query.get_or_404(config_id)
    config_data = json.loads(config.config_data or '{}')

    items_config = config_data.get('items', [])
    if not items_config:
        return jsonify({'code': 1, 'message': 'Config has no items'}), 400

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
