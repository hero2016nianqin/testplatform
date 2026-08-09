from sqlalchemy import JSON as _JSON
from sqlalchemy.dialects.postgresql import JSONB as _JSONB
from app.config.settings import get_settings

# 运行时检测：PostgreSQL → JSONB, SQLite等 → JSON
_settings = get_settings()
if _settings.DATABASE_URL.startswith("postgresql"):
    JSONField = _JSONB
else:
    JSONField = _JSON
