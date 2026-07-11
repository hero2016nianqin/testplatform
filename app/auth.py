"""
认证与授权工具模块

提供登录状态校验、角色权限检查的装饰器，
用于保护需要特定权限的 API 路由和页面路由。

角色层级（从低到高）：
  operator(操作人员) < process(工艺人员) < developer(装备开发人员) < super_admin(超级管理员)
"""

from functools import wraps
from flask import session, redirect, url_for, jsonify, request

from app.models.user import ROLE_HIERARCHY, ROLE_LABELS


def login_required(f):
    """登录验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.path.startswith('/api/'):
                return jsonify({'code': 401, 'message': '请先登录'}), 401
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function


def role_required(min_role):
    """
    角色权限验证装饰器。
    在 login_required 基础上，检查用户角色是否 >= min_role。

    用法:
        @role_required('process')
        def some_route(): ...
    """
    min_level = ROLE_HIERARCHY.get(min_role, -1)

    def decorator(f):
        @wraps(f)
        @login_required
        def decorated_function(*args, **kwargs):
            user_role = session.get('role', 'operator')
            user_level = ROLE_HIERARCHY.get(user_role, -1)
            if user_level < min_level:
                if request.path.startswith('/api/'):
                    label = ROLE_LABELS.get(min_role, min_role)
                    return jsonify({'code': 403,
                                    'message': f'权限不足，需要 {label} 及以上权限'}), 403
                return redirect('/')
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# 保留兼容的快捷装饰器
process_required = role_required('process')
developer_required = role_required('developer')
super_admin_required = role_required('super_admin')


def get_current_user():
    """获取当前登录用户信息"""
    if 'user_id' not in session:
        return None
    return {
        'user_id': session['user_id'],
        'username': session['username'],
        'display_name': session['display_name'],
        'role': session['role'],
    }
