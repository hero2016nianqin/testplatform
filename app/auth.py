"""
认证与授权工具模块

提供登录状态校验、角色权限检查的装饰器，
用于保护需要特定权限的 API 路由和页面路由。
"""

from functools import wraps
from flask import session, redirect, url_for, jsonify, request


def login_required(f):
    """
    登录验证装饰器。
    检查 session 中是否存在 user_id，不存在则返回 401 或重定向。

    用法:
        @login_required
        def some_route():
            ...
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            # API 请求返回 JSON，页面请求返回重定向
            if request.path.startswith('/api/'):
                return jsonify({'code': 401,
                                'message': '请先登录'}), 401
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function


def process_required(f):
    """
    工艺工程师权限验证装饰器。
    在 login_required 基础上，额外检查 role 是否为 process。

    用法:
        @process_required
        def admin_only_route():
            ...
    """
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if session.get('role') != 'process':
            if request.path.startswith('/api/'):
                return jsonify({'code': 403,
                                'message': '权限不足，需要工艺工程师权限'}), 403
            return redirect('/')
        return f(*args, **kwargs)
    return decorated_function


def get_current_user():
    """
    从 session 中获取当前登录用户信息。

    Returns:
        包含 username, display_name, role 的字典，未登录返回 None
    """
    if 'user_id' not in session:
        return None
    return {
        'user_id': session['user_id'],
        'username': session['username'],
        'display_name': session['display_name'],
        'role': session['role'],
    }
