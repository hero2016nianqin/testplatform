"""
Flask 应用工厂模块

负责创建和配置 Flask 应用实例，按顺序完成以下初始化：
1. 加载配置项
2. 初始化数据库（SQLAlchemy）
3. 初始化 SocketIO（实时通信）
4. 初始化 CORS（跨域支持）
5. 创建数据库表
6. 创建默认用户账号
7. 注册所有路由蓝图
8. 启动后台调度器
9. 创建必要的文件目录
"""

import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO
from flask_cors import CORS
from sqlalchemy import text

# 全局扩展实例，供 models 和 services 模块引用
db = SQLAlchemy()
socketio = SocketIO()
cors = CORS()

def create_app(config_object=None):
    """
    应用工厂函数，创建并配置 Flask 应用实例。

    Args:
        config_object: 可选的配置对象，默认为 DefaultConfig

    Returns:
        配置好的 Flask 应用实例
    """
    app = Flask(__name__)

    # 加载配置：使用默认配置或传入的自定义配置
    if config_object is None:
        from config.default_config import DefaultConfig
        app.config.from_object(DefaultConfig)
    else:
        app.config.from_object(config_object)

    # 设置 session 过期时间为 24 小时
    app.config['PERMANENT_SESSION_LIFETIME'] = 86400

    # 初始化各扩展组件
    db.init_app(app)
    socketio.init_app(app, cors_allowed_origins='*')
    cors.init_app(app)

    # 导入数据模型（确保它们在 SQLAlchemy 中注册），然后自动建表
    from app.models import (
        TestItem, TestResult, TestRun, User,
        TestItemTemplate, TestSequence, TestSequenceStep,
    )
    from app.models.station import (
        Factory, ProductionLine,
        TestStation, TestChassis, TestSlot,
        EquipmentConfig, HardwareParam, SoftwareConfig, ScenarioConfig,
        EquipmentMetrics, EquipmentPropertyPage,
    )
    from app.models.version import (
        TestVersion, ReleaseStep, VersionArchiveItem, ReleaseDeployment,
        VersionBinaryFile, SubScenario,
    )
    with app.app_context():
        db.create_all()

        # 批量迁移：一次查询表结构，只对缺少的列执行 ALTER TABLE
        def _migrate_table(table, columns):
            """检查表是否存在指定列，缺少则添加"""
            try:
                existing = {row[1] for row in db.session.execute(text(f'PRAGMA table_info({table})')).fetchall()}
                for col_def in columns:
                    col_name = col_def.split()[0]
                    if col_name not in existing:
                        db.session.execute(text(f'ALTER TABLE {table} ADD COLUMN {col_def}'))
            except Exception:
                pass

        _migrate_table('test_versions', [
            'project_name VARCHAR(200) DEFAULT ""',
            'sequence_id INTEGER DEFAULT 0',
            'process_type VARCHAR(200) DEFAULT ""',
            'workstation VARCHAR(200) DEFAULT ""',
            'codes_config TEXT DEFAULT "[]"',
            'type VARCHAR(30) DEFAULT "standard"',
            'bom_code VARCHAR(200) DEFAULT ""',
            'tps_name VARCHAR(200) DEFAULT ""',
            'domain_tags VARCHAR(500) DEFAULT ""',
            'inherit_from_id INTEGER DEFAULT NULL',
        ])
        _migrate_table('software_configs', [
            'project_name VARCHAR(200) DEFAULT ""',
            'sequence_id INTEGER DEFAULT 0',
            'sequence_data TEXT DEFAULT ""',
            'process_type VARCHAR(50) DEFAULT ""',
            'workstation VARCHAR(50) DEFAULT ""',
            'selected_code VARCHAR(100) DEFAULT ""',
            'bom_code VARCHAR(200) DEFAULT ""',
        ])
        _migrate_table('test_runs', [
            'sequence_id INTEGER DEFAULT 0',
            'sequence_name VARCHAR(200) DEFAULT ""',
        ])
        try:
            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS sub_scenarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    version_id INTEGER NOT NULL REFERENCES test_versions(id),
                    name VARCHAR(200) NOT NULL,
                    description TEXT DEFAULT '',
                    sort_order INTEGER DEFAULT 0,
                    process_type VARCHAR(100) DEFAULT '',
                    workstation VARCHAR(100) DEFAULT '',
                    sequence_id INTEGER DEFAULT 0,
                    hardware_params TEXT DEFAULT '{}',
                    software_metrics TEXT DEFAULT '[]',
                    property_page TEXT DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
        except Exception:
            pass

        db.session.commit()
        # 自动填充示例数据，但跳过 seed_sample_stations()，以避免设备配置方面的冲突
        # 仅填充最基本的示例数据
        try:
            from app.routes.auth_routes import seed_default_users
            seed_default_users()
            print("Create default admin user")
        except Exception as e:
            print(f"Failed to create default user: {e}")
        
        print("Initialization completed - no sample equipment created to avoid conflicts")

    # 注册各功能模块的路由蓝图，每个蓝图有独立的 URL 前缀
    from app.routes.auth_routes import auth_bp
    from app.routes.station_routes import station_bp
    from app.routes.test_routes import test_bp
    from app.routes.log_routes import log_bp
    from app.routes.init_routes import init_bp
    from app.routes.version_routes import version_bp

    # 认证相关路由（登录页 + API）
    app.register_blueprint(auth_bp)
    # 工站相关 API
    app.register_blueprint(station_bp, url_prefix='/api/stations')
    # API 路由组
    app.register_blueprint(test_bp, url_prefix='/api/tests')
    app.register_blueprint(log_bp, url_prefix='/api/logs')
    app.register_blueprint(init_bp, url_prefix='/api/init')
    app.register_blueprint(version_bp, url_prefix='/api')

    # 前端页面路由（渲染 HTML 模板）
    from app.routes.main_routes import main_bp
    app.register_blueprint(main_bp)

    # 初始化后台调度器（定时清理过期批次等）
    from app.services.scheduler import init_scheduler
    init_scheduler(app)

    # 确保上传和日志目录存在
    os.makedirs(app.config.get('UPLOAD_FOLDER', 'uploads'), exist_ok=True)
    os.makedirs(app.config.get('LOG_FOLDER', 'logs'), exist_ok=True)

    return app
