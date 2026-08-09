# Test Platform — 总体设计文档

## 1. 项目概述

Test Platform 是一个面向生产线装备的**测试管理平台**，提供装备定义、部署、版本管理、测试执行、记录查询等完整闭环功能。

### 核心能力

| 能力 | 说明 |
|---|---|
| **装备层级管理** | 厂区 → 线体 → 工站(TestStation) → 机柜(Cabinet) → 机框(Chassis) → 槽位(Slot) |
| **装备定义模板** | 可复用的装备模板，包含布局结构、默认参数，支持版本化 |
| **扫码即测** | 单一槽位扫码立即执行测试，无批处理队列 |
| **版本归档与发布** | 两级审批流程(发布+发行)，支持多厂区目标部署 |
| **测试记录查询** | R1/R2/R3 三级层级表格，支持展开与 CSV 导出 |
| **测试序列管理** | 测试项模板(微服务地址/关键项标记/超时) + 可排序测试序列 |
| **关键项中断** | 关键测试项失败时自动终止后续所有测试项的执行 |
| **角色权限** | 四级角色：操作员(operator) < 工艺(process) < 开发(developer) < 超级管理员(super_admin) |
| **版本类型** | 标准版(standard)、多工序版(multi_process)、产品族版(product_family)，支持继承 |

---

## 2. 技术栈

| 层 | 技术 | 说明 |
|---|---|---|---|
| **后端框架** | Flask 3.x | WSGI 应用框架，工厂模式 |
| **WSGI 服务器** | Gunicorn + eventlet workers | 多进程并发，单机 8000+ 并发 |
| **反向代理** | Nginx | 静态文件直服、负载均衡、WebSocket 代理 |
| **ORM** | SQLAlchemy 3.x (Flask-SQLAlchemy) | 数据库映射 + 连接池 |
| **数据库** | PostgreSQL 15+ (可配置) | 支持行级锁、高并发读写 |
| **实时通信** | Socket.IO (Flask-SocketIO + Redis) | 跨 worker 广播测试进度 |
| **Session** | Redis (flask-session) | 多 worker 共享登录状态 |
| **缓存** | Redis (Flask-Caching) | API 响应缓存，降低 DB 压力 |
| **任务调度** | Celery + Redis Beat | 分布式异步任务，不阻塞 worker |
| **前端** | Bootstrap 5.3 + 原生 JavaScript | 无前端框架 |
| **文件格式** | CSV / XLSX / JSON / XML / YAML | 配置导入导出 |
| **二进制存储** | 文件系统 + VersionBinaryFile 模型 | 固件/驱动等二进制文件管理 |
| **模板引擎** | Jinja2 (Flask 内置) | 服务端渲染 |
| **认证** | Session (Redis) + pbkdf2:sha256 | 分布式 session 共享 |

### 核心依赖

```
# Web 框架
flask>=3.0, flask-sqlalchemy>=3.1, flask-socketio>=5.3, flask-cors>=4.0
flask-session>=0.8, flask-caching>=2.1

# 数据库
psycopg2-binary>=2.9

# 实时通信
python-socketio>=5.11, eventlet>=0.33

# 任务调度
celery>=5.3, redis>=5.0

# 数据处理
pandas>=2.1, openpyxl>=3.1

# WSGI 服务器
gunicorn>=21.2
```

---

## 3. 应用架构

### 3.1 目录结构

