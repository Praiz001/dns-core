"""
Database session management.

Provides async database session factory and dependency injection.
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from app.config import settings

# Create async engine
if settings.ENVIRONMENT == "test":
    engine = create_async_engine(
        str(settings.DATABASE_URL),
        echo=settings.DB_ECHO,
        poolclass=NullPool,
    )
else:
    engine = create_async_engine(
        str(settings.DATABASE_URL),
        echo=settings.DB_ECHO,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
    )

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Provide an async database session.
    
    Usage:
        async with get_db_session() as session:
            # Use session
            pass
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for FastAPI routes to get database session.
    
    Usage:
        @app.get("/")
        async def route(db: AsyncSession = Depends(get_db)):
            pass
    """
    async with get_db_session() as session:
        yield session
