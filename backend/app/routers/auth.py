"""
认证与用户管理 API
对应 design.md §5.1, §5.2, §4.4, §8
"""
from fastapi import APIRouter, Depends, Request, Response, Query
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from app.deps.db_deps import get_db
from app.deps.redis_deps import get_redis
from app.deps.auth_deps import get_current_user, require_developer, require_super_admin
from app.core.response import success, paginated
from app.schemas.auth import (
    ResetPasswordReq,
    LoginReq, UserCreateReq, UserUpdateReq, LoginResp, UserResp,
    RegistrationReq, RegistrationResp, AuditLogResp,
)
from app.services.auth_service import AuthService

router = APIRouter(tags=["认证"])


@router.post("/login")
async def login(
    req: LoginReq,
    response: Response,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    """登录 — 验证密码，创建 Redis Session"""
    user_data, session_id = await AuthService.login(db, redis, req.username, req.password)
    response.set_cookie(
        key="session_id",
        value=session_id,
        max_age=86400,
        httponly=True,
        samesite="lax",
    )
    return success(data=user_data, message="登录成功")


@router.post("/logout")
async def logout(
    request: Request,
    redis: Redis = Depends(get_redis),
):
    """登出 — 清除 Redis Session"""
    session_id = request.cookies.get("session_id")
    await AuthService.logout(redis, session_id)
    return success(message="已登出")


@router.get("/me")
async def get_me(
    request: Request,
    redis: Redis = Depends(get_redis),
):
    """当前用户信息"""
    session_id = request.cookies.get("session_id")
    user = await AuthService.get_current_user(redis, session_id)
    return success(data=user)


# ── Account Registration ──

@router.post("/register")
async def register(
    req: RegistrationReq,
    db: AsyncSession = Depends(get_db),
):
    """账号自助注册（提交审核申请）"""
    reg = await AuthService.register(
        db, req.username, req.display_name, req.password,
        req.department, req.requested_role, req.requested_domains, req.justification,
    )
    return success(data={"id": reg.id, "status": reg.status}, message="注册申请已提交，请等待管理员审核")


@router.get("/registrations")
async def list_registrations(
    status: str = "pending",
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_super_admin),
):
    """注册申请列表 (super_admin)"""
    regs, total = await AuthService.list_registrations(db, status, page, page_size)
    items = [RegistrationResp(**r.to_dict()) for r in regs]
    return paginated(items, total, page, page_size)


@router.put("/registrations/{reg_id}/approve")
async def approve_registration(
    reg_id: int,
    approved_domains: list = Query(default=None, alias="approved_domains"),
    comment: str = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_super_admin),
    request: Request = None,
):
    """审核通过注册申请 (super_admin)"""
    u = await AuthService.approve_registration(
        db, reg_id, user.get("id", 0), user.get("username", ""), comment, approved_domains,
    )
    await AuthService.log_audit(
        db, user.get("id", 0), user.get("username", ""), "approve_registration",
        resource_type="account_registration", resource_id=str(reg_id),
        detail={"username": u.username, "approved_domains": approved_domains or u.domains},
        ip_address=request.client.host if request else None,
    )
    return success(data=UserResp(**u.to_dict()), message="账号已审核并激活")


@router.put("/registrations/{reg_id}/reject")
async def reject_registration(
    reg_id: int,
    comment: str = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_super_admin),
    request: Request = None,
):
    """驳回注册申请 (super_admin)"""
    reg = await AuthService.reject_registration(db, reg_id, user.get("id", 0), comment)
    await AuthService.log_audit(
        db, user.get("id", 0), user.get("username", ""), "reject_registration",
        resource_type="account_registration", resource_id=str(reg_id),
        detail={"comment": comment},
        ip_address=request.client.host if request else None,
    )
    return success(data=RegistrationResp(**reg.to_dict()), message="注册申请已驳回")


@router.get("/audit-logs")
async def list_audit_logs(
    action: str = None,
    resource_type: str = None,
    user_id: int = None,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_super_admin),
):
    """审计日志列表 (super_admin)"""
    logs, total = await AuthService.list_audit_logs(db, page, page_size, action, resource_type, user_id)
    items = [AuditLogResp(
        id=l.id, user_id=l.user_id, username=l.username, action=l.action,
        resource_type=l.resource_type, resource_id=l.resource_id, detail=l.detail,
        ip_address=l.ip_address, created_at=l.created_at,
    ) for l in logs]
    return paginated(items, total, page, page_size)


# ── User Management ──

@router.get("/users")
async def list_users(
    page: int = 1,
    page_size: int = 20,
    role: str = None,
    status: str = None,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_developer),
):
    """用户列表 (developer+)"""
    users, total = await AuthService.list_users(db, page, page_size, role_filter=role, status_filter=status)
    items = [UserResp(**u.to_dict()) for u in users]
    return paginated(items, total, page, page_size)


@router.post("/users")
async def create_user(
    req: UserCreateReq,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_developer),
    request: Request = None,
):
    """创建用户 (developer+)"""
    u = await AuthService.create_user(
        db, req.username, req.display_name, req.password, req.role, req.domains,
        created_by=user.get("username", ""), is_active=True,
    )
    await AuthService.log_audit(
        db, user.get("id", 0), user.get("username", ""), "create_user",
        resource_type="user", resource_id=str(u.id),
        detail={"username": u.username, "role": u.role, "domains": u.domains},
        ip_address=request.client.host if request else None,
    )
    return success(data=UserResp(**u.to_dict()), message="用户创建成功")


@router.put("/users/{user_id}")
async def update_user(
    user_id: int,
    req: UserUpdateReq,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_developer),
    request: Request = None,
):
    """更新用户 (developer+)"""
    data = req.model_dump(exclude_none=True)
    u = await AuthService.update_user(db, user_id, data)
    await AuthService.log_audit(
        db, user.get("id", 0), user.get("username", ""), "update_user",
        resource_type="user", resource_id=str(user_id),
        detail={"updated_fields": list(data.keys())},
        ip_address=request.client.host if request else None,
    )
    return success(data=UserResp(**u.to_dict()), message="用户更新成功")


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_super_admin),
    request: Request = None,
):
    """删除用户 (super_admin)"""
    await AuthService.delete_user(db, user_id)
    await AuthService.log_audit(
        db, user.get("id", 0), user.get("username", ""), "delete_user",
        resource_type="user", resource_id=str(user_id),
        ip_address=request.client.host if request else None,
    )
    return success(message="用户已删除")


@router.put("/users/{user_id}/reset-password")
async def reset_password(
    user_id: int,
    req: ResetPasswordReq,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_super_admin),
    request: Request = None,
):
    """重置用户密码 (super_admin)"""
    u = await AuthService.reset_password(db, user_id, req.new_password)
    await AuthService.log_audit(
        db, user.get("id", 0), user.get("username", ""), "reset_password",
        resource_type="user", resource_id=str(user_id),
        detail={"target_username": u.username},
        ip_address=request.client.host if request else None,
    )
    return success(message="密码重置成功")