```
test_platform/
├── run.py                         # 入口点
├── .env.example                   # 环境变量模板
├── Dockerfile                     # 生产容器镜像
├── docker-compose.yml             # 全栈容器编排 (PostgreSQL + Redis + Flask + Celery + Nginx)
├── nginx.conf                     # Nginx 反向代理+静态文件配置
├── gunicorn.conf.py               # Gunicorn 多 worker 配置
├── config/
│   ├── default_config.py          # Flask 配置 (PostgreSQL/Redis/连接池)
│   └── config_manager.py          # 配置文件导入/导出/校验
├── database/                      # 数据库文件（开发环境 SQLite 使用）
├── app/
│   ├── __init__.py                # 应用工厂 (create_app)
│   ├── auth.py                    # 认证装饰器 (4 级角色)
│   ├── models/                    # 数据模型
│   │   ├── user.py                # User (含 last_login, created_at)
│   │   ├── test_item.py           # TestItem
│   │   ├── test_sequence.py       # TestItemTemplate / TestSequence / TestSequenceStep
│   │   ├── test_result.py         # TestResult (含 duration_ms, remark)
│   │   ├── test_run.py            # TestRun (含 station_id, slot_id, sequence_id)
│   │   ├── station.py             # Factory/Line/Station/Cabinet/Chassis/Slot + 配置模型 + EquipmentMetrics/PropertyPage
│   │   └── version.py             # TestVersion/SubScenario/ReleaseStep/ArchiveItem/Deployment/VersionBinaryFile
│   ├── routes/                    # 路由层
│   │   ├── auth_routes.py         # 认证 API + 用户管理 CRUD
│   │   ├── main_routes.py         # 页面路由 (10 页)
│   │   ├── test_routes.py         # 测试项 + 模板 + 序列 + 测试执行 API
│   │   ├── station_routes.py      # 层级 + 装备 + 配置 + 指标 + 属性页 API
│   │   ├── log_routes.py          # 日志查询/导出/上传/下载/统计
│   │   ├── init_routes.py         # 系统初始化/重置/导入默认配置
│   │   └── version_routes.py      # 版本归档/发布/发行/二进制/子场景
│   ├── services/                  # 业务逻辑层
│   │   ├── test_executor.py       # 测试执行引擎 (SocketIO 推送)
│   │   ├── log_service.py         # 文件日志存储/压缩/统计
│   │   └── scheduler.py           # 后台调度 (APScheduler)
│   ├── templates/                 # Jinja2 模板 (10 页)
│   ├── static/
│   │   ├── css/style.css
│   │   └── js/main.js
├── config/
│   ├── default_config.py          # Flask 默认配置
│   └── config_manager.py          # 配置文件导入/导出/校验 (CSV/XLSX/JSON/XML)
├── uploads/                       # 上传文件 (含版本二进制、装备配置)
└── logs/                          # 日志文件
```

### 3.2 分层职责

```
┌─────────────────────────────────────────────────────┐
│  Nginx (反向代理 + 静态文件 /static/)                │
│  └─ upstream → Gunicorn (8 workers × eventlet)      │
├─────────────────────────────────────────────────────┤
│  templates/ (Jinja2 服务端渲染 + 原生 JS)            │
│  └─ 通过 apiFetch/fetch 调用 REST API                 │
├─────────────────────────────────────────────────────┤
│  routes/ (蓝图 Blueprint)                            │
│  └─ 请求解析/参数校验/权限检查 → 调用模型/服务        │
├─────────────────────────────────────────────────────┤
│  services/ (业务逻辑)                                │
│  ├─ test_executor.py → SocketIO (Redis) 推送         │
│  ├─ log_service.py → 文件存储                        │
│  ├─ tasks.py → Celery 异步任务                       │
│  └─ scheduler.py → Celery Beat 定时调度              │
├─────────────────────────────────────────────────────┤
│  models/ (SQLAlchemy ORM)                           │
│  └─ 数据定义/关系映射/to_dict 序列化                  │
├─────────────────────────────────────────────────────┤
│  PostgreSQL + Redis                                  │
│  ├─ 数据库 (连接池 20/40)                            │
│  └─ 缓存/Session/SocketIO 消息队列/Celery Broker     │
└─────────────────────────────────────────────────────┘
```

### 3.3 启动流程 (create_app)

1. 加载配置 → 2. 初始化 db/Redis Session/Redis Cache/SocketIO(Redis)/CORS → 3. 注册模型 → 4. `db.create_all()` → 5. 数据库迁移(列添加, PostgreSQL 原生 ALTER TABLE) → 6. 种子数据(4个默认用户) → 7. 注册蓝图 → 8. 初始化 Celery → 9. 创建目录

### 3.4 部署架构 (Docker Compose)

```
┌─────────────────────────────────────────────────────────────┐
│  nginx:1.25 (80端口)                                         │
│  ├─ /static/* → 直接读取 app/static/                         │
│  ├─ /socket.io/* → WebSocket 升级代理                        │
│  └─ /* → proxy_pass → flask:5000                            │
├─────────────────────────────────────────────────────────────┤
│  flask (Gunicorn 8w × eventlet, 2000 conn/worker)           │
│  ├─ 连接 PostgreSQL (pool_size=20, max_overflow=40)          │
│  ├─ 连接 Redis (Session + Cache + SocketIO + Celery)         │
│  └─ 文件存储 → uploads/ logs/                               │
├─────────────────────────────────────────────────────────────┤
│  celery-worker (4并发, 执行异步任务)                          │
│  └─ cleanup_expired_runs / compress_old_logs                │
├─────────────────────────────────────────────────────────────┤
│  celery-beat (定时触发)                                       │
│  └─ 每小时 → cleanup_expired_runs                            │
│  └─ 每天 → compress_old_logs                                │
├─────────────────────────────────────────────────────────────┤
│  postgres:15 (数据库)                                        │
│  └─ testplatform 库                                          │
├─────────────────────────────────────────────────────────────┤
│  redis:7 (消息队列 + 缓存 + Session)                         │
│  └─ db0: Session + Cache + SocketIO                         │
│  └─ db1: Celery Broker                                      │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. 数据模型

### 4.1 层级管理模型 (物理拓扑)

```
Factory (厂区)
  └─ ProductionLine (线体)
       └─ TestStation (工站/装备)
            ├─ EquipmentConfig (装备参数, 1:1)
            ├─ HardwareParam (硬件参数, 1:N)
            ├─ SoftwareConfig (软件参数, 1:1)
            ├─ ScenarioConfig (场景参数, 1:1)
            ├─ Cabinet (机柜, 1:N)
            │    └─ TestChassis (机框, 1:N)
            │         └─ TestSlot (槽位, 1:N)
            └─ EquipmentDefinition (定义模板, N:1)
