"""Health Check Route"""
from fastapi import APIRouter, status
from datetime import datetime
import aio_pika

from app.config import settings
from app.schemas.push import HealthResponse
from app.utils.database import engine
from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("/health", response_model=HealthResponse, status_code=status.HTTP_200_OK)
async def health_check():
    """Health check endpoint"""
    dependencies = {}
    overall_status = "healthy"
    
    # Check database
    try:
        async with engine.connect() as conn:
            await conn.execute("SELECT 1")
        dependencies["database"] = "healthy"
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        dependencies["database"] = "unhealthy"
        overall_status = "unhealthy"
    
    # Check RabbitMQ
    try:
        connection = await aio_pika.connect_robust(
            settings.RABBITMQ_URL,
            timeout=5
        )
        await connection.close()
        dependencies["rabbitmq"] = "healthy"
    except Exception as e:
        logger.error(f"RabbitMQ health check failed: {str(e)}")
        dependencies["rabbitmq"] = "unhealthy"
        overall_status = "unhealthy"
    
    return HealthResponse(
        service=settings.SERVICE_NAME,
        status=overall_status,
        timestamp=datetime.utcnow(),
        dependencies=dependencies
    )
