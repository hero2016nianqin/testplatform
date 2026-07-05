import os
import json
import re
from datetime import datetime
from flask import Blueprint, request, jsonify, session, current_app
from app import db
from app.models.version import TestVersion, ReleaseStep, VersionArchiveItem, ReleaseDeployment, VersionBinaryFile
from app.models import TestItem, TestConfig, User
from app.models.station import TestStation, SoftwareConfig, EquipmentMetrics, EquipmentPropertyPage
from app.models.test_sequence import TestSequence, TestSequenceStep, TestItemTemplate
from app.auth import login_required

version_bp = Blueprint('versions', __name__)


def _current_user():
    return session.get('display_name', '')


def _load_archive_sequence_steps(version_id):
    """从版本归档中加载序列步骤快照"""
    items = VersionArchiveItem.query.filter_by(
        version_id=version_id, type='sequence_step'
    ).order_by(VersionArchiveItem.id).all()
    steps = []
    for a in items:
        snap = a.data_snapshot
        if isinstance(snap, str):
            try:
                snap = json.loads(snap)
            except (json.JSONDecodeError, TypeError):
                snap = {}
        steps.append(snap)
    return steps


@version_bp.route('/versions', methods=['GET'])
@login_required
def list_versions():
    versions = TestVersion.query.order_by(TestVersion.created_at.desc()).all()
    data = []
    for v in versions:
        d = v.to_dict()
        step_count = ReleaseStep.query.filter_by(version_id=v.id).count()
        done_count = ReleaseStep.query.filter(
            ReleaseStep.version_id == v.id,
            ReleaseStep.status == 'approved'
        ).count()
        dep_count = ReleaseDeployment.query.filter_by(version_id=v.id).count()
        dep_done = ReleaseDeployment.query.filter_by(version_id=v.id, status='deployed').count()
        d['step_progress'] = f'{done_count}/{step_count}' if step_count else '0/0'
        d['deploy_progress'] = f'{dep_done}/{dep_count}' if dep_count else '0/0'
        factories = db.session.query(ReleaseDeployment.factory_name).filter(
            ReleaseDeployment.version_id == v.id,
            ReleaseDeployment.factory_name != ''
        ).distinct().all()
        d['deploy_factories'] = [f[0] for f in factories]
        data.append(d)
    return jsonify({'code': 0, 'data': data})


@version_bp.route('/versions', methods=['POST'])
@login_required
def create_version():
    data = request.get_json()
    if not data:
        return jsonify({'code': 1, 'message': '请求数据为空'}), 400
    version = (data.get('version') or '').strip()
    project_name = (data.get('project_name') or '').strip()
    if not version:
        return jsonify({'code': 1, 'message': '版本号不能为空'}), 400
    if not project_name:
        return jsonify({'code': 1, 'message': '工程名称不能为空'}), 400
    # Check (project_name, version) uniqueness
    existing = TestVersion.query.filter_by(project_name=project_name, version=version).first()
    if existing:
        return jsonify({'code': 1, 'message': f'工程"{project_name}"的版本"{version}"已存在'}), 400
    sequence_id = data.get('sequence_id', 0) or 0
    try:
        sequence_id = int(sequence_id)
    except (ValueError, TypeError):
        sequence_id = 0
    if not sequence_id:
        return jsonify({'code': 1, 'message': '必须选择测试序列（sequence_id）'}), 400
    description = data.get('description', '')
    archive_items = data.get('archive_items', [])
    steps_config = data.get('steps_config', {})
    v = TestVersion(version=version, project_name=project_name,
                    description=description, status='draft',
                    created_by=_current_user(),
                    sequence_id=sequence_id)
    db.session.add(v)
    db.session.flush()
    stage1_configs = [
        {'step_order': 1, 'step_name': '测试经理审核', 'approver_role': '测试经理',
         'assigned_to': steps_config.get('test_manager', '')},
        {'step_order': 2, 'step_name': '项目经理审核', 'approver_role': '项目经理',
         'assigned_to': steps_config.get('project_manager', '')},
    ]
    for step_cfg in stage1_configs:
        db.session.add(ReleaseStep(version_id=v.id, stage=1, **step_cfg))
    for ai in archive_items:
        db.session.add(VersionArchiveItem(version_id=v.id, type=ai.get('type', ''),
                                           item_id=ai.get('item_id'),
                                           data_snapshot=ai.get('data_snapshot', '{}')))
    # Snapshot sequence steps if sequence_id is given
    if v.sequence_id:
        seq = TestSequence.query.get(v.sequence_id)
        if seq:
            for step in seq.steps.order_by(TestSequenceStep.step_order).all():
                t = step.template
                db.session.add(VersionArchiveItem(
                    version_id=v.id, type='sequence_step',
                    item_id=step.id,
                    data_snapshot=json.dumps({
                        'step_order': step.step_order,
                        'timeout_seconds': step.timeout_seconds,
                        'template_id': t.id if t else 0,
                        'template_name': t.name if t else '',
                        'template_service_address': t.service_address if t else '',
                        'template_is_critical': t.is_critical if t else False,
                        'template_category': t.category if t else '',
                        'sequence_name': seq.name,
                        'sequence_version': seq.version,
                    }, ensure_ascii=False)))
    db.session.commit()
    return jsonify({'code': 0, 'data': v.to_dict()})


