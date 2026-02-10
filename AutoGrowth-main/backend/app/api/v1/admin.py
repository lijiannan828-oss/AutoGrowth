"""Admin API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.services.program_sync_service import ProgramSyncService

router = APIRouter()


@router.post(
    "/sync/programs",
    summary="手动触发 Program Info 同步",
    description="从 Google Sheets 同步 Program Info 数据到数据库",
    status_code=status.HTTP_200_OK,
)
async def sync_programs(
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Manually trigger Program Info synchronization from Google Sheets.
    
    Returns:
        dict: Synchronization result with statistics
    """
    try:
        sync_service = ProgramSyncService()
        result = await sync_service.sync_from_sheets(db)
        
        return {
            "success": True,
            "result": {
                "created": result.created,
                "updated": result.updated,
                "total": result.total,
                "errors": result.errors,
            },
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sync failed: {str(e)}",
        )

