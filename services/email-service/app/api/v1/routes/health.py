"""
Health check endpoint for monitoring service status.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import aio_pika

from app.schemas.common import HealthCheckResponse, APIResponse
from app.config import settings
from app.db.session import get_db
from app.utils.cache import cache
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get("/health", response_model=APIResponse[HealthCheckResponse])
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Health check endpoint.
    
    Checks connectivity to:
    - Database (PostgreSQL)
    - Message Queue (RabbitMQ)
    - Cache (Redis)
    """
    health_status = {
        "status": "healthy",
        "service": settings.SERVICE_NAME,
        "version": "1.0.0",
        "database": "unknown",
        "rabbitmq": "unknown",
        "redis": "unknown"
    }
    
    # Check database
    try:
        result = await db.execute(text("SELECT 1"))
        if result:
            health_status["database"] = "connected"
        else:
            health_status["database"] = "error"
            health_status["status"] = "degraded"
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        health_status["database"] = "disconnected"
        health_status["status"] = "unhealthy"
    
    # Check RabbitMQ
    try:
        connection = await aio_pika.connect_robust(
            settings.RABBITMQ_URL,
            timeout=5
        )
        await connection.close()
        health_status["rabbitmq"] = "connected"
    except Exception as e:
        logger.error(f"RabbitMQ health check failed: {str(e)}")
        health_status["rabbitmq"] = "disconnected"
        health_status["status"] = "unhealthy"
    
    # Check Redis
    try:
        if not cache.redis_client:
            await cache.connect()
        
        if cache.redis_client:
            await cache.redis_client.ping()
            health_status["redis"] = "connected"
        else:
            health_status["redis"] = "disconnected"
            health_status["status"] = "degraded"
    except Exception as e:
        logger.error(f"Redis health check failed: {str(e)}")
        health_status["redis"] = "disconnected"
        health_status["status"] = "degraded"
    
    response_data = HealthCheckResponse(**health_status)
    
    return APIResponse(
        success=health_status["status"] != "unhealthy",
        message=f"Service is {health_status['status']}",
        data=response_data
    )
