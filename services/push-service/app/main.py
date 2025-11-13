"""Push Service Main Application"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import asyncio

from app.config import settings
from app.api.v1.routes import health, push
from app.consumers.push_consumer import start_consumer
from app.utils.logger import get_logger
from app.utils.database import init_db

logger = get_logger(__name__)

# Create FastAPI application
app = FastAPI(
    title="Push Notification Service",
    version=settings.SERVICE_VERSION,
    description="Microservice for sending push notifications via FCM/OneSignal"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/api/v1", tags=["Health"])
app.include_router(push.router, prefix="/api/v1/push", tags=["Push Notifications"])


@app.on_event("startup")
async def startup_event():
    """Initialize on startup"""
    logger.info(f"Starting {settings.SERVICE_NAME} v{settings.SERVICE_VERSION}")
    
    # Initialize database
    try:
        await init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
    
    # Start RabbitMQ consumer
    logger.info("Starting RabbitMQ consumer...")
    asyncio.create_task(start_consumer())


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down push service...")


@app.get("/")
def root():
    """Root endpoint"""
    return {
        "service": settings.SERVICE_NAME,
        "version": settings.SERVICE_VERSION,
        "status": "running"
    }
