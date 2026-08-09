import math
from typing import Tuple, Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


async def paginate(
    session: AsyncSession,
    stmt,
    page: Optional[int] = 1,
    page_size: Optional[int] = 20,
    max_page_size: int = 200,
) -> Tuple[list, int, int, int]:
    if page_size is None or page_size < 1:
        page_size = 20
    if page_size > max_page_size:
        page_size = max_page_size
    if page is None or page < 1:
        page = 1

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await session.execute(count_stmt)
    total = total_result.scalar() or 0

    total_pages = max(1, math.ceil(total / page_size))
    offset = (page - 1) * page_size
    result = await session.execute(stmt.offset(offset).limit(page_size))
    items = list(result.scalars().all())

    return items, total, page, page_size
