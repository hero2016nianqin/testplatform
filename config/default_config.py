"""
应用默认配置模块

定义 Flask 应用的各项默认配置参数，包括数据库连接、Redis、
文件上传路径、调度器设置等。所有配置可通过环境变量覆盖。

策略:
  开发环境 — 默认使用 SQLite + 文件 Session + 简单缓存 (零外部依赖)
  生产环境 — 通过 DATABASE_URI/REDIS_URL 环境变量一键切换
"""

import os

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class DefaultConfig:
    # Flask 密钥
    SECRET_KEY = os.environ.get('SECRET_KEY', 'test-platform-secret-key')

    # ── 数据库 ──────────────────────────────────────────────────────
    # 默认 SQLite (开发零依赖); 生产通过 DATABASE_URI 切换到 PostgreSQL
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URI',
        'sqlite:///' + os.path.join(_BASE, 'database', 'test_platform.db')
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # 连接池（仅 PostgreSQL 时生效，SQLite 会忽略）
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': int(os.environ.get('DB_POOL_SIZE', '20')),
        'max_overflow': int(os.environ.get('DB_MAX_OVERFLOW', '40')),
        'pool_pre_ping': True,
        'pool_recycle': 300,
    } if 'postgresql' in os.environ.get('DATABASE_URI', '') else {}

    # ── Redis ────────────────────────────────────────────────────────
    REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.environ.get('REDIS_PORT', '6379'))
    REDIS_DB = int(os.environ.get('REDIS_DB', '0'))
    REDIS_PASSWORD = os.environ.get('REDIS_PASSWORD', '')
    _redis_url = os.environ.get(
        'REDIS_URL',
        f'redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}'
            if REDIS_PASSWORD else
        f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}'
    )
    REDIS_URL = _redis_url

    # ── Session (有 Redis 用 Redis，否则用 filesystem) ──────────────
    SESSION_TYPE = os.environ.get('SESSION_TYPE',
                                  'redis' if os.environ.get('REDIS_URL') else 'filesystem')
    SESSION_PERMANENT = True
    SESSION_USE_SIGNER = True
    SESSION_KEY_PREFIX = 'session:'
    SESSION_REDIS = None  # 由 create_app 注入

    # ── Cache (有 Redis 用 Redis，否则用内存) ────────────────────────
    CACHE_TYPE = os.environ.get('CACHE_TYPE',
                                'RedisCache' if os.environ.get('REDIS_URL') else 'SimpleCache')
    CACHE_REDIS_URL = REDIS_URL
    CACHE_DEFAULT_TIMEOUT = 60
    CACHE_KEY_PREFIX = 'cache:'

    # ── SocketIO (有 Redis 用消息队列，否则内存模式) ─────────────────
    SOCKETIO_MESSAGE_QUEUE = REDIS_URL if os.environ.get('REDIS_URL') else None

    # ── Celery (依赖 Redis) ─────────────────────────────────────────
    CELERY_BROKER_URL = REDIS_URL if os.environ.get('REDIS_URL') else None
    CELERY_RESULT_BACKEND = REDIS_URL if os.environ.get('REDIS_URL') else None

    # ── 文件路径 ─────────────────────────────────────────────────────
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', os.path.join(_BASE, 'uploads'))
    LOG_FOLDER = os.environ.get('LOG_FOLDER', os.path.join(_BASE, 'logs'))

    # ── 调度器 ──────────────────────────────────────────────────────
    SCHEDULER_API_ENABLED = True
    SCHEDULER_TIMEZONE = 'Asia/Shanghai'

    # ── 其他 ─────────────────────────────────────────────────────────
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'json', 'xml', 'yaml', 'yml'}
