"""
用户认证 API 路由模块

提供登录、登出、获取当前用户信息和用户管理功能。
首次启动时自动创建默认的工艺工程师账号。
"""

from datetime import datetime
from flask import Blueprint, request, jsonify, session, render_template

from app import db
from app.models.user import User
from app.auth import login_required, process_required

# 认证蓝图，无 API 前缀
auth_bp = Blueprint('auth', __name__)


def seed_default_users():
    """
    初始化默认用户账号（启动时自动调用）。
    如果数据库中没有任何用户，创建两个默认账号。
    """
    if User.query.count() == 0:
        # 默认工艺工程师账号
        admin = User(
            username='admin',
            display_name='工艺工程师',
            role='process',
        )
        admin.set_password('admin123')
        db.session.add(admin)

        # 默认生产操作员账号
        operator = User(
            username='operator',
            display_name='生产操作员',
            role='production',
        )
        operator.set_password('123456')
        db.session.add(operator)
        db.session.commit()


@auth_bp.route('/login', methods=['GET'])
def login_page():
    """登录页面"""
    return render_template('login.html')


@auth_bp.route('/api/auth/login', methods=['POST'])
def login():
    """
    用户登录。
    请求体:
        username: 用户名
        password: 密码
    """
    data = request.get_json() or {}
    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not username or not password:
        return jsonify({'code': 1, 'message': '用户名和密码不能为空'}), 400

    user = User.query.filter_by(username=username, is_active=True).first()
    if not user or not user.check_password(password):
        return jsonify({'code': 1, 'message': '用户名或密码错误'}), 401

    # 记录登录时间
    user.last_login = datetime.utcnow()
    db.session.commit()

    # 写入 session
    session['user_id'] = user.id
    session['username'] = user.username
    session['display_name'] = user.display_name
    session['role'] = user.role
    session.permanent = True

    return jsonify({
        'code': 0,
        'data': user.to_dict(),
        'message': f'欢迎回来，{user.display_name}',
    })


@auth_bp.route('/api/auth/logout', methods=['POST'])
def logout():
    """用户登出，清除 session"""
    session.clear()
    return jsonify({'code': 0, 'message': '已退出登录'})


@auth_bp.route('/api/auth/me', methods=['GET'])
def current_user():
    """获取当前登录用户信息"""
    if 'user_id' not in session:
        return jsonify({'code': 401, 'message': '未登录',
                        'data': None}), 401
    return jsonify({
        'code': 0,
        'data': {
            'user_id': session['user_id'],
            'username': session['username'],
            'display_name': session['display_name'],
            'role': session['role'],
        }
    })


# ==================== 用户管理（仅工艺工程师可操作） ====================

@auth_bp.route('/api/auth/users', methods=['GET'])
@process_required
def list_users():
    """获取所有用户列表（仅工艺工程师）"""
    users = User.query.order_by(User.created_at).all()
    return jsonify({
        'code': 0,
        'data': [u.to_dict() for u in users],
        'total': len(users),
    })


@auth_bp.route('/api/auth/users', methods=['POST'])
@process_required
def create_user():
    """
    创建新用户（仅工艺工程师）。
    请求体:
        username: 用户名（必填）
        display_name: 显示名称（必填）
        password: 密码（必填）
        role: 角色（production/process，默认 production）
    """
    data = request.get_json() or {}
    username = data.get('username', '').strip()
    display_name = data.get('display_name', '').strip()
    password = data.get('password', '')
    role = data.get('role', 'production')

    if not username or not display_name or not password:
        return jsonify({'code': 1, 'message': '用户名、显示名称和密码不能为空'}), 400
    if role not in ('production', 'process'):
        return jsonify({'code': 1, 'message': '角色无效'}), 400
    if User.query.filter_by(username=username).first():
        return jsonify({'code': 1, 'message': '用户名已存在'}), 409

    user = User(
        username=username,
        display_name=display_name,
        role=role,
    )
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    return jsonify({'code': 0, 'data': user.to_dict(),
                    'message': '用户创建成功'})


@auth_bp.route('/api/auth/users/<int:user_id>', methods=['PUT'])
@process_required
def update_user(user_id):
    """更新用户信息（仅工艺工程师）"""
    user = User.query.get_or_404(user_id)
    data = request.get_json() or {}

    if 'display_name' in data:
        user.display_name = data['display_name'].strip()
    if 'password' in data and data['password']:
        user.set_password(data['password'])
    if 'role' in data:
        user.role = data['role']
    if 'is_active' in data:
        user.is_active = bool(data['is_active'])

    db.session.commit()
    return jsonify({'code': 0, 'data': user.to_dict(),
                    'message': '已更新'})


@auth_bp.route('/api/auth/users/<int:user_id>', methods=['DELETE'])
@process_required
def delete_user(user_id):
    """删除用户（仅工艺工程师）"""
    user = User.query.get_or_404(user_id)
    # 不允许删除自己
    if user.id == session.get('user_id'):
        return jsonify({'code': 1, 'message': '不能删除自己'}), 400
    db.session.delete(user)
    db.session.commit()
    return jsonify({'code': 0, 'message': '已删除'})