@version_bp.route('/versions/<int:version_id>', methods=['GET'])
@login_required
def get_version(version_id):
    v = TestVersion.query.get_or_404(version_id)
    d = v.to_dict()
    d['steps'] = [s.to_dict() for s in v.steps]
    d['archive_items'] = [a.to_dict() for a in v.archive_items]
    d['deployments'] = [dep.to_dict() for dep in v.deployments]
    d['binary_count'] = VersionBinaryFile.query.filter_by(version_id=version_id).count()
    return jsonify({'code': 0, 'data': d})


@version_bp.route('/versions/<int:version_id>/submit-step', methods=['POST'])
@login_required
def submit_step(version_id):
    v = TestVersion.query.get_or_404(version_id)
    data = request.get_json()
    step_id = data.get('step_id')
    action = data.get('action')
    comment = data.get('comment', '')
    if not step_id or action not in ('approve', 'reject'):
        return jsonify({'code': 1, 'message': 'step_id and action required'}), 400
    step = ReleaseStep.query.filter_by(id=step_id, version_id=version_id).first()
    if not step:
        return jsonify({'code': 1, 'message': 'step not found'}), 404
    if step.status != 'pending':
        return jsonify({'code': 1, 'message': '步骤已处理'}), 400
    current_user = _current_user()
    if step.assigned_to and step.assigned_to != current_user:
        return jsonify({'code': 1, 'message': f'该步骤需要 {step.assigned_to} 处理'}), 403
    step.status = 'approved' if action == 'approve' else 'rejected'
    step.approved_by = current_user
    step.approved_at = datetime.utcnow()
    step.comment = comment
    v.updated_at = datetime.utcnow()
    stage1_done = ReleaseStep.query.filter_by(version_id=version_id, stage=1).count()
    stage1_approved = ReleaseStep.query.filter_by(version_id=version_id, stage=1, status='approved').count()
    stage2_done = ReleaseStep.query.filter_by(version_id=version_id, stage=2).count()
    stage2_approved = ReleaseStep.query.filter_by(version_id=version_id, stage=2, status='approved').count()
    if stage1_done > 0 and stage1_approved == stage1_done:
        v.status = 'released'
    if stage2_done > 0 and stage2_approved == stage2_done:
        v.status = 'deployed'
    db.session.commit()
    return jsonify({'code': 0, 'data': step.to_dict()})


