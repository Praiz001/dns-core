import logging
import sys
from pythonjsonlogger import jsonlogger
from app.config import settings


def get_logger(name: str) -> logging.Logger:
    """Get configured logger"""
    
    logger = logging.getLogger(name)
    logger.setLevel(settings.log_level)
    
    # Avoid duplicate handlers
    if logger.hasHandlers():
        return logger
    
    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(settings.log_level)
    
    # Use JSON formatter for production
    if settings.environment == "production":
        formatter = jsonlogger.JsonFormatter(
            '%(timestamp)s %(level)s %(name)s %(message)s',
            rename_fields={'levelname': 'level', 'asctime': 'timestamp'}
        )
    else:
        # Use simple formatter for development
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger