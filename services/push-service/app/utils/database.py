from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import AsyncAdaptedQueuePool
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Create async engine
# Session mode maintains persistent connections and supports ALL PostgreSQL features
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    # Use connection pooling since Session Mode supports persistent connections
    poolclass=AsyncAdaptedQueuePool,
    pool_size=5,  # Number of permanent connections to maintain
    max_overflow=10,  # Additional connections when under load
    pool_timeout=30,  # Timeout waiting for connection from pool
    pool_recycle=3600,  # Recycle connections after 1 hour
    pool_pre_ping=True,  # Verify connections before using
    future=True,
    connect_args={
        "server_settings": {
            "application_name": settings.SERVICE_NAME
        },
        # Connection timeout
        "timeout": 10,
        # Command execution timeout
        "command_timeout": 60
    }
)

# Create session maker
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session"""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {str(e)}")
            raise
        finally:
            await session.close()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for FastAPI to get database session"""
    async with get_session() as session:
        yield session


async def init_db():
    """Initialize database tables"""
    from app.models.push_delivery import Base
    
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise