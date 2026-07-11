"""
数据模型模块

定义测试平台的所有数据表：
- User:            用户账号（生产操作员/工艺工程师）
- TestItem:        测试项定义（名称、标准值、上下限、分类）
- TestItemTemplate: 测试项模板（微服务地址、关键项标记、超时）
- TestSequence:    测试序列（有序模板集合）
- TestSequenceStep: 序列步骤（模板与顺序的关联）
- TestResult:      测试结果记录（实测值、合格判定、偏差）
- TestRun:         测试批次（状态跟踪、通过/失败统计）
- TestStation:     测试工站
- TestChassis:     机框
- TestSlot:        槽位
- EquipmentConfig: 装备参数配置
- HardwareParam:   硬件参数
- SoftwareConfig:  软件参数配置
- ScenarioConfig:  场景参数配置
- TestVersion:     版本归档
- ReleaseStep:     发布审批步骤
- VersionArchiveItem: 归档内容条目
- ReleaseDeployment:  发行目标
"""

from .user import User
from .test_item import TestItem
from .test_sequence import TestItemTemplate, TestSequence, TestSequenceStep
from .test_result import TestResult
from .test_run import TestRun
from .station import (
    TestStation, TestChassis, TestSlot,
    EquipmentConfig, HardwareParam, SoftwareConfig, ScenarioConfig,
    EquipmentMetrics, EquipmentPropertyPage,
)
from .version import TestVersion, ReleaseStep, VersionArchiveItem, ReleaseDeployment, VersionBinaryFile, SubScenario

__all__ = [
    'User', 'TestItem', 'TestItemTemplate', 'TestSequence', 'TestSequenceStep',
    'TestResult', 'TestRun',
    'TestStation', 'TestChassis', 'TestSlot',
    'EquipmentConfig', 'HardwareParam', 'SoftwareConfig', 'ScenarioConfig',
    'EquipmentMetrics', 'EquipmentPropertyPage',
    'TestVersion', 'ReleaseStep', 'VersionArchiveItem', 'ReleaseDeployment',
    'VersionBinaryFile', 'SubScenario',
]
