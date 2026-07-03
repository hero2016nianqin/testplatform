"""
测试配置方案模型

保存完整的测试配置方案快照（JSON 格式），支持版本管理。
可用于在不同产品型号或产线之间切换测试参数，也支持将来
通过配置模板引擎实现更灵活的参数注入。
"""

from datetime import datetime
from app import db


class TestConfig(db.Model):
    """测试配置方案表 - 存储完整的配置模板"""

    __tablename__ = 'test_configs'

    # 主键，自增 ID
    id = db.Column(db.Integer, primary_key=True)
    # 配置方案名称，唯一标识
    name = db.Column(db.String(200), nullable=False, unique=True)
    # 方案描述
    description = db.Column(db.Text, default='')
    # 配置数据（JSON 字符串），包含完整的测试项列表和参数
    config_data = db.Column(db.Text, default='{}')
    # 版本号，支持通过版本号进行方案演进管理
    version = db.Column(db.String(50), default='1.0')
    # 是否当前激活的方案
    is_active = db.Column(db.Boolean, default=True)
    # 创建时间
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # 更新时间，自动记录
    updated_at = db.Column(db.DateTime, default=datetime.utcnow,
                           onupdate=datetime.utcnow)

    def to_dict(self):
        """序列化为字典，不含具体 config_data 内容（体积较大时按需加载）"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'version': self.version,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat()
                          if self.created_at else None,
            'updated_at': self.updated_at.isoformat()
                          if self.updated_at else None,
        }

    def __repr__(self):
        return f'<TestConfig {self.name} v{self.version}>'
