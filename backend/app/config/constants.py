from typing import Dict

# ── 角色层级 ──────────────────────────────────────────────
# 超级管理员: 系统全部页面、全部 BOM、全部领域无限制操作，不受任何规则约束
# 装备经理/装备测试经理: 所有领域数据只读；可处理评审、归档流程
# 装备开发人员: 新建BOM指标配置、维护领域责任人、编辑自身绑定领域内测试项
# 各细分领域开发人员: 仅编辑自身绑定领域内测试项
# 生产工艺人员: 仅可查看已归档/已发布BOM
# 生产操作人员: 仅查阅已发布BOM
ROLE_HIERARCHY: Dict[str, int] = {
    "operator": 0,
    "process": 1,
    "developer": 2,
    "equipment_manager": 3,
    "equipment_test_manager": 3,
    "fd_developer": 2,        # 功放开发
    "duxingqi_developer": 2,   # 双进制器开发
    "trx_developer": 2,       # TRX 开发
    "algorithm_developer": 2, # 算法开发
    "power_developer": 2,     # 电源开发
    "board_software_developer": 2,  # 单板软件开发
    "ict_developer": 2,       # ICT 开发
    "product_se": 2,          # 产品 SE
    "equipment_developer": 2,  # 装备开发人员 (新增专属权限)
    "super_admin": 4,
}

ROLE_LABELS: Dict[str, str] = {
    "operator": "操作人员",
    "process": "工艺人员",
    "developer": "装备开发人员",
    "equipment_manager": "装备经理",
    "equipment_test_manager": "装备测试经理",
    "fd_developer": "功放开发",
    "duxingqi_developer": "双进制器开发",
    "trx_developer": "TRX 开发",
    "algorithm_developer": "算法开发",
    "power_developer": "电源开发",
    "board_software_developer": "单板软件开发",
    "ict_developer": "ICT 开发",
    "product_se": "产品 SE",
    "equipment_developer": "装备开发人员",
    "super_admin": "超级管理员",
}

# ── 槽位状态 ──────────────────────────────────────────────
SLOT_STATUS_IDLE = "idle"
SLOT_STATUS_TESTING = "testing"
SLOT_STATUS_PASS = "pass"
SLOT_STATUS_FAIL = "fail"
SLOT_STATUS_DISABLED = "disabled"

# ── 测试批次状态 ──────────────────────────────────────────
RUN_STATUS_PENDING = "pending"
RUN_STATUS_RUNNING = "running"
RUN_STATUS_COMPLETED = "completed"
RUN_STATUS_FAILED = "failed"

# ── 版本状态 ──────────────────────────────────────────────
VERSION_STATUS_DRAFT = "draft"
VERSION_STATUS_RELEASED = "released"
VERSION_STATUS_DEPLOYED = "deployed"
VERSION_STATUS_DELISTED = "delisted"

# ── 版本类型 ──────────────────────────────────────────────
VERSION_TYPE_STANDARD = "standard"
VERSION_TYPE_MULTI_PROCESS = "multi_process"
VERSION_TYPE_PRODUCT_FAMILY = "product_family"

# ── 子场景内置类型（均以大写风格保存，格式：工序-工位）──────────
SUB_SCENARIO_PRESETS = [
    "FT1-MP1",
    "FT2-MP2",
    "FT2-MP3",
    "FT2-MP4",
    "FT2-MP5",
    "OFT-MP1",
    "ESS-MP1",
]

# ── 审批阶段 ──────────────────────────────────────────────
STAGE1_RELEASE = 1
STAGE2_DEPLOY = 2

# ── WebSocket 事件 ────────────────────────────────────────
WS_EVENT_RUN_STARTED = "run_started"
WS_EVENT_ITEM_TESTED = "item_tested"
WS_EVENT_RUN_COMPLETED = "run_completed"
WS_EVENT_RUN_FAILED = "run_failed"

# ── 归档条目类型 ──────────────────────────────────────────
ARCHIVE_TYPE_TEST_ITEM = "test_item"
ARCHIVE_TYPE_CONFIG = "config"
ARCHIVE_TYPE_SEQUENCE_STEP = "sequence_step"
ARCHIVE_TYPE_HARDWARE_PARAMS = "hardware_params"
ARCHIVE_TYPE_PROPERTY_PAGE = "property_page"
ARCHIVE_TYPE_METRICS_JSON = "metrics_json"

# ── 分页默认值 ────────────────────────────────────────────
DEFAULT_PAGE = 1
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 200
