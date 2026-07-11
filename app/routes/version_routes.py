import os
import json
import re
from datetime import datetime
from flask import Blueprint, request, jsonify, session, current_app
from app import db
from app.models.version import TestVersion, ReleaseStep, VersionArchiveItem, ReleaseDeployment, VersionBinaryFile, SubScenario
from app.models import TestItem, User
from app.models.station import TestStation, ProductionLine, SoftwareConfig, EquipmentMetrics, EquipmentPropertyPage
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
    scope = request.args.get('scope', 'all')
    versions = TestVersion.query.order_by(TestVersion.created_at.desc()).all()
    current_user = _current_user()
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
        # 判断是否与当前用户相关（创建者或待审批步骤的审批人）
        is_creator = v.created_by == current_user
        pending_my = ReleaseStep.query.filter(
            ReleaseStep.version_id == v.id,
            ReleaseStep.status == 'pending',
            ReleaseStep.assigned_to == current_user
        ).count()
        d['is_mine'] = is_creator or pending_my > 0
        data.append(d)
    if scope == 'mine':
        data = [d for d in data if d['is_mine']]
    return jsonify({'code': 0, 'data': data})


@version_bp.route('/versions/<int:version_id>', methods=['PUT'])
@login_required
def update_version(version_id):
    """编辑版本基本信息（仅draft状态允许编辑）"""
    v = TestVersion.query.get_or_404(version_id)
    if v.status != 'draft':
        return jsonify({'code': 1, 'message': '仅草稿状态的版本可编辑'}), 400
    data = request.get_json()
    if not data:
        return jsonify({'code': 1, 'message': '请求数据为空'}), 400
    if 'description' in data:
        v.description = data['description']
    if 'process_type' in data:
        pt = data['process_type']
        v.process_type = ','.join(pt) if isinstance(pt, list) else str(pt) if pt else ''
    if 'workstation' in data:
        ws = data['workstation']
        v.workstation = ','.join(ws) if isinstance(ws, list) else str(ws) if ws else ''
    if v.type in ('multi_process', 'product_family'):
        if 'bom_code' in data:
            v.bom_code = data.get('bom_code', '')
        if 'tps_name' in data:
            v.tps_name = data.get('tps_name', '')
        if 'domain_tags' in data:
            v.domain_tags = data.get('domain_tags', '')
    if 'sub_scenarios' in data and data['sub_scenarios']:
        # Replace all sub-scenarios for this version
        SubScenario.query.filter_by(version_id=v.id).delete()
        for idx, ss_data in enumerate(data['sub_scenarios']):
            name = (ss_data.get('name') or '').strip()
            if not name:
                continue
            def _to_json_str(val, default='{}'):
                if isinstance(val, (dict, list)):
                    return json.dumps(val, ensure_ascii=False)
                if isinstance(val, str) and val:
                    return val
                return default
            db.session.add(SubScenario(
                version_id=v.id,
                name=name,
                sort_order=idx,
                process_type=ss_data.get('process_type', ''),
                workstation=ss_data.get('workstation', ''),
                sequence_id=ss_data.get('sequence_id', 0) or 0,
                hardware_params=_to_json_str(ss_data.get('hardware_params'), '{}'),
                software_metrics=_to_json_str(ss_data.get('software_metrics'), '[]'),
                property_page=_to_json_str(ss_data.get('property_page'), '{}'),
            ))
    # Handle standard version fields
    if 'sequence_id' in data:
        seq_id = data['sequence_id'] or 0
        try:
            seq_id = int(seq_id)
        except (ValueError, TypeError):
            seq_id = 0
        if seq_id:
            v.sequence_id = seq_id
    if 'archive_items' in data:
        # Remove existing non-sequence_step archive items, add new ones
        VersionArchiveItem.query.filter_by(version_id=v.id).filter(VersionArchiveItem.type != 'sequence_step').delete()
        for ai in data['archive_items']:
            db.session.add(VersionArchiveItem(
                version_id=v.id,
                type=ai.get('type', ''),
                item_id=ai.get('item_id'),
                data_snapshot=ai.get('data_snapshot', '{}'),
            ))
    if 'steps_config' in data:
        steps_config = data['steps_config']
        existing_steps = ReleaseStep.query.filter_by(version_id=v.id).count()
        if not existing_steps:
            stage_map = {'test_manager': 1, 'project_manager': 2}
            label_map = {'test_manager': '测试经理', 'project_manager': '项目经理'}
            for role in ('test_manager', 'project_manager'):
                assignee = (steps_config.get(role) or '').strip()
                db.session.add(ReleaseStep(
                    version_id=v.id, stage=role, step_order=stage_map[role],
                    label=label_map[role],
                    assignee=assignee,
                    status='pending',
                ))
    db.session.commit()
    return jsonify({'code': 0, 'data': v.to_dict(), 'message': '版本已更新'})


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
    existing = TestVersion.query.filter_by(project_name=project_name, version=version).first()
    if existing:
        return jsonify({'code': 1, 'message': f'工程"{project_name}"的版本"{version}"已存在'}), 400

    version_type = data.get('type', 'standard')
    description = data.get('description', '')
    steps_config = data.get('steps_config', {})
    process_type = data.get('process_type', '')
    workstation = data.get('workstation', '')
    if isinstance(process_type, list):
        process_type = ','.join(process_type)
    if isinstance(workstation, list):
        workstation = ','.join(workstation)
    codes_config = data.get('codes_config', [])
    if isinstance(codes_config, list):
        codes_config = json.dumps(codes_config, ensure_ascii=False)
    else:
        codes_config = '[]'

    bom_code = data.get('bom_code', '')
    tps_name = data.get('tps_name', '')
    domain_tags = data.get('domain_tags', '')
    inherit_from_id = data.get('inherit_from_id')

    if version_type == 'multi_process':
        if not bom_code:
            return jsonify({'code': 1, 'message': '多工序版本必须填写BOM编码'}), 400
        if not tps_name:
            return jsonify({'code': 1, 'message': '多工序版本必须填写TPS名称'}), 400
    elif version_type == 'product_family':
        pass
    else:
        version_type = 'standard'

    v = TestVersion(version=version, project_name=project_name,
                    description=description, status='draft',
                    created_by=_current_user(),
                    process_type=process_type,
                    workstation=workstation,
                    codes_config=codes_config,
                    type=version_type,
                    bom_code=bom_code,
                    tps_name=tps_name,
                    domain_tags=domain_tags,
                    inherit_from_id=inherit_from_id)
    db.session.add(v)
    db.session.flush()

    # Handle standard version: require sequence_id
    if version_type == 'standard':
        sequence_id = data.get('sequence_id', 0) or 0
        try:
            sequence_id = int(sequence_id)
        except (ValueError, TypeError):
            sequence_id = 0
        if not sequence_id:
            return jsonify({'code': 1, 'message': '标准版本必须选择测试序列（sequence_id）'}), 400
        v.sequence_id = sequence_id
        archive_items = data.get('archive_items', [])
        for ai in archive_items:
            db.session.add(VersionArchiveItem(version_id=v.id, type=ai.get('type', ''),
                                               item_id=ai.get('item_id'),
                                               data_snapshot=ai.get('data_snapshot', '{}')))
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

    # Handle multi_process version: create sub-scenarios
    if version_type == 'multi_process':
        sub_scenarios_data = data.get('sub_scenarios', [])
        if not sub_scenarios_data:
            return jsonify({'code': 1, 'message': '多工序版本必须至少有一个子场景'}), 400
        for idx, ss_data in enumerate(sub_scenarios_data):
            name = (ss_data.get('name') or '').strip()
            if not name:
                return jsonify({'code': 1, 'message': f'子场景 #{idx+1} 名称不能为空'}), 400
            process_type_ss = ss_data.get('process_type', '')
            workstation_ss = ss_data.get('workstation', '')
            if not process_type_ss:
                # Try to parse from name: "FT-MP1" -> process_type="FT", workstation="MP1"
                parts = name.split('-', 1)
                if len(parts) == 2:
                    process_type_ss = parts[0]
                    workstation_ss = parts[1]
            db.session.add(SubScenario(
                version_id=v.id,
                name=name,
                sort_order=idx,
                process_type=process_type_ss,
                workstation=workstation_ss,
                sequence_id=ss_data.get('sequence_id', 0) or 0,
                hardware_params=json.dumps(ss_data['hardware_params'], ensure_ascii=False) if isinstance(ss_data.get('hardware_params'), (dict, list)) else (ss_data.get('hardware_params') or '{}'),
                software_metrics=json.dumps(ss_data['software_metrics'], ensure_ascii=False) if isinstance(ss_data.get('software_metrics'), (dict, list)) else (ss_data.get('software_metrics') or '[]'),
                property_page=json.dumps(ss_data['property_page'], ensure_ascii=False) if isinstance(ss_data.get('property_page'), (dict, list)) else (ss_data.get('property_page') or '{}'),
            ))

    # Handle inheritance: copy sub-scenarios and archive items from source version
    if v.inherit_from_id:
        src = TestVersion.query.get(v.inherit_from_id)
        if src:
            # Copy sub-scenarios if version is multi_process and no new ones provided
            if version_type == 'multi_process' and not data.get('sub_scenarios'):
                for ss in SubScenario.query.filter_by(version_id=src.id).order_by(SubScenario.sort_order).all():
                    db.session.add(SubScenario(
                        version_id=v.id,
                        name=ss.name,
                        description=ss.description,
                        sort_order=ss.sort_order,
                        process_type=ss.process_type,
                        workstation=ss.workstation,
                        sequence_id=ss.sequence_id,
                        hardware_params=ss.hardware_params,
                        software_metrics=ss.software_metrics,
                        property_page=ss.property_page,
                    ))
            # Copy archive items if standard and no new ones provided
            if version_type == 'standard' and not data.get('archive_items'):
                for ai in VersionArchiveItem.query.filter_by(version_id=src.id).all():
                    db.session.add(VersionArchiveItem(
                        version_id=v.id,
                        type=ai.type,
                        item_id=ai.item_id,
                        data_snapshot=ai.data_snapshot,
                    ))
            # Copy binary files
            for bf in VersionBinaryFile.query.filter_by(version_id=src.id).all():
                import shutil
                new_path = bf.file_path.replace(f'/versions/{src.id}/', f'/versions/{v.id}/')
                dst_dir = os.path.dirname(new_path)
                os.makedirs(dst_dir, exist_ok=True)
                if os.path.exists(bf.file_path):
                    shutil.copy2(bf.file_path, new_path)
                db.session.add(VersionBinaryFile(
                    version_id=v.id,
                    filename=bf.filename,
                    file_path=new_path,
                    file_size=bf.file_size,
                    description=bf.description,
                ))

    stage1_configs = [
        {'step_order': 1, 'step_name': '测试经理审核', 'approver_role': '测试经理',
         'assigned_to': steps_config.get('test_manager', '')},
        {'step_order': 2, 'step_name': '项目经理审核', 'approver_role': '项目经理',
         'assigned_to': steps_config.get('project_manager', '')},
    ]
    for step_cfg in stage1_configs:
        db.session.add(ReleaseStep(version_id=v.id, stage=1, **step_cfg))

    db.session.commit()
    return jsonify({'code': 0, 'data': v.to_dict()})


