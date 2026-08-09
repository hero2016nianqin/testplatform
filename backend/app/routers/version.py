"""
版本管理 API
对应 design.md §4.3, §5.1, §5.2, §7.3-7.5
"""
from fastapi import APIRouter, Depends, Query, UploadFile, File, Form
from fastapi.responses import Response, RedirectResponse
from app.utils.rate_limiter import rate_limit
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.deps.db_deps import get_db
from app.deps.auth_deps import get_current_user, require_developer, require_super_admin, require_process
from app.core.response import success, paginated
from app.models.version import VersionBinaryFile, SubScenario, VersionArchiveItem
from app.schemas.version import (
    VersionCreateReq, VersionUpdateReq, VersionResp,
    SubScenarioCreateReq, SubScenarioUpdateReq, SubScenarioResp,
    StepSubmitReq, AssignApproversReq,
    DeploymentCreateReq, DeploymentApproveReq, DeploymentResp,
    ArchiveItemResp, BinaryFileResp, VersionDetailResp,
)
from app.services.version_service import VersionService

router = APIRouter(tags=["版本管理"])

svc = VersionService()


# ── Version CRUD ──
@router.get("")
async def list_versions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    status: str = Query(None),
    project_name: str = Query(None),
    scope: str = Query(None),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    items, total = await svc.list_versions(
        db, page, page_size, status, project_name, scope,
        user.get("display_name") if scope == "mine" else None,
    )
    return paginated(items, total, page, page_size)


