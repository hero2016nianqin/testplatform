"""
用户模型

定义系统用户，区分两类角色：
- production: 生产操作员，仅能执行测试和查看日志
- process:    工艺工程师，拥有全部权限（设置、初始化、配置管理）

密码使用 Werkzeug 的 pbkdf2:sha256 方式加密存储（兼容 Python 3.9）。
"""

from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from app import db


class User(db.Model):
    """用户表 - 存储登录账号和角色信息"""

    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    # 登录用户名，唯一
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    # 用户显示名称（操作员姓名）
    display_name = db.Column(db.String(100), nullable=False)
    # 加密后的密码哈希（pbkdf2:sha256 算法）
    password_hash = db.Column(db.String(256), nullable=False)
    # 角色: production(生产操作员) / process(工艺工程师)
    role = db.Column(db.String(20), nullable=False, default='production')
    # 是否启用
    is_active = db.Column(db.Boolean, default=True)
    # 最后登录时间
    last_login = db.Column(db.DateTime, nullable=True)
    # 创建时间
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password: str):
        """设置密码（存储为 pbkdf2:sha256 哈希值）"""
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')

    def check_password(self, password: str) -> bool:
        """校验密码"""
        return check_password_hash(self.password_hash, password)

    @property
    def is_process(self) -> bool:
        """是否为工艺工程师"""
        return self.role == 'process'

    @property
    def is_production(self) -> bool:
        """是否为生产操作员"""
        return self.role == 'production'

    def to_dict(self):
        """序列化为字典（不返回密码哈希）"""
        return {
            'id': self.id,
            'username': self.username,
            'display_name': self.display_name,
            'role': self.role,
            'role_label': '工艺工程师' if self.role == 'process'
                          else '生产操作员',
            'is_active': self.is_active,
            'last_login': self.last_login.isoformat()
                          if self.last_login else None,
            'created_at': self.created_at.isoformat()
                          if self.created_at else None,
        }

    def __repr__(self):
        return f'<User {self.username} [{self.role}]>'