@version_bp.route('/versions/<int:version_id>/sub-scenarios', methods=['GET'])
@login_required
def list_sub_scenarios(version_id):
    TestVersion.query.get_or_404(version_id)
    scenarios = SubScenario.query.filter_by(version_id=version_id).order_by(SubScenario.sort_order).all()
    return jsonify({'code': 0, 'data': [s.to_dict() for s in scenarios]})


@version_bp.route('/sub-scenarios/<int:ss_id>', methods=['GET'])
@login_required
def get_sub_scenario(ss_id):
    ss = SubScenario.query.get_or_404(ss_id)
    return jsonify({'code': 0, 'data': ss.to_dict()})


@version_bp.route('/sub-scenarios', methods=['POST'])
@login_required
def create_sub_scenario():
    data = request.get_json()
    if not data or not data.get('version_id'):
        return jsonify({'code': 1, 'message': '缺少版本ID'}), 400
    v = TestVersion.query.get(data['version_id'])
    if not v:
        return jsonify({'code': 1, 'message': '版本不存在'}), 404
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'code': 1, 'message': '子场景名称不能为空'}), 400
    max_order = db.session.query(db.func.max(SubScenario.sort_order)).filter_by(version_id=v.id).scalar() or 0
    ss = SubScenario(
        version_id=v.id,
        name=name,
        description=data.get('description', ''),
        sort_order=max_order + 1,
        sequence_id=data.get('sequence_id', 0) or 0,
    )
    db.session.add(ss)
    db.session.commit()
    return jsonify({'code': 0, 'data': ss.to_dict()})


