"""
Database connection management.
Provides async PostgreSQL connection with SQLAlchemy 2.0.
"""
import asyncio
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from config import settings


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


# Create async engine
engine: AsyncEngine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    poolclass=NullPool if settings.environment == "test" else None,
    pool_size=10 if settings.environment != "test" else None,
    max_overflow=20 if settings.environment != "test" else None,
)

# Create async session maker
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting async database session.
    
    Usage:
        async with get_async_session() as session:
            ...
    
    Or as FastAPI dependency:
        session: AsyncSession = Depends(get_async_session)
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def sync_enums() -> None:
    """
    Sync PostgreSQL enum types with Python enum definitions.
    Adds any missing values to existing enum types.
    This handles the case where Python enums were extended
    but no DB migration was run.
    """
    from sqlalchemy import text
    
    # Map of PostgreSQL enum type name -> list of required values
    enum_sync_map = {
        'requesttype': [
            'text', 'image', 'video', 'voice', 'document',
            'presentation', 'video_animate', 'long_video',
        ],
    }
    
    async with engine.begin() as conn:
        for type_name, required_values in enum_sync_map.items():
            # Check if enum type exists
            result = await conn.execute(text(
                "SELECT enumlabel FROM pg_enum "
                "JOIN pg_type ON pg_enum.enumtypid = pg_type.oid "
                "WHERE pg_type.typname = :type_name "
                "ORDER BY pg_enum.enumsortorder"
            ), {"type_name": type_name})
            current_values = {row[0] for row in result}
            
            if not current_values:
                continue  # Enum doesn't exist yet, create_all will handle it
            
            for value in required_values:
                if value not in current_values:
                    await conn.execute(text(
                        f"ALTER TYPE {type_name} ADD VALUE IF NOT EXISTS '{value}'"
                    ))


async def init_db() -> None:
    """
    Initialize database - create all tables and sync enum types.
    Should be called on application startup.
    """
    # Sync enum values before create_all (so new values are available)
    try:
        await sync_enums()
    except Exception:
        pass  # Enum type may not exist yet on first run
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """
    Close database connections.
    Should be called on application shutdown.
    """
    await engine.dispose()
