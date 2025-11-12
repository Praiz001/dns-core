"""
Configuration management using Pydantic Settings.

Loads configuration from environment variables with validation.
"""

from typing import List, Union
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import PostgresDsn, field_validator


class Settings(BaseSettings):
    """Application settings with environment variable loading."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="allow"
    )
    
    # Application
    ENVIRONMENT: str = "development"
    SERVICE_NAME: str = "email-service"
    LOG_LEVEL: str = "INFO"
    CORS_ORIGINS: Union[List[str], str] = "*"
    PORT: int = 8003
    
    # Database
    DATABASE_URL: PostgresDsn
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_ECHO: bool = False
    
    # Redis
    REDIS_URL: str
    CACHE_TTL: int = 300  # 5 minutes
    
    # RabbitMQ
    RABBITMQ_URL: str
    RABBITMQ_EMAIL_QUEUE: str = "email.queue"
    RABBITMQ_DLQ: str = "failed.email.dlq"
    RABBITMQ_PREFETCH_COUNT: int = 10
    RABBITMQ_RETRY_DELAY: int = 5000  # milliseconds
    
    # External Services
    USER_SERVICE_URL: str
    TEMPLATE_SERVICE_URL: str
    API_GATEWAY_URL: str
    
    # Email Provider
    EMAIL_PROVIDER: str = "smtp"  # smtp or sendgrid
    EMAIL_FROM_ADDRESS: str
    EMAIL_FROM_NAME: str = "Notification System"
    
    # SMTP Configuration
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_USE_TLS: bool = True
    
    # SendGrid Configuration
    SENDGRID_API_KEY: str = ""
    
    # Retry Configuration
    MAX_RETRY_ATTEMPTS: int = 3
    RETRY_MULTIPLIER: int = 2
    RETRY_MIN_WAIT: int = 1  # seconds
    RETRY_MAX_WAIT: int = 10  # seconds
    
    # Circuit Breaker Configuration
    CIRCUIT_BREAKER_FAIL_MAX: int = 5
    CIRCUIT_BREAKER_TIMEOUT: int = 60  # seconds
    
    # HTTP Client Configuration
    HTTP_TIMEOUT: int = 30  # seconds
    HTTP_MAX_RETRIES: int = 3
    
    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v) -> List[str]:
        """Parse CORS origins from comma-separated string."""
        if v is None or v == "":
            return ["*"]
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        if isinstance(v, list):
            return v
        return ["*"]


# Global settings instance
settings = Settings()
