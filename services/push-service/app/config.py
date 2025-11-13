"""Application Configuration"""
import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Application settings"""
    
    # Service Configuration
    SERVICE_NAME: str = "push-service"
    SERVICE_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Database Configuration
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/push_db"
    
    # RabbitMQ Configuration
    RABBITMQ_URL: str = "amqp://guest:guest@localhost:5672/"
    RABBITMQ_QUEUE: str = "push.queue"
    RABBITMQ_EXCHANGE: str = "notifications.direct"
    RABBITMQ_ROUTING_KEY: str = "push"
    RABBITMQ_DLX_EXCHANGE: str = "notifications.dlx"
    RABBITMQ_DLX_ROUTING_KEY: str = "failed.push"
    RABBITMQ_PREFETCH_COUNT: int = 10
    
    # External Services
    USER_SERVICE_URL: str = "http://localhost:8001"
    TEMPLATE_SERVICE_URL: str = "http://localhost:8002"
    API_GATEWAY_URL: str = "http://localhost:3000"
    
    # Push Provider Configuration 
    GOOGLE_APPLICATION_CREDENTIALS: Optional[str] = None
    FCM_PROJECT_ID: Optional[str] = None
    FCM_V1_API_URL: str = "https://fcm.googleapis.com/v1/projects/{project_id}/messages:send"
    
    # Legacy API (Deprecated - use HTTP v1 instead)
    FCM_SERVER_KEY: Optional[str] = None
    FCM_API_URL: str = "https://fcm.googleapis.com/fcm/send"
    
    # OneSignal Configuration (Alternative)
    ONESIGNAL_APP_ID: Optional[str] = None
    ONESIGNAL_API_KEY: Optional[str] = None
    ONESIGNAL_API_URL: str = "https://onesignal.com/api/v1/notifications"
    
    # Redis Configuration (for caching)
    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_TTL: int = 300  # 5 minutes
    
    # Circuit Breaker Configuration
    CIRCUIT_BREAKER_FAIL_MAX: int = 5
    CIRCUIT_BREAKER_TIMEOUT: int = 60
    
    # Retry Configuration
    MAX_RETRY_ATTEMPTS: int = 3
    RETRY_MIN_WAIT: int = 2
    RETRY_MAX_WAIT: int = 10
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="allow"
    )


settings = Settings()
