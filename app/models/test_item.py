"""
测试项模型

定义单个测试项目的属性，包括测试名称、标准值、合格范围上下限、
所属分类、排序和启用状态。是测试平台的核心数据模型之一。
"""

from datetime import datetime
from app import db


class TestItem(db.Model):
    """测试项表 - 存储所有可执行的测试项目定义"""

    __tablename__ = 'test_items'

    # 主键，自增 ID
    id = db.Column(db.Integer, primary_key=True)
    # 测试项名称，建立索引加速查询
    name = db.Column(db.String(200), nullable=False, index=True)
    # 测试项描述，说明测试目的和方法
    description = db.Column(db.Text, default='')
    # 标准值（标称值），作为偏差计算的基准
    expected_value = db.Column(db.Float, nullable=False)
    # 合格判定下限，实测值 >= min_value 时通过
    min_value = db.Column(db.Float, nullable=False)
    # 合格判定上限，实测值 <= max_value 时通过
    max_value = db.Column(db.Float, nullable=False)
    # 计量单位，如 V、A、Hz、°C 等
    unit = db.Column(db.String(50), default='')
    # 分类标签，用于测试项分组和筛选
    category = db.Column(db.String(100), default='general', index=True)
    # 是否启用，禁用项不参与测试执行
    is_active = db.Column(db.Boolean, default=True)
    # 排序序号，控制测试项在页面上的显示顺序
    sort_order = db.Column(db.Integer, default=0)
    # 创建时间
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # 更新时间，自动记录
    updated_at = db.Column(db.DateTime, default=datetime.utcnow,
                           onupdate=datetime.utcnow)

    # 关联的测试结果列表（一对多关系）
    results = db.relationship('TestResult', backref='test_item', lazy='dynamic')

    def to_dict(self):
        """序列化为字典，用于 JSON 响应"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'expected_value': self.expected_value,
            'min_value': self.min_value,
            'max_value': self.max_value,
            'unit': self.unit,
            'category': self.category,
            'is_active': self.is_active,
            'sort_order': self.sort_order,
        }

    def __repr__(self):
        return f'<TestItem {self.name}>'
