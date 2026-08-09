# FastAPI + Vue3 SPA 重构架构计划

## 1. 后端标准化分层目录树

```
test_platform_v2/
├── backend/
│   ├── app/
│   │   ├── __init__.py                  # FastAPI App 工厂 (create_app)
│   │   ├── config/                      # 配置层
│   │   │   ├── __init__.py
│   │   │   ├── settings.py              # Pydantic Settings (多环境)
│   │   │   └── constants.py             # 全局常量
│   │   │
│   │   ├── core/                        # 核心基础设施
│   │   │   ├── __init__.py
│   │   │   ├── database.py              # 异步 SQLAlchemy
│   │   │   ├── redis.py                 # Redis 集群连接池
│   │   │   ├── minio_client.py          # MinIO 预签名 URL
│   │   │   ├── security.py              # Session RBAC
│   │   │   ├── exceptions.py            # BusinessException
│   │   │   └── response.py              # 统一响应体 ApiResponse
│   │   │
│   │   ├── models/                      # 异步 SQLAlchemy ORM
│   │   │   ├── __init__.py              # Base + 全 model
│   │   │   ├── user.py                  # User
│   │   │   ├── station.py               # Factory/Line/Station/Cabinet/Chassis/Slot
│   │   │   ├── station_config.py        # EquipmentConfig/HardwareParam/SoftwareConfig/ScenarioConfig
│   │   │   ├── equipment.py             # EquipmentDefinition/Metrics/PropertyPage
│   │   │   ├── test_item.py             # TestItem
│   │   │   ├── test_sequence.py         # TestItemTemplate/TestSequence/TestSequenceStep
│   │   │   ├── test_run.py              # TestRun (分区表)
│   │   │   ├── test_result.py           # TestResult (分区表)
│   │   │   └── version.py               # TestVersion/SubScenario/ReleaseStep/...
│   │   │
│   │   ├── schemas/                     # Pydantic request/response
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── station.py
│   │   │   ├── equipment.py
│   │   │   ├── test_item.py
│   │   │   ├── test_sequence.py
│   │   │   ├── test_run.py
│   │   │   ├── test_result.py
│   │   │   ├── version.py
│   │   │   ├── log.py
│   │   │   └── common.py
│   │   │
│   │   ├── routers/                     # FastAPI APIRouter
│   │   │   ├── __init__.py
│   │   │   ├── auth.py                  # /api/v1/auth/*
│   │   │   ├── station.py               # /api/v1/stations/*
│   │   │   ├── test.py                  # /api/v1/tests/*
│   │   │   ├── version.py               # /api/v1/versions/*
│   │   │   ├── log.py                   # /api/v1/logs/*
│   │   │   └── init.py                  # /api/v1/init/*
│   │   │
│   │   ├── services/                    # 业务逻辑层
│   │   │   ├── __init__.py
│   │   │   ├── auth_service.py
│   │   │   ├── station_service.py
│   │   │   ├── equipment_service.py
│   │   │   ├── test_executor.py
│   │   │   ├── test_service.py
│   │   │   ├── version_service.py
│   │   │   ├── log_service.py
│   │   │   └── config_manager.py
│   │   │
│   │   ├── deps/                        # FastAPI Depends
│   │   │   ├── __init__.py
│   │   │   ├── auth_deps.py
│   │   │   ├── db_deps.py
│   │   │   └── redis_deps.py
│   │   │
│   │   ├── utils/                       # 工具函数
│   │   │   ├── __init__.py
│   │   │   ├── cache.py
│   │   │   ├── pagination.py
│   │   │   ├── export.py
│   │   │   └── batch_id.py
│   │   │
│   │   └── ws/                          # WebSocket
│   │       ├── __init__.py
│   │       ├── manager.py
│   │       └── handlers.py
│   │
│   ├── tasks/                           # Celery 异步任务
│   │   ├── __init__.py
│   │   ├── celery_app.py
│   │   ├── test_tasks.py
│   │   ├── deploy_tasks.py
│   │   ├── archive_tasks.py
│   │   └── cleanup_tasks.py
│   │
│   ├── scripts/                         # 运维脚本
│   │   ├── migrate_sqlite_to_pg.py
│   │   ├── seed_data.py
│   │   └── init_db.py
│   │
│   ├── tests/                           # 测试
│   │   ├── conftest.py
│   │   ├── test_auth.py
│   │   ├── test_station.py
│   │   ├── test_test.py
│   │   ├── test_version.py
│   │   └── test_log.py
│   │
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
│
├── deploy/
│   ├── docker-compose.yml
│   ├── nginx.conf
│   └── pg_init.sql
│
└── docs/
    └── architecture-v2.md
```