```

**槽位状态:** `idle` / `testing` / `pass` / `fail` / `disabled`

**装备级指标 (EquipmentMetrics):**
- 每个装备独立一份，发布时从 TestItem 模板实例化
- 存储为 `metrics_json` (JSON 数组)，产线不可见，仅开发人员可修改
- 字段: `[{name, expected_value, min_value, max_value, unit, category, sort_order}]`

**装备级属性页 (EquipmentPropertyPage):**
- 每个装备独立一份，产线可见且可现场修改
- 存储为 `page_json` (JSON 对象)
- 发布时从版本归档的 `property_page` 类型合并写入

**装备字段补充:**
- `TestStation` 新增: `process_type`(工序) / `workstation`(工位) / `actuator`(执行器) / `hardware_code` / `software_code` / `has_settings`
- `EquipmentConfig` 新增: `equipment_ip` / `equipment_service_address` / `process_control_enabled` / `test_mode_{normal,verify,calibration}` / `barcode_verify_enabled`
- `SoftwareConfig` 新增: `sequence_data`(序列快照) / `process_type` / `workstation` / `selected_code`(被测编码) / `bom_code` / `dut_firmware_version` / `dut_hardware_version`

### 4.2 测试模型

```
TestItem (测试项定义)
  └─ name / expected_value / min_value / max_value / unit / category

TestRun (测试批次)
  └─ batch_id (yyyyMMddHHmmss-8hex) / serial_number / operator / task_order
  └─ status (pending / running / completed / failed)
  └─ station_id / slot_id
  └─ TestResult (测试结果, 1:N)
       └─ actual_value / passed / deviation / duration_ms

TestConfig (配置方案)
  └─ name / config_data (JSON) / version / is_active

TestItemTemplate (测试项模板)
  └─ name / service_address / is_critical / timeout_seconds / category
  └─ 不含参数 (expected_value/min/max/unit)，参数随版本归档下发

TestSequence (测试序列)
  └─ name / version / is_active
  └─ TestSequenceStep (序列步骤, 1:N)
       └─ step_order / template_id / timeout_seconds
       └─ template -> TestItemTemplate
```

### 4.3 版本管理模型

```
TestVersion (版本)
  └─ project_name / version / status (draft→released→deployed→delisted)
  └─ type (standard / multi_process / product_family)
  └─ sequence_id / process_type / workstation / codes_config (JSON)
  └─ bom_code / tps_name / domain_tags / inherit_from_id
  ├─ SubScenario (子场景, 1:N, 仅 multi_process)
  │    └─ name / sort_order / process_type / workstation
  │    └─ sequence_id / hardware_params / software_metrics / property_page
  ├─ ReleaseStep (审批步骤, 1:N)
  │    └─ stage (1=发布, 2=发行) / step_order / step_name
  │    └─ assigned_to / status / approved_by / comment
  ├─ VersionArchiveItem (归档项, 1:N)
  │    └─ type (test_item / config / sequence_step / hardware_params / property_page / metrics_json) / item_id / data_snapshot (JSON)
  ├─ VersionBinaryFile (二进制文件, 1:N)
  │    └─ filename / file_path / file_size / description
  └─ ReleaseDeployment (发行目标, 1:N)
       └─ factory/line/station / assigned_to (TE工程师)
       └─ status (pending→approved→deployed)
```

### 4.4 用户模型

```
User
  └─ username (UNIQUE) / display_name / password_hash (pbkdf2:sha256)
  └─ role (operator / process / developer / super_admin) / is_active
  └─ last_login / created_at
