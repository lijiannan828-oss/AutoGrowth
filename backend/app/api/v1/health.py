"""Health check endpoints."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health", summary="API health status")
async def health_status() -> dict[str, str]:
    return {"status": "ok"}