@version_bp.route('/versions/<int:version_id>/deployments', methods=['POST'])
@login_required
def create_deployments(version_id):
    v = TestVersion.query.get_or_404(version_id)
    data = request.get_json()
    targets = data.get('targets', [])
    if not targets:
        return jsonify({'code': 1, 'message': '请至少选择一个发行目标'}), 400
    te_engineer = data.get('te_engineer', '')
    existing_stage2 = ReleaseStep.query.filter_by(version_id=version_id, stage=2).count()
    if existing_stage2 == 0:
        stage2_configs = [
            {'step_order': 1, 'step_name': 'TE工程师审核', 'approver_role': 'TE工程师',
             'assigned_to': te_engineer},
        ]
        for s_cfg in stage2_configs:
            db.session.add(ReleaseStep(version_id=version_id, stage=2, **s_cfg))
    created = []
    for t in targets:
        dep = ReleaseDeployment(
            version_id=version_id,
            factory_id=t.get('factory_id'),
            factory_name=t.get('factory_name', ''),
            line_id=t.get('line_id'),
            line_name=t.get('line_name', ''),
            station_id=t.get('station_id'),
            station_name=t.get('station_name', ''),
            status='pending',
            assigned_to=(te_engineer if t.get('assign_te') else '') or te_engineer,
        )
        db.session.add(dep)
        db.session.flush()
        created.append(dep.to_dict())
    v.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'code': 0, 'data': created})


@version_bp.route('/deployments/<int:dep_id>/approve', methods=['POST'])
@login_required
def approve_deployment(dep_id):
    dep = ReleaseDeployment.query.get_or_404(dep_id)
    data = request.get_json()
    action = data.get('action', 'approve')
    comment = data.get('comment', '')
    if dep.status != 'pending':
        return jsonify({'code': 1, 'message': '已经处理'}), 400
    current_user = _current_user()
    if dep.assigned_to and dep.assigned_to != current_user:
        return jsonify({'code': 1, 'message': f'该目标需要 {dep.assigned_to} 处理'}), 403
    dep.status = 'approved' if action == 'approve' else 'rejected'
    dep.approved_by = current_user
    dep.approved_at = datetime.utcnow()
    dep.comment = comment
    db.session.commit()
    return jsonify({'code': 0, 'data': dep.to_dict()})