@version_bp.route('/sub-scenarios/<int:ss_id>', methods=['PUT'])
@login_required
def update_sub_scenario(ss_id):
    ss = SubScenario.query.get_or_404(ss_id)
    data = request.get_json()
    if not data:
        return jsonify({'code': 1, 'message': '请求数据为空'}), 400
    if 'name' in data:
        ss.name = data['name']
    if 'description' in data:
        ss.description = data.get('description', '')
    if 'sort_order' in data:
        ss.sort_order = int(data['sort_order'])
    if 'process_type' in data:
        ss.process_type = data.get('process_type', '')
    if 'workstation' in data:
        ss.workstation = data.get('workstation', '')
    if 'sequence_id' in data:
        ss.sequence_id = int(data['sequence_id'])
    if 'hardware_params' in data:
        hp = data['hardware_params']
        ss.hardware_params = json.dumps(hp, ensure_ascii=False) if isinstance(hp, (dict, list)) else str(hp)
    if 'software_metrics' in data:
        sm = data['software_metrics']
        ss.software_metrics = json.dumps(sm, ensure_ascii=False) if isinstance(sm, (dict, list)) else str(sm)
    if 'property_page' in data:
        pp = data['property_page']
        ss.property_page = json.dumps(pp, ensure_ascii=False) if isinstance(pp, (dict, list)) else str(pp)
    db.session.commit()
    return jsonify({'code': 0, 'data': ss.to_dict()})


