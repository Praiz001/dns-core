"""
Email Service - Main Application Entry Point

This service consumes email notification messages from RabbitMQ,
processes them, and sends emails via configured providers.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import asyncio

from app.config import settings
from app.api.v1.routes import health, webhooks
from app.consumers.email_consumer import start_consumer
from app.utils.logger import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    # Startup
    logger.info("Starting Email Service...")
    
    # Start RabbitMQ consumer in background
    consumer_task = asyncio.create_task(start_consumer())
    
    logger.info("Email Service started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Email Service...")
    consumer_task.cancel()
    try:
        await consumer_task
    except asyncio.CancelledError:
        logger.info("Consumer task cancelled")
    logger.info("Email Service shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="Email Service",
    version="1.0.0",
    description="Microservice for processing and sending email notifications",
    lifespan=lifespan,
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/api/v1", tags=["Health"])
app.include_router(webhooks.router, prefix="/api/v1", tags=["Webhooks"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "email-service",
        "version": "1.0.0",
        "status": "running"
    }