def _push_version_to_station(station, v):
    if not station:
        return
    station.deployed_version = v.version
    soft = SoftwareConfig.query.filter_by(station_id=station.id).first()
    if not soft:
        soft = SoftwareConfig(station_id=station.id, project_name=v.project_name or '')
        db.session.add(soft)
    soft.dut_version = v.version
    soft.project_name = v.project_name or ''

    # ---- 1. Test items -> EquipmentMetrics (per-equipment instantiation) ----
    archive_items = VersionArchiveItem.query.filter_by(version_id=v.id, type='test_item').all()
    if archive_items:
        soft.selected_test_item_ids = json.dumps([a.item_id for a in archive_items], ensure_ascii=False)
        # Instantiate per-equipment metrics from test item snapshots
        metrics_list = []
        for a in archive_items:
            snap = a.data_snapshot
            if isinstance(snap, str):
                try:
                    snap = json.loads(snap)
                except (json.JSONDecodeError, TypeError):
                    snap = {}
            metrics_list.append({
                'name': snap.get('name', f'Item {a.item_id}'),
                'expected_value': snap.get('expected_value', 0),
                'min_value': snap.get('min_value', 0),
                'max_value': snap.get('max_value', 0),
                'unit': snap.get('unit', ''),
                'category': snap.get('category', ''),
                'sort_order': snap.get('sort_order', 0),
                'item_id': a.item_id,
            })
        eq_metrics = EquipmentMetrics.query.filter_by(station_id=station.id).first()
        if not eq_metrics:
            eq_metrics = EquipmentMetrics(station_id=station.id)
            db.session.add(eq_metrics)
        eq_metrics.metrics_json = json.dumps(metrics_list, ensure_ascii=False)

    # ---- 1b. metrics_json archive -> EquipmentMetrics (fallback if no test_item archives) ----
    if not archive_items:
        metrics_archives = (
            VersionArchiveItem.query.filter_by(version_id=v.id, type='metrics_json').all()
            +
            VersionArchiveItem.query.filter_by(version_id=v.id, type='metrics_ini').all()
        )
        if metrics_archives:
            merged_metrics = []
            for a in metrics_archives:
                raw = a.data_snapshot
                if not isinstance(raw, str):
                    continue
                # Write to station directory as file
                station_dir = os.path.join(
                    current_app.config.get('UPLOAD_FOLDER', 'uploads'),
                    'stations', str(station.id), 'metrics'
                )
                os.makedirs(station_dir, exist_ok=True)
                # Determine file extension from archive type
                ext = '.json' if a.type == 'metrics_json' else '.ini'
                filepath = os.path.join(station_dir, f'metrics{ext}')
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(raw)
                # Also try to parse JSON for in-memory use
                if a.type == 'metrics_json':
                    try:
                        parsed = json.loads(raw)
                        if isinstance(parsed, list):
                            merged_metrics.extend(parsed)
                        elif isinstance(parsed, dict):
                            merged_metrics.append(parsed)
                    except (json.JSONDecodeError, TypeError):
                        pass
            if merged_metrics:
                eq_metrics = EquipmentMetrics.query.filter_by(station_id=station.id).first()
                if not eq_metrics:
                    eq_metrics = EquipmentMetrics(station_id=station.id)
                    db.session.add(eq_metrics)
                eq_metrics.metrics_json = json.dumps(merged_metrics, ensure_ascii=False)

    # ---- 2. Sequence data (existing) ----
    seq_snapshots = VersionArchiveItem.query.filter_by(version_id=v.id, type='sequence_step').order_by(
        VersionArchiveItem.id).all()
    if seq_snapshots:
        soft.sequence_id = v.sequence_id
        steps_data = []
        for a in seq_snapshots:
            snap = a.data_snapshot
            if isinstance(snap, str):
                try:
                    snap = json.loads(snap)
                except (json.JSONDecodeError, TypeError):
                    snap = {}
            steps_data.append(snap)
        soft.sequence_data = json.dumps(steps_data, ensure_ascii=False)

    # ---- 2b. Hardware params -> write to disk ----
    hw_archives = VersionArchiveItem.query.filter_by(
        version_id=v.id, type='hardware_params'
    ).all()
    if hw_archives:
        station_dir = os.path.join(
            current_app.config.get('UPLOAD_FOLDER', 'uploads'),
            'stations', str(station.id), 'config'
        )
        os.makedirs(station_dir, exist_ok=True)
        for a in hw_archives:
            filepath = os.path.join(station_dir, 'hardware_params.json')
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(a.data_snapshot if isinstance(a.data_snapshot, str) else '{}')

    # ---- 3. Property page -> EquipmentPropertyPage (visible, editable) ----
    prop_archives = VersionArchiveItem.query.filter_by(
        version_id=v.id, type='property_page'
    ).all()
    if prop_archives:
        # Merge multiple property page archives
        merged = {}
        for a in prop_archives:
            snap = a.data_snapshot
            if isinstance(snap, str):
                try:
                    snap = json.loads(snap)
                except (json.JSONDecodeError, TypeError):
                    snap = {}
            if isinstance(snap, dict):
                merged.update(snap)
        # Write raw file to station directory
        station_dir = os.path.join(
            current_app.config.get('UPLOAD_FOLDER', 'uploads'),
            'stations', str(station.id), 'config'
        )
        os.makedirs(station_dir, exist_ok=True)
        filepath = os.path.join(station_dir, 'property_page.json')
        # Use last archive's content for the file
        last_snap = prop_archives[-1].data_snapshot if prop_archives else '{}'
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(last_snap if isinstance(last_snap, str) else '{}')
        eq_pp = EquipmentPropertyPage.query.filter_by(station_id=station.id).first()
        if not eq_pp:
            eq_pp = EquipmentPropertyPage(station_id=station.id)
            db.session.add(eq_pp)
        eq_pp.page_json = json.dumps(merged, ensure_ascii=False)

    # ---- 4. Binary files - copy to station-specific directory ----
    binaries = VersionBinaryFile.query.filter_by(version_id=v.id).all()
    if binaries:
        station_dir = os.path.join(
            current_app.config.get('UPLOAD_FOLDER', 'uploads'),
            'stations', str(station.id), 'binaries'
        )
        os.makedirs(station_dir, exist_ok=True)
        for bf in binaries:
            src = bf.file_path
            if os.path.exists(src):
                dst = os.path.join(station_dir, bf.filename)
                import shutil
                shutil.copy2(src, dst)


