from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings


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

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


@lru_cache()
def get_settings() -> Settings:
    return Settings()
