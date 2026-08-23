import os
from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import dotenv_values


class Settings(BaseSettings):
    # App
    APP_ENV: str = "dev"
    DEBUG: bool = True
    SECRET_KEY: str = "dev-secret-key-change-in-prod"
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///../database/test_platform.db"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_ECHO: bool = False

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_MAX_CONNECTIONS: int = 50
    REDIS_SESSION_DB: int = 0
    REDIS_CACHE_DB: int = 0
    REDIS_PUBSUB_DB: int = 0

    # MinIO
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "testplatform"
    MINIO_SECRET_KEY: str = "testplatform123"
    MINIO_BUCKET: str = "testplatform"
    MINIO_SECURE: bool = False

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"
    CELERY_WORKER_CONCURRENCY: int = 8

    # XXL-Job
    XXL_JOB_ADMIN_URL: str = "http://localhost:8080/xxl-job-admin"
    XXL_JOB_APPNAME: str = "test-platform"
    XXL_JOB_PORT: int = 9999

    # File
    UPLOAD_FOLDER: str = "uploads"
    LOG_FOLDER: str = "logs"

    # Log
    LOG_LEVEL: str = "DEBUG"
    LOG_FILE: str = "logs/app.log"

    # Session
    SESSION_TTL_SECONDS: int = 86400  # 24h

    model_config = SettingsConfigDict(env_file_encoding="utf-8", extra="ignore")


def _resolve_env_file(app_env: str):  # -> Optional[str]
    """按环境解析配置文件：
    - 优先使用 .env.{APP_ENV}（如 .env.prod / .env.dev）
    - prod 环境且无 .env.prod 时，兼容回退到 .env
    - dev 环境无 .env.dev 时返回 None（使用默认 SQLite 等内置默认值）
    """
    env_file = f".env.{app_env}"
    if os.path.exists(env_file):
        return env_file
    if app_env == "prod" and os.path.exists(".env"):
        return ".env"
    return None


@lru_cache()
def get_settings() -> Settings:
    # APP_ENV 优先级：进程环境变量 > .env 文件 > 默认 dev
    app_env = os.environ.get("APP_ENV")
    if not app_env:
        vals = dotenv_values(".env")
        app_env = (vals or {}).get("APP_ENV", "dev")
    env_file = _resolve_env_file(app_env)
    if env_file:
        return Settings(_env_file=env_file)
    return Settings()