@version_bp.route('/deployments/<int:dep_id>/execute', methods=['POST'])
@login_required
def execute_deployment(dep_id):
    dep = ReleaseDeployment.query.get_or_404(dep_id)
    if dep.status != 'approved':
        return jsonify({'code': 1, 'message': '未被审核通过'}), 400
    dep.status = 'deployed'
    dep.deployed_at = datetime.utcnow()
    v = TestVersion.query.get(dep.version_id)
    if v:
        v.updated_at = datetime.utcnow()
        total_deps = ReleaseDeployment.query.filter_by(version_id=v.id).count()
        done_deps = ReleaseDeployment.query.filter_by(version_id=v.id, status='deployed').count()
        if total_deps > 0 and total_deps == done_deps:
            v.status = 'deployed'
        # Resolve target scope to stations and push version info
        if dep.station_id:
            _push_version_to_station(TestStation.query.get(dep.station_id), v)
        elif dep.line_id:
            for s in TestStation.query.filter_by(line_id=dep.line_id).all():
                _push_version_to_station(s, v)
        elif dep.factory_id:
            for s in TestStation.query.join(ProductionLine).filter(ProductionLine.factory_id == dep.factory_id).all():
                _push_version_to_station(s, v)
        else:
            for s in TestStation.query.all():
                _push_version_to_station(s, v)
    db.session.commit()
    return jsonify({'code': 0, 'data': dep.to_dict()})


@version_bp.route('/stations/<int:station_id>/deployed-version', methods=['GET'])
@login_required
def get_station_deployed_version(station_id):
    project_filter = request.args.get('project', '').strip()
    # First try to find a ReleaseDeployment record
    q = ReleaseDeployment.query.filter_by(
        station_id=station_id, status='deployed'
    )
    if project_filter:
        # Find via version's project_name
        dep = q.join(TestVersion).filter(
            TestVersion.project_name == project_filter
        ).order_by(ReleaseDeployment.deployed_at.desc()).first()
    else:
        dep = q.order_by(ReleaseDeployment.deployed_at.desc()).first()
    if dep:
        v = TestVersion.query.get(dep.version_id)
        if v:
            archive_items = VersionArchiveItem.query.filter_by(version_id=v.id, type='test_item').all()
            test_items = []
            for item in archive_items:
                snap = item.data_snapshot
                if isinstance(snap, str):
                    try:
                        snap = json.loads(snap)
                    except (json.JSONDecodeError, TypeError):
                        snap = {}
                test_items.append({
                    'id': item.item_id,
                    'name': snap.get('name', ''),
                    'expected_value': snap.get('expected_value', ''),
                    'min_value': snap.get('min_value', ''),
                    'max_value': snap.get('max_value', ''),
                    'unit': snap.get('unit', ''),
                })
            seq_steps = _load_archive_sequence_steps(v.id)
            binary_count = VersionBinaryFile.query.filter_by(version_id=v.id).count()
            return jsonify({'code': 0, 'data': {
                'version_id': v.id,
                'version': v.version,
                'project_name': v.project_name,
                'description': v.description,
                'deployed_at': dep.deployed_at.isoformat() if dep.deployed_at else None,
                'test_items': test_items,
                'sequence_data': json.dumps(seq_steps, ensure_ascii=False),
                'binary_count': binary_count,
                'factory_name': dep.factory_name,
                'line_name': dep.line_name,
                'station_name': dep.station_name,
            }})
    # Fallback: check station.deployed_version field directly
    station = TestStation.query.get(station_id)
    if station and station.deployed_version and station.deployed_version not in ('',):
        if project_filter:
            # When a project filter is given, try to find the version by project+version
            v = TestVersion.query.filter_by(
                project_name=project_filter,
                version=station.deployed_version
            ).first()
            if not v:
                v = TestVersion.query.filter(
                    TestVersion.project_name == project_filter,
                    TestVersion.status.in_(['released', 'deployed'])
                ).order_by(TestVersion.updated_at.desc()).first()
        else:
            v = TestVersion.query.filter_by(version=station.deployed_version).first()
            if not v:
                v = TestVersion.query.filter(
                    TestVersion.status.in_(['released', 'deployed'])
                ).order_by(TestVersion.updated_at.desc()).first()
        # Get archived test items if version found
        test_items = []
        seq_steps = []
        if v:
            archive_items = VersionArchiveItem.query.filter_by(version_id=v.id, type='test_item').all()
            for item in archive_items:
                snap = item.data_snapshot
                if isinstance(snap, str):
                    try:
                        snap = json.loads(snap)
                    except (json.JSONDecodeError, TypeError):
                        snap = {}
                test_items.append({
                    'id': item.item_id,
                    'name': snap.get('name', ''),
                    'expected_value': snap.get('expected_value', ''),
                    'min_value': snap.get('min_value', ''),
                    'max_value': snap.get('max_value', ''),
                    'unit': snap.get('unit', ''),
                })
            seq_steps = _load_archive_sequence_steps(v.id)
        return jsonify({'code': 0, 'data': {
            'version_id': v.id if v else 0,
            'version': station.deployed_version,
            'project_name': v.project_name if v else '',
            'description': v.description if v else '',
            'deployed_at': None,
            'test_items': test_items,
            'sequence_data': json.dumps(seq_steps, ensure_ascii=False),
            'factory_name': '',
            'line_name': '',
            'station_name': station.name,
        }})
    return jsonify({'code': 0, 'data': None})


