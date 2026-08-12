from datetime import datetime, timedelta
from typing import Optional


def parse_datetime(value, end_of_day: bool = False) -> Optional[datetime]:
    """将日期字符串解析为 datetime 对象（PostgreSQL timestamp 需要 datetime 类型参数）。

    支持格式：'YYYY-MM-DD'、'YYYY-MM-DD HH:MM:SS'、ISO 格式（含 'T' 与微秒）。
    end_of_day=True 时归一到当天 23:59:59.999999（用于 `<=` 区间闭区间）。
    解析失败返回 None。
    """
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    dt: Optional[datetime] = None
    for fmt in (
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
    ):
        try:
            dt = datetime.strptime(s, fmt)
            break
        except ValueError:
            continue
    if dt is None:
        try:
            dt = datetime.fromisoformat(s)
        except ValueError:
            try:
                dt = datetime.strptime(s, "%Y-%m-%d")
            except ValueError:
                return None
    if dt.tzinfo is not None:
        dt = dt.replace(tzinfo=None)
    if end_of_day:
        dt = dt.replace(hour=23, minute=59, second=59, microsecond=999999)
    return dt
