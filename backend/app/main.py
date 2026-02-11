"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import create_engine_with_connector, close_connector, init_db
from app.core.firestore import close_firestore, init_firestore
from app.core.scheduler import start_scheduler, shutdown_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup: Initialize database connection
    try:
        await create_engine_with_connector()
        await init_db()
        print("[OK] Database connection initialized")
    except Exception as e:
        print(f"[WARN] Database connection failed (will use Google Sheets only): {e}")
    
    # Startup: Start scheduler
    try:
        await start_scheduler()
        print("[OK] Scheduler started")
    except Exception as e:
        print(f"[WARN] Scheduler failed to start: {e}")
    
    # Startup: Initialize Firestore client (optional)
    try:
        init_firestore()
    except Exception as e:
        print(f"[WARN] Firestore initialization error: {e}")

    yield
    
    # Shutdown: Stop scheduler
    try:
        await shutdown_scheduler()
        print("[OK] Scheduler stopped")
    except Exception as e:
        print(f"[WARN] Error stopping scheduler: {e}")
    
    # Shutdown: Close database connection
    try:
        await close_connector()
        print("[OK] Database connection closed")
    except Exception as e:
        print(f"[WARN] Error closing database connection: {e}")

    # Shutdown: Close Firestore client
    try:
        close_firestore()
    except Exception as e:
        print(f"[WARN] Error closing Firestore client: {e}")


def create_application() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
        version="0.1.0",
        lifespan=lifespan,
    )

    # Determine allowed origins for CORS
    allowed_origins = settings.frontend_origins or ["*"]
    allow_credentials = False if allowed_origins == ["*"] else True

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=allow_credentials,
    )

    app.include_router(api_router, prefix="/api/v1")

    return app


app = create_application()


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