```

---

## 5. API 设计

### 5.1 蓝图注册

| 蓝图 | 前缀 | 文件 | 职责 |
|---|---|---|---|---|
| `auth_bp` | (无) | `auth_routes.py` | 登录/登出 + 用户 CRUD |
| `main_bp` | (无) | `main_routes.py` | 页面渲染 (10 页) |
| `test_bp` | `/api/tests` | `test_routes.py` | 测试项/模板/序列 CRUD + 测试执行 |
| `station_bp` | `/api/stations` | `station_routes.py` | 厂区/线体/装备/机柜/机框/槽位 + 四类配置 + 指标/属性页 |
| `log_bp` | `/api/logs` | `log_routes.py` | 日志查询/导出/上传/下载/统计 |
| `init_bp` | `/api/init` | `init_routes.py` | 系统初始化/重置/导入默认配置 |
| `version_bp` | `/api` | `version_routes.py` | 版本归档/发布/发行/二进制/子场景/部署 |
| — | `config_manager.py` | (服务层) | 配置文件解析校验 (CSV/XLSX/JSON/XML) |

### 5.2 关键 API 端点

#### 测试流程
- `POST /api/tests/runs` — 创建测试批次（支持 sequence_id/sequence_name）
- `POST /api/tests/runs/{id}/results` — 提交单条测试结果（支持 is_critical 标记，返回 stop 标记）
- `PUT /api/tests/runs/{run_id}` — 完成/失败批次
- `GET /api/tests/records` — R1/R2/R3 层级记录查询

#### 测试模板与序列
- `GET/POST /api/tests/templates` — 列表/创建测试项模板
- `PUT/DELETE /api/tests/templates/{id}` — 更新/删除模板
- `GET/POST /api/tests/sequences` — 列表/创建测试序列（含步骤）
- `GET /api/tests/sequences/{id}` — 序列详情（含步骤+模板信息）
- `PUT/DELETE /api/tests/sequences/{id}` — 更新/删除序列

#### 用户管理 (auth_routes.py)
- `POST /api/auth/login` — 登录 (记录 last_login)
- `POST /api/auth/logout` — 登出
- `GET /api/auth/me` — 当前用户信息
- `GET/POST /api/auth/users` — 列表/创建用户 (developer+)
- `PUT/DELETE /api/auth/users/{id}` — 更新/删除用户 (developer+)

#### 装备管理
- `GET /api/stations/{id}/detail` — 完整层级树(station→cabinet→chassis→slot)
- `POST /api/stations` — 创建工站(自动按定义模板创建完整层级)
- `GET/PUT /api/stations/{id}/equipment` — 装备参数 CRUD
- `GET/POST /api/stations/{id}/hardware` — 硬件参数列表/添加
- `PUT/DELETE /api/stations/hardware/{id}` — 更新/删除硬件参数
- `PUT /api/stations/{id}/hardware/batch` — 批量替换硬件参数
- `GET/PUT /api/stations/{id}/software` — 软件配置 CRUD
- `GET/PUT /api/stations/{id}/scenario` — 场景参数 CRUD
- `GET/PUT /api/stations/{id}/metrics` — 装备级指标配置
- `GET/PUT /api/stations/{id}/property-page` — 装备级属性页
- `GET /api/stations/{id}/version-check` — 版本对比(已发行 vs 最新)
- `POST /api/stations/{id}/update-version` — 更新到定义最新版本
- `GET /api/stations/{id}/deployed-version` — 当前部署版本信息(含测试项/子场景)
- `GET /api/stations/{id}/deployed-versions` — 所有可用版本列表
- `GET /api/stations/{id}/deployed-archives` — 已发行版本的硬件参数/属性页

#### 版本管理
- `POST /api/versions` — 创建版本(支持 standard/multi_process/product_family)
- `GET /api/versions` — 版本列表(支持 scope=mine 筛选)
- `GET/PUT /api/versions/{id}` — 版本详情/编辑(草稿状态)
- `POST /api/versions/{id}/submit-step` — 审批步骤提交
- `POST /api/versions/{id}/assign-approvers` — 设置审批人
- `POST /api/versions/{id}/deployments` — 创建发行目标
- `POST /api/deployments/{id}/approve` — 审批发行目标
- `POST /api/deployments/{id}/execute` — 执行发行(按目标作用域推送至各工站)
- `POST /api/versions/{id}/delist` — 下架版本 (super_admin)
- `POST /api/versions/{id}/restore` — 恢复已下架版本 (super_admin)
- `DELETE /api/versions/{id}` — 删除草稿/已下架版本 (super_admin)
- `GET /api/pending-approvals` — 当前用户待办列表
- `GET /api/next-version?project=X` — 自动建议下一版本号
- `GET /api/versions/{id}/inherit-data` — 获取继承源版本完整数据
- `GET /api/all-users` — 获取所有活跃用户(用于审批人选择)
- `GET /api/archive-configs` — 获取可归档的测试项列表

#### 版本二进制文件
- `POST /api/versions/{id}/binaries` — 上传二进制文件 (multipart)
- `GET /api/versions/{id}/binaries` — 列出版本二进制文件
- `DELETE /api/versions/{id}/binaries/{file_id}` — 删除二进制文件
- `GET /api/versions/{id}/binaries/{file_id}/download` — 下载二进制文件

#### 版本子场景 (SubScenario)
- `GET /api/versions/{id}/sub-scenarios` — 列出版本的子场景
- `GET/PUT/POST/DELETE /api/sub-scenarios/{id}` — 子场景 CRUD
- `GET /api/versions/{id}/sub-scenarios/{ss_id}/{field}/download` — 下载子场景 JSON 字段文件

#### 归档条目下载
- `GET /api/versions/{id}/archive-items/{item_id}/download` — 下载归档条目 JSON 文件

---

## 6. 前端架构

### 6.1 页面结构

| 路由 | 模板 | 权限 | 功能 |
|---|---|---|---|---|
| `/` | `index.html` | 任意 | 仪表盘 |
| `/lines` | `test_run.html` (lines 视图) | 任意 | 线体列表 |
| `/equipment` | `test_run.html` (equipment 视图) | 任意 | 装备测试(双击槽位扫码测试) |
| `/records` | `test_records.html` | 任意 | R1/R2/R3 测试记录(展开+CSV导出) |
| `/settings` | `config_settings.html` | process | 全局配置 7 标签页：测试项/导入/导出/配置方案/装备定义/厂区线体/测试序列 |
| `/init` | `initialization.html` | developer+ | 系统初始化/重置/导入默认配置 |
| `/releases` | `releases.html` | 任意 | 版本管理 3 标签页：版本列表/创建版本/待审批 |
| `/station-settings/{id}` | `station_settings.html` | process+ | 单站配置 4 标签页：装备参数/硬件参数/软件参数/场景参数 |
| `/logs` | `test_logs.html` | 任意 | 日志查询(搜索/导出/上传/统计) |

### 6.2 模板继承

```
base.html (全局布局：导航栏+厂区选择器+用户菜单)
  ├─ index.html (仪表盘)
  ├─ test_run.html (核心测试界面)
  ├─ test_records.html (测试记录)
  ├─ test_logs.html (日志查询)
  ├─ config_settings.html (全局配置, 7 标签页: 测试项/导入/导出/配置方案/装备定义/厂区线体/测试序列)
  ├─ station_settings.html (单站配置, 4 标签页)
  ├─ releases.html (版本管理, 3 标签页)
  ├─ initialization.html (系统初始化)
  └─ login.html (独立页面, 不继承 base)
