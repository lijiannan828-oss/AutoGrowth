"""Database engine and session configuration using Cloud SQL Python Connector."""

import asyncpg
from contextlib import asynccontextmanager
from typing import AsyncIterator

from google.cloud.sql.connector import Connector
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.engine import Engine
from sqlalchemy import event, text

from app.core.config import settings
from app.models import Base

# Initialize Cloud SQL Connector
connector = None
engine: Engine | None = None
SessionLocal: async_sessionmaker | None = None


def init_connector() -> Connector:
    """Initialize Cloud SQL Connector (must be called in the event loop)."""
    global connector
    if connector is None:
        # Use service account credentials if available
        import os
        from pathlib import Path
        
        creds_path = settings.google_application_credentials
        if creds_path and not os.path.isabs(creds_path):
            creds_path = str(Path(__file__).parent.parent.parent / creds_path)
        # Fallback: if env var points to无效路径或未提供，优先使用仓库内本地 credentials（开发环境）
        default_local_creds = Path(__file__).parent.parent.parent / "service-account.json"
        if not creds_path or not os.path.exists(creds_path):
            if default_local_creds.exists():
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(default_local_creds)
        else:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = creds_path
        
        connector = Connector()
    return connector


def get_connector() -> Connector:
    """Get or create Cloud SQL Connector."""
    if connector is None:
        return init_connector()
    return connector


async def get_asyncpg_connection():
    """Get asyncpg connection using Cloud SQL Connector.
    
    This function is called by SQLAlchemy's async_creator, which runs in a greenlet context.
    We need to create a new Connector instance here to ensure it's in the correct event loop.
    """
    if not settings.cloud_sql_connection_name:
        # Fallback to direct connection if connection name not set
        if settings.database_url:
            # Parse database_url and create direct connection
            import re
            from urllib.parse import unquote
            match = re.match(
                r"postgresql\+asyncpg://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)",
                settings.database_url,
            )
            if match:
                user, password, host, port, database = match.groups()
                return await asyncpg.connect(
                    host=host,
                    port=int(port),
                    user=unquote(user),
                    password=unquote(password),
                    database=database,
                )
        raise ValueError("Either CLOUD_SQL_CONNECTION_NAME or DATABASE_URL must be set")

    # Create a new Connector instance in the current greenlet/event loop context
    # This is necessary because SQLAlchemy's greenlet mechanism runs async_creator
    # in a different context, and Connector must be initialized in the same loop
    # where connect_async is called
    import os
    import asyncio
    from pathlib import Path
    
    # Set up credentials if needed
    creds_path = settings.google_application_credentials
    if creds_path and not os.path.isabs(creds_path):
        creds_path = str(Path(__file__).parent.parent.parent / creds_path)
    
    if creds_path and os.path.exists(creds_path):
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = creds_path
    
    # Get the current event loop to ensure Connector is initialized in the same loop
    loop = asyncio.get_event_loop()
    
    # Create connector in the current event loop context
    # Using loop parameter ensures it's bound to the correct loop
    temp_connector = Connector(loop=loop)
    
    # Cloud SQL Connector handles authentication automatically via service account
    # When password is disabled, we can either:
    # 1. Use IAM authentication (requires IAM database user to be created in Cloud SQL)
    # 2. Use traditional user with Cloud SQL Connector's automatic auth (no password needed)
    
    # Try IAM auth first if enabled, otherwise use traditional auth
    db_user = settings.database_user
    use_iam = settings.use_iam_auth
    
    # If IAM auth is enabled, try to use service account email as IAM database user
    if use_iam:
        import json
        creds_path = settings.google_application_credentials
        if creds_path and not os.path.isabs(creds_path):
            creds_path = str(Path(__file__).parent.parent.parent / creds_path)
        
        if creds_path and os.path.exists(creds_path):
            try:
                with open(creds_path, 'r') as f:
                    creds = json.load(f)
                    # For IAM auth, use service account email as database user
                    # Note: Cloud SQL requires username without .gserviceaccount.com suffix
                    # Format: sa-dev@project-id.iam (not sa-dev@project-id.iam.gserviceaccount.com)
                    if 'client_email' in creds:
                        client_email = creds['client_email']
                        # Remove .gserviceaccount.com suffix if present
                        if client_email.endswith('.gserviceaccount.com'):
                            db_user = client_email[:-len('.gserviceaccount.com')]
                        else:
                            db_user = client_email
            except Exception:
                pass  # Fall back to configured user
    
    # Build connection parameters
    conn_params = {
        "user": db_user,
        "db": settings.database_name,
        "enable_iam_auth": use_iam,
    }
    
    # If password is provided and not using IAM auth, add password
    if settings.database_password and not use_iam:
        conn_params["password"] = settings.database_password
    
    return await temp_connector.connect_async(
        settings.cloud_sql_connection_name,
        "asyncpg",
        **conn_params
    )


async def create_engine_with_connector():
    """Create SQLAlchemy engine using Cloud SQL Connector."""
    global engine, SessionLocal

    if engine is not None:
        return engine

    if settings.cloud_sql_connection_name:
        # Initialize connector in the current event loop
        init_connector()
        
        # Use Cloud SQL Connector with asyncpg
        # Reference: https://cloud.google.com/sql/docs/postgres/connect-connectors#python
        from sqlalchemy.ext.asyncio import create_async_engine
        from sqlalchemy.pool import NullPool

        # SQLAlchemy asyncpg driver supports passing an async connection function
        # We'll use the async_creator parameter (available in SQLAlchemy 2.0+)
        engine = create_async_engine(
            "postgresql+asyncpg://",
            echo=False,
            poolclass=NullPool,  # Cloud SQL Connector handles pooling
            connect_args={
                "prepared_statement_cache_size": 0,
                "server_settings": {
                    "application_name": "autogrowth_backend",
                },
            },
            # Use async_creator for async connection creation
            async_creator=get_asyncpg_connection,
        )
    elif settings.database_url:
        # Fallback to direct connection
        from sqlalchemy.ext.asyncio import create_async_engine

        engine = create_async_engine(
            settings.database_url, echo=False, pool_pre_ping=True
        )
    else:
        raise ValueError(
            "Either CLOUD_SQL_CONNECTION_NAME or DATABASE_URL must be set"
        )

    SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    return engine


@asynccontextmanager
async def get_session() -> AsyncIterator[AsyncSession]:
    """Get database session."""
    if SessionLocal is None:
        await create_engine_with_connector()
    session = SessionLocal()
    try:
        yield session
    finally:
        await session.close()


async def init_db() -> None:
    """Create database tables if they do not exist."""
    if engine is None:
        await create_engine_with_connector()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_connector() -> None:
    """Close Cloud SQL Connector."""
    global connector, engine
    if engine:
        await engine.dispose()
        engine = None
    if connector:
        await connector.close_async()
        connector = None


__all__ = [
    "engine",
    "SessionLocal",
    "get_session",
    "init_db",
    "create_engine_with_connector",
    "close_connector",
]
