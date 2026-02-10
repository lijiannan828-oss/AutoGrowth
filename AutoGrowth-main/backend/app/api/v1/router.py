"""API router registration."""

from fastapi import APIRouter

from . import admin, ai_video, fission, generate, health, oauth, pipeline, programs, relay, subtitle, tts


api_router = APIRouter()

api_router.include_router(health.router, tags=["health"])
api_router.include_router(programs.router, prefix="/data", tags=["programs"])
api_router.include_router(generate.router, prefix="/generate", tags=["generation"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(oauth.router, prefix="/oauth", tags=["oauth"])
api_router.include_router(pipeline.router, prefix="/pipeline", tags=["pipeline"])
api_router.include_router(fission.router, prefix="/fission", tags=["fission"])
api_router.include_router(relay.router, tags=["relay"])
api_router.include_router(subtitle.router, tags=["subtitle"])
api_router.include_router(ai_video.router, prefix="/ai-video", tags=["ai-video"])
api_router.include_router(tts.router, prefix="/tts", tags=["tts"])