```

### 6.3 前端关键设计

- **无前端框架**: 全部使用原生 JavaScript，通过 `fetch`/`apiFetch` 调用 REST API
- **apiFetch 辅助函数**: 统一 HTTP 错误处理 + JSON 解析，避免静默失败
- **Socket.IO 实时推送**: `run_started` / `item_tested` / `run_completed` / `run_failed` 事件驱动日志面板和槽位进度更新
- **厂区选择器**: 通过 `setFactoryLocked/unlocked` 控制显隐，仅在装备视图显示
- **状态持久化**: `sessionStorage` 存储当前版本 ID 和标签页状态，页面刷新后自动恢复

---

## 7. 核心业务流程

### 7.1 装备创建流程

```
1. 创建 EquipmentDefinition (含 layout_config 布局模板)
2. POST /api/stations → 传入 definition_id
3. 系统自动:
   ├─ 创建 EquipmentConfig (默认值)
   ├─ 创建 SoftwareConfig (默认值)
   ├─ 创建 ScenarioConfig (默认值)
   ├─ 按 layout_config 创建 Cabinet → Chassis → Slots
   └─ 创建 HardwareParam 样本
```

### 7.2 测试执行流程

**传统模式（基于 TestItem + selected_test_item_ids）：**

```
1. 用户双击槽位 → 弹出扫码弹窗
2. 用户扫码 (输入序列号)
3. 前端 GET /api/stations/{id}/software → 获取 software_config.selected_test_item_ids
4. POST /api/tests/runs → 创建 TestRun (status=running)
5. Socket.IO 推送 run_started → 日志面板显示
6. 逐个执行已选测试项:
   ├─ POST /api/tests/runs/{id}/results → 提交单条结果
   └─ Socket.IO 推送 item_tested → 日志面板 + 槽位进度条
