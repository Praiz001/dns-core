from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.db.session import get_db
from app.utils.redis_client import redis_client
from app.schemas.common import APIResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=APIResponse)
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Health check endpoint
    
    Checks:
    - Service is running
    - Database connection
    - Redis connection (optional)
    """
    
    health_status = {
        "service": "template-service",
        "status": "healthy",
        "database": "unknown",
        "redis": "unknown"
    }
    
    # Check database connection
    try:
        await db.execute(text("SELECT 1"))
        health_status["database"] = "connected"
    except Exception as e:
        health_status["database"] = f"disconnected: {str(e)}"
        health_status["status"] = "unhealthy"
    
    # Check Redis connection
    try:
        if redis_client.redis:
            await redis_client.redis.ping()
            health_status["redis"] = "connected"
        else:
            health_status["redis"] = "not configured"
    except Exception as e:
        health_status["redis"] = f"disconnected: {str(e)}"
        # Redis is optional, so don't mark service as unhealthy
    
    return APIResponse(
        success=health_status["status"] == "healthy",
        data=health_status,
        message=f"Service is {health_status['status']}",
        meta=None
    )