@version_bp.route('/stations/<int:station_id>/deployed-versions', methods=['GET'])
@login_required
def list_station_deployed_versions(station_id):
    """返回某装备所有可用的已发行版本列表（含版本ID、工程名、版本号、描述）"""
    # 1. From ReleaseDeployment records
    deps = ReleaseDeployment.query.filter_by(
        station_id=station_id, status='deployed'
    ).order_by(ReleaseDeployment.deployed_at.desc()).all()
    seen = set()
    result = []
    for dep in deps:
        v = TestVersion.query.get(dep.version_id)
        if v:
            key = (v.project_name, v.version)
            if key not in seen:
                seen.add(key)
                result.append({
                    'version_id': v.id,
                    'version': v.version,
                    'project_name': v.project_name,
                    'description': v.description,
                })
    # 2. Also include all released/deployed versions (so dropdown always has options)
    versions = TestVersion.query.filter(
        TestVersion.status.in_(['released', 'deployed'])
    ).order_by(TestVersion.updated_at.desc()).all()
    for v in versions:
        key = (v.project_name, v.version)
        if key not in seen:
            seen.add(key)
            result.append({
                'version_id': v.id,
                'version': v.version,
                'project_name': v.project_name,
                'description': v.description,
            })
    return jsonify({'code': 0, 'data': result})


@version_bp.route('/versions/<int:version_id>/delist', methods=['POST'])
@login_required
def delist_version(version_id):
    v = TestVersion.query.get_or_404(version_id)
    v.status = 'delisted'
    v.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'code': 0, 'data': v.to_dict()})


@version_bp.route('/versions/<int:version_id>/restore', methods=['POST'])
@login_required
def restore_version(version_id):
    v = TestVersion.query.get_or_404(version_id)
    v.status = 'draft'
    v.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'code': 0, 'data': v.to_dict()})


@version_bp.route('/versions/<int:version_id>', methods=['DELETE'])
@login_required
def delete_version(version_id):
    v = TestVersion.query.get_or_404(version_id)
    if v.status not in ('draft', 'delisted'):
        return jsonify({'code': 1, 'message': '只能删除草稿或已下架的版本'}), 400
    db.session.delete(v)
    db.session.commit()
    return jsonify({'code': 0, 'message': '已删除'})


@version_bp.route('/pending-approvals', methods=['GET'])
@login_required
def get_pending_approvals():
    current_user = _current_user()
    steps = ReleaseStep.query.filter_by(status='pending').filter(
        ReleaseStep.assigned_to == current_user
    ).all()
    result = []
    for s in steps:
        v = TestVersion.query.get(s.version_id)
        if v:
            result.append({
                'step': s.to_dict(),
                'version': v.to_dict(),
                'type': 'step',
            })
    deps = ReleaseDeployment.query.filter_by(status='pending').filter(
        ReleaseDeployment.assigned_to == current_user
    ).all()
    for d in deps:
        v = TestVersion.query.get(d.version_id)
        if v:
            result.append({
                'step': {'step_name': 'TE审核 - ' + (d.factory_name or d.station_name or '')},
                'version': v.to_dict(),
                'type': 'deployment',
                'dep_id': d.id,
            })
    return jsonify({'code': 0, 'data': result})