7. PUT /api/tests/runs/{id} → 标记为 completed/failed
8. Socket.IO 推送 run_completed/run_failed → 日志面板
```

**序列模式（基于 TestSequence + TestItemTemplate）：**

```
1. 用户双击槽位 → 弹出扫码弹窗
2. 用户扫码 (输入序列号)
3. 前端 GET /api/stations/{id}/software → 检查 software_config.sequence_id
4. 若 sequence_id > 0:
   ├─ GET /api/tests/sequences/{id} → 获取序列步骤（含模板信息）
   └─ 步骤列表中包含: template_id, template_is_critical, timeout_seconds
5. POST /api/tests/runs (带 sequence_id/sequence_name) → 创建 TestRun
6. 逐个执行序列步骤:
   ├─ POST /api/tests/runs/{id}/results (带 is_critical) → 提交结果
   ├─ 服务端判定: passed = min <= actual <= max
   ├─ 服务端返回: {stop: is_critical && !passed}
   ├─ 若 stop == true → 前端立即终止后续步骤,状态标记为 failed
   └─ 若 stop == false → 继续下一步（500ms 间隔）
7. 全部完成或被关键项中断 → 更新槽位状态 / 完成批次
```

### 7.3 版本类型

```
standard (标准版):
  ├─ 关联一个测试序列 (sequence_id)
  ├─ 归档: test_item 快照 + sequence_step 快照
  └─ 部署时推送到 EquipmentMetrics + SoftwareConfig

multi_process (多工序版):
  ├─ 不关联单一序列，使用 SubScenario 列表
  ├─ 每个子场景: name / process_type / workstation / sequence_id
  ├─ 每个子场景含: hardware_params / software_metrics / property_page
  └─ 需要 BOM 编码 (bom_code) + TPS 名称 (tps_name)

product_family (产品族版):
  ├─ 类似 multi_process 但不强制工序和工位
  └─ 按 domain_tags 组织

版本继承:
  ├─ inherit_from_id 指向源版本
  ├─ 创建时自动复制: 子场景 / 归档条目 / 二进制文件
  └─ 可作为基版快速衍生新版本
```

### 7.4 版本发布与发行流程

```
阶段 1: 发布 (草稿 → 已发布)
  ├─ 创建 TestVersion (draft, 指定 project_name + version + type)
  ├─ 标准版: 必须指定 sequence_id，自动归档序列步骤快照
  ├─ 多工序版: 必须指定 BOM 编码和至少一个 SubScenario
  ├─ 创建 Stage1 步骤: 测试经理审核 → 项目经理审核
  ├─ 提交步骤审批 (校验 assigned_to == session.display_name)
  └─ 全部通过 → status = released

阶段 2: 发行 (已发布 → 已发行)
  ├─ 创建发行目标 (多厂区/线体/工站, 指定 TE 工程师)
  ├─ 自动创建 Stage2 步骤: TE 工程师审核
  ├─ TE 工程师审批发行目标
  ├─ 执行发行 → 按目标作用域推送并调用 _push_version_to_station():
  │   ├─ station_id → 单站
  │   ├─ line_id → 展开到该线下所有工站
  │   ├─ factory_id → 展开到该厂区下所有工站
  │   └─ 全厂区 → 所有工站
  │
  │   推送内容 (_push_version_to_station):
  │   ├─ 1. TestItem 归档 → EquipmentMetrics (实例化, 每个装备独立)
  │   ├─ 2. metrics_json/metrics_ini → 写入磁盘 + EquipmentMetrics
  │   ├─ 3. SequenceStep 快照 → SoftwareConfig.sequence_data
  │   ├─ 4. HardwareParams 归档 → 写入装备目录
  │   ├─ 5. PropertyPage 归档 → EquipmentPropertyPage (合并写入)
  │   └─ 6. BinaryFile → 复制到装备 binaries 目录
  │
  └─ 全部部署完成 → status = deployed

下架与恢复:
  ├─ 仅 super_admin 可下架 (delist) 已发布/已发行版本
  └─ 已下架版本可恢复 (restore) 为草稿状态
```

### 7.5 审批流转

```
当前用户 → GET /api/pending-approvals → 返回待办列表
  ├─ type=step: ReleaseStep (stage1 审批)
  └─ type=deployment: ReleaseDeployment (stage2 审批)

提交审批:
  └─ POST /api/versions/{id}/submit-step (step 审批)
  └─ POST /api/deployments/{id}/approve (deployment 审批)

校验:
  └─ step.assigned_to == session.display_name (403 不匹配)
  └─ dep.assigned_to == session.display_name (403 不匹配)
