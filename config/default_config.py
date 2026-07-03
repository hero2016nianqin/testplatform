"""
应用默认配置模块

定义 Flask 应用的各项默认配置参数，包括数据库连接、文件上传路径、
调度器设置等。所有配置可通过环境变量覆盖，方便不同部署环境切换。
"""

import os


class DefaultConfig:
    # Flask 密钥，用于 session 加密和 CSRF 保护
    SECRET_KEY = os.environ.get('SECRET_KEY', 'test-platform-secret-key')

    # SQLAlchemy 数据库连接 URI，默认使用项目目录下的 SQLite 文件
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URI',
        'sqlite:///' + os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                     'database', 'test_platform.db')
    )
    # 禁用 SQLAlchemy 事件系统以提升性能
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # 上传文件存储路径
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                 'uploads')
    # 日志文件存储路径
    LOG_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                              'logs')

    # 启用 APScheduler API 端点
    SCHEDULER_API_ENABLED = True
    # 调度器默认时区
    SCHEDULER_TIMEZONE = 'Asia/Shanghai'

    # 最大上传文件大小（16MB）
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024

    # 允许导入的配置文件扩展名
    ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'json', 'xml', 'yaml', 'yml'}
