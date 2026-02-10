"""Program list API endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.repositories.program_repository import ProgramRepository
from app.schemas.program import ProgramListResponse

router = APIRouter()


@router.get(
    "/programs",
    response_model=ProgramListResponse,
    summary="获取剧目列表",
    description="返回按上线时间倒序排序的剧目列表，支持分页与关键字搜索。",
)
async def list_programs(
    page: int = Query(1, ge=1, description="页码，从 1 开始"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    keyword: str | None = Query(None, description="按剧名或 Program Code 模糊搜索"),
    db: AsyncSession = Depends(get_db_session),
) -> ProgramListResponse:
    repository = ProgramRepository(db)
    result = await repository.list_programs(page=page, page_size=page_size, keyword=keyword)
    return result