```

---

## 8. 权限模型

| 角色 | 值 | 层级 | 说明 | 权限 |
|---|---|---|---|---|---|
| **操作人员** | `operator` | 0 | 生产线操作员 | 测试执行、记录查询、日志查看 |
| **工艺人员** | `process` | 1 | 工艺工程师 | operator + 装备/配置管理 |
| **装备开发人员** | `developer` | 2 | 开发工程师 | process + 版本归档/发布/用户管理 |
| **超级管理员** | `super_admin` | 3 | 系统管理员 | 全部权限(含下架版本/删除版本) |

权限控制方式:
- 路由层: `@login_required` / `@role_required(min_role)` 装饰器
  - 快捷装饰器: `@process_required` / `@developer_required` / `@super_admin_required`
- 页面层: 导航栏元素通过 `if session.role` 判断显隐
- 审批层: 校验 `assigned_to == session.display_name`

---

## 9. 关键设计决策

| 决策 | 选择 | 理由 |
|---|---|---|
| **前端框架** | 无 (原生 JS) | 依赖少，直接操作 DOM，适合工业场景 |
| **数据库** | SQLite (可配置) | 单机部署场景，无需独立数据库服务 |
| **Cabinet 模型** | 置于 Station 与 Chassis 之间 | 支持多机柜机框的物理层级映射 |
| **测试模式** | 扫码即测，无批处理 | 单槽位扫码立即测试，简化操作流程 |
| **进度反馈** | 槽位填充条 + 状态文字 | 不改变槽位外层 class，保持布局稳定 |
| **日志面板** | 固定底部，仅用户手动拖拽 | 程序不自动调整高度，避免干扰用户操作 |
| **版本唯一性** | (project_name, version) 组合唯一 | 允许不同工程使用相同版本号 |
| **版本号自动递增** | 应用层实现 | 同一工程下新建版本自动继承上一版本号并加 1 |
| **发行作用域** | 按层级展开 | station → line → factory → 全厂区，逐级覆盖 |
| **测试项过滤** | 依据 SoftwareConfig.selected_test_item_ids | 每个工站可独立选择要执行的测试项 |
| **测试项模板** | 模板不含参数，仅含元数据 | 参数随版本归档下发，不同版本可用不同阈值 |
| **关键标记** | 关键项失败时服务端返回 stop=true | 前端根据 stop 标记停止递归，响应快 |
| **超时默认值** | 模板 timeout_seconds + 步骤可覆盖 | 同名项在不同序列中可能有不同超时要求 |
| **旧 TestItem 保留** | TestItemTemplate 与之并存 | 避免破坏已有 TestResult 关联关系 |
| **四级角色** | operator < process < developer < super_admin | 满足产线不同角色权限粒度需求 |
| **版本类型** | standard / multi_process / product_family | multi_process 通过 SubScenario 列表管理多个工序 |
| **版本继承** | inherit_from_id + 复制策略 | 以现有版本为基版快速衍生新版本, 减少重复配置 |
| **二进制文件** | VersionBinaryFile + 文件系统 | 固件/驱动等大文件独立于数据库存储, 部署时推送到目标装备 |
| **指标配置** | EquipmentMetrics (per-equipment) | 每个装备独立实例化, 互不影响, 可现场调整 |
| **属性页** | EquipmentPropertyPage (per-equipment) | 产线可见可修改, 发布时从版本归档合并写入 |
| **硬件参数批量替换** | PUT batch 全量替换 | 简化部署时的参数同步, 避免逐条 CRUD |
| **部署推送** | _push_version_to_station 集中函数 | 统一管理部署时写入指标/参数/文件到目标装备 |
| **配置导入格式** | ConfigManager 统一解析 | CSV/XLSX/JSON/XML 四格式支持, 可扩展 |
| **日志压缩** | 30天前的 .json → .gz | 自动压缩节省磁盘, 不丢失历史数据 |
| **审批人分配** | 通过 settings 页面选择 | 代替直接输入用户名, 降低输入错误 |
| **工站工序/工位** | process_type + workstation 字段 | 支持按工序筛选装备和版本, 灵活匹配 |

---

## 10. 数据库迁移策略

由于使用 SQLite，不支持 `ALTER TABLE DROP CONSTRAINT`，采用表重建策略:

1. `ALTER TABLE ADD COLUMN` — 新增列（忽略已存在异常）
2. 检查 `sqlite_master.sql` 中是否包含 `UNIQUE` → 若存在则重建表:
   - `PRAGMA foreign_keys=off`
   - `CREATE TABLE xxx_new ...`
   - `INSERT INTO xxx_new SELECT * FROM xxx`
   - `DROP TABLE xxx`
   - `ALTER TABLE xxx_new RENAME TO xxx`
   - `PRAGMA foreign_keys=on`

当前已执行的迁移:
- `software_configs` 表添加 `project_name` / `sequence_id` / `sequence_data` / `process_type` / `workstation` / `selected_code` / `bom_code` 列
- `test_versions` 表添加 `project_name` / `sequence_id` / `process_type` / `workstation` / `codes_config` / `type` / `bom_code` / `tps_name` / `domain_tags` / `inherit_from_id` 列
- `test_versions` 表移除 `version` 列的 UNIQUE 约束
- `test_runs` 表添加 `sequence_id` / `sequence_name` 列
- 新建 `test_item_templates` / `test_sequences` / `test_sequence_steps` 三张表
- 新建 `sub_scenarios` 表 (版本子场景)
- 新建 `equipment_metrics` 表 (装备级指标)
- 新建 `equipment_property_pages` 表 (装备级属性页)
- 新建 `cabinets` 表 (机柜, 位于 Station 与 Chassis 之间)
- 新建 `version_binary_files` 表 (版本二进制文件)

---

## 11. 种子数据

首次启动(`Factory.query.count() == 0`)时自动创建:

**用户 (4 类角色):**
- `admin` / `admin123` — 超级管理员 (super_admin)
- `developer` / `123456` — 装备开发人员 (developer)
- `process` / `123456` — 工艺人员 (process)
- `operator` / `123456` — 操作人员 (operator)

**厂区/线体/装备:**
- SMT 一厂 → SMT 线体 01/02 → SPI 检测装备、贴片机测试站
- 组装厂 → 组装线 01 → 功能测试站

**装备定义:**
- SPI 检测装备 (v2.1.0): 1 机柜 × 2 机框 × 4+4 槽位
- 贴片机测试站 (v1.5.0): 1 机柜 × 3 机框 × 4+4+2 槽位
- 功能测试站 (v3.0.0): 1 机柜 × 1 机框 × 8 槽位

**测试项模板与序列:**
- 6 个测试项模板：电压测试(关键)、电流测试、频率测试、温度测量(关键)、绝缘测试(关键)、噪声测试
- 1 个测试序列：FCT 标准测试序列，按顺序包含全部 6 个模板步骤

**装备硬件参数样本 (每个装备):**
- 测试仪 IP/端口、万用表 IP/型号、电源 IP/通道数、GPIB 地址、串口波特率等 8 项

---

## 12. 实时通信 (Socket.IO)

| 事件 | 方向 | 触发时机 | 负载 |
|---|---|---|---|
| `run_started` | 服务端→客户端 | 测试批次开始 | `{batch_id, operator, serial_number}` |
| `item_tested` | 服务端→客户端 | 单条测试完成 | `{item_name, passed, actual_value, slot_id}` |
| `run_completed` | 服务端→客户端 | 全部测试通过 | `{batch_id, total, passed, failed}` |
| `run_failed` | 服务端→客户端 | 测试过程出错 | `{batch_id, error}` |

客户端处理: 日志面板追加条目 + 槽位进度条更新（不重置整个视图）。

---

## 13. 开发与部署

**开发启动 (SQLite + Flask dev server):**
```bash
cd test_platform
python3 run.py
# 访问 http://localhost:5000
```

**生产部署 (Docker Compose):**
```bash
cd test_platform
cp .env.example .env   # 修改 SECRET_KEY 等敏感配置
docker compose up -d
# 访问 http://localhost:80
```

**手动启动 Gunicorn (生产):**
```bash
# 确保 PostgreSQL 和 Redis 已运行
export DATABASE_URI=postgresql://user:pass@localhost:5432/testplatform
export REDIS_URL=redis://localhost:6379/0
gunicorn -c gunicorn.conf.py run:app
```

**启动 Celery Worker + Beat:**
```bash
celery -A app.services.celery_app worker -l info -c 4
celery -A app.services.celery_app beat -l info
```

**重置数据库:**
```bash
# SQLite:
rm -f database/test_platform.db
# PostgreSQL:
docker compose down -v   # 删除 volume 重建
```

**配置项:**
| 环境变量 | 配置项 | 默认值 |
|---|---|---|
| `SECRET_KEY` | 签名密钥 | `test-platform-secret-key` |
| `DATABASE_URI` | 数据库连接 | `postgresql://testplatform:testplatform@localhost:5432/testplatform` |
| `REDIS_URL` | Redis 连接 | `redis://localhost:6379/0` |
| `DB_POOL_SIZE` | 连接池大小 | `20` |
| `DB_MAX_OVERFLOW` | 连接池溢出上限 | `40` |
| `UPLOAD_FOLDER` | 上传目录 | `./uploads` |
| `LOG_FOLDER` | 日志目录 | `./logs` |