@version_bp.route('/next-version', methods=['GET'])
@login_required
def get_next_version():
    project_name = request.args.get('project', '').strip()
    if not project_name:
        return jsonify({'code': 0, 'data': {'version': '', 'is_new': True}})
    last = TestVersion.query.filter_by(project_name=project_name)\
        .order_by(TestVersion.created_at.desc()).first()
    if not last:
        return jsonify({'code': 0, 'data': {'version': '1.0.0', 'is_new': True}})
    # Try to extract numeric prefix and increment
    v = last.version
    m = re.match(r'^(\D*)(\d+(?:\.\d+)*)', v)
    if m:
        prefix = m.group(1)
        num_part = m.group(2)
        parts = num_part.split('.')
        if len(parts) == 1:
            next_ver = prefix + str(int(parts[0]) + 1)
        elif len(parts) == 2:
            next_ver = prefix + f'{int(parts[0]) + 1}.0'
        else:
            next_ver = prefix + f'{int(parts[0]) + 1}.' + '.'.join(parts[1:])
    else:
        next_ver = '1.0.0'
    return jsonify({'code': 0, 'data': {'version': next_ver, 'is_new': False}})


@version_bp.route('/all-users', methods=['GET'])
@login_required
def list_all_users():
    users = User.query.filter_by(is_active=True).all()
    return jsonify({'code': 0, 'data': [u.to_dict() for u in users]})


@version_bp.route('/archive-configs', methods=['GET'])
@login_required
def get_archive_configs():
    items = TestItem.query.filter_by(is_active=True).order_by(TestItem.sort_order).all()
    configs = TestConfig.query.filter_by(is_active=True).all()
    return jsonify({
        'code': 0,
        'data': {
            'test_items': [i.to_dict() for i in items],
            'configs': [c.to_dict() for c in configs],
        }
    })


@version_bp.route('/versions/<int:version_id>/binaries', methods=['POST'])
@login_required
def upload_version_binary(version_id):
    """上传版本二进制文件 (multipart)"""
    v = TestVersion.query.get_or_404(version_id)
    if 'file' not in request.files:
        return jsonify({'code': 1, 'message': '未选择文件'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'code': 1, 'message': '文件名为空'}), 400
    description = request.form.get('description', '')
    upload_dir = os.path.join(
        current_app.config.get('UPLOAD_FOLDER', 'uploads'),
        'versions', str(version_id), 'binaries'
    )
    os.makedirs(upload_dir, exist_ok=True)
    safe_name = file.filename
    filepath = os.path.join(upload_dir, safe_name)
    file.save(filepath)
    file_size = os.path.getsize(filepath)
    bf = VersionBinaryFile(
        version_id=version_id,
        filename=safe_name,
        file_path=filepath,
        file_size=file_size,
        description=description,
    )
    db.session.add(bf)
    db.session.commit()
    return jsonify({'code': 0, 'data': bf.to_dict(), 'message': f'已上传 {safe_name}'})


@version_bp.route('/versions/<int:version_id>/binaries', methods=['GET'])
@login_required
def list_version_binaries(version_id):
    """列出版本已上传的二进制文件"""
    files = VersionBinaryFile.query.filter_by(version_id=version_id).order_by(
        VersionBinaryFile.created_at.desc()).all()
    return jsonify({'code': 0, 'data': [f.to_dict() for f in files]})


@version_bp.route('/versions/<int:version_id>/binaries/<int:file_id>', methods=['DELETE'])
@login_required
def delete_version_binary(version_id, file_id):
    """删除版本二进制文件"""
    bf = VersionBinaryFile.query.filter_by(id=file_id, version_id=version_id).first_or_404()
    if os.path.exists(bf.file_path):
        os.remove(bf.file_path)
    db.session.delete(bf)
    db.session.commit()
    return jsonify({'code': 0, 'message': '已删除'})