## 2. 全局统一响应体、异常、CORS、日志

### 统一 JSON 响应体

```python
from typing import Generic, TypeVar, Optional, Any
from pydantic import BaseModel

T = TypeVar("T")

class ApiResponse(BaseModel, Generic[T]):
    code: int = 0
    message: str = "ok"
    data: Optional[T] = None

class PaginatedData(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int
```

### 业务异常

```python
class BusinessException(Exception):
    def __init__(self, code: int, message: str, status_code: int = 400): ...
class AuthError(BusinessException): ...
class ForbiddenError(BusinessException): ...
class NotFoundError(BusinessException): ...
```

### CORS

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## 3. 环境变量模板

见 `backend/.env.example` (dev/test/prod 三种)

## 4. PostgreSQL DDL 要点

- 全部原 JSON → JSONB
- test_runs / test_results / test_logs 按月声明式分区
- 26 张表完整复刻原 SQLite 模型
- 外键、唯一约束、索引、字段注释齐全

## 5. 编码命名规范

| 层 | 规范 |
|---|---|
| Python 文件 | snake_case |
| 类 | PascalCase |
| 函数/变量 | snake_case |
| 数据库列 | snake_case |
| API 路由 | /api/v1/{resource}/{id} |
| Pydantic 模型 | {Name}Req / {Name}Resp |
| Vue 组件 | PascalCase.vue |
| Vue 路由 | kebab-case |

## 6. 12 周里程碑

| 周 | 里程碑 |
|---|---|
| W1-2 | 后端基建 (脚手架 + ORM + DB + Redis + RBAC + MinIO) |
| W3-4 | 全部 REST API v1 CRUD + 版本审批 |
| W5 | WebSocket 实时日志 |
| W6 | Celery 异步任务 + XXL-Job |
| W7-8 | Vue3 SPA 基座 |
| W9-10 | 前端全业务页面 |
| W11 | Docker 容器化 + 部署 |
| W12 | 全功能测试 + 压测 + 文档 |

## 7. 业务模块 ↔ 设计文档交叉引用

| 模块 | 设计文档 | 核心表 |
|---|---|---|
| Auth | §4.4, §5, §8 | User |
| Station | §4.1, §5, §7.1 | Factory/Line/Station/Chassis/Slot/Cabinet |
| Equip Config | §4.1, §5 | EquipmentConfig/HardwareParam/SoftwareConfig/ScenarioConfig |
| Metrics | §4.1, §5, §7.4 | EquipmentMetrics/EquipmentPropertyPage |
| Test Item | §4.2, §5, §7.2 | TestItem |
| Test Sequence | §4.2, §5, §7.2 | TestItemTemplate/TestSequence/TestSequenceStep |
| Test Run | §4.2, §5, §6.1, §12 | TestRun/TestResult |
| Version | §4.3, §5, §7.3-7.5 | TestVersion/SubScenario/ReleaseStep/ArchiveItem/BinaryFile/Deployment |
| Log | §5, §6.1 | TestLog |
| Init | §5, §11 | 种子数据 |

## 8. 第 1-2 周后端基建开发清单

### Day 1: 脚手架
1. `requirements.txt`
2. `app/__init__.py`
3. `app/config/settings.py`
4. `app/config/constants.py`

### Day 2: 核心基础设施
5. `app/core/database.py`
6. `app/core/redis.py`
7. `app/core/minio_client.py`
8. `app/core/response.py`
9. `app/core/exceptions.py`
10. `app/core/security.py`

### Day 3: Dependencies + 工具
11. `app/deps/auth_deps.py`
12. `app/deps/db_deps.py`
13. `app/deps/redis_deps.py`
14. `app/utils/cache.py`
15. `app/utils/pagination.py`
16. `app/utils/export.py`
17. `app/utils/batch_id.py`

### Day 4-5: ORM 模型
18. `app/models/__init__.py`
19. `app/models/user.py`
20. `app/models/station.py`
21. `app/models/station_config.py`
22. `app/models/equipment.py`
23. `app/models/test_item.py`
24. `app/models/test_sequence.py`
25. `app/models/test_run.py`
26. `app/models/test_result.py`
27. `app/models/version.py`

### Day 6-7: 迁移 + 种子数据
28. `backend/alembic/env.py`
29. `backend/scripts/init_db.py`
30. `backend/scripts/seed_data.py`
31. `backend/scripts/migrate_sqlite_to_pg.py`
32. `backend/tests/conftest.py`
33. `backend/tests/test_auth.py`