@router.post("", dependencies=[Depends(require_developer), Depends(rate_limit("create_version", 20, 60))])
async def create_version(
    req: VersionCreateReq,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    v = await svc.create_version(db, req.model_dump(), user.get("display_name", ""))
    return success(data=v.to_dict(), message="版本创建成功")


# ── Static routes must come before parameterized routes ──
@router.get("/pending-approvals")
async def pending_approvals(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    items = await svc.get_pending_approvals(db, user)
    return success(data=items)


@router.get("/next-version")
async def next_version(
    project_name: str = Query(""),
    db: AsyncSession = Depends(get_db),
):
    result = await svc.get_next_version(db, project_name or "")
    return success(data=result)


@router.get("/all-users")
async def all_users(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    users = await svc.list_all_users(db)
    return success(data=users)


@router.get("/archive-configs")
async def archive_configs(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    data = await svc.get_archive_configs(db)
    return success(data=data)


@router.get("/sub-scenario-presets")
async def sub_scenario_presets():
    from app.config.constants import SUB_SCENARIO_PRESETS
    return success(data={
        "presets": SUB_SCENARIO_PRESETS,
        "format_hint": "工序-工位，例如 FT-MP9，保存时自动转为大写",
    })


@router.get("/{version_id}")
async def get_version(version_id: int, db: AsyncSession = Depends(get_db)):
    d = await svc.get_version_detail(db, version_id)
    return success(data=d)


@router.put("/{version_id}", dependencies=[Depends(require_developer)])
async def update_version(version_id: int, req: VersionUpdateReq, db: AsyncSession = Depends(get_db)):
    v = await svc.update_version(db, version_id, req.model_dump(exclude_none=True))
    return success(data=v.to_dict(), message="版本更新成功")


@router.delete("/{version_id}", dependencies=[Depends(require_super_admin)])
async def delete_version(version_id: int, db: AsyncSession = Depends(get_db)):
    await svc.delete_version(db, version_id)
    return success(message="版本已删除")


@router.post("/{version_id}/delist", dependencies=[Depends(require_super_admin)])
async def delist_version(version_id: int, db: AsyncSession = Depends(get_db)):
    v = await svc.delist_version(db, version_id)
    return success(data=v.to_dict(), message="版本已下架")


@router.post("/{version_id}/restore", dependencies=[Depends(require_super_admin)])
async def restore_version(version_id: int, db: AsyncSession = Depends(get_db)):
    v = await svc.restore_version(db, version_id)
    return success(data=v.to_dict(), message="版本已恢复")


# ── SubScenarios ──
@router.get("/{version_id}/sub-scenarios")
async def list_sub_scenarios(version_id: int, db: AsyncSession = Depends(get_db)):
    items = await svc.list_sub_scenarios(db, version_id)
    return success(data=[SubScenarioResp(**s.to_dict()) for s in items])


@router.post("/{version_id}/sub-scenarios", dependencies=[Depends(require_developer)])
async def create_sub_scenario(version_id: int, req: SubScenarioCreateReq, db: AsyncSession = Depends(get_db)):
    ss = await svc.create_sub_scenario(db, version_id, req.model_dump())
    return success(data=SubScenarioResp(**ss.to_dict()), message="子场景创建成功")


@router.put("/sub-scenarios/{ss_id}", dependencies=[Depends(require_developer)])
async def update_sub_scenario(ss_id: int, req: SubScenarioUpdateReq, db: AsyncSession = Depends(get_db)):
    ss = await svc.update_sub_scenario(db, ss_id, req.model_dump(exclude_none=True))
    return success(data=SubScenarioResp(**ss.to_dict()), message="子场景更新成功")


@router.delete("/sub-scenarios/{ss_id}", dependencies=[Depends(require_developer)])
async def delete_sub_scenario(ss_id: int, db: AsyncSession = Depends(get_db)):
    await svc.delete_sub_scenario(db, ss_id)
    return success(message="子场景已删除")


@router.get("/sub-scenarios/{ss_id}")
async def get_sub_scenario(ss_id: int, db: AsyncSession = Depends(get_db)):
    from app.core.exceptions import NotFoundError
    r = await db.execute(select(SubScenario).where(SubScenario.id == ss_id))
    ss = r.scalar_one_or_none()
    if not ss:
        raise NotFoundError("子场景不存在")
    return success(data=SubScenarioResp(**ss.to_dict()))


# ── SubScenario JSON download ──
@router.get("/{version_id}/sub-scenarios/{ss_id}/{field}/download")
async def download_sub_scenario_json(version_id: int, ss_id: int, field: str, db: AsyncSession = Depends(get_db)):
    from app.core.exceptions import NotFoundError, BusinessException
    if field not in ("hardware_params", "property_page", "software_metrics"):
        raise BusinessException(400, "无效字段")
    r = await db.execute(select(SubScenario).where(SubScenario.id == ss_id, SubScenario.version_id == version_id))
    ss = r.scalar_one_or_none()
    if not ss:
        raise NotFoundError("子场景不存在")
    import json as json_lib, urllib.parse
    raw = getattr(ss, field, None) or {}
    pretty = json_lib.dumps(raw, indent=2, ensure_ascii=False)
    encoded_name = urllib.parse.quote(f"{ss.name}_{field}.json", safe='')
    return Response(content=pretty, media_type="application/json",
                    headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_name}"})


# ── Archive Item JSON download ──
@router.get("/{version_id}/archive-items/{item_id}/download")
async def download_archive_item_json(version_id: int, item_id: int, db: AsyncSession = Depends(get_db)):
    from app.core.exceptions import NotFoundError
    r = await db.execute(select(VersionArchiveItem).where(
        VersionArchiveItem.id == item_id, VersionArchiveItem.version_id == version_id))
    ai = r.scalar_one_or_none()
    if not ai:
        raise NotFoundError("归档条目不存在")
    import json as json_lib
    raw = ai.data_snapshot or {}
    pretty = json_lib.dumps(raw, indent=2, ensure_ascii=False)
    filename = f"archive_{ai.id}_{ai.type}.json"
    return Response(content=pretty, media_type="application/json",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})


# ── Approvers (Stage1) ──
@router.post("/{version_id}/assign-approvers", dependencies=[Depends(require_developer)])
async def assign_approvers(version_id: int, req: AssignApproversReq, db: AsyncSession = Depends(get_db)):
    steps = await svc.assign_approvers(db, version_id, req.test_manager, req.project_manager)
    return success(data=[s.to_dict() for s in steps], message="审批人设置成功")


@router.post("/{version_id}/submit-step")
async def submit_step(
    version_id: int,
    req: StepSubmitReq,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    step = await svc.submit_step(db, version_id, req.step_id, req.action, req.comment, user)
    return success(data=step.to_dict(), message="审批已提交")


# ── Binary Files ──
@router.get("/{version_id}/binaries")
async def list_binaries(version_id: int, db: AsyncSession = Depends(get_db)):
    items = await svc.list_binaries(db, version_id)
    return success(data=[BinaryFileResp(**b.to_dict()) for b in items])


@router.post("/{version_id}/binaries", dependencies=[Depends(require_developer)])
async def upload_binary(
    version_id: int,
    file: UploadFile = File(...),
    description: str = Form(""),
    sub_scenario_id: int = Form(0),
    db: AsyncSession = Depends(get_db),
):
    import os
    content = await file.read()
    object_name = f"versions/{version_id}/{file.filename}"
    temp_path = os.path.join("/tmp", file.filename or "upload.bin")
    with open(temp_path, "wb") as f:
        f.write(content)

    from app.core.minio_client import upload_file
    from app.config import get_settings
    settings = get_settings()
    if os.environ.get("APP_ENV", settings.APP_ENV) == "dev":
        local_dir = f"/tmp/opencode_files/{object_name}"
        os.makedirs(os.path.dirname(local_dir), exist_ok=True)
        with open(local_dir, "wb") as f:
            f.write(content)
        stored_path = local_dir
    else:
        try:
            await upload_file(object_name, temp_path, file.content_type or "application/octet-stream")
            stored_path = object_name
        except Exception:
            local_dir = f"/tmp/opencode_files/{object_name}"
            os.makedirs(os.path.dirname(local_dir), exist_ok=True)
            with open(local_dir, "wb") as f:
                f.write(content)
            stored_path = local_dir
    os.remove(temp_path)
    bf = await svc.create_binary(db, version_id, {
        "filename": file.filename or "unknown",
        "file_path": stored_path,
        "file_size": len(content),
        "description": description,
        "sub_scenario_id": sub_scenario_id or None,
    })
    return success(data=BinaryFileResp(**bf.to_dict()), message="文件上传成功")


@router.delete("/{version_id}/binaries/{file_id}", dependencies=[Depends(require_developer)])
async def delete_binary(version_id: int, file_id: int, db: AsyncSession = Depends(get_db)):
    r = await db.get(VersionBinaryFile, file_id)
    if r:
        import os
        if r.file_path and os.path.exists(r.file_path):
            os.remove(r.file_path)
        else:
            from app.core.minio_client import remove_file
            try:
                await remove_file(r.file_path)
            except Exception:
                pass
    await svc.delete_binary(db, file_id)
    return success(message="文件已删除")


@router.get("/{version_id}/binaries/{file_id}/download")
async def download_binary(version_id: int, file_id: int, db: AsyncSession = Depends(get_db)):
    from app.core.exceptions import NotFoundError
    r = await db.get(VersionBinaryFile, file_id)
    if not r:
        raise NotFoundError("文件不存在")
    import os
    if r.file_path and os.path.exists(r.file_path):
        return Response(content=open(r.file_path, "rb").read(),
                        media_type="application/octet-stream",
                        headers={"Content-Disposition": f'attachment; filename="{r.filename}"'})
    from app.core.minio_client import presigned_download_url
    url = await presigned_download_url(r.file_path)
    return RedirectResponse(url)


# ── Deployments (Stage2) ──
@router.post("/{version_id}/deployments", dependencies=[Depends(require_developer), Depends(rate_limit("create_deployment", 20, 60))])
async def create_deployment(version_id: int, req: DeploymentCreateReq, db: AsyncSession = Depends(get_db)):
    deps = await svc.create_deployments(db, version_id, req.model_dump())
    return success(data=[DeploymentResp(**d.to_dict()) for d in deps], message="发行目标创建成功")


@router.post("/deployments/{deployment_id}/approve")
async def approve_deployment(
    deployment_id: int,
    req: DeploymentApproveReq,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    dep = await svc.approve_deployment(db, deployment_id, req.action, req.comment, user)
    return success(data=DeploymentResp(**dep.to_dict()), message="发行审批通过")


@router.post("/deployments/{deployment_id}/execute", dependencies=[Depends(require_developer)])
async def execute_deployment(deployment_id: int, db: AsyncSession = Depends(get_db)):
    dep = await svc.execute_deployment(db, deployment_id)
    return success(data=DeploymentResp(**dep.to_dict()), message="发行执行成功")


# ── Archive Items ──
@router.get("/{version_id}/archive-items")
async def list_archive_items(version_id: int, db: AsyncSession = Depends(get_db)):
    items = await svc.list_archive_items(db, version_id)
    return success(data=[ArchiveItemResp(**a.to_dict()) for a in items])


@router.get("/{version_id}/inherit-data")
async def get_inherit_data(version_id: int, db: AsyncSession = Depends(get_db)):
    d = await svc.get_inherit_data(db, version_id)
    return success(data=d)
