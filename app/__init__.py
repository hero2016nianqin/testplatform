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
    from app.models import TestItem, TestResult, TestConfig, TestRun, User
    from app.models.station import (
        TestStation, TestChassis, TestSlot,
        EquipmentConfig, HardwareParam, SoftwareConfig, ScenarioConfig,
    )
    with app.app_context():
        db.create_all()
        # 如果没有用户数据，创建默认账号
        from app.routes.auth_routes import seed_default_users
        seed_default_users()
        # 如果没有工站数据，创建默认示例工站
        from app.routes.station_routes import seed_sample_stations
        seed_sample_stations()

    # 注册各功能模块的路由蓝图，每个蓝图有独立的 URL 前缀
    from app.routes.auth_routes import auth_bp
    from app.routes.station_routes import station_bp
    from app.routes.test_routes import test_bp
    from app.routes.config_routes import config_bp
    from app.routes.log_routes import log_bp
    from app.routes.init_routes import init_bp

    # 认证相关路由（登录页 + API）
    app.register_blueprint(auth_bp)
    # 工站相关 API
    app.register_blueprint(station_bp, url_prefix='/api/stations')
    # API 路由组
    app.register_blueprint(test_bp, url_prefix='/api/tests')
    app.register_blueprint(config_bp, url_prefix='/api/configs')
    app.register_blueprint(log_bp, url_prefix='/api/logs')
    app.register_blueprint(init_bp, url_prefix='/api/init')

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
