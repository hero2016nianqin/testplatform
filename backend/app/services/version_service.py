import json as json_lib
from datetime import datetime
from typing import Optional, List

from sqlalchemy import select, func, case, or_, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.version import (
    TestVersion, SubScenario, ReleaseStep, VersionArchiveItem,
    VersionBinaryFile, ReleaseDeployment,
)
from app.models.station import TestStation, ProductionLine
from app.models.station_config import SoftwareConfig, HardwareParam
from app.models.equipment import EquipmentMetrics, EquipmentPropertyPage
from app.models.test_item import TestItem
from app.models.test_sequence import TestSequence, TestSequenceStep, TestItemTemplate
from app.models.user import User
from app.core.exceptions import NotFoundError, ForbiddenError, BusinessException
from app.config import (
    VERSION_STATUS_DRAFT, VERSION_STATUS_RELEASED, VERSION_STATUS_DEPLOYED, VERSION_STATUS_DELISTED,
    VERSION_TYPE_STANDARD, VERSION_TYPE_MULTI_PROCESS, VERSION_TYPE_PRODUCT_FAMILY,
    STAGE1_RELEASE, STAGE2_DEPLOY,
)


class VersionService:

    # ── Version CRUD ──
    @staticmethod
    async def list_versions(
        db: AsyncSession, page: int = 1, page_size: int = 20,
        status: Optional[str] = None, project_name: Optional[str] = None,
        scope: Optional[str] = None, display_name: Optional[str] = None,
    ) -> tuple[list[dict], int]:
        stmt = select(TestVersion)
        if status:
            stmt = stmt.where(TestVersion.status == status)
        if project_name:
            stmt = stmt.where(TestVersion.project_name.like(f"%{project_name}%"))
        stmt = stmt.order_by(TestVersion.created_at.desc())

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await db.execute(count_stmt)).scalar() or 0

        r = await db.execute(stmt.offset((page - 1) * page_size).limit(page_size))
        versions = list(r.scalars().all())
        if not versions:
            return [], total

        ids = [v.id for v in versions]

        # Bulk aggregations (avoid N+1 per row)
        r = await db.execute(
            select(
                ReleaseStep.version_id,
                func.count(ReleaseStep.id),
                func.coalesce(func.sum(case((ReleaseStep.status == "approved", 1), else_=0)), 0),
            )
            .where(ReleaseStep.version_id.in_(ids))
            .group_by(ReleaseStep.version_id)
        )
        step_map = {vid: (cnt, done) for vid, cnt, done in r.all()}

        r = await db.execute(
            select(
                ReleaseDeployment.version_id,
                func.count(ReleaseDeployment.id),
                func.coalesce(func.sum(case((ReleaseDeployment.status == "deployed", 1), else_=0)), 0),
            )
            .where(ReleaseDeployment.version_id.in_(ids))
            .group_by(ReleaseDeployment.version_id)
        )
        dep_map = {vid: (cnt, done) for vid, cnt, done in r.all()}

        r = await db.execute(
            select(ReleaseDeployment.version_id, ReleaseDeployment.factory_name)
            .where(ReleaseDeployment.version_id.in_(ids), ReleaseDeployment.factory_name != "")
            .distinct()
        )
        fac_map: dict = {}
        for vid, fac in r.all():
            fac_map.setdefault(vid, []).append(fac)

        pending_map: dict = {}
        if display_name:
            r = await db.execute(
                select(ReleaseStep.version_id, func.count(ReleaseStep.id))
                .where(
                    ReleaseStep.version_id.in_(ids),
                    ReleaseStep.status == "pending",
                    ReleaseStep.assigned_to == display_name,
                )
                .group_by(ReleaseStep.version_id)
            )
            pending_map = {vid: cnt for vid, cnt in r.all()}

        result = []
        for v in versions:
            d = v.to_dict()
            sc, sd = step_map.get(v.id, (0, 0))
            dc, dd = dep_map.get(v.id, (0, 0))
            d["step_progress"] = f"{sd}/{sc}" if sc else "0/0"
            d["deploy_progress"] = f"{dd}/{dc}" if dc else "0/0"
            d["deploy_factories"] = fac_map.get(v.id, [])
            is_creator = v.created_by == display_name if display_name else False
            pending_my = pending_map.get(v.id, 0)
            d["is_mine"] = is_creator or pending_my > 0
            result.append(d)
        return result, total

    @staticmethod
    async def get_version(db: AsyncSession, version_id: int) -> TestVersion:
        r = await db.execute(select(TestVersion).where(TestVersion.id == version_id))
        v = r.scalar_one_or_none()
        if not v:
            raise NotFoundError("版本不存在")
        return v

    @staticmethod
    async def get_version_detail(db: AsyncSession, version_id: int) -> dict:
        v = await VersionService.get_version(db, version_id)
        d = v.to_dict()

        r = await db.execute(select(ReleaseStep).where(ReleaseStep.version_id == version_id).order_by(ReleaseStep.stage, ReleaseStep.step_order))
        d["steps"] = [s.to_dict() for s in r.scalars().all()]

        r = await db.execute(select(VersionArchiveItem).where(VersionArchiveItem.version_id == version_id))
        d["archive_items"] = [a.to_dict() for a in r.scalars().all()]

        r = await db.execute(select(ReleaseDeployment).where(ReleaseDeployment.version_id == version_id))
        d["deployments"] = [dep.to_dict() for dep in r.scalars().all()]

        r = await db.execute(select(VersionBinaryFile).where(VersionBinaryFile.version_id == version_id).order_by(VersionBinaryFile.created_at.desc()))
        binaries = list(r.scalars().all())
        d["binary_files"] = [b.to_dict() for b in binaries]
        d["binary_count"] = len(binaries)

        r = await db.execute(select(SubScenario).where(SubScenario.version_id == version_id).order_by(SubScenario.sort_order))
        d["sub_scenarios"] = [s.to_dict() for s in r.scalars().all()]

        return d

    @staticmethod
    async def create_version(db: AsyncSession, data: dict, created_by: str) -> TestVersion:
        vtype = data.get("type", VERSION_TYPE_STANDARD)
        if vtype not in (VERSION_TYPE_STANDARD, VERSION_TYPE_MULTI_PROCESS, VERSION_TYPE_PRODUCT_FAMILY):
            raise BusinessException(400, f"无效的版本类型: {vtype}")

        project_name = (data.get("project_name") or "").strip()
        version = (data.get("version") or "").strip()
        if not project_name:
            raise BusinessException(400, "工程名称不能为空")
        if not version:
            raise BusinessException(400, "版本号不能为空")

        # Check duplicate
        r = await db.execute(select(TestVersion).where(
            TestVersion.project_name == project_name, TestVersion.version == version))
        if r.scalar_one_or_none():
            raise BusinessException(400, f'工程"{project_name}"的版本"{version}"已存在')

        process_type = data.get("process_type", "")
        workstation = data.get("workstation", "")
        if isinstance(process_type, list):
            process_type = ",".join(process_type)
        if isinstance(workstation, list):
            workstation = ",".join(workstation)
        codes_config = data.get("codes_config", [])

        bom_code = data.get("bom_code", "")
        tps_name = data.get("tps_name", "")
        domain_tags = data.get("domain_tags", "")
        inherit_from_id = data.get("inherit_from_id")

        # Type-specific validation
        if vtype in (VERSION_TYPE_MULTI_PROCESS, VERSION_TYPE_PRODUCT_FAMILY):
            if not bom_code:
                raise BusinessException(400, "必须填写BOM编码")
        if vtype == VERSION_TYPE_MULTI_PROCESS and not tps_name:
            raise BusinessException(400, "多工序版本必须填写TPS名称")

        v = TestVersion(
            project_name=project_name, version=version,
            description=data.get("description", ""),
            type=vtype, status=VERSION_STATUS_DRAFT,
            created_by=created_by,
            process_type=process_type, workstation=workstation,
            codes_config=codes_config,
            bom_code=bom_code, tps_name=tps_name, domain_tags=domain_tags,
            inherit_from_id=inherit_from_id,
        )
        db.add(v)
        await db.flush()

        # Standard version: require sequence_id + archive sequence steps
        if vtype == VERSION_TYPE_STANDARD:
            sequence_id = data.get("sequence_id", 0) or 0
            try:
                sequence_id = int(sequence_id)
            except (ValueError, TypeError):
                sequence_id = 0
            if not sequence_id:
                raise BusinessException(400, "标准版本必须选择测试序列（sequence_id）")
            v.sequence_id = sequence_id

            # Archive provided items
            for ai in data.get("archive_items", []):
                db.add(VersionArchiveItem(
                    version_id=v.id, type=ai.get("type", ""),
                    item_id=ai.get("item_id"),
                    data_snapshot=ai.get("data_snapshot", {}),
                ))

            # Auto-archive sequence steps
            r = await db.execute(select(TestSequence).where(TestSequence.id == sequence_id))
            seq = r.scalar_one_or_none()
            if seq:
                r = await db.execute(
                    select(TestSequenceStep).where(TestSequenceStep.sequence_id == sequence_id)
                    .order_by(TestSequenceStep.step_order))
                for step in r.scalars().all():
                    t = None
                    if step.template_id:
                        r2 = await db.execute(select(TestItemTemplate).where(TestItemTemplate.id == step.template_id))
                        t = r2.scalar_one_or_none()
                    db.add(VersionArchiveItem(
                        version_id=v.id, type="sequence_step",
                        item_id=step.id,
                        data_snapshot={
                            "step_order": step.step_order,
                            "timeout_seconds": step.timeout_seconds,
                            "template_id": t.id if t else 0,
                            "template_name": t.name if t else "",
                            "template_service_address": t.service_address if t else "",
                            "template_is_critical": t.is_critical if t else False,
                            "template_category": t.category if t else "",
                            "sequence_name": seq.name,
                            "sequence_version": seq.version,
                        },
                    ))

        # Multi-process & product-family version: validate sub-scenarios
        created_subs: list[SubScenario] = []
        if vtype in (VERSION_TYPE_MULTI_PROCESS, VERSION_TYPE_PRODUCT_FAMILY):
            sub_scenarios_data = data.get("sub_scenarios", [])
            if not sub_scenarios_data:
                raise BusinessException(400, "必须至少有一个子场景")
            for idx, ss_data in enumerate(sub_scenarios_data):
                name = (ss_data.get("name") or "").strip().upper()
                if not name:
                    raise BusinessException(400, f"子场景 #{idx + 1} 名称不能为空")
                process_type_ss = ss_data.get("process_type", "")
                workstation_ss = ss_data.get("workstation", "")
                if not process_type_ss and "-" in name:
                    parts = name.split("-", 1)
                    process_type_ss = parts[0]
                    workstation_ss = parts[1]
                ss = SubScenario(
                    version_id=v.id, name=name, sort_order=idx,
                    process_type=process_type_ss, workstation=workstation_ss,
                    sequence_id=ss_data.get("sequence_id", 0) or 0,
                    hardware_params=ss_data.get("hardware_params", {}),
                    software_metrics=ss_data.get("software_metrics", []),
                    property_page=ss_data.get("property_page", {}),
                    metrics_json=ss_data.get("metrics_json") or None,
                    metrics_ini=ss_data.get("metrics_ini") or None,
                )
                db.add(ss)
                created_subs.append(ss)

        # Inheritance
        if inherit_from_id:
            r = await db.execute(select(TestVersion).where(TestVersion.id == inherit_from_id))
            src = r.scalar_one_or_none()
            if src:
                # Map old sub-scenario id -> new sub-scenario id (matched by name)
                ss_map: dict = {}
                if vtype in (VERSION_TYPE_MULTI_PROCESS, VERSION_TYPE_PRODUCT_FAMILY) and created_subs:
                    # New subs need IDs before inheritance mapping can use them
                    await db.flush()
                    r = await db.execute(
                        select(SubScenario).where(SubScenario.version_id == src.id).order_by(SubScenario.sort_order))
                    src_by_name = {s.name.upper(): s for s in r.scalars().all()}
                    for ns in created_subs:
                        src_ss = src_by_name.get(ns.name.upper())
                        if src_ss:
                            ss_map[src_ss.id] = ns.id
                # Copy sub-scenarios (multi-process / product-family, no new ones provided)
                if vtype in (VERSION_TYPE_MULTI_PROCESS, VERSION_TYPE_PRODUCT_FAMILY) and not data.get("sub_scenarios"):
                    r = await db.execute(
                        select(SubScenario).where(SubScenario.version_id == src.id).order_by(SubScenario.sort_order))
                    for ss in r.scalars().all():
                        db.add(SubScenario(
                            version_id=v.id, name=ss.name, description=ss.description,
                            sort_order=ss.sort_order, process_type=ss.process_type,
                            workstation=ss.workstation, sequence_id=ss.sequence_id,
                            hardware_params=ss.hardware_params,
                            software_metrics=ss.software_metrics,
                            property_page=ss.property_page,
                            metrics_json=ss.metrics_json,
                            metrics_ini=ss.metrics_ini,
                        ))
                # Copy archive-items (standard, no new ones provided)
                if vtype == VERSION_TYPE_STANDARD and not data.get("archive_items"):
                    r = await db.execute(
                        select(VersionArchiveItem).where(VersionArchiveItem.version_id == src.id))
                    for ai in r.scalars().all():
                        db.add(VersionArchiveItem(
                            version_id=v.id, type=ai.type, item_id=ai.item_id,
                            data_snapshot=ai.data_snapshot,
                        ))
                # Copy binary files (remap sub_scenario_id to the new sub-scenarios)
                import os, shutil
                r = await db.execute(
                    select(VersionBinaryFile).where(VersionBinaryFile.version_id == src.id))
                for bf in r.scalars().all():
                    old_ss = bf.sub_scenario_id or 0
                    new_path = (bf.file_path or '').replace(f"/versions/{src.id}/", f"/versions/{v.id}/")
                    if bf.file_path and os.path.exists(bf.file_path):
                        try:
                            os.makedirs(os.path.dirname(new_path), exist_ok=True)
                            shutil.copyfile(bf.file_path, new_path)
                        except Exception:
                            new_path = bf.file_path
                    else:
                        try:
                            from app.core.minio_client import get_minio_client
                            from app.config import get_settings
                            client = get_minio_client()
                            client.copy_object(
                                get_settings().MINIO_BUCKET, new_path, bf.file_path)
                        except Exception:
                            pass
                    db.add(VersionBinaryFile(
                        version_id=v.id, filename=bf.filename,
                        file_path=new_path,
                        file_size=bf.file_size, description=bf.description,
                        sub_scenario_id=ss_map.get(old_ss, 0),
                    ))

        # Auto-create Stage1 release steps
        steps_config = data.get("steps_config", {})
        stage1_configs = [
            {"step_order": 1, "step_name": "测试经理审核", "approver_role": "测试经理",
             "assigned_to": steps_config.get("test_manager", "")},
            {"step_order": 2, "step_name": "项目经理审核", "approver_role": "项目经理",
             "assigned_to": steps_config.get("project_manager", "")},
        ]
        for sc in stage1_configs:
            db.add(ReleaseStep(version_id=v.id, stage=STAGE1_RELEASE, **sc))

        await db.flush()
        await db.refresh(v)
        return v

    @staticmethod
    async def update_version(db, version_id: int, data: dict) -> TestVersion:
        v = await VersionService.get_version(db, version_id)
        if v.status != VERSION_STATUS_DRAFT:
            raise BusinessException(400, "只有草稿状态可以编辑")

        if "description" in data:
            v.description = data["description"]
        if "process_type" in data:
            pt = data["process_type"]
            v.process_type = ",".join(pt) if isinstance(pt, list) else (str(pt) if pt else "")
        if "workstation" in data:
            ws = data["workstation"]
            v.workstation = ",".join(ws) if isinstance(ws, list) else (str(ws) if ws else "")

        # Type-specific fields
        if v.type in (VERSION_TYPE_MULTI_PROCESS, VERSION_TYPE_PRODUCT_FAMILY):
            if "bom_code" in data:
                v.bom_code = data.get("bom_code", "")
            if "tps_name" in data:
                v.tps_name = data.get("tps_name", "")
            if "domain_tags" in data:
                v.domain_tags = data.get("domain_tags", "")

        # Handle sub_scenarios replacement
        if "sub_scenarios" in data and data["sub_scenarios"]:
            r = await db.execute(select(SubScenario).where(SubScenario.version_id == v.id))
            for ss in r.scalars().all():
                await db.delete(ss)
            for idx, ss_data in enumerate(data["sub_scenarios"]):
                name = (ss_data.get("name") or "").strip().upper()
                if not name:
                    continue
                def to_json(val, default=None):
                    if isinstance(val, (dict, list)):
                        return val
                    return val if val else (default or {})
                db.add(SubScenario(
                    version_id=v.id, name=name, sort_order=idx,
                    process_type=ss_data.get("process_type", ""),
                    workstation=ss_data.get("workstation", ""),
                    sequence_id=ss_data.get("sequence_id", 0) or 0,
                    hardware_params=to_json(ss_data.get("hardware_params"), {}),
                    software_metrics=to_json(ss_data.get("software_metrics"), []),
                    property_page=to_json(ss_data.get("property_page"), {}),
                    metrics_json=ss_data.get("metrics_json") or None,
                    metrics_ini=ss_data.get("metrics_ini") or None,
                ))

        # Handle sequence_id
        if "sequence_id" in data:
            seq_id = data["sequence_id"] or 0
            try:
                seq_id = int(seq_id)
            except (ValueError, TypeError):
                seq_id = 0
            if seq_id:
                v.sequence_id = seq_id

        # Handle archive_items
        if "archive_items" in data:
            r = await db.execute(select(VersionArchiveItem).where(
                VersionArchiveItem.version_id == v.id,
                VersionArchiveItem.type != "sequence_step",
            ))
            for ai in r.scalars().all():
                await db.delete(ai)
            for ai in data["archive_items"]:
                db.add(VersionArchiveItem(
                    version_id=v.id, type=ai.get("type", ""),
                    item_id=ai.get("item_id"),
                    data_snapshot=ai.get("data_snapshot", {}),
                ))

        # Handle steps_config (first-time setup only)
        if "steps_config" in data:
            r = await db.execute(select(ReleaseStep).where(
                ReleaseStep.version_id == v.id, ReleaseStep.stage == STAGE1_RELEASE))
            existing = list(r.scalars().all())
            if not existing:
                steps_config = data["steps_config"]
                order_map = {"test_manager": 1, "project_manager": 2}
                label_map = {"test_manager": "测试经理", "project_manager": "项目经理"}
                for role in ("test_manager", "project_manager"):
                    assignee = (steps_config.get(role) or "").strip()
                    db.add(ReleaseStep(
                        version_id=v.id, stage=STAGE1_RELEASE,
                        step_order=order_map[role], step_name=label_map[role],
                        assigned_to=assignee, status="pending",
                    ))

        await db.flush()
        await db.refresh(v)
        return v

    @staticmethod
    async def delete_version(db, version_id: int):
        v = await VersionService.get_version(db, version_id)
        if v.status not in (VERSION_STATUS_DRAFT, VERSION_STATUS_DELISTED):
            raise BusinessException(400, "只有草稿或已下架版本可以删除")
        await db.delete(v)
        await db.flush()

    @staticmethod
    async def delist_version(db, version_id: int):
        v = await VersionService.get_version(db, version_id)
        if v.status not in (VERSION_STATUS_RELEASED, VERSION_STATUS_DEPLOYED):
            raise BusinessException(400, "只能下架已发布或已发行版本")
        v.status = VERSION_STATUS_DELISTED
        await db.flush()
        await db.refresh(v)
        return v

    @staticmethod
    async def restore_version(db, version_id: int):
        v = await VersionService.get_version(db, version_id)
        if v.status != VERSION_STATUS_DELISTED:
            raise BusinessException(400, "只能恢复已下架版本")
        v.status = VERSION_STATUS_DRAFT
        await db.flush()
        return v

    # ── SubScenario ──
    @staticmethod
    async def list_sub_scenarios(db, version_id: int) -> list[SubScenario]:
        r = await db.execute(
            select(SubScenario).where(SubScenario.version_id == version_id).order_by(SubScenario.sort_order))
        return list(r.scalars().all())

    @staticmethod
    async def create_sub_scenario(db, version_id: int, data: dict) -> SubScenario:
        r = await db.execute(select(func.max(SubScenario.sort_order)).where(SubScenario.version_id == version_id))
        max_order = r.scalar() or 0
        data.pop("sort_order", None)
        if data.get("name"):
            data["name"] = str(data["name"]).strip().upper()
        ss = SubScenario(version_id=version_id, sort_order=max_order + 1, **data)
        db.add(ss)
        await db.flush()
        return ss

    @staticmethod
    async def update_sub_scenario(db, ss_id: int, data: dict) -> SubScenario:
        r = await db.execute(select(SubScenario).where(SubScenario.id == ss_id))
        ss = r.scalar_one_or_none()
        if not ss:
            raise NotFoundError("子场景不存在")
        if data.get("name"):
            data["name"] = str(data["name"]).strip().upper()
        for k, v_item in data.items():
            if v_item is not None:
                setattr(ss, k, v_item)
        await db.flush()
        return ss

    @staticmethod
    async def delete_sub_scenario(db, ss_id: int):
        r = await db.execute(select(SubScenario).where(SubScenario.id == ss_id))
        ss = r.scalar_one_or_none()
        if not ss:
            raise NotFoundError("子场景不存在")
        await db.delete(ss)
        await db.flush()

    # ── Release Steps (Stage1) ──
    @staticmethod
    async def assign_approvers(db, version_id: int, test_manager: str = "", project_manager: str = ""):
        v = await VersionService.get_version(db, version_id)
        r = await db.execute(
            select(ReleaseStep).where(ReleaseStep.version_id == version_id, ReleaseStep.stage == STAGE1_RELEASE)
            .order_by(ReleaseStep.step_order))
        steps = list(r.scalars().all())
        if not steps:
            raise BusinessException(400, "未找到发布步骤")
        for s in steps:
            if s.step_order == 1 and s.status == "pending":
                s.assigned_to = test_manager
            if s.step_order == 2 and s.status == "pending":
                s.assigned_to = project_manager
        await db.flush()
        return steps

    @staticmethod
    async def submit_step(db, version_id: int, step_id: int, action: str, comment: str, current_user: dict):
        v = await VersionService.get_version(db, version_id)
        if v.status not in (VERSION_STATUS_DRAFT, VERSION_STATUS_RELEASED):
            raise BusinessException(400, "当前版本状态不允许提交审批")

        if action not in ("approve", "reject"):
            raise BusinessException(400, "无效的操作，必须为 approve 或 reject")

        r = await db.execute(select(ReleaseStep).where(
            ReleaseStep.id == step_id, ReleaseStep.version_id == version_id))
        step = r.scalar_one_or_none()
        if not step:
            raise NotFoundError("审批步骤不存在")
        if step.status != "pending":
            raise BusinessException(400, "该步骤已完成审批")

        display_name = current_user.get("display_name", "")
        if step.assigned_to and step.assigned_to != display_name:
            raise ForbiddenError(f"该步骤需要 {step.assigned_to} 处理")

        step.status = "approved" if action == "approve" else "rejected"
        step.approved_by = display_name
        step.approved_at = datetime.utcnow()
        step.comment = comment
        await db.flush()

        # Check if all Stage1 approved → released
        r = await db.execute(select(ReleaseStep).where(
            ReleaseStep.version_id == version_id, ReleaseStep.stage == STAGE1_RELEASE))
        stage1 = list(r.scalars().all())
        stage1_approved = sum(1 for s in stage1 if s.status == "approved")
        if stage1 and stage1_approved == len(stage1):
            v.status = VERSION_STATUS_RELEASED
            await db.flush()
        else:
            # Check Stage2
            r = await db.execute(select(ReleaseStep).where(
                ReleaseStep.version_id == version_id, ReleaseStep.stage == STAGE2_DEPLOY))
            stage2 = list(r.scalars().all())
            stage2_approved = sum(1 for s in stage2 if s.status == "approved")
            if stage2 and stage2_approved == len(stage2):
                v.status = VERSION_STATUS_DEPLOYED
        await db.flush()

        return step

    # ── Binary Files ──
    @staticmethod
    async def list_binaries(db, version_id: int) -> list[VersionBinaryFile]:
        r = await db.execute(
            select(VersionBinaryFile).where(VersionBinaryFile.version_id == version_id)
            .order_by(VersionBinaryFile.created_at.desc()))
        return list(r.scalars().all())

    @staticmethod
    async def create_binary(db, version_id: int, data: dict) -> VersionBinaryFile:
        bf = VersionBinaryFile(version_id=version_id, **data)
        db.add(bf)
        await db.flush()
        return bf

    @staticmethod
    async def delete_binary(db, file_id: int):
        r = await db.execute(select(VersionBinaryFile).where(VersionBinaryFile.id == file_id))
        bf = r.scalar_one_or_none()
        if not bf:
            raise NotFoundError("文件不存在")
        await db.delete(bf)
        await db.flush()

    # ── Archive Items ──
    @staticmethod
    async def list_archive_items(db, version_id: int) -> list[VersionArchiveItem]:
        r = await db.execute(
            select(VersionArchiveItem).where(VersionArchiveItem.version_id == version_id))
        return list(r.scalars().all())

    # ── Deployments (Stage2) ──
    @staticmethod
    async def create_deployments(db, version_id: int, data: dict) -> list[ReleaseDeployment]:
        v = await VersionService.get_version(db, version_id)
        if v.status not in (VERSION_STATUS_RELEASED, VERSION_STATUS_DEPLOYED):
            raise BusinessException(400, "仅已发布或已发行的版本可创建发行目标")

        targets = data.get("targets", [])
        if not targets:
            raise BusinessException(400, "请至少选择一个发行目标")

        te_engineer = data.get("te_engineer", "")

        # Auto-create Stage2 release step if not exists
        r = await db.execute(select(ReleaseStep).where(
            ReleaseStep.version_id == version_id, ReleaseStep.stage == STAGE2_DEPLOY))
        if not list(r.scalars().all()):
            db.add(ReleaseStep(
                version_id=version_id, stage=STAGE2_DEPLOY,
                step_order=1, step_name="TE工程师审核",
                approver_role="TE工程师", assigned_to=te_engineer,
            ))

        created = []
        for t in targets:
            dep = ReleaseDeployment(
                version_id=version_id,
                factory_id=t.get("factory_id"),
                factory_name=t.get("factory_name", ""),
                line_id=t.get("line_id"),
                line_name=t.get("line_name", ""),
                station_id=t.get("station_id"),
                station_name=t.get("station_name", ""),
                status="pending",
                assigned_to=(t.get("assign_te") and te_engineer) or te_engineer,
            )
            db.add(dep)
            await db.flush()
            created.append(dep)
        await db.flush()
        return created

    @staticmethod
    async def approve_deployment(db, deployment_id: int, action: str, comment: str, current_user: dict):
        r = await db.execute(select(ReleaseDeployment).where(ReleaseDeployment.id == deployment_id))
        dep = r.scalar_one_or_none()
        if not dep:
            raise NotFoundError("发行目标不存在")
        if dep.status != "pending":
            raise BusinessException(400, "已经处理")

        display_name = current_user.get("display_name", "")
        if dep.assigned_to and dep.assigned_to != display_name:
            raise ForbiddenError(f"该目标需要 {dep.assigned_to} 处理")

        dep.status = "approved" if action == "approve" else "rejected"
        dep.approved_by = display_name
        dep.approved_at = datetime.utcnow()
        dep.comment = comment
        await db.flush()
        return dep

    @staticmethod
    async def _resolve_station_ids(db, dep) -> list[int]:
        if dep.station_id:
            return [dep.station_id]
        if dep.line_id:
            r = await db.execute(select(TestStation).where(TestStation.line_id == dep.line_id))
            return [s.id for s in r.scalars().all()]
        if dep.factory_id:
            r = await db.execute(
                select(TestStation).join(ProductionLine, TestStation.line_id == ProductionLine.id)
                .where(ProductionLine.factory_id == dep.factory_id))
            return [s.id for s in r.scalars().all()]
        r = await db.execute(select(TestStation))
        return [s.id for s in r.scalars().all()]

    @staticmethod
    async def execute_deployment(db, deployment_id: int) -> ReleaseDeployment:
        r = await db.execute(select(ReleaseDeployment).where(ReleaseDeployment.id == deployment_id))
        dep = r.scalar_one_or_none()
        if not dep:
            raise NotFoundError("发行目标不存在")
        if dep.status != "approved":
            raise BusinessException(400, "只有已审批的发行目标可以执行")

        dep.status = "deployed"
        dep.deployed_at = datetime.utcnow()
        v = await db.get(TestVersion, dep.version_id)
        if v:
            station_ids = await VersionService._resolve_station_ids(db, dep)
            for sid in station_ids:
                await VersionService._push_version_to_station(db, dep.version_id, sid)

            # Also execute all other approved deployments for same version
            r = await db.execute(
                select(ReleaseDeployment).where(
                    ReleaseDeployment.version_id == dep.version_id,
                    ReleaseDeployment.status == "approved",
                    ReleaseDeployment.id != dep.id))
            for other in r.scalars().all():
                other.status = "deployed"
                other.deployed_at = datetime.utcnow()
                other_sids = await VersionService._resolve_station_ids(db, other)
                for sid in other_sids:
                    await VersionService._push_version_to_station(db, dep.version_id, sid)

            v.status = VERSION_STATUS_DEPLOYED

        await db.flush()
        return dep

    @staticmethod
    async def _push_version_to_station(db, version_id: int, station_id: int):
        v = await db.get(TestVersion, version_id)
        if not v:
            return
        station = await db.get(TestStation, station_id)
        if not station:
            return

        station.deployed_version = v.version

        # Get or create SoftwareConfig
        r = await db.execute(select(SoftwareConfig).where(SoftwareConfig.station_id == station_id))
        sw = r.scalar_one_or_none()
        if not sw:
            sw = SoftwareConfig(station_id=station_id, project_name=v.project_name or "")
            db.add(sw)
            await db.flush()
        sw.dut_version = v.version
        sw.project_name = v.project_name or ""

        # 1. Test items → EquipmentMetrics
        r = await db.execute(select(VersionArchiveItem).where(
            VersionArchiveItem.version_id == version_id, VersionArchiveItem.type == "test_item"))
        test_item_archives = list(r.scalars().all())
        if test_item_archives:
            sw.selected_test_item_ids = [a.item_id for a in test_item_archives]
            metrics_list = []
            for a in test_item_archives:
                snap = a.data_snapshot or {}
                metrics_list.append({
                    "name": snap.get("name", f"Item {a.item_id}"),
                    "expected_value": snap.get("expected_value", 0),
                    "min_value": snap.get("min_value", 0),
                    "max_value": snap.get("max_value", 0),
                    "unit": snap.get("unit", ""),
                    "category": snap.get("category", ""),
                    "sort_order": snap.get("sort_order", 0),
                    "item_id": a.item_id,
                })
            r = await db.execute(select(EquipmentMetrics).where(EquipmentMetrics.station_id == station_id))
            eqm = r.scalar_one_or_none()
            if not eqm:
                eqm = EquipmentMetrics(station_id=station_id)
                db.add(eqm)
            eqm.metrics_json = metrics_list

        # 1b. metrics_json archive fallback
        if not test_item_archives:
            r = await db.execute(select(VersionArchiveItem).where(
                VersionArchiveItem.version_id == version_id,
                VersionArchiveItem.type.in_(["metrics_json", "metrics_ini"])))
            metrics_archives = list(r.scalars().all())
            if metrics_archives:
                merged_metrics = []
                for a in metrics_archives:
                    raw = a.data_snapshot
                    if isinstance(raw, list):
                        merged_metrics.extend(raw)
                    elif isinstance(raw, dict):
                        merged_metrics.append(raw)
                if merged_metrics:
                    r = await db.execute(select(EquipmentMetrics).where(EquipmentMetrics.station_id == station_id))
                    eqm = r.scalar_one_or_none()
                    if not eqm:
                        eqm = EquipmentMetrics(station_id=station_id)
                        db.add(eqm)
                    eqm.metrics_json = merged_metrics

        # 2. Sequence data
        r = await db.execute(select(VersionArchiveItem).where(
            VersionArchiveItem.version_id == version_id, VersionArchiveItem.type == "sequence_step")
            .order_by(VersionArchiveItem.id))
        seq_snapshots = list(r.scalars().all())
        if seq_snapshots:
            sw.sequence_id = v.sequence_id
            sw.sequence_data = [a.data_snapshot for a in seq_snapshots]

        # 3. Property page → EquipmentPropertyPage
        r = await db.execute(select(VersionArchiveItem).where(
            VersionArchiveItem.version_id == version_id, VersionArchiveItem.type == "property_page"))
        prop_archives = list(r.scalars().all())
        if prop_archives:
            merged = {}
            for a in prop_archives:
                snap = a.data_snapshot or {}
                if isinstance(snap, dict):
                    merged.update(snap)
            r = await db.execute(select(EquipmentPropertyPage).where(EquipmentPropertyPage.station_id == station_id))
            eqpp = r.scalar_one_or_none()
            if not eqpp:
                eqpp = EquipmentPropertyPage(station_id=station_id)
                db.add(eqpp)
            if isinstance(eqpp.page_json, dict) and isinstance(merged, dict):
                eqpp.page_json = {**eqpp.page_json, **merged}
            else:
                eqpp.page_json = merged

        await db.flush()

        # 4. Sub-scenario data → HardwareParam + EquipmentPropertyPage
        r = await db.execute(select(SubScenario).where(SubScenario.version_id == version_id))
        all_sub_scenarios = list(r.scalars().all())
        if all_sub_scenarios:
            # 4a. Hardware params: replace station's existing params with sub-scenario data
            await db.execute(delete(HardwareParam).where(HardwareParam.station_id == station_id))
            sort = 1
            for ss in all_sub_scenarios:
                hw = ss.hardware_params or {}
                if isinstance(hw, dict):
                    for key, val in hw.items():
                        db.add(HardwareParam(
                            station_id=station_id, param_name=str(key),
                            param_value=str(val) if val is not None else "",
                            group_name=f"sub_scenario_{ss.id}", sort_order=sort))
                        sort += 1

            # 4b. Property page: merge sub-scenario property_pages
            merged_pp = {}
            for ss in all_sub_scenarios:
                pp = ss.property_page or {}
                if isinstance(pp, dict):
                    merged_pp.update(pp)
            if merged_pp:
                r = await db.execute(select(EquipmentPropertyPage).where(EquipmentPropertyPage.station_id == station_id))
                eqpp = r.scalar_one_or_none()
                if not eqpp:
                    eqpp = EquipmentPropertyPage(station_id=station_id)
                    db.add(eqpp)
                if isinstance(eqpp.page_json, dict):
                    eqpp.page_json = {**eqpp.page_json, **merged_pp}
                else:
                    eqpp.page_json = merged_pp

        await db.flush()

    # ── Pending Approvals ──
    @staticmethod
    async def get_pending_approvals(db, current_user: dict) -> list[dict]:
        display_name = current_user.get("display_name", "")
        items = []
        r = await db.execute(select(ReleaseStep).where(
            ReleaseStep.assigned_to == display_name, ReleaseStep.status == "pending"))
        for step in r.scalars().all():
            version = await db.get(TestVersion, step.version_id)
            items.append({
                "step": step.to_dict(),
                "version": version.to_dict() if version else {},
                "type": "step",
            })
        r = await db.execute(select(ReleaseDeployment).where(
            ReleaseDeployment.assigned_to == display_name,
            ReleaseDeployment.status.in_(["pending", "approved"])))
        for dep in r.scalars().all():
            version = await db.get(TestVersion, dep.version_id)
            items.append({
                "step": {"step_name": f"TE审核 - {dep.factory_name or dep.station_name or ''}"},
                "version": version.to_dict() if version else {},
                "type": "deployment",
                "dep_id": dep.id,
                "assigned_to": dep.assigned_to,
                "status": dep.status,
                "created_at": dep.created_at.isoformat() if dep.created_at else "",
            })
        return items

    @staticmethod
    async def get_next_version(db, project_name: str) -> dict:
        if not project_name:
            return {"version": "", "is_new": True}
        r = await db.execute(
            select(TestVersion).where(TestVersion.project_name == project_name)
            .order_by(TestVersion.created_at.desc()).limit(1))
        last = r.scalar_one_or_none()
        if not last:
            return {"version": "1.0.0", "is_new": True}
        v = last.version
        import re
        m = re.match(r"^(\D*)(\d+(?:\.\d+)*)", v)
        if m:
            prefix = m.group(1)
            num_part = m.group(2)
            parts = num_part.split(".")
            if len(parts) == 1:
                next_ver = prefix + str(int(parts[0]) + 1)
            elif len(parts) == 2:
                next_ver = prefix + f"{int(parts[0]) + 1}.0"
            else:
                next_ver = prefix + f"{int(parts[0]) + 1}." + ".".join(parts[1:])
        else:
            next_ver = "1.0.0"
        return {"version": next_ver, "is_new": False}

    @staticmethod
    async def list_pending_versions(db) -> list[TestVersion]:
        r = await db.execute(
            select(TestVersion).where(TestVersion.status == VERSION_STATUS_RELEASED)
            .order_by(TestVersion.created_at.desc()))
        return list(r.scalars().all())

    @staticmethod
    async def get_station_deployed_version(db, station_id: int, project: str = "", sequence_id: int = 0) -> dict:
        # When sequence_id is specified, return items from sequence directly
        if sequence_id:
            r = await db.execute(select(TestSequence).where(TestSequence.id == sequence_id))
            seq = r.scalar_one_or_none()
            test_items = []
            if seq:
                r = await db.execute(
                    select(TestSequenceStep).where(TestSequenceStep.sequence_id == seq.id)
                    .order_by(TestSequenceStep.step_order))
                for i, step in enumerate(r.scalars().all()):
                    t = await db.get(TestItemTemplate, step.template_id) if step.template_id else None
                    test_items.append({
                        "id": t.id if t else -(i + 1),
                        "name": t.name if t else f"步骤 {i + 1}",
                        "expected_value": "",
                        "min_value": "",
                        "max_value": "",
                        "unit": "",
                    })
            return {"code": 0, "data": {
                "version_id": 0, "version": "", "project_name": project,
                "description": "", "type": "", "bom_code": "", "tps_name": "",
                "sub_scenarios": [], "deployed_at": None,
                "test_items": test_items,
                "sequence_data": [], "binary_count": 0,
                "factory_name": "", "line_name": "", "station_name": "",
            }}

        # Find deployment
        q = select(ReleaseDeployment).where(
            ReleaseDeployment.station_id == station_id, ReleaseDeployment.status == "deployed")
        if project:
            q = q.join(TestVersion).where(TestVersion.project_name == project)
            q = q.order_by(ReleaseDeployment.deployed_at.desc())
        else:
            q = q.order_by(ReleaseDeployment.deployed_at.desc())
        r = await db.execute(q)
        dep = r.scalar_one_or_none()

        if dep:
            v = await db.get(TestVersion, dep.version_id)
            if v:
                data = await VersionService._build_deployed_version_response(db, v, dep=dep, station_id=station_id)
                return {"code": 0, "data": data}

        # Fallback: check station.deployed_version directly
        station = await db.get(TestStation, station_id)
        if station and station.deployed_version:
            v = None
            if project:
                r = await db.execute(select(TestVersion).where(
                    TestVersion.project_name == project,
                    TestVersion.version == station.deployed_version).limit(1))
                v = r.scalars().first()
            if not v:
                r = await db.execute(select(TestVersion).where(
                    TestVersion.project_name == project).order_by(TestVersion.updated_at.desc()).limit(1))
                v = r.scalars().first()
            if not v:
                r = await db.execute(select(TestVersion).where(
                    TestVersion.version == station.deployed_version).order_by(TestVersion.updated_at.desc()).limit(1))
                v = r.scalars().first()
            if not v:
                r = await db.execute(select(TestVersion).where(
                    TestVersion.status.in_([VERSION_STATUS_RELEASED, VERSION_STATUS_DEPLOYED])
                ).order_by(TestVersion.updated_at.desc()).limit(1))
                v = r.scalars().first()
            if v:
                data = await VersionService._build_deployed_version_response(db, v, station_id=station_id)
                return {"code": 0, "data": data}

        return {"code": 0, "data": None}

    @staticmethod
    async def _build_deployed_version_response(db, v: TestVersion, dep=None, station_id: int = 0) -> dict:
        test_items = []
        r = await db.execute(select(VersionArchiveItem).where(
            VersionArchiveItem.version_id == v.id, VersionArchiveItem.type == "test_item"))
        for item in r.scalars().all():
            snap = item.data_snapshot or {}
            test_items.append({
                "id": item.item_id,
                "name": snap.get("name", ""),
                "expected_value": snap.get("expected_value", ""),
                "min_value": snap.get("min_value", ""),
                "max_value": snap.get("max_value", ""),
                "unit": snap.get("unit", ""),
            })
        # Derive from sequence steps if no test_item archives
        if not test_items:
            r = await db.execute(select(VersionArchiveItem).where(
                VersionArchiveItem.version_id == v.id, VersionArchiveItem.type == "sequence_step")
                .order_by(VersionArchiveItem.id))
            seq_steps = list(r.scalars().all())
            if seq_steps:
                for i, step_data in enumerate(seq_steps):
                    snap = step_data.data_snapshot or {}
                    name = snap.get("template_name", "") or snap.get("step_name", "") or f"步骤 {i + 1}"
                    test_items.append({
                        "id": snap.get("template_id", 0) or -(i + 1),
                        "name": name, "expected_value": "", "min_value": "", "max_value": "", "unit": "",
                    })
            else:
                r = await db.execute(select(TestItem).where(TestItem.is_active == True).order_by(TestItem.sort_order))
                for item in r.scalars().all():
                    test_items.append({
                        "id": item.id, "name": item.name,
                        "expected_value": str(item.expected_value) if item.expected_value else "",
                        "min_value": str(item.min_value) if item.min_value else "",
                        "max_value": str(item.max_value) if item.max_value else "",
                        "unit": item.unit or "",
                    })

        # Sequence steps data
        r = await db.execute(select(VersionArchiveItem).where(
            VersionArchiveItem.version_id == v.id, VersionArchiveItem.type == "sequence_step")
            .order_by(VersionArchiveItem.id))
        seq_steps_data = [{"step_order": a.data_snapshot.get("step_order") if isinstance(a.data_snapshot, dict) else 0,
                           "template_name": a.data_snapshot.get("template_name") if isinstance(a.data_snapshot, dict) else "",
                           **({"data_snapshot": a.data_snapshot} if not isinstance(a.data_snapshot, str) else {})}
                          for a in r.scalars().all()]

        r = await db.execute(select(func.count(VersionBinaryFile.id)).where(VersionBinaryFile.version_id == v.id))
        binary_count = r.scalar() or 0

        r = await db.execute(select(SubScenario).where(SubScenario.version_id == v.id).order_by(SubScenario.sort_order))
        ss_list = [s.to_dict() for s in r.scalars().all()]

        return {
            "version_id": v.id,
            "version": v.version,
            "project_name": v.project_name,
            "description": v.description,
            "type": v.type or "standard",
            "bom_code": v.bom_code or "",
            "tps_name": v.tps_name or "",
            "sub_scenarios": ss_list,
            "deployed_at": dep.deployed_at.isoformat() if dep and dep.deployed_at else None,
            "test_items": test_items,
            "sequence_data": seq_steps_data,
            "binary_count": binary_count,
            "factory_name": dep.factory_name if dep else "",
            "line_name": dep.line_name if dep else "",
            "station_name": dep.station_name if dep else ((await db.get(TestStation, station_id)).name if station_id and (await db.get(TestStation, station_id)) else ""),
        }

    @staticmethod
    async def list_station_deployed_versions(db, station_id: int, deployed_only: bool = False) -> list[dict]:
        deps = await db.execute(
            select(ReleaseDeployment).where(
                ReleaseDeployment.station_id == station_id, ReleaseDeployment.status == "deployed")
            .order_by(ReleaseDeployment.deployed_at.desc()))
        seen = set()
        result = []
        for dep in deps.scalars().all():
            v = await db.get(TestVersion, dep.version_id)
            if v and v.status != VERSION_STATUS_DELISTED:
                key = (v.project_name, v.version)
                if key not in seen:
                    seen.add(key)
                    ss_list = await db.execute(
                        select(SubScenario).where(SubScenario.version_id == v.id).order_by(SubScenario.sort_order))
                    sub_scenarios = []
                    for s in ss_list.scalars().all():
                        sd = s.to_dict()
                        bf = await db.execute(
                            select(VersionBinaryFile).where(
                                VersionBinaryFile.version_id == v.id,
                                VersionBinaryFile.sub_scenario_id == s.id))
                        sd["binary_files"] = [{"id": f.id, "filename": f.filename, "file_size": f.file_size, "description": f.description} for f in bf.scalars().all()]
                        sub_scenarios.append(sd)
                    result.append({
                        "version_id": v.id,
                        "version": v.version,
                        "project_name": v.project_name,
                        "description": v.description,
                        "type": v.type or "standard",
                        "bom_code": v.bom_code or "",
                        "tps_name": v.tps_name or "",
                        "process_type": v.process_type or "",
                        "workstation": v.workstation or "",
                        "codes_config": v.codes_config or [],
                        "sub_scenarios": sub_scenarios,
                    })
        if not deployed_only:
            # Also include released/deployed versions not yet deployed to this station
            versions = await db.execute(
                select(TestVersion).where(TestVersion.status.in_([VERSION_STATUS_RELEASED, VERSION_STATUS_DEPLOYED]))
                .order_by(TestVersion.updated_at.desc()))
            for v in versions.scalars().all():
                key = (v.project_name, v.version)
                if key not in seen:
                    seen.add(key)
                    ss_list = await db.execute(
                        select(SubScenario).where(SubScenario.version_id == v.id).order_by(SubScenario.sort_order))
                    sub_scenarios = []
                    for s in ss_list.scalars().all():
                        sd = s.to_dict()
                        bf = await db.execute(
                            select(VersionBinaryFile).where(
                                VersionBinaryFile.version_id == v.id,
                                VersionBinaryFile.sub_scenario_id == s.id))
                        sd["binary_files"] = [{"id": f.id, "filename": f.filename, "file_size": f.file_size, "description": f.description} for f in bf.scalars().all()]
                        sub_scenarios.append(sd)
                    result.append({
                        "version_id": v.id,
                        "version": v.version,
                        "project_name": v.project_name,
                        "description": v.description,
                        "type": v.type or "standard",
                        "bom_code": v.bom_code or "",
                        "tps_name": v.tps_name or "",
                        "process_type": v.process_type or "",
                        "workstation": v.workstation or "",
                        "codes_config": v.codes_config or [],
                        "sub_scenarios": sub_scenarios,
                    })
        return result

    @staticmethod
    async def get_station_deployed_archives(db, station_id: int) -> dict:
        station = await db.get(TestStation, station_id)
        if not station:
            return None

        # Find deployment by scope priority: station → line → factory → global
        dep = None
        for scope_field in ["station_id", "line_id"]:
            if scope_field == "station_id":
                r = await db.execute(select(ReleaseDeployment).where(
                    ReleaseDeployment.station_id == station_id, ReleaseDeployment.status == "deployed")
                    .order_by(ReleaseDeployment.deployed_at.desc()))
                dep = r.scalars().first()
                if dep:
                    break
            elif scope_field == "line_id" and station.line_id:
                r = await db.execute(select(ReleaseDeployment).where(
                    ReleaseDeployment.line_id == station.line_id, ReleaseDeployment.status == "deployed")
                    .order_by(ReleaseDeployment.deployed_at.desc()).limit(1))
                dep = r.scalars().first()
                if dep:
                    break

        if not dep:
            r = await db.execute(select(ProductionLine.factory_id).where(ProductionLine.id == station.line_id))
            factory_id_row = r.scalar_one_or_none()
            if factory_id_row:
                r = await db.execute(select(ReleaseDeployment).where(
                    ReleaseDeployment.factory_id == factory_id_row, ReleaseDeployment.status == "deployed")
                    .order_by(ReleaseDeployment.deployed_at.desc()).limit(1))
                dep = r.scalars().first()

        if not dep:
            r = await db.execute(select(ReleaseDeployment).where(ReleaseDeployment.status == "deployed")
                                 .order_by(ReleaseDeployment.deployed_at.desc()).limit(1))
            dep = r.scalars().first()

        if not dep:
            return None

        v = await db.get(TestVersion, dep.version_id)
        if not v:
            return None

        # Read hardware_params and property_page from sub-scenarios
        r = await db.execute(select(SubScenario).where(SubScenario.version_id == v.id).order_by(SubScenario.sort_order))
        hw_items = []
        pp_items = []
        for ss in r.scalars().all():
            if ss.hardware_params and isinstance(ss.hardware_params, dict):
                hw_items.append({"sub_scenario": ss.name, "data": ss.hardware_params})
            if ss.property_page and isinstance(ss.property_page, dict):
                pp_items.append({"sub_scenario": ss.name, "data": ss.property_page})

        merged_hw = {}
        for item in hw_items:
            merged_hw.update(item["data"])
        merged_pp = {}
        for item in pp_items:
            merged_pp.update(item["data"])

        return {
            "version_id": v.id,
            "version": v.version,
            "hardware_params_list": hw_items,
            "property_page_list": pp_items,
            "hardware_params": merged_hw,
            "property_page": merged_pp,
        }

    @staticmethod
    async def get_inherit_data(db, version_id: int) -> dict:
        v = await VersionService.get_version(db, version_id)
        d = v.to_dict()
        r = await db.execute(select(VersionArchiveItem).where(VersionArchiveItem.version_id == version_id))
        d["archive_items"] = [a.to_dict() for a in r.scalars().all()]
        r = await db.execute(select(func.count(VersionBinaryFile.id)).where(VersionBinaryFile.version_id == version_id))
        d["binary_count"] = r.scalar() or 0
        r = await db.execute(select(VersionBinaryFile).where(VersionBinaryFile.version_id == version_id))
        d["binary_files"] = [b.to_dict() for b in r.scalars().all()]
        return d

    @staticmethod
    async def get_archive_configs(db) -> dict:
        r = await db.execute(select(TestItem).where(TestItem.is_active == True).order_by(TestItem.sort_order))
        test_items = [i.to_dict() for i in r.scalars().all()]
        r = await db.execute(select(TestSequence).where(TestSequence.is_active == True))
        sequences = [s.to_dict() for s in r.scalars().all()]
        return {"test_items": test_items, "sequences": sequences}

    @staticmethod
    async def list_all_users(db) -> list[dict]:
        r = await db.execute(select(User).where(User.is_active == True).order_by(User.display_name))
        return [{"id": u.id, "display_name": u.display_name, "role": u.role} for u in r.scalars().all()]
