"""
数据模型模块

定义测试平台的五个核心数据表：
- User:      用户账号（生产操作员/工艺工程师）
- TestItem:   测试项定义（名称、标准值、上下限、分类）
- TestResult: 测试结果记录（实测值、合格判定、偏差）
- TestConfig: 配置方案快照（版本管理、JSON 配置数据）
- TestRun:    测试批次（状态跟踪、通过/失败统计）
"""

from .user import User
from .test_item import TestItem
from .test_result import TestResult
from .test_config import TestConfig
from .test_run import TestRun

__all__ = ['User', 'TestItem', 'TestResult', 'TestConfig', 'TestRun']
