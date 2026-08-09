"""
Flask 应用工厂模块

负责创建和配置 Flask 应用实例，按顺序完成以下初始化：
1. 加载配置项
2. 初始化数据库（SQLAlchemy + 连接池）
3. 初始化 Session（Redis 或文件系统）
4. 初始化 Cache（Redis 或内存）
5. 初始化 SocketIO（Redis 消息队列或内存）
6. 初始化 CORS
7. 创建数据库表 + 迁移
8. 创建默认用户账号（种子数据）
9. 注册所有路由蓝图
10. 启动后台调度器（Celery Beat 或空）
11. 创建必要的文件目录
"""

import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO
from flask_cors import CORS
from flask_session import Session as FlaskSession
from flask_caching import Cache
from sqlalchemy import text

# 全局扩展实例，供 models 和 services 模块引用
db = SQLAlchemy()
socketio = SocketIO()
cors = CORS()
flask_session = FlaskSession()
cache = Cache()


def _is_sqlite(app):
    """判断当前是否使用 SQLite 数据库"""
    uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
    return uri.startswith('sqlite')


def _has_redis(app):
    """判断 Redis 是否可用"""
    return bool(app.config.get('REDIS_URL'))


def create_app(config_object=None):
    """
    应用工厂函数，创建并配置 Flask 应用实例。
    """
    app = Flask(__name__)

    # ── 加载配置 ────────────────────────────────────────────────────
    if config_object is None:
        from config.default_config import DefaultConfig
        app.config.from_object(DefaultConfig)
    else:
        app.config.from_object(config_object)

    app.config['PERMANENT_SESSION_LIFETIME'] = 86400  # 24h

    # ── 初始化各扩展组件 ─────────────────────────────────────────────
    db.init_app(app)

    # SocketIO — 有 Redis 时启用消息队列（跨 worker 广播）
    msg_queue = app.config.get('SOCKETIO_MESSAGE_QUEUE')
    if msg_queue:
        socketio.init_app(app, cors_allowed_origins='*',
                          message_queue=msg_queue)
    else:
        socketio.init_app(app, cors_allowed_origins='*')

    cors.init_app(app)

    # Session — 有 Redis 时用 Redis，否则 filesystem
    if _has_redis(app) and app.config.get('SESSION_TYPE') == 'redis':
        from redis import Redis
        app.config['SESSION_REDIS'] = Redis.from_url(
            app.config['REDIS_URL'],
            socket_keepalive=True,
            retry_on_timeout=True,
        )
    flask_session.init_app(app)

    # Cache — 有 Redis 时用 RedisCache，否则 SimpleCache
    if _has_redis(app) and 'RedisCache' in str(app.config.get('CACHE_TYPE', '')):
        cache.init_app(app, config={
            'CACHE_TYPE': 'RedisCache',
            'CACHE_REDIS_URL': app.config['REDIS_URL'],
            'CACHE_DEFAULT_TIMEOUT': app.config.get('CACHE_DEFAULT_TIMEOUT', 60),
        })
    else:
        cache.init_app(app, config={
            'CACHE_TYPE': 'SimpleCache',
            'CACHE_DEFAULT_TIMEOUT': app.config.get('CACHE_DEFAULT_TIMEOUT', 60),
        })

    # ── 数据模型注册 + 建表 + 迁移 + 种子数据 ────────────────────────
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

        # ── 字段迁移 ──────────────────────────────────────────────
        def _ensure_columns(table, columns):
            """检查表是否存在指定列，缺少则添加"""
            inspector = db.inspect(db.engine)
            existing = {c['name'] for c in inspector.get_columns(table)}
            for col_def in columns:
                col_name = col_def.split()[0]
                if col_name not in existing:
                    try:
                        db.session.execute(
                            text(f'ALTER TABLE {table} ADD COLUMN {col_def}')
                        )
                        db.session.commit()
                    except Exception:
                        db.session.rollback()

        _ensure_columns('test_versions', [
            'project_name VARCHAR(200) DEFAULT \'\'',
            'sequence_id INTEGER DEFAULT 0',
            'process_type VARCHAR(200) DEFAULT \'\'',
            'workstation VARCHAR(200) DEFAULT \'\'',
            'codes_config TEXT DEFAULT \'[]\'',
            'type VARCHAR(30) DEFAULT \'standard\'',
            'bom_code VARCHAR(200) DEFAULT \'\'',
            'tps_name VARCHAR(200) DEFAULT \'\'',
            'domain_tags VARCHAR(500) DEFAULT \'\'',
            'inherit_from_id INTEGER DEFAULT NULL',
        ])
        _ensure_columns('software_configs', [
            'project_name VARCHAR(200) DEFAULT \'\'',
            'sequence_id INTEGER DEFAULT 0',
            'sequence_data TEXT DEFAULT \'\'',
            'process_type VARCHAR(50) DEFAULT \'\'',
            'workstation VARCHAR(50) DEFAULT \'\'',
            'selected_code VARCHAR(100) DEFAULT \'\'',
            'bom_code VARCHAR(200) DEFAULT \'\'',
        ])
        _ensure_columns('test_runs', [
            'sequence_id INTEGER DEFAULT 0',
            'sequence_name VARCHAR(200) DEFAULT \'\'',
        ])

        # 子场景表安全兜底
        try:
            pk_type = 'INTEGER' if _is_sqlite(app) else 'SERIAL'
            sql = (
                'CREATE TABLE IF NOT EXISTS sub_scenarios ('
                f' id {pk_type} PRIMARY KEY,'
                ' version_id INTEGER NOT NULL REFERENCES test_versions(id),'
                ' name VARCHAR(200) NOT NULL,'
                ' description TEXT DEFAULT \'\','
                ' sort_order INTEGER DEFAULT 0,'
                ' process_type VARCHAR(100) DEFAULT \'\','
                ' workstation VARCHAR(100) DEFAULT \'\','
                ' sequence_id INTEGER DEFAULT 0,'
                ' hardware_params TEXT DEFAULT \'{}\','
                ' software_metrics TEXT DEFAULT \'[]\','
                ' property_page TEXT DEFAULT \'{}\','
                ' created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
                ' )'
            )
            db.session.execute(text(sql))
            db.session.commit()
        except Exception:
            db.session.rollback()

        # ── 种子数据 ─────────────────────────────────────────────
        try:
            from app.routes.auth_routes import seed_default_users
            seed_default_users()
            print("Default users created")
        except Exception as e:
            print(f"Failed to create default user: {e}")

        print("Initialization completed")

    # ── 注册蓝图 ──────────────────────────────────────────────────
    from app.routes.auth_routes import auth_bp
    from app.routes.station_routes import station_bp
    from app.routes.test_routes import test_bp
    from app.routes.log_routes import log_bp
    from app.routes.init_routes import init_bp
    from app.routes.version_routes import version_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(station_bp, url_prefix='/api/stations')
    app.register_blueprint(test_bp, url_prefix='/api/tests')
    app.register_blueprint(log_bp, url_prefix='/api/logs')
    app.register_blueprint(init_bp, url_prefix='/api/init')
    app.register_blueprint(version_bp, url_prefix='/api')

    from app.routes.main_routes import main_bp
    app.register_blueprint(main_bp)

    # ── 启动后台调度器 ─────────────────────────────────────────────
    if _has_redis(app):
        from app.services.scheduler import init_scheduler
        init_scheduler(app)
    else:
        print("Redis not available, Celery scheduler skipped.")

    # ── 创建目录 ──────────────────────────────────────────────────
    os.makedirs(app.config.get('UPLOAD_FOLDER', 'uploads'), exist_ok=True)
    os.makedirs(app.config.get('LOG_FOLDER', 'logs'), exist_ok=True)

    return app
