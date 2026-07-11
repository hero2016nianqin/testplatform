"""
用户模型

定义系统用户，区分四类角色（按权限从低到高）：
- operator:     操作人员，仅能执行测试和查看日志
- process:      工艺人员，可修改测试装备参数
- developer:    装备开发人员，可进行版本归档、参数设置等
- super_admin:  超级管理员，拥有全部权限（含下架版本）
"""

from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from app import db

ROLE_HIERARCHY = {
    'operator': 0,
    'process': 1,
    'developer': 2,
    'super_admin': 3,
}

ROLE_LABELS = {
    'operator': '操作人员',
    'process': '工艺人员',
    'developer': '装备开发人员',
    'super_admin': '超级管理员',
}


class User(db.Model):
    """用户表 - 存储登录账号和角色信息"""

    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    display_name = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='operator')
    is_active = db.Column(db.Boolean, default=True)
    last_login = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'display_name': self.display_name,
            'role': self.role,
            'role_label': ROLE_LABELS.get(self.role, self.role),
            'is_active': self.is_active,
            'last_login': self.last_login.isoformat()
                          if self.last_login else None,
            'created_at': self.created_at.isoformat()
                          if self.created_at else None,
        }

    def __repr__(self):
        return f'<User {self.username} [{self.role}]>'
