from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List, Union


class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    app_name: str = "template-service"
    app_version: str = "1.0.0"
    environment: str = "development"
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8002
    
    # Database
    database_url: str
    
    # Redis
    redis_url: str
    redis_ttl: int = 3600  # 1 hour cache
    
    # CORS
    cors_origins: Union[List[str], str] = "*"
    
    # Logging
    log_level: str = "INFO"
    
    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v) -> List[str]:
        """Parse CORS origins from comma-separated string or list."""
        if v is None or v == "":
            return ["*"]
        if isinstance(v, str):
            if v == "*":
                return ["*"]
            return [origin.strip() for origin in v.split(",")]
        if isinstance(v, list):
            return v
        return ["*"]
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings() # type: ignore