@version_bp.route('/sub-scenarios/<int:ss_id>', methods=['DELETE'])
@login_required
def delete_sub_scenario(ss_id):
    ss = SubScenario.query.get_or_404(ss_id)
    db.session.delete(ss)
    db.session.commit()
    return jsonify({'code': 0, 'message': '已删除'})


@version_bp.route('/versions/<int:version_id>', methods=['GET'])
@login_required
def get_version(version_id):
    v = TestVersion.query.get_or_404(version_id)
    d = v.to_dict()
    d['steps'] = [s.to_dict() for s in v.steps]
    d['archive_items'] = [a.to_dict() for a in v.archive_items]
    d['deployments'] = [dep.to_dict() for dep in v.deployments]
    d['binaries'] = [f.to_dict() for f in VersionBinaryFile.query.filter_by(version_id=version_id).order_by(VersionBinaryFile.created_at.desc()).all()]
    d['binary_count'] = len(d['binaries'])
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


@version_bp.route('/versions/<int:version_id>/assign-approvers', methods=['POST'])
@login_required
def assign_approvers(version_id):
    """发布流程中设置审批人"""
    v = TestVersion.query.get_or_404(version_id)
    data = request.get_json() or {}
    steps = ReleaseStep.query.filter_by(version_id=version_id, stage=1).order_by(ReleaseStep.step_order).all()
    if not steps:
        return jsonify({'code': 1, 'message': '未找到发布步骤'}), 400
    test_manager = data.get('test_manager', '')
    project_manager = data.get('project_manager', '')
    for s in steps:
        if s.step_order == 1 and s.status == 'pending':
            s.assigned_to = test_manager
        if s.step_order == 2 and s.status == 'pending':
            s.assigned_to = project_manager
    db.session.commit()
    return jsonify({'code': 0, 'data': [s.to_dict() for s in steps]})


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
    seq_id_filter = request.args.get('sequence_id', '').strip()
    
    # When sequence_id is specified, return test items from that sequence directly
    if seq_id_filter:
        try:
            seq_id = int(seq_id_filter)
        except (ValueError, TypeError):
            seq_id = 0
        if seq_id:
            from app.models.test_sequence import TestSequence, TestSequenceStep
            seq = TestSequence.query.get(seq_id)
            if seq:
                steps = TestSequenceStep.query.filter_by(sequence_id=seq.id).order_by(TestSequenceStep.step_order).all()
                test_items = []
                for i, step in enumerate(steps):
                    t = step.template
                    test_items.append({
                        'id': t.id if t else -(i+1),
                        'name': t.name if t else f'步骤 {i+1}',
                        'expected_value': '',
                        'min_value': '',
                        'max_value': '',
                        'unit': '',
                    })
            else:
                test_items = []
            # Return minimal version info with the sequence-specific items
            return jsonify({'code': 0, 'data': {
                'version_id': 0, 'version': '', 'project_name': project_filter,
                'description': '', 'type': '', 'bom_code': '', 'tps_name': '',
                'sub_scenarios': [], 'deployed_at': None,
                'test_items': test_items,
                'sequence_data': '[]', 'binary_count': 0,
                'factory_name': '', 'line_name': '', 'station_name': '',
            }})
    
    q = ReleaseDeployment.query.filter_by(
        station_id=station_id, status='deployed'
    )
    if project_filter:
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
                try:
                    snap = json.loads(item.data_snapshot) if isinstance(item.data_snapshot, str) else {}
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
            # If no explicit test_item archive items, derive from sequence steps
            if not test_items:
                seq_steps_data = _load_archive_sequence_steps(v.id)
                if seq_steps_data:
                    for i, step in enumerate(seq_steps_data):
                        name = step.get('template_name', '') or step.get('step_name', '') or f'步骤 {i+1}'
                        test_items.append({
                            'id': step.get('template_id', 0) or -(i+1),
                            'name': name,
                            'expected_value': '',
                            'min_value': '',
                            'max_value': '',
                            'unit': '',
                        })
                else:
                    # Fallback to all active TestItem records
                    from app.models.test_item import TestItem
                    all_items = TestItem.query.filter_by(is_active=True).order_by(TestItem.sort_order).all()
                    test_items = [{'id': item.id, 'name': item.name,
                                   'expected_value': str(item.expected_value) if item.expected_value else '',
                                   'min_value': str(item.min_value) if item.min_value else '',
                                   'max_value': str(item.max_value) if item.max_value else '',
                                   'unit': item.unit or ''} for item in all_items]
            seq_steps = _load_archive_sequence_steps(v.id)
            binary_count = VersionBinaryFile.query.filter_by(version_id=v.id).count()
            ss_list = []
            try:
                ss_list = [s.to_dict() for s in SubScenario.query.filter_by(version_id=v.id).order_by(SubScenario.sort_order).all()]
            except Exception:
                ss_list = []
            return jsonify({'code': 0, 'data': {
                'version_id': v.id,
                'version': v.version,
                'project_name': v.project_name,
                'description': v.description,
                'type': v.type or 'standard',
                'bom_code': v.bom_code or '',
                'tps_name': v.tps_name or '',
                'sub_scenarios': ss_list,
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
            # If no explicit test_item archive items, derive from sequence steps
            if not test_items:
                seq_steps_data = _load_archive_sequence_steps(v.id)
                if seq_steps_data:
                    for i, step in enumerate(seq_steps_data):
                        name = step.get('template_name', '') or step.get('step_name', '') or f'步骤 {i+1}'
                        test_items.append({
                            'id': step.get('template_id', 0) or -(i+1),
                            'name': name,
                            'expected_value': '',
                            'min_value': '',
                            'max_value': '',
                            'unit': '',
                        })
                else:
                    # Fallback to all active TestItem records
                    from app.models.test_item import TestItem
                    all_items = TestItem.query.filter_by(is_active=True).order_by(TestItem.sort_order).all()
                    test_items = [{'id': item.id, 'name': item.name,
                                   'expected_value': str(item.expected_value) if item.expected_value else '',
                                   'min_value': str(item.min_value) if item.min_value else '',
                                   'max_value': str(item.max_value) if item.max_value else '',
                                   'unit': item.unit or ''} for item in all_items]
            seq_steps = _load_archive_sequence_steps(v.id)
        ss_list = []
        if v:
            try:
                ss_list = [s.to_dict() for s in SubScenario.query.filter_by(version_id=v.id).order_by(SubScenario.sort_order).all()]
            except Exception:
                ss_list = []
        return jsonify({'code': 0, 'data': {
            'version_id': v.id if v else 0,
            'version': station.deployed_version,
            'project_name': v.project_name if v else '',
            'description': v.description if v else '',
            'type': v.type if v else 'standard',
            'bom_code': v.bom_code if v else '',
            'tps_name': v.tps_name if v else '',
            'sub_scenarios': ss_list,
            'deployed_at': None,
            'test_items': test_items,
            'sequence_data': json.dumps(seq_steps, ensure_ascii=False),
            'factory_name': '',
            'line_name': '',
            'station_name': station.name,
        }})
    return jsonify({'code': 0, 'data': None})


@version_bp.route('/stations/<int:station_id>/deployed-archives', methods=['GET'])
@login_required
def get_station_deployed_archives(station_id):
    station = TestStation.query.get(station_id)
    if not station:
        return jsonify({'code': 0, 'data': None})
    dep = ReleaseDeployment.query.filter_by(station_id=station_id, status='deployed').order_by(ReleaseDeployment.deployed_at.desc()).first()
    if not dep and station.line_id:
        dep = ReleaseDeployment.query.filter_by(line_id=station.line_id, status='deployed').order_by(ReleaseDeployment.deployed_at.desc()).first()
    if not dep:
        factory_id = db.session.query(ProductionLine.factory_id).filter(ProductionLine.id == station.line_id).scalar()
        if factory_id:
            dep = ReleaseDeployment.query.filter_by(factory_id=factory_id, status='deployed').order_by(ReleaseDeployment.deployed_at.desc()).first()
    if not dep:
        dep = ReleaseDeployment.query.filter_by(status='deployed').order_by(ReleaseDeployment.deployed_at.desc()).first()
    if not dep:
        return jsonify({'code': 0, 'data': None})
    v = TestVersion.query.get(dep.version_id)
    if not v:
        return jsonify({'code': 0, 'data': None})

    # Read hardware_params and property_page from sub-scenarios (multi-process)
    hw_items = []
    pp_items = []
    ss_list = SubScenario.query.filter_by(version_id=v.id).order_by(SubScenario.sort_order).all()
    for ss in ss_list:
        try:
            hw = json.loads(ss.hardware_params or '{}')
            if isinstance(hw, dict) and hw:
                hw_items.append({'sub_scenario': ss.name, 'data': hw})
        except Exception:
            pass
        try:
            pp = json.loads(ss.property_page or '{}')
            if isinstance(pp, dict) and pp:
                pp_items.append({'sub_scenario': ss.name, 'data': pp})
        except Exception:
            pass

    merged_hw = {}
    for item in hw_items: merged_hw.update(item['data'])
    merged_pp = {}
    for item in pp_items: merged_pp.update(item['data'])

    return jsonify({
        'code': 0,
        'data': {
            'version_id': v.id,
            'version': v.version,
            'hardware_params_list': hw_items,
            'property_page_list': pp_items,
            'hardware_params': merged_hw,
            'property_page': merged_pp,
        }
    })


def _version_summary(v):
    d = v.to_dict()
    ss = []
    try:
        ss = [s.to_dict() for s in SubScenario.query.filter_by(version_id=v.id).order_by(SubScenario.sort_order).all()]
    except Exception:
        ss = []
    return {
        'version_id': v.id,
        'version': v.version,
        'project_name': v.project_name,
        'description': v.description,
        'type': v.type or 'standard',
        'bom_code': v.bom_code or '',
        'tps_name': v.tps_name or '',
        'process_type': v.process_type or '',
        'workstation': v.workstation or '',
        'codes_config': d.get('codes_config', []),
        'sub_scenarios': ss,
    }


@version_bp.route('/stations/<int:station_id>/deployed-versions', methods=['GET'])
@login_required
def list_station_deployed_versions(station_id):
    """返回某装备所有可用的已发行版本列表"""
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
                result.append(_version_summary(v))
    versions = TestVersion.query.filter(
        TestVersion.status.in_(['released', 'deployed'])
    ).order_by(TestVersion.updated_at.desc()).all()
    for v in versions:
        key = (v.project_name, v.version)
        if key not in seen:
            seen.add(key)
            result.append(_version_summary(v))
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


@version_bp.route('/versions/<int:version_id>/inherit-data', methods=['GET'])
@login_required
def get_inherit_data(version_id):
    """返回用于继承预填充的版本完整数据"""
    v = TestVersion.query.get_or_404(version_id)
    d = v.to_dict()
    # Include archive items summary
    d['archive_items'] = [a.to_dict() for a in v.archive_items]
    d['binary_count'] = VersionBinaryFile.query.filter_by(version_id=version_id).count()
    binaries = VersionBinaryFile.query.filter_by(version_id=version_id).all()
    d['binaries'] = [b.to_dict() for b in binaries]
    return jsonify({'code': 0, 'data': d})


@version_bp.route('/all-users', methods=['GET'])
@login_required
def list_all_users():
    users = User.query.filter_by(is_active=True).all()
    return jsonify({'code': 0, 'data': [u.to_dict() for u in users]})


@version_bp.route('/archive-configs', methods=['GET'])
@login_required
def get_archive_configs():
    items = TestItem.query.filter_by(is_active=True).order_by(TestItem.sort_order).all()
    return jsonify({
        'code': 0,
        'data': {
            'test_items': [i.to_dict() for i in items],
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


@version_bp.route('/versions/<int:version_id>/binaries/<int:file_id>/download', methods=['GET'])
@login_required
def download_version_binary(version_id, file_id):
    """下载版本二进制文件"""
    from flask import send_file
    bf = VersionBinaryFile.query.filter_by(id=file_id, version_id=version_id).first_or_404()
    if not os.path.exists(bf.file_path):
        return jsonify({'code': 1, 'message': '文件不存在'}), 404
    return send_file(bf.file_path, as_attachment=True, download_name=bf.filename)


@version_bp.route('/versions/<int:version_id>/sub-scenarios/<int:ss_id>/<field>/download', methods=['GET'])
@login_required
def download_sub_scenario_json(version_id, ss_id, field):
    """下载子场景JSON字段文件(hardware_params/property_page/software_metrics)"""
    from flask import Response
    ss = SubScenario.query.filter_by(id=ss_id, version_id=version_id).first_or_404()
    if field not in ('hardware_params', 'property_page', 'software_metrics'):
        return jsonify({'code': 1, 'message': '无效字段'}), 400
    raw = getattr(ss, field, None) or '{}'
    try:
        pretty = json.dumps(json.loads(raw), indent=2, ensure_ascii=False)
    except (json.JSONDecodeError, TypeError):
        pretty = raw
    filename = f'{ss.name}_{field}.json'
    return Response(pretty, mimetype='application/json',
                    headers={'Content-Disposition': f'attachment; filename="{filename}"'})


@version_bp.route('/versions/<int:version_id>/archive-items/<int:item_id>/download', methods=['GET'])
@login_required
def download_archive_item_json(version_id, item_id):
    """下载归档条目JSON文件"""
    from flask import Response
    ai = VersionArchiveItem.query.filter_by(id=item_id, version_id=version_id).first_or_404()
    raw = ai.data_snapshot or '{}'
    try:
        pretty = json.dumps(json.loads(raw), indent=2, ensure_ascii=False)
    except (json.JSONDecodeError, TypeError):
        pretty = raw
    filename = f'archive_{ai.id}_{ai.type}.json'
    return Response(pretty, mimetype='application/json',
                    headers={'Content-Disposition': f'attachment; filename="{filename}"'})
