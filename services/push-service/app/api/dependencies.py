"""Dependency Injection"""
from functools import lru_cache

from app.providers.fcm import FCMProvider
from app.services.push_service import PushService


@lru_cache()
def get_push_provider():
    """Get push provider instance (singleton)"""
    return FCMProvider()


@lru_cache()
def get_push_service():
    """Get push service instance (singleton)"""
    provider = get_push_provider()
    return PushService(provider)
