"""
日志和测试结果查询 API 路由模块

提供测试日志的查询、导出、上传、下载功能，
以及测试结果的按条件搜索和统计接口。
"""

import os
from flask import Blueprint, request, jsonify, current_app, send_file

from app import db
from app.models import TestResult, TestRun
from app.services.log_service import LogService

# 日志管理蓝图，URL 前缀为 /api/logs
log_bp = Blueprint('logs', __name__)


def get_log_service() -> LogService:
    """从应用配置中获取日志服务实例"""
    log_folder = current_app.config.get('LOG_FOLDER', 'logs')
    return LogService(log_folder)


@log_bp.route('', methods=['GET'])
def list_logs():
    """
    获取操作日志列表。
    查询参数:
        batch_id: 按批次号筛选（可选）
        page: 页码（默认1）
        per_page: 每页条数（默认50）
    """
    batch_id = request.args.get('batch_id')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)

    service = get_log_service()
    logs = service.get_logs(batch_id=batch_id, page=page,
                            per_page=per_page)

    total_query = TestRun.query
    if batch_id:
        total_query = total_query.filter(
            TestRun.batch_id.like(f'%{batch_id}%'))
    total = total_query.count()

    return jsonify({
        'code': 0,
        'data': logs,
        'total': total,
        'page': page,
        'per_page': per_page,
    })


@log_bp.route('/results', methods=['GET'])
def query_test_results():
    """
    查询测试结果，支持多条件组合筛选。
    查询参数:
        batch_id: 批次号
        operator: 操作员
        serial_number: 序列号
        passed: PASS/FAIL（true/false）
        start_date: 开始时间（ISO格式）
        end_date: 结束时间（ISO格式）
        page: 页码
        per_page: 每页条数
    """
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    batch_id = request.args.get('batch_id')
    operator = request.args.get('operator')
    serial_number = request.args.get('serial_number')
    passed = request.args.get('passed')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    query = TestResult.query.join(TestRun)

    if batch_id:
        query = query.filter(TestRun.batch_id.like(f'%{batch_id}%'))
    if operator:
        query = query.filter(TestResult.operator.like(f'%{operator}%'))
    if serial_number:
        query = query.filter(
            TestResult.serial_number.like(f'%{serial_number}%'))
    if passed is not None:
        query = query.filter(TestResult.passed == (passed.lower() == 'true'))
    if start_date:
        from datetime import datetime
        query = query.filter(
            TestResult.tested_at >= datetime.fromisoformat(start_date))
    if end_date:
        from datetime import datetime
        query = query.filter(
            TestResult.tested_at <= datetime.fromisoformat(end_date))

    query = query.order_by(TestResult.tested_at.desc())
    pagination = query.paginate(page=page, per_page=per_page)

    return jsonify({
        'code': 0,
        'data': [r.to_dict() for r in pagination.items],
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
    })


@log_bp.route('/export', methods=['GET'])
def export_logs():
    """
    导出测试结果为 CSV 文件。
    查询参数:
        batch_id: 批次号（可选）
        format: 导出格式（默认 csv）
    """
    from datetime import datetime
    import csv
    import io

    batch_id = request.args.get('batch_id')
    export_format = request.args.get('format', 'csv')

    query = TestResult.query.join(TestRun)
    if batch_id:
        query = query.filter(TestRun.batch_id == batch_id)
    results = query.all()

    if not results:
        return jsonify({'code': 1, 'message': 'No results to export'}), 404

    if export_format == 'csv':
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            'ID', 'Batch ID', 'Item', 'Operator', 'Serial Number',
            'Expected', 'Actual', 'Min', 'Max', 'Passed', 'Deviation',
            'Duration (ms)', 'Remark', 'Tested At'
        ])
        for r in results:
            writer.writerow([
                r.id, r.test_run.batch_id if r.test_run else '',
                r.test_item.name if r.test_item else '',
                r.operator, r.serial_number,
                r.test_item.expected_value if r.test_item else '',
                r.actual_value,
                r.test_item.min_value if r.test_item else '',
                r.test_item.max_value if r.test_item else '',
                'PASS' if r.passed else 'FAIL',
                r.deviation, r.duration_ms, r.remark,
                r.tested_at.isoformat() if r.tested_at else '',
            ])
        output.seek(0)
        from flask import Response
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={
                'Content-Disposition':
                    f'attachment; filename=test_results_{batch_id or "all"}.csv'
            },
        )

    return jsonify({
        'code': 0,
        'data': [r.to_dict() for r in results],
        'total': len(results),
    })


@log_bp.route('/upload', methods=['POST'])
def upload_log():
    """
    上传日志文件到服务器存储目录。
    请求体: multipart/form-data, 字段名: file
    """
    if 'file' not in request.files:
        return jsonify({'code': 1, 'message': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'code': 1, 'message': 'Empty filename'}), 400

    service = get_log_service()
    filepath = os.path.join(service.log_folder, file.filename)
    file.save(filepath)

    return jsonify({
        'code': 0,
        'data': {'filename': file.filename, 'path': filepath},
        'message': 'Log uploaded',
    })


@log_bp.route('/download/<batch_id>', methods=['GET'])
def download_log(batch_id):
    """下载指定批次的日志文件（JSON 格式）"""
    from datetime import datetime
    import json

    service = get_log_service()
    logs = service.get_logs(batch_id=batch_id)
    from flask import Response
    return Response(
        json.dumps(logs, ensure_ascii=False, indent=2),
        mimetype='application/json',
        headers={
            'Content-Disposition':
                f'attachment; filename=logs_{batch_id}.json'
        },
    )


@log_bp.route('/statistics', methods=['GET'])
def log_statistics():
    """获取日志存储统计信息（文件数、大小等）"""
    service = get_log_service()
    stats = service.get_log_statistics()
    return jsonify({'code': 0, 'data': stats